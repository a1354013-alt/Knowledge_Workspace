from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.context import UPLOAD_DIR, db
from app.database import delete_from_kb_vector_db, delete_from_vector_db
from app.kb_index import index_knowledge_entry, index_logbook_entry, index_photo, index_saved_prompt
from app.models import (
    EmbeddingProviderStatusResponse,
    IndexItemType,
    IndexRebuildResponse,
    IndexStatusItemResponse,
    IndexStatusResponse,
    IndexStatusSummaryItem,
)
from app.services.core import process_file
from app.vector_db import get_embedding_provider_descriptor


def get_provider_status() -> EmbeddingProviderStatusResponse:
    descriptor = get_embedding_provider_descriptor()
    status = "ready" if descriptor.available and descriptor.semantic_search_ready else "degraded"
    if not descriptor.available:
        status = "disabled"
    return EmbeddingProviderStatusResponse(
        configured_provider=descriptor.name,
        active_provider=descriptor.kind,
        status=status,
        demo_mode=descriptor.demo_mode,
        semantic_search_ready=descriptor.semantic_search_ready,
        message=descriptor.message,
        details=list(descriptor.details),
    )


@dataclass(frozen=True)
class IndexTarget:
    item_type: IndexItemType
    item_id: str
    title: str
    status: str
    error: str
    indexed_at: str
    updated_at: str


def _document_target(row: dict[str, Any]) -> IndexTarget:
    return IndexTarget(
        item_type="document",
        item_id=str(row["doc_id"]),
        title=str(row.get("filename", "") or "Document"),
        status=str(row.get("index_status", "pending") or "pending"),
        error=str(row.get("index_error", "") or ""),
        indexed_at=str(row.get("indexed_at", "") or ""),
        updated_at=str(row.get("updated_at", "") or row.get("uploaded_at", "") or ""),
    )


def _kb_target(item_type: IndexItemType, row: dict[str, Any], *, id_key: str, title_key: str) -> IndexTarget:
    return IndexTarget(
        item_type=item_type,
        item_id=str(row[id_key]),
        title=str(row.get(title_key, "") or item_type.title()),
        status=str(row.get("index_status", "pending") or "pending"),
        error=str(row.get("index_error", "") or ""),
        indexed_at=str(row.get("indexed_at", "") or ""),
        updated_at=str(row.get("updated_at", "") or row.get("created_at", "") or ""),
    )


def _sync_document_status(doc_id: str, *, status: str, error: str = "", indexed_at: str = "") -> None:
    db.update_document(doc_id, index_status=status, index_error=error, indexed_at=indexed_at)


def _sync_knowledge_status(entry_id: str, *, status: str, error: str = "", indexed_at: str = "") -> None:
    db.update_knowledge_entry(entry_id, index_status=status, index_error=error, indexed_at=indexed_at)


def _sync_logbook_status(entry_id: str, *, status: str, error: str = "", indexed_at: str = "") -> None:
    db.update_logbook_entry(entry_id, index_status=status, index_error=error, indexed_at=indexed_at)


def _sync_photo_status(photo_id: str, *, status: str, error: str = "", indexed_at: str = "") -> None:
    db.update_photo(photo_id, index_status=status, index_error=error, indexed_at=indexed_at)


def _sync_prompt_status(prompt_id: str, *, status: str, error: str = "", indexed_at: str = "") -> None:
    db.update_saved_prompt_index(prompt_id, index_status=status, index_error=error, indexed_at=indexed_at)


def sync_document_index(document: dict[str, Any]) -> None:
    doc_id = str(document["doc_id"])
    delete_from_vector_db(doc_id)
    if int(document.get("is_active", 1)) != 1 or str(document.get("status", "")) == "archived":
        _sync_document_status(doc_id, status="pending", error="", indexed_at="")
        return

    file_path = UPLOAD_DIR / str(document["saved_filename"])
    if not file_path.exists():
        message = f"Document file is missing: {file_path}"
        _sync_document_status(doc_id, status="failed", error=message, indexed_at="")
        raise FileNotFoundError(message)

    try:
        process_file(
            doc_id,
            str(file_path),
            str(document["filename"]),
            str(document.get("uploaded_by") or ""),
            str(document.get("status") or "reviewed"),
            int(document.get("is_active", 1)),
        )
    except Exception as exc:
        detail = str(exc)
        _sync_document_status(
            doc_id,
            status="unavailable" if "vector index unavailable" in detail.lower() else "failed",
            error=detail,
            indexed_at="",
        )
        raise
    else:
        _sync_document_status(
            doc_id,
            status="indexed",
            error="",
            indexed_at=document.get("updated_at", "") or document.get("uploaded_at", "") or "",
        )


def sync_knowledge_entry_index(entry: dict[str, Any]) -> None:
    item_id = f"knowledge:{entry['entry_id']}"
    delete_from_kb_vector_db(item_id)
    if int(entry.get("is_active", 1)) != 1 or str(entry.get("status", "")) == "archived":
        _sync_knowledge_status(str(entry["entry_id"]), status="pending", error="", indexed_at="")
        return
    try:
        index_knowledge_entry(entry)
    except Exception as exc:
        detail = str(exc)
        _sync_knowledge_status(
            str(entry["entry_id"]),
            status="unavailable" if "vector index unavailable" in detail.lower() else "failed",
            error=detail,
            indexed_at="",
        )
        raise
    else:
        _sync_knowledge_status(
            str(entry["entry_id"]),
            status="indexed",
            error="",
            indexed_at=str(entry.get("updated_at", "") or entry.get("created_at", "") or ""),
        )


def sync_logbook_entry_index(entry: dict[str, Any]) -> None:
    item_id = f"logbook:{entry['entry_id']}"
    delete_from_kb_vector_db(item_id)
    if int(entry.get("is_active", 1)) != 1 or str(entry.get("status", "")) == "archived":
        _sync_logbook_status(str(entry["entry_id"]), status="pending", error="", indexed_at="")
        return
    try:
        index_logbook_entry(entry)
    except Exception as exc:
        detail = str(exc)
        _sync_logbook_status(
            str(entry["entry_id"]),
            status="unavailable" if "vector index unavailable" in detail.lower() else "failed",
            error=detail,
            indexed_at="",
        )
        raise
    else:
        _sync_logbook_status(
            str(entry["entry_id"]),
            status="indexed",
            error="",
            indexed_at=str(entry.get("updated_at", "") or entry.get("created_at", "") or ""),
        )


def sync_photo_index(entry: dict[str, Any]) -> None:
    item_id = f"photo:{entry['photo_id']}"
    delete_from_kb_vector_db(item_id)
    if int(entry.get("is_active", 1)) != 1 or str(entry.get("status", "")) == "archived":
        _sync_photo_status(str(entry["photo_id"]), status="pending", error="", indexed_at="")
        return
    try:
        index_photo(entry)
    except Exception as exc:
        detail = str(exc)
        _sync_photo_status(
            str(entry["photo_id"]),
            status="unavailable" if "vector index unavailable" in detail.lower() else "failed",
            error=detail,
            indexed_at="",
        )
        raise
    else:
        _sync_photo_status(
            str(entry["photo_id"]),
            status="indexed",
            error="",
            indexed_at=str(entry.get("updated_at", "") or entry.get("created_at", "") or ""),
        )


def sync_prompt_index(entry: dict[str, Any]) -> None:
    item_id = f"prompt:{entry['prompt_id']}"
    delete_from_kb_vector_db(item_id)
    if int(entry.get("is_active", 1)) != 1:
        _sync_prompt_status(str(entry["prompt_id"]), status="pending", error="", indexed_at="")
        return
    try:
        index_saved_prompt(entry)
    except Exception as exc:
        detail = str(exc)
        _sync_prompt_status(
            str(entry["prompt_id"]),
            status="unavailable" if "vector index unavailable" in detail.lower() else "failed",
            error=detail,
            indexed_at="",
        )
        raise
    else:
        _sync_prompt_status(
            str(entry["prompt_id"]),
            status="indexed",
            error="",
            indexed_at=str(entry.get("updated_at", "") or entry.get("created_at", "") or ""),
        )


def get_index_status(current_user: dict[str, Any]) -> IndexStatusResponse:
    user_id = str(current_user["sub"])
    documents = [_document_target(row) for row in db.list_documents(user_id=user_id, include_archived=True)]
    knowledge = [
        _kb_target("knowledge", row, id_key="entry_id", title_key="title")
        for row in db.list_knowledge_entries(user_id=user_id, include_archived=True, limit=500)
    ]
    logbook = [
        _kb_target("logbook", row, id_key="entry_id", title_key="title")
        for row in db.list_logbook_entries(user_id=user_id, include_archived=True, limit=500)
    ]
    photos = [
        _kb_target("photo", row, id_key="photo_id", title_key="filename")
        for row in db.list_photos(user_id=user_id, include_archived=True, limit=500)
    ]
    prompts = [
        _kb_target("prompt", row, id_key="prompt_id", title_key="title")
        for row in db.list_saved_prompts(user_id=user_id, limit=500)
    ]

    grouped = {
        "document": documents,
        "knowledge": knowledge,
        "logbook": logbook,
        "photo": photos,
        "prompt": prompts,
    }
    summary = {
        item_type: IndexStatusSummaryItem(
            total=len(items),
            pending=sum(1 for item in items if item.status == "pending"),
            indexed=sum(1 for item in items if item.status == "indexed"),
            failed=sum(1 for item in items if item.status == "failed"),
            unavailable=sum(1 for item in items if item.status == "unavailable"),
        )
        for item_type, items in grouped.items()
    }
    failed_items = [
        IndexStatusItemResponse(
            item_type=item.item_type,
            item_id=item.item_id,
            title=item.title,
            status=item.status,
            error=item.error,
            indexed_at=item.indexed_at,
            updated_at=item.updated_at,
        )
        for items in grouped.values()
        for item in items
        if item.status in {"failed", "pending", "unavailable"}
    ]
    return IndexStatusResponse(provider=get_provider_status(), summary=summary, failed_items=failed_items)


def rebuild_all_indexes(current_user: dict[str, Any]) -> IndexRebuildResponse:
    rebuilt = 0
    failed = 0
    items: list[IndexStatusItemResponse] = []
    for item_type in ("document", "knowledge", "logbook", "photo", "prompt"):
        response = rebuild_single_item_type(current_user, item_type)
        rebuilt += response.rebuilt
        failed += response.failed
        items.extend(response.items)
    return IndexRebuildResponse(
        message=f"Rebuilt {rebuilt} item(s); {failed} failed.",
        provider=get_provider_status(),
        rebuilt=rebuilt,
        failed=failed,
        items=items,
    )


def rebuild_single_item_type(current_user: dict[str, Any], item_type: IndexItemType) -> IndexRebuildResponse:
    user_id = str(current_user["sub"])
    rows: list[dict[str, Any]]
    if item_type == "document":
        rows = db.list_documents(user_id=user_id, include_archived=True)
    elif item_type == "knowledge":
        rows = db.list_knowledge_entries(user_id=user_id, include_archived=True, limit=500)
    elif item_type == "logbook":
        rows = db.list_logbook_entries(user_id=user_id, include_archived=True, limit=500)
    elif item_type == "photo":
        rows = db.list_photos(user_id=user_id, include_archived=True, limit=500)
    else:
        rows = db.list_saved_prompts(user_id=user_id, limit=500)

    result_items: list[IndexStatusItemResponse] = []
    rebuilt = 0
    failed = 0
    for row in rows:
        try:
            _rebuild_row(item_type, row)
            rebuilt += 1
        except Exception:
            failed += 1
        result_items.append(_serialize_target(item_type, row))
    return IndexRebuildResponse(
        message=f"Rebuilt {rebuilt} {item_type} item(s); {failed} failed.",
        provider=get_provider_status(),
        rebuilt=rebuilt,
        failed=failed,
        items=result_items,
    )


def rebuild_single_item(current_user: dict[str, Any], item_type: IndexItemType, item_id: str) -> IndexRebuildResponse:
    user_id = str(current_user["sub"])
    row: dict[str, Any] | None
    if item_type == "document":
        row = db.get_document(item_id)
        if not row or str(row.get("uploaded_by", "")) != user_id:
            raise LookupError("Document not found.")
    elif item_type == "knowledge":
        row = db.get_knowledge_entry(item_id)
        if not row or str(row.get("created_by", "")) != user_id:
            raise LookupError("Knowledge entry not found.")
    elif item_type == "logbook":
        row = db.get_logbook_entry(item_id)
        if not row or str(row.get("created_by", "")) != user_id:
            raise LookupError("Logbook entry not found.")
    elif item_type == "photo":
        row = db.get_photo(item_id)
        if not row or str(row.get("uploaded_by", "")) != user_id:
            raise LookupError("Photo not found.")
    else:
        row = db.get_saved_prompt(item_id)
        if not row or str(row.get("created_by", "")) != user_id:
            raise LookupError("Prompt not found.")

    rebuilt = 0
    failed = 0
    try:
        _rebuild_row(item_type, row)
        rebuilt = 1
    except Exception:
        failed = 1
    return IndexRebuildResponse(
        message=f"Rebuilt {item_type}:{item_id}.",
        provider=get_provider_status(),
        rebuilt=rebuilt,
        failed=failed,
        items=[_serialize_target(item_type, row)],
    )


def _serialize_target(item_type: IndexItemType, row: dict[str, Any]) -> IndexStatusItemResponse:
    if item_type == "document":
        target = _document_target(db.get_document(str(row["doc_id"])) or row)
    elif item_type == "knowledge":
        target = _kb_target(
            "knowledge", db.get_knowledge_entry(str(row["entry_id"])) or row, id_key="entry_id", title_key="title"
        )
    elif item_type == "logbook":
        target = _kb_target(
            "logbook", db.get_logbook_entry(str(row["entry_id"])) or row, id_key="entry_id", title_key="title"
        )
    elif item_type == "photo":
        target = _kb_target("photo", db.get_photo(str(row["photo_id"])) or row, id_key="photo_id", title_key="filename")
    else:
        target = _kb_target(
            "prompt", db.get_saved_prompt(str(row["prompt_id"])) or row, id_key="prompt_id", title_key="title"
        )
    return IndexStatusItemResponse(
        item_type=target.item_type,
        item_id=target.item_id,
        title=target.title,
        status=target.status,
        error=target.error,
        indexed_at=target.indexed_at,
        updated_at=target.updated_at,
    )


def _rebuild_row(item_type: IndexItemType, row: dict[str, Any]) -> None:
    if item_type == "document":
        sync_document_index(row)
    elif item_type == "knowledge":
        sync_knowledge_entry_index(row)
    elif item_type == "logbook":
        sync_logbook_entry_index(row)
    elif item_type == "photo":
        sync_photo_index(row)
    else:
        sync_prompt_index(row)
