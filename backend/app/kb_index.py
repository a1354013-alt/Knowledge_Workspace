from __future__ import annotations

from typing import Any

from app.database import add_to_kb_vector_db, delete_from_kb_vector_db
from app.search_content import (
    build_knowledge_search_text,
    build_logbook_search_text,
    build_photo_search_text,
    build_prompt_search_text,
)
from app.services.core import split_text
from app.vector_db import vector_db_unavailable_reason


def _build_metadata(
    *,
    item_id: str,
    item_type: str,
    title: str,
    owner_user_id: str,
    location: str | None = None,
    is_active: int = 1,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "item_type": item_type,
        "title": title,
        "location": location or "",
        "owner_user_id": owner_user_id,
        "is_active": int(is_active),
    }


def index_knowledge_entry(entry: dict[str, Any]) -> bool:
    item_id = f"knowledge:{entry['entry_id']}"
    if int(entry.get("is_active", 1)) != 1 or entry.get("status") == "archived":
        delete_from_kb_vector_db(item_id)
        return True
    text = build_knowledge_search_text(entry)

    chunks = split_text(text)
    metadata = _build_metadata(
        item_id=item_id,
        item_type="knowledge",
        title=entry.get("title") or "Knowledge note",
        owner_user_id=str(entry.get("created_by", "") or ""),
        is_active=int(entry.get("is_active", 1)),
    )
    if not add_to_kb_vector_db(item_id, chunks, [dict(metadata) for _ in chunks]):
        raise RuntimeError(f"{vector_db_unavailable_reason()} Knowledge entry {item_id} was not indexed.")
    return True


def index_logbook_entry(entry: dict[str, Any]) -> bool:
    item_id = f"logbook:{entry['entry_id']}"
    if int(entry.get("is_active", 1)) != 1 or entry.get("status") == "archived":
        delete_from_kb_vector_db(item_id)
        return True
    text = build_logbook_search_text(entry)

    chunks = split_text(text)
    metadata = _build_metadata(
        item_id=item_id,
        item_type="logbook",
        title=entry.get("title") or "Logbook",
        owner_user_id=str(entry.get("created_by", "") or ""),
        is_active=int(entry.get("is_active", 1)),
    )
    if not add_to_kb_vector_db(item_id, chunks, [dict(metadata) for _ in chunks]):
        raise RuntimeError(f"{vector_db_unavailable_reason()} Logbook entry {item_id} was not indexed.")
    return True


def index_photo(entry: dict[str, Any]) -> bool:
    item_id = f"photo:{entry['photo_id']}"
    if int(entry.get("is_active", 1)) != 1 or entry.get("status") == "archived":
        delete_from_kb_vector_db(item_id)
        return True
    text = build_photo_search_text(entry)

    chunks = split_text(text)
    metadata = _build_metadata(
        item_id=item_id,
        item_type="photo",
        title=entry.get("filename") or "Photo",
        owner_user_id=str(entry.get("uploaded_by", "") or ""),
        is_active=int(entry.get("is_active", 1)),
    )
    if not add_to_kb_vector_db(item_id, chunks, [dict(metadata) for _ in chunks]):
        raise RuntimeError(f"{vector_db_unavailable_reason()} Photo {item_id} was not indexed.")
    return True


def index_saved_prompt(entry: dict[str, Any]) -> bool:
    item_id = f"prompt:{entry['prompt_id']}"
    if int(entry.get("is_active", 1)) != 1:
        delete_from_kb_vector_db(item_id)
        return True
    text = build_prompt_search_text(entry)
    chunks = split_text(text)
    metadata = _build_metadata(
        item_id=item_id,
        item_type="prompt",
        title=entry.get("title") or "Saved prompt",
        owner_user_id=str(entry.get("created_by", "") or ""),
        is_active=int(entry.get("is_active", 1)),
    )
    if not add_to_kb_vector_db(item_id, chunks, [dict(metadata) for _ in chunks]):
        raise RuntimeError(f"{vector_db_unavailable_reason()} Prompt {item_id} was not indexed.")
    return True
