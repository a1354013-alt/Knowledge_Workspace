from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.context import db
from app.models import (
    DocumentResponse,
    ItemLinkResolved,
    ItemLinksResponse,
    ItemSummary,
    MeResponse,
)

logger = logging.getLogger("knowledge_workspace")


def serialize_me(current_user: dict) -> MeResponse:
    return MeResponse(
        user_id=current_user["sub"],
        role=current_user["role"],
        display_name=current_user.get("display_name", ""),
    )


def serialize_document(document: dict) -> DocumentResponse:
    return DocumentResponse(
        id=document["doc_id"],
        filename=document["filename"],
        category=str(document.get("category", "") or ""),
        tags=str(document.get("tags", "") or ""),
        status=str(document.get("status", "") or "reviewed"),
        uploaded_at=str(document["uploaded_at"]),
        updated_at=str(document.get("updated_at") or document["uploaded_at"]),
        file_size=int(document.get("file_size", 0)),
        uploaded_by=document.get("uploaded_by"),
    )


def safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        logger.warning("Could not delete file %s because it is locked by the OS.", path)


def item_id_from_parts(prefix: str, raw_id: str) -> str:
    value = str(raw_id or "").strip()
    if not value:
        raise ValueError("Missing item id.")
    return f"{prefix}:{value}"


def parse_item_id(item_id: str) -> tuple[str, str]:
    raw = str(item_id or "").strip()
    if ":" not in raw:
        raise ValueError("Invalid item id format. Expected '<type>:<id>'.")
    prefix, rest = raw.split(":", 1)
    prefix = prefix.strip()
    rest = rest.strip()
    if not prefix or not rest:
        raise ValueError("Invalid item id format. Expected '<type>:<id>'.")
    return prefix, rest


def resolve_item_summary(*, item_id: str, user_id: str) -> ItemSummary | None:
    try:
        prefix, raw_id = parse_item_id(item_id)
    except ValueError:
        return None

    if prefix == "knowledge":
        entry = db.get_knowledge_entry(raw_id)
        if not entry or str(entry.get("created_by", "")) != user_id:
            return None
        return ItemSummary(
            item_id=item_id,
            item_type="knowledge_entry",
            title=str(entry.get("title", "") or "Knowledge note"),
            status=str(entry.get("status", "") or "draft"),
            created_at=str(entry.get("created_at", "") or ""),
            updated_at=str(entry.get("updated_at", "") or ""),
        )

    if prefix == "logbook":
        entry = db.get_logbook_entry(raw_id)
        if not entry or str(entry.get("created_by", "")) != user_id:
            return None
        return ItemSummary(
            item_id=item_id,
            item_type="logbook_entry",
            title=str(entry.get("title", "") or "Logbook note"),
            status=str(entry.get("status", "") or "draft"),
            created_at=str(entry.get("created_at", "") or ""),
            updated_at=str(entry.get("updated_at", "") or ""),
        )

    if prefix == "document":
        doc = db.get_document(raw_id)
        if not doc or str(doc.get("uploaded_by", "")) != user_id:
            return None
        return ItemSummary(
            item_id=item_id,
            item_type="document",
            title=str(doc.get("filename", "") or "Document"),
            status=str(doc.get("status", "") or "reviewed"),
            created_at=str(doc.get("uploaded_at", "") or ""),
            updated_at=str(doc.get("updated_at", "") or ""),
        )

    if prefix == "photo":
        photo = db.get_photo(raw_id)
        if not photo or str(photo.get("uploaded_by", "")) != user_id:
            return None
        return ItemSummary(
            item_id=item_id,
            item_type="photo",
            title=str(photo.get("filename", "") or "Photo"),
            status=str(photo.get("status", "") or "reviewed"),
            created_at=str(photo.get("uploaded_at", "") or ""),
            updated_at=str(photo.get("updated_at", "") or ""),
        )

    if prefix == "prompt":
        prompt = db.get_saved_prompt(raw_id)
        if not prompt or str(prompt.get("created_by", "")) != user_id:
            return None
        return ItemSummary(
            item_id=item_id,
            item_type="saved_prompt",
            title=str(prompt.get("title", "") or "Saved prompt"),
            status="active",
            created_at=str(prompt.get("created_at", "") or ""),
            updated_at=str(prompt.get("updated_at", "") or ""),
        )

    if prefix == "autotest_run":
        run = db.get_autotest_run(run_id=raw_id, created_by=user_id)
        if not run:
            return None
        return ItemSummary(
            item_id=item_id,
            item_type="autotest_run",
            title=str(run.get("project_name", "") or run.get("source_ref", "") or "AutoTest run"),
            status=str(run.get("status", "") or ""),
            created_at=str(run.get("created_at", "") or ""),
            updated_at=str(run.get("created_at", "") or ""),
            source_type=str(run.get("source_type", "") or ""),
            source_ref=str(run.get("source_ref", "") or ""),
        )

    return None


def build_links_response(*, item_id: str, user_id: str) -> ItemLinksResponse:
    links = db.list_links(item_id)
    resolved: list[ItemLinkResolved] = []
    for link in links:
        from_item_id = str(link.get("from_item_id", "") or "")
        to_item_id = str(link.get("to_item_id", "") or "")
        other_id = to_item_id if from_item_id == item_id else from_item_id
        resolved.append(
            ItemLinkResolved(
                link_id=str(link.get("link_id", "") or ""),
                from_item_id=from_item_id,
                to_item_id=to_item_id,
                link_type=str(link.get("link_type", "") or "references"),
                created_at=str(link.get("created_at", "") or ""),
                other_item=resolve_item_summary(item_id=other_id, user_id=user_id),
            )
        )
    return ItemLinksResponse(item_id=item_id, links=resolved)


def normalize_related_item_ids(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def maybe_link_source_item(*, from_item_id: str, source_type: str, source_ref: str) -> None:
    st = str(source_type or "").strip()
    if st in {"manual", ""}:
        return
    ref = str(source_ref or "").strip()
    if not ref or ":" not in ref:
        return
    try:
        prefix, _rest = parse_item_id(ref)
    except ValueError:
        return
    if prefix not in {"document", "photo", "autotest_run", "prompt", "logbook", "knowledge"}:
        return
    db.add_link(str(from_item_id), ref, link_type="derived_from")


def sync_source_ref_link(*, from_item_id: str, old_source_ref: str, new_source_ref: str, source_type: str) -> None:
    old_ref = str(old_source_ref or "").strip()
    new_ref = str(new_source_ref or "").strip()
    if old_ref and ":" in old_ref:
        try:
            prefix, _rest = parse_item_id(old_ref)
        except ValueError:
            prefix = ""
        if prefix in {"document", "photo", "autotest_run", "prompt", "logbook", "knowledge"}:
            db.delete_links(from_item_id=str(from_item_id), to_item_id=old_ref, link_type="derived_from")

    if new_ref != old_ref:
        maybe_link_source_item(from_item_id=from_item_id, source_type=source_type, source_ref=new_ref)


def detect_project_type(zip_path: Path) -> str:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = {name.lower() for name in archive.namelist()}
    except zipfile.BadZipFile as exc:
        raise ValueError("Uploaded file is not a valid zip archive.") from exc

    if any(name.endswith("package.json") for name in names):
        return "node"
    if any(name.endswith("pyproject.toml") for name in names) or any(name.endswith("requirements.txt") for name in names):
        return "python"
    return "unknown"


def detect_fail_step(zip_path: Path) -> str | None:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for candidate in (".autotest_fail_step", "autotest_fail_step.txt"):
                if candidate in archive.namelist():
                    raw = archive.read(candidate)
                    value = raw.decode("utf-8", errors="ignore").strip().lower()
                    return value or None
    except zipfile.BadZipFile as exc:
        raise ValueError("Uploaded file is not a valid zip archive.") from exc
    return None


def require_owned_row(row: dict[str, Any] | None, *, user_id: str, owner_key: str, not_found: str) -> dict[str, Any]:
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found)
    if str(row.get(owner_key, "")) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this item.")
    return row

