from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status

from app.api.common import (
    item_id_from_parts,
    list_visible_related_item_ids_for_user,
    maybe_link_source_item,
    run_deindex_side_effect,
    run_index_side_effect,
    side_effect_warning,
    sync_source_ref_link,
    utc_now_iso,
    validate_related_item_ids_for_user,
    validate_source_ref_for_user,
)
from app.context import db
from app.database import delete_from_kb_vector_db
from app.dependencies import get_current_user
from app.models import (
    LogbookEntryCreateRequest,
    LogbookEntryPageResponse,
    LogbookEntryResponse,
    LogbookEntryUpdateRequest,
    MessageResponse,
    PromoteToKnowledgeResponse,
)
from app.services.indexing_service import sync_knowledge_entry_index, sync_logbook_entry_index


def serialize_logbook_entry(row: dict, *, user_id: str) -> LogbookEntryResponse:
    return LogbookEntryResponse(
        id=row["entry_id"],
        title=row.get("title", ""),
        status=row.get("status", "draft") or "draft",
        run_id=row.get("run_id", "") or "",
        problem=row.get("problem", ""),
        root_cause=row.get("root_cause", ""),
        solution=row.get("solution", ""),
        tags=row.get("tags", ""),
        source_type=row.get("source_type", "manual") or "manual",
        source_ref=row.get("source_ref", "") or "",
        related_item_ids=list_visible_related_item_ids_for_user(
            item_id=item_id_from_parts("logbook", row["entry_id"]),
            user_id=user_id,
        ),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )


async def list_logbook_entries(
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: dict = Depends(get_current_user),
) -> LogbookEntryPageResponse:
    user_id = current_user["sub"]
    rows = db.list_logbook_entries(limit=limit, offset=offset, user_id=user_id, include_archived=False)
    total = db.count_logbook_entries(user_id=user_id, include_archived=False)
    return LogbookEntryPageResponse(
        items=[serialize_logbook_entry(row, user_id=user_id) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(rows) < total,
    )


async def create_logbook_entry(
    request: LogbookEntryCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    user_id = current_user["sub"]
    entry_id = str(uuid.uuid4())
    related_item_ids = validate_related_item_ids_for_user(item_ids=request.related_item_ids, user_id=user_id)
    source_ref = validate_source_ref_for_user(source_ref=request.source_ref, user_id=user_id)

    created = db.add_logbook_entry(
        entry_id=entry_id,
        title=request.title,
        status=request.status,
        run_id="",
        problem=request.problem,
        root_cause=request.root_cause,
        solution=request.solution,
        tags=request.tags,
        source_type=request.source_type,
        source_ref=source_ref,
        created_by=user_id,
    )
    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create logbook entry.")

    entry = db.get_logbook_entry(entry_id)
    if entry:
        db.set_reference_links(item_id_from_parts("logbook", entry_id), related_item_ids)
        maybe_link_source_item(
            from_item_id=item_id_from_parts("logbook", entry_id),
            source_type=request.source_type,
            source_ref=source_ref,
            user_id=user_id,
        )
        warning = run_index_side_effect(
            label="Logbook entry",
            item_id=entry_id,
            operation=lambda: sync_logbook_entry_index(entry),
            on_error=lambda index_status, detail: db.update_logbook_entry(
                entry_id, index_status=index_status, index_error=detail, indexed_at=""
            ),
        )
        if warning:
            db.queue_index_repair(
                item_id=item_id_from_parts("logbook", entry_id),
                item_type="logbook",
                action="index",
                owner_user_id=str(user_id),
                last_error=warning,
            )
        else:
            db.resolve_index_repair(
                item_id=item_id_from_parts("logbook", entry_id),
                action="index",
                owner_user_id=str(user_id),
            )
    else:
        warning = None
    return MessageResponse(message=side_effect_warning("Logbook entry created.", warning))


async def update_logbook_entry(
    entry_id: str,
    request: LogbookEntryUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    user_id = current_user["sub"]
    existing = db.get_logbook_entry(entry_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    if existing.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit this logbook entry.")

    updates = request.model_dump(exclude_none=True)
    related = updates.pop("related_item_ids", None)
    if not updates and related is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No logbook fields provided.")

    if related is not None:
        related = validate_related_item_ids_for_user(item_ids=related, user_id=user_id)
    if "source_ref" in updates:
        updates["source_ref"] = validate_source_ref_for_user(source_ref=updates["source_ref"], user_id=user_id)

    if updates and not db.update_logbook_entry(entry_id, **updates):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update logbook entry.")
    if related is not None:
        db.set_reference_links(item_id_from_parts("logbook", entry_id), related)
    if "source_type" in updates or "source_ref" in updates:
        source_type = updates.get("source_type", existing.get("source_type", "manual"))
        source_ref = updates.get("source_ref", existing.get("source_ref", ""))
        sync_source_ref_link(
            from_item_id=item_id_from_parts("logbook", entry_id),
            old_source_ref=str(existing.get("source_ref", "")),
            new_source_ref=str(source_ref),
            source_type=str(source_type),
            user_id=user_id,
        )

    updated = db.get_logbook_entry(entry_id) or existing
    warning = run_index_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: sync_logbook_entry_index(updated),
        on_error=lambda index_status, detail: db.update_logbook_entry(
            entry_id, index_status=index_status, index_error=detail, indexed_at=""
        ),
    )
    if warning:
        db.queue_index_repair(
            item_id=item_id_from_parts("logbook", entry_id),
            item_type="logbook",
            action="index",
            owner_user_id=str(user_id),
            last_error=warning,
        )
    else:
        db.resolve_index_repair(
            item_id=item_id_from_parts("logbook", entry_id),
            action="index",
            owner_user_id=str(user_id),
        )
    return MessageResponse(message=side_effect_warning("Logbook entry updated.", warning))


async def promote_logbook_to_knowledge(
    entry_id: str, current_user: dict = Depends(get_current_user)
) -> PromoteToKnowledgeResponse:
    user_id = current_user["sub"]
    logbook = db.get_logbook_entry(entry_id)
    if not logbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    if logbook.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot promote this logbook entry.")

    knowledge_id = str(uuid.uuid4())
    related_item_ids = list_visible_related_item_ids_for_user(item_id=f"logbook:{entry_id}", user_id=user_id)
    with db.transaction() as conn:
        now = utc_now_iso()
        conn.execute(
            """
            INSERT INTO knowledge_entries
            (entry_id, title, status, problem, root_cause, solution, tags, notes, source_type, source_ref, created_by, is_active, index_status, index_error, indexed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                knowledge_id,
                str(logbook.get("title") or "").strip() or "Troubleshooting: verified fix",
                "verified",
                str(logbook.get("problem") or ""),
                str(logbook.get("root_cause") or ""),
                str(logbook.get("solution") or ""),
                str(logbook.get("tags") or ""),
                f"promoted_from=logbook:{entry_id}",
                str(logbook.get("source_type") or "manual"),
                str(logbook.get("source_ref") or ""),
                user_id,
                1,
                "pending",
                "",
                "",
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO item_links (link_id, from_item_id, to_item_id, link_type, created_at)
            VALUES (lower(hex(randomblob(16))), ?, ?, 'produced', ?)
            """,
            (f"logbook:{entry_id}", f"knowledge:{knowledge_id}", now),
        )
        for related in related_item_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO item_links (link_id, from_item_id, to_item_id, link_type, created_at)
                VALUES (lower(hex(randomblob(16))), ?, ?, 'references', ?)
                """,
                (f"knowledge:{knowledge_id}", related, now),
            )
        archived = conn.execute(
            """
            UPDATE logbook_entries
            SET status = 'archived',
                is_active = 0,
                index_status = 'excluded',
                index_error = '',
                indexed_at = '',
                updated_at = ?
            WHERE entry_id = ? AND created_by = ?
            """,
            (now, entry_id, user_id),
        )
        if int(archived.rowcount or 0) == 0:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to promote to knowledge.")
        run_id = str(logbook.get("run_id") or "").strip()
        if run_id:
            conn.execute(
                "UPDATE autotest_runs SET solution_entry_id = ?, updated_at = ? WHERE run_id = ? AND created_by = ?",
                (knowledge_id, now, run_id, user_id),
            )

    warnings: list[str] = []
    logbook_warning = run_deindex_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: delete_from_kb_vector_db(f"logbook:{entry_id}"),
    )
    if logbook_warning:
        db.queue_index_repair(
            item_id=f"logbook:{entry_id}",
            item_type="logbook",
            action="deindex",
            owner_user_id=str(user_id),
            last_error=logbook_warning,
        )
        warnings.append(logbook_warning)
    else:
        db.resolve_index_repair(item_id=f"logbook:{entry_id}", action="deindex", owner_user_id=str(user_id))

    promoted = db.get_knowledge_entry(knowledge_id)
    if promoted:
        knowledge_warning = run_index_side_effect(
            label="Knowledge entry",
            item_id=knowledge_id,
            operation=lambda: sync_knowledge_entry_index(promoted),
            on_error=lambda index_status, detail: db.update_knowledge_entry(
                knowledge_id, index_status=index_status, index_error=detail, indexed_at=""
            ),
        )
        if knowledge_warning:
            warnings.append(knowledge_warning)
            db.queue_index_repair(
                item_id=f"knowledge:{knowledge_id}",
                item_type="knowledge",
                action="index",
                owner_user_id=str(user_id),
                last_error=knowledge_warning,
            )
        else:
            db.resolve_index_repair(item_id=f"knowledge:{knowledge_id}", action="index", owner_user_id=str(user_id))

    archived_logbook = db.get_logbook_entry(entry_id) or logbook
    archived_warning = run_index_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: sync_logbook_entry_index(archived_logbook),
        on_error=lambda index_status, detail: db.update_logbook_entry(
            entry_id, index_status=index_status, index_error=detail, indexed_at=""
        ),
    )
    if archived_warning:
        warnings.append(archived_warning)
        db.queue_index_repair(
            item_id=f"logbook:{entry_id}",
            item_type="logbook",
            action="index",
            owner_user_id=str(user_id),
            last_error=archived_warning,
        )
    else:
        db.resolve_index_repair(item_id=f"logbook:{entry_id}", action="index", owner_user_id=str(user_id))

    return PromoteToKnowledgeResponse(
        message=side_effect_warning("Promoted to verified knowledge entry.", " ".join(warnings)),
        knowledge_entry_id=knowledge_id,
    )


async def delete_logbook_entry(entry_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    user_id = current_user["sub"]
    existing = db.get_logbook_entry(entry_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    if existing.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this logbook entry.")
    item_id = f"logbook:{entry_id}"
    warning = run_deindex_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: delete_from_kb_vector_db(item_id),
    )
    if warning:
        db.queue_index_repair(
            item_id=item_id,
            item_type="logbook",
            action="deindex",
            owner_user_id=str(user_id),
            last_error=warning,
        )
    else:
        db.resolve_index_repair(item_id=item_id, action="deindex", owner_user_id=str(user_id))
    db.delete_search_content(item_id)
    db.delete_links(from_item_id=item_id)
    db.delete_links(to_item_id=item_id)
    if not db.delete_logbook_entry(entry_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    return MessageResponse(message=side_effect_warning("Logbook entry deleted.", warning))
