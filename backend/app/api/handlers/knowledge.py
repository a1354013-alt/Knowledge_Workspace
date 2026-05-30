from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from app.api.common import (
    KNOWLEDGE_REVISION_FIELDS,
    item_id_from_parts,
    knowledge_revision_snapshot,
    list_visible_related_item_ids_for_user,
    maybe_link_source_item,
    run_index_side_effect,
    serialize_knowledge_revision,
    side_effect_warning,
    sync_source_ref_link,
    validate_related_item_ids_for_user,
    validate_source_ref_for_user,
)
from app.context import db
from app.dependencies import get_current_user
from app.models import (
    KnowledgeEntryCreateRequest,
    KnowledgeEntryResponse,
    KnowledgeEntryUpdateRequest,
    KnowledgeRevisionDiffResponse,
    KnowledgeRevisionResponse,
    MessageResponse,
)
from app.services.indexing_service import sync_knowledge_entry_index


async def list_knowledge_entries(current_user: dict = Depends(get_current_user)) -> list[KnowledgeEntryResponse]:
    user_id = current_user["sub"]
    return [
        KnowledgeEntryResponse(
            id=row["entry_id"],
            title=row.get("title", ""),
            status=row.get("status", "draft") or "draft",
            problem=row.get("problem", ""),
            root_cause=row.get("root_cause", ""),
            solution=row.get("solution", ""),
            tags=row.get("tags", ""),
            notes=row.get("notes", ""),
            source_type=row.get("source_type", "manual") or "manual",
            source_ref=row.get("source_ref", "") or "",
            related_item_ids=list_visible_related_item_ids_for_user(
                item_id=item_id_from_parts("knowledge", row["entry_id"]),
                user_id=user_id,
            ),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
        for row in db.list_knowledge_entries(limit=50, user_id=user_id, include_archived=False)
    ]


async def create_knowledge_entry(
    request: KnowledgeEntryCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    user_id = current_user["sub"]
    entry_id = str(uuid.uuid4())
    related_item_ids = validate_related_item_ids_for_user(item_ids=request.related_item_ids, user_id=user_id)
    source_ref = validate_source_ref_for_user(source_ref=request.source_ref, user_id=user_id)

    created = db.add_knowledge_entry(
        entry_id=entry_id,
        title=request.title,
        status=request.status,
        problem=request.problem,
        root_cause=request.root_cause,
        solution=request.solution,
        tags=request.tags,
        notes=request.notes,
        created_by=user_id,
        source_type=request.source_type,
        source_ref=source_ref,
    )
    if not created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create knowledge entry."
        )

    entry = db.get_knowledge_entry(entry_id)
    if entry:
        db.add_knowledge_revision(
            entry_id=entry_id,
            snapshot=knowledge_revision_snapshot(entry),
            change_note="Initial version",
            created_by=user_id,
        )
        db.set_reference_links(item_id_from_parts("knowledge", entry_id), related_item_ids)
        maybe_link_source_item(
            from_item_id=item_id_from_parts("knowledge", entry_id),
            source_type=request.source_type,
            source_ref=source_ref,
            user_id=user_id,
        )
        warning = run_index_side_effect(
            label="Knowledge entry",
            item_id=entry_id,
            operation=lambda: sync_knowledge_entry_index(entry),
            on_error=lambda index_status, detail: db.update_knowledge_entry(
                entry_id, index_status=index_status, index_error=detail, indexed_at=""
            ),
        )
        if warning:
            db.queue_index_repair(
                item_id=item_id_from_parts("knowledge", entry_id),
                item_type="knowledge",
                action="index",
                owner_user_id=str(user_id),
                last_error=warning,
            )
        else:
            db.resolve_index_repair(
                item_id=item_id_from_parts("knowledge", entry_id),
                action="index",
                owner_user_id=str(user_id),
            )
    else:
        warning = None
    return MessageResponse(message=side_effect_warning("Knowledge entry created.", warning))


async def update_knowledge_entry(
    entry_id: str,
    request: KnowledgeEntryUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    user_id = current_user["sub"]
    existing = db.get_knowledge_entry(entry_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found.")
    if existing.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit this knowledge entry.")

    updates = request.model_dump(exclude_none=True)
    related = updates.pop("related_item_ids", None)
    change_note = str(updates.pop("change_note", "") or "").strip()
    if not updates and related is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No knowledge fields provided.")

    if related is not None:
        related = validate_related_item_ids_for_user(item_ids=related, user_id=user_id)
    if "source_ref" in updates:
        updates["source_ref"] = validate_source_ref_for_user(source_ref=updates["source_ref"], user_id=user_id)

    if updates:
        db.add_knowledge_revision(
            entry_id=entry_id,
            snapshot=knowledge_revision_snapshot(existing),
            change_note=change_note or "Updated knowledge entry",
            created_by=user_id,
        )
    if updates and not db.update_knowledge_entry(entry_id, **updates):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update knowledge entry."
        )
    if related is not None:
        db.set_reference_links(item_id_from_parts("knowledge", entry_id), related)
    if "source_type" in updates or "source_ref" in updates:
        source_type = updates.get("source_type", existing.get("source_type", "manual"))
        source_ref = updates.get("source_ref", existing.get("source_ref", ""))
        sync_source_ref_link(
            from_item_id=item_id_from_parts("knowledge", entry_id),
            old_source_ref=str(existing.get("source_ref", "")),
            new_source_ref=str(source_ref),
            source_type=str(source_type),
            user_id=user_id,
        )

    updated = db.get_knowledge_entry(entry_id) or existing
    warning = run_index_side_effect(
        label="Knowledge entry",
        item_id=entry_id,
        operation=lambda: sync_knowledge_entry_index(updated),
        on_error=lambda index_status, detail: db.update_knowledge_entry(
            entry_id, index_status=index_status, index_error=detail, indexed_at=""
        ),
    )
    if warning:
        db.queue_index_repair(
            item_id=item_id_from_parts("knowledge", entry_id),
            item_type="knowledge",
            action="index",
            owner_user_id=str(user_id),
            last_error=warning,
        )
    else:
        db.resolve_index_repair(
            item_id=item_id_from_parts("knowledge", entry_id),
            action="index",
            owner_user_id=str(user_id),
        )
    return MessageResponse(message=side_effect_warning("Knowledge entry updated.", warning))


async def list_knowledge_revisions(
    entry_id: str, current_user: dict = Depends(get_current_user)
) -> list[KnowledgeRevisionResponse]:
    entry = db.get_knowledge_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found.")
    if entry.get("created_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access these revisions.")
    return [
        serialize_knowledge_revision(row)
        for row in db.list_knowledge_revisions(entry_id, created_by=current_user["sub"])
    ]


async def get_knowledge_revision_diff(
    entry_id: str,
    revision_id: str,
    current_user: dict = Depends(get_current_user),
) -> KnowledgeRevisionDiffResponse:
    entry = db.get_knowledge_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found.")
    revision = db.get_knowledge_revision(revision_id, entry_id=entry_id, created_by=current_user["sub"])
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge revision not found.")

    changed = []
    for field in KNOWLEDGE_REVISION_FIELDS:
        old_value = str(revision.get(field, "") or "")
        new_value = str(entry.get(field, "") or "")
        if old_value != new_value:
            changed.append({"field": field, "old_value": old_value, "new_value": new_value})
    return KnowledgeRevisionDiffResponse(revision_id=revision_id, entry_id=entry_id, changed=changed)


async def restore_knowledge_revision(
    entry_id: str,
    revision_id: str,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    user_id = current_user["sub"]
    entry = db.get_knowledge_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found.")
    if entry.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot restore this knowledge entry.")

    revision = db.get_knowledge_revision(revision_id, entry_id=entry_id, created_by=user_id)
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge revision not found.")

    db.add_knowledge_revision(
        entry_id=entry_id,
        snapshot=knowledge_revision_snapshot(entry),
        change_note=f"Pre-restore snapshot before restoring revision {revision.get('version_number', '')}",
        created_by=user_id,
    )

    restore_payload = {field: revision.get(field, entry.get(field, "")) for field in KNOWLEDGE_REVISION_FIELDS}
    if not db.update_knowledge_entry(entry_id, **restore_payload):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore knowledge revision."
        )

    sync_source_ref_link(
        from_item_id=item_id_from_parts("knowledge", entry_id),
        old_source_ref=str(entry.get("source_ref", "")),
        new_source_ref=str(restore_payload.get("source_ref", entry.get("source_ref", ""))),
        source_type=str(restore_payload.get("source_type", entry.get("source_type", "manual"))),
        user_id=user_id,
    )

    restored = db.get_knowledge_entry(entry_id) or entry
    warning = run_index_side_effect(
        label="Knowledge entry",
        item_id=entry_id,
        operation=lambda: sync_knowledge_entry_index(restored),
        on_error=lambda index_status, detail: db.update_knowledge_entry(
            entry_id, index_status=index_status, index_error=detail, indexed_at=""
        ),
    )
    if warning:
        db.queue_index_repair(
            item_id=item_id_from_parts("knowledge", entry_id),
            item_type="knowledge",
            action="index",
            owner_user_id=str(user_id),
            last_error=warning,
        )
    else:
        db.resolve_index_repair(
            item_id=item_id_from_parts("knowledge", entry_id),
            action="index",
            owner_user_id=str(user_id),
        )
    return MessageResponse(message=side_effect_warning("Knowledge revision restored.", warning))
