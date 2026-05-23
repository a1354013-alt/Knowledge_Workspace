from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from app.api.common import (
    item_id_from_parts,
    list_visible_related_item_ids_for_user,
    maybe_link_source_item,
    run_deindex_side_effect,
    run_index_side_effect,
    side_effect_warning,
    sync_source_ref_link,
    validate_related_item_ids_for_user,
    validate_source_ref_for_user,
)
from app.context import db
from app.database import delete_from_kb_vector_db
from app.dependencies import get_current_user
from app.kb_index import index_knowledge_entry, index_logbook_entry
from app.models import (
    LogbookEntryCreateRequest,
    LogbookEntryResponse,
    LogbookEntryUpdateRequest,
    MessageResponse,
    PromoteToKnowledgeResponse,
)


async def list_logbook_entries(current_user: dict = Depends(get_current_user)) -> list[LogbookEntryResponse]:
    user_id = current_user["sub"]
    return [
        LogbookEntryResponse(
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
        for row in db.list_logbook_entries(limit=100, user_id=user_id, include_archived=False)
    ]


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
            operation=lambda: index_logbook_entry(entry),
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
        operation=lambda: index_logbook_entry(updated),
    )
    return MessageResponse(message=side_effect_warning("Logbook entry updated.", warning))


async def promote_logbook_to_knowledge(entry_id: str, current_user: dict = Depends(get_current_user)) -> PromoteToKnowledgeResponse:
    user_id = current_user["sub"]
    logbook = db.get_logbook_entry(entry_id)
    if not logbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    if logbook.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot promote this logbook entry.")

    knowledge_id = str(uuid.uuid4())
    ok = db.add_knowledge_entry(
        entry_id=knowledge_id,
        title=str(logbook.get("title") or "").strip() or "Troubleshooting: verified fix",
        status="verified",
        problem=str(logbook.get("problem") or ""),
        root_cause=str(logbook.get("root_cause") or ""),
        solution=str(logbook.get("solution") or ""),
        tags=str(logbook.get("tags") or ""),
        notes=f"promoted_from=logbook:{entry_id}",
        created_by=user_id,
        source_type=str(logbook.get("source_type") or "manual"),
        source_ref=str(logbook.get("source_ref") or ""),
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to promote to knowledge.")

    db.add_link(f"logbook:{entry_id}", f"knowledge:{knowledge_id}", link_type="produced")
    db.add_link(f"knowledge:{knowledge_id}", f"logbook:{entry_id}", link_type="derived_from")
    for related in list_visible_related_item_ids_for_user(item_id=f"logbook:{entry_id}", user_id=user_id):
        db.add_link(f"knowledge:{knowledge_id}", related, link_type="references")

    db.update_logbook_entry(entry_id, status="archived")

    warnings: list[str] = []
    logbook_warning = run_deindex_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: delete_from_kb_vector_db(f"logbook:{entry_id}"),
    )
    if logbook_warning:
        warnings.append(logbook_warning)

    promoted = db.get_knowledge_entry(knowledge_id)
    if promoted:
        knowledge_warning = run_index_side_effect(
            label="Knowledge entry",
            item_id=knowledge_id,
            operation=lambda: index_knowledge_entry(promoted),
        )
        if knowledge_warning:
            warnings.append(knowledge_warning)

    archived_logbook = db.get_logbook_entry(entry_id) or logbook
    archived_warning = run_index_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: index_logbook_entry(archived_logbook),
    )
    if archived_warning:
        warnings.append(archived_warning)

    run_id = str(logbook.get("run_id") or "").strip()
    if run_id:
        db.update_autotest_run(run_id, solution_entry_id=knowledge_id)

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
    db.delete_links(from_item_id=item_id)
    db.delete_links(to_item_id=item_id)
    if not db.delete_logbook_entry(entry_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    return MessageResponse(message=side_effect_warning("Logbook entry deleted.", warning))
