from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, HTTPException, status

from app.api.common import (
    item_id_from_parts,
    parse_item_id,
    resolve_item_summary,
    run_index_side_effect,
    side_effect_warning,
    utc_now_iso,
    validate_related_item_ids_for_user,
    validate_source_ref_for_user,
)
from app.api.runtime import db
from app.dependencies import get_current_user
from app.models import (
    BulkImportResult,
    ImportErrorDetail,
    KnowledgeBulkImportRequest,
    KnowledgeEntryCreateRequest,
    LogbookBulkImportRequest,
    LogbookEntryCreateRequest,
    PromptBulkImportRequest,
    SavedPromptCreateRequest,
)
from app.services.indexing_service import sync_knowledge_entry_index, sync_logbook_entry_index, sync_prompt_index


def _duplicate_errors(rows: list[tuple[int, tuple[str, ...]]]) -> list[ImportErrorDetail]:
    seen: dict[tuple[str, ...], int] = {}
    errors: list[ImportErrorDetail] = []
    for row_number, key in rows:
        if key in seen:
            errors.append(
                ImportErrorDetail(
                    row=row_number,
                    field="-",
                    reason=f"Duplicate import row. First occurrence is row {seen[key]}.",
                )
            )
            continue
        seen[key] = row_number
    return errors


def _fail_validation(errors: list[ImportErrorDetail]) -> None:
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[error.model_dump() for error in errors],
        )


def _knowledge_key(values: KnowledgeEntryCreateRequest) -> tuple[str, ...]:
    return (
        values.title.strip().lower(),
        values.problem.strip().lower(),
        values.solution.strip().lower(),
    )


def _logbook_key(values: LogbookEntryCreateRequest) -> tuple[str, ...]:
    return (
        values.title.strip().lower(),
        values.problem.strip().lower(),
        values.solution.strip().lower(),
    )


def _prompt_key(values: SavedPromptCreateRequest) -> tuple[str, ...]:
    return (values.title.strip().lower(), values.content.strip().lower())


def _insert_knowledge(conn: Any, *, entry_id: str, values: KnowledgeEntryCreateRequest, user_id: str) -> None:
    now = utc_now_iso()
    conn.execute(
        """
        INSERT INTO knowledge_entries
        (entry_id, title, status, problem, root_cause, solution, tags, notes, source_type, source_ref, created_by, is_active, index_status, index_error, indexed_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', '', '', ?, ?)
        """,
        (
            entry_id,
            values.title,
            values.status,
            values.problem,
            values.root_cause,
            values.solution,
            values.tags,
            values.notes,
            values.source_type,
            values.source_ref,
            user_id,
            0 if values.status == "archived" else 1,
            now,
            now,
        ),
    )
    conn.execute(
        """
        INSERT INTO knowledge_revisions
        (revision_id, entry_id, version_number, title, status, problem, root_cause, solution, tags, notes, source_type, source_ref, change_note, created_by, created_at)
        VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Initial import version', ?, ?)
        """,
        (
            str(uuid.uuid4()),
            entry_id,
            values.title,
            values.status,
            values.problem,
            values.root_cause,
            values.solution,
            values.tags,
            values.notes,
            values.source_type,
            values.source_ref,
            user_id,
            now,
        ),
    )
    item_id = item_id_from_parts("knowledge", entry_id)
    for related in values.related_item_ids:
        conn.execute(
            """
            INSERT OR IGNORE INTO item_links (link_id, from_item_id, to_item_id, link_type, created_at)
            VALUES (lower(hex(randomblob(16))), ?, ?, 'references', ?)
            """,
            (item_id, related, now),
        )
    _insert_source_link(conn, from_item_id=item_id, source_type=values.source_type, source_ref=values.source_ref, user_id=user_id, now=now)


def _insert_logbook(conn: Any, *, entry_id: str, values: LogbookEntryCreateRequest, user_id: str) -> None:
    now = utc_now_iso()
    conn.execute(
        """
        INSERT INTO logbook_entries
        (entry_id, title, status, run_id, problem, root_cause, solution, tags, source_type, source_ref, created_by, is_active, index_status, index_error, indexed_at, created_at, updated_at)
        VALUES (?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, 'pending', '', '', ?, ?)
        """,
        (
            entry_id,
            values.title,
            values.status,
            values.problem,
            values.root_cause,
            values.solution,
            values.tags,
            values.source_type,
            values.source_ref,
            user_id,
            0 if values.status == "archived" else 1,
            now,
            now,
        ),
    )
    item_id = item_id_from_parts("logbook", entry_id)
    for related in values.related_item_ids:
        conn.execute(
            """
            INSERT OR IGNORE INTO item_links (link_id, from_item_id, to_item_id, link_type, created_at)
            VALUES (lower(hex(randomblob(16))), ?, ?, 'references', ?)
            """,
            (item_id, related, now),
        )
    _insert_source_link(conn, from_item_id=item_id, source_type=values.source_type, source_ref=values.source_ref, user_id=user_id, now=now)


def _insert_prompt(conn: Any, *, prompt_id: str, values: SavedPromptCreateRequest, user_id: str) -> None:
    now = utc_now_iso()
    conn.execute(
        """
        INSERT INTO saved_prompts
        (prompt_id, title, content, tags, created_by, is_active, index_status, index_error, indexed_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, 'pending', '', '', ?, ?)
        """,
        (prompt_id, values.title, values.content, values.tags, user_id, now, now),
    )


def _insert_source_link(
    conn: Any,
    *,
    from_item_id: str,
    source_type: str,
    source_ref: str,
    user_id: str,
    now: str,
) -> None:
    if str(source_type or "").strip() in {"manual", ""}:
        return
    ref = str(source_ref or "").strip()
    try:
        parse_item_id(ref)
    except ValueError:
        return
    if resolve_item_summary(item_id=ref, user_id=user_id) is None:
        return
    conn.execute(
        """
        INSERT OR IGNORE INTO item_links (link_id, from_item_id, to_item_id, link_type, created_at)
        VALUES (lower(hex(randomblob(16))), ?, ?, 'derived_from', ?)
        """,
        (from_item_id, ref, now),
    )


def _index_created_items(kind: str, created_ids: list[str], *, user_id: str) -> list[str]:
    warnings: list[str] = []
    for item_id in created_ids:
        if kind == "knowledge":
            row = db.get_knowledge_entry(item_id)
            if not row:
                continue
            warning = run_index_side_effect(
                label="Knowledge entry",
                item_id=item_id,
                operation=lambda row=row: sync_knowledge_entry_index(row),
                on_error=lambda index_status, detail, item_id=item_id: db.update_knowledge_entry(
                    item_id, index_status=index_status, index_error=detail, indexed_at=""
                ),
            )
        elif kind == "logbook":
            row = db.get_logbook_entry(item_id)
            if not row:
                continue
            warning = run_index_side_effect(
                label="Logbook entry",
                item_id=item_id,
                operation=lambda row=row: sync_logbook_entry_index(row),
                on_error=lambda index_status, detail, item_id=item_id: db.update_logbook_entry(
                    item_id, index_status=index_status, index_error=detail, indexed_at=""
                ),
            )
        else:
            row = db.get_saved_prompt(item_id)
            if not row:
                continue
            warning = run_index_side_effect(
                label="Prompt",
                item_id=item_id,
                operation=lambda row=row: sync_prompt_index(row),
                on_error=lambda index_status, detail, item_id=item_id: db.update_saved_prompt_index(
                    item_id, index_status=index_status, index_error=detail, indexed_at=""
                ),
            )
        queue_item_id = item_id_from_parts("prompt" if kind == "prompt" else kind, item_id)
        if warning:
            warnings.append(warning)
            db.queue_index_repair(
                item_id=queue_item_id,
                item_type="prompt" if kind == "prompt" else kind,
                action="index",
                owner_user_id=str(user_id),
                last_error=warning,
            )
        else:
            db.resolve_index_repair(item_id=queue_item_id, action="index", owner_user_id=str(user_id))
    return warnings


async def import_knowledge_entries(
    request: KnowledgeBulkImportRequest,
    current_user: dict = Depends(get_current_user),
) -> BulkImportResult:
    user_id = current_user["sub"]
    errors = _duplicate_errors([(row.row_number, _knowledge_key(row.values)) for row in request.rows])
    for row in request.rows:
        row.values.related_item_ids = validate_related_item_ids_for_user(
            item_ids=row.values.related_item_ids,
            user_id=user_id,
        )
        row.values.source_ref = validate_source_ref_for_user(source_ref=row.values.source_ref, user_id=user_id)
    _fail_validation(errors)
    if request.dry_run:
        return BulkImportResult(total_rows=len(request.rows), success_rows=len(request.rows), failed_rows=0, dry_run=True)

    created_ids = [str(uuid.uuid4()) for _ in request.rows]
    with db.transaction() as conn:
        for entry_id, row in zip(created_ids, request.rows, strict=True):
            _insert_knowledge(conn, entry_id=entry_id, values=row.values, user_id=user_id)

    warnings = _index_created_items("knowledge", created_ids, user_id=user_id)
    return BulkImportResult(
        total_rows=len(request.rows),
        success_rows=len(request.rows),
        failed_rows=0,
        created_ids=created_ids,
        errors=[
            ImportErrorDetail(row=0, field="index", reason=side_effect_warning("Knowledge import indexed.", " ".join(warnings)))
        ]
        if warnings
        else [],
    )


async def import_logbook_entries(
    request: LogbookBulkImportRequest,
    current_user: dict = Depends(get_current_user),
) -> BulkImportResult:
    user_id = current_user["sub"]
    errors = _duplicate_errors([(row.row_number, _logbook_key(row.values)) for row in request.rows])
    for row in request.rows:
        row.values.related_item_ids = validate_related_item_ids_for_user(
            item_ids=row.values.related_item_ids,
            user_id=user_id,
        )
        row.values.source_ref = validate_source_ref_for_user(source_ref=row.values.source_ref, user_id=user_id)
    _fail_validation(errors)
    if request.dry_run:
        return BulkImportResult(total_rows=len(request.rows), success_rows=len(request.rows), failed_rows=0, dry_run=True)

    created_ids = [str(uuid.uuid4()) for _ in request.rows]
    with db.transaction() as conn:
        for entry_id, row in zip(created_ids, request.rows, strict=True):
            _insert_logbook(conn, entry_id=entry_id, values=row.values, user_id=user_id)

    warnings = _index_created_items("logbook", created_ids, user_id=user_id)
    return BulkImportResult(
        total_rows=len(request.rows),
        success_rows=len(request.rows),
        failed_rows=0,
        created_ids=created_ids,
        errors=[ImportErrorDetail(row=0, field="index", reason=" ".join(warnings))] if warnings else [],
    )


async def import_prompts(
    request: PromptBulkImportRequest,
    current_user: dict = Depends(get_current_user),
) -> BulkImportResult:
    user_id = current_user["sub"]
    _fail_validation(_duplicate_errors([(row.row_number, _prompt_key(row.values)) for row in request.rows]))
    if request.dry_run:
        return BulkImportResult(total_rows=len(request.rows), success_rows=len(request.rows), failed_rows=0, dry_run=True)

    created_ids = [str(uuid.uuid4()) for _ in request.rows]
    with db.transaction() as conn:
        for prompt_id, row in zip(created_ids, request.rows, strict=True):
            _insert_prompt(conn, prompt_id=prompt_id, values=row.values, user_id=user_id)

    warnings = _index_created_items("prompt", created_ids, user_id=user_id)
    return BulkImportResult(
        total_rows=len(request.rows),
        success_rows=len(request.rows),
        failed_rows=0,
        created_ids=created_ids,
        errors=[ImportErrorDetail(row=0, field="index", reason=" ".join(warnings))] if warnings else [],
    )
