from __future__ import annotations

import logging
import mimetypes
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException, status

from app.context import db
from app.models import (
    DocumentResponse,
    ItemLinkResolved,
    ItemLinksResponse,
    ItemSummary,
    KnowledgeRevisionResponse,
    MeResponse,
)
from app.repositories.repository_utils import normalize_index_status
from app.source_types import canonicalize_source_type

logger = logging.getLogger("knowledge_workspace")
OWNED_ITEM_PREFIXES = frozenset({"document", "photo", "autotest_run", "prompt", "logbook", "knowledge"})
MAX_SAFE_DOWNLOAD_FILENAME_LENGTH = 180


def serialize_me(current_user: dict) -> MeResponse:
    return MeResponse(
        user_id=current_user["sub"],
        role=current_user["role"],
        display_name=current_user.get("display_name", ""),
    )


def serialize_document(document: dict) -> DocumentResponse:
    index_status = normalize_index_status(
        document.get("index_status"),
        is_active=document.get("is_active", 1),
        workflow_status=document.get("status", ""),
    )
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
        index_status=index_status,
        index_error=str(document.get("index_error", "") or ""),
        indexed_at=str(document.get("indexed_at", "") or ""),
    )


KNOWLEDGE_REVISION_FIELDS: tuple[str, ...] = (
    "title",
    "status",
    "problem",
    "root_cause",
    "solution",
    "tags",
    "notes",
    "source_type",
    "source_ref",
)


def knowledge_revision_snapshot(entry: dict) -> dict[str, str]:
    return {field: str(entry.get(field, "") or "") for field in KNOWLEDGE_REVISION_FIELDS}


def serialize_knowledge_revision(row: dict) -> KnowledgeRevisionResponse:
    return KnowledgeRevisionResponse(
        revision_id=str(row.get("revision_id", "")),
        entry_id=str(row.get("entry_id", "")),
        version_number=int(row.get("version_number", 0)),
        title=str(row.get("title", "")),
        status=str(row.get("status", "draft") or "draft"),
        problem=str(row.get("problem", "")),
        root_cause=str(row.get("root_cause", "")),
        solution=str(row.get("solution", "")),
        tags=str(row.get("tags", "")),
        notes=str(row.get("notes", "")),
        source_type=str(row.get("source_type", "manual") or "manual"),
        source_ref=str(row.get("source_ref", "") or ""),
        change_note=str(row.get("change_note", "") or ""),
        created_at=str(row.get("created_at", "") or ""),
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _item_summary(
    *,
    item_id: str,
    item_type: str,
    title: str,
    status: str,
    created_at: str,
    updated_at: str,
    source_type: str = "",
    source_ref: str = "",
) -> ItemSummary:
    return ItemSummary(
        item_id=item_id,
        item_type=item_type,
        title=title,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        source_type=source_type,
        source_ref=source_ref,
    )


def _resolve_owned_summary(
    *,
    item_id: str,
    user_id: str,
    raw_id: str,
    getter: Callable[[str], dict[str, Any] | None],
    owner_key: str,
    item_type: str,
    title_field: str,
    default_title: str,
    status_value: str,
    created_key: str,
    updated_key: str,
    source_type_key: str = "",
    source_ref_key: str = "",
) -> ItemSummary | None:
    row = getter(raw_id)
    if not row or str(row.get(owner_key, "")) != user_id:
        return None
    return _item_summary(
        item_id=item_id,
        item_type=item_type,
        title=str(row.get(title_field, "") or default_title),
        status=str(row.get("status", "") or status_value),
        created_at=str(row.get(created_key, "") or ""),
        updated_at=str(row.get(updated_key, "") or ""),
        source_type=str(row.get(source_type_key, "") or "") if source_type_key else "",
        source_ref=str(row.get(source_ref_key, "") or "") if source_ref_key else "",
    )


def resolve_item_summary(*, item_id: str, user_id: str) -> ItemSummary | None:
    try:
        prefix, raw_id = parse_item_id(item_id)
    except ValueError:
        return None

    if prefix == "knowledge":
        return _resolve_owned_summary(
            item_id=item_id,
            user_id=user_id,
            raw_id=raw_id,
            getter=db.get_knowledge_entry,
            owner_key="created_by",
            item_type="knowledge",
            title_field="title",
            default_title="Knowledge note",
            status_value="draft",
            created_key="created_at",
            updated_key="updated_at",
            source_type_key="source_type",
            source_ref_key="source_ref",
        )

    if prefix == "logbook":
        return _resolve_owned_summary(
            item_id=item_id,
            user_id=user_id,
            raw_id=raw_id,
            getter=db.get_logbook_entry,
            owner_key="created_by",
            item_type="logbook",
            title_field="title",
            default_title="Logbook note",
            status_value="draft",
            created_key="created_at",
            updated_key="updated_at",
            source_type_key="source_type",
            source_ref_key="source_ref",
        )

    if prefix == "document":
        return _resolve_owned_summary(
            item_id=item_id,
            user_id=user_id,
            raw_id=raw_id,
            getter=db.get_document,
            owner_key="uploaded_by",
            item_type="document",
            title_field="filename",
            default_title="Document",
            status_value="reviewed",
            created_key="uploaded_at",
            updated_key="updated_at",
        )

    if prefix == "photo":
        return _resolve_owned_summary(
            item_id=item_id,
            user_id=user_id,
            raw_id=raw_id,
            getter=db.get_photo,
            owner_key="uploaded_by",
            item_type="photo",
            title_field="filename",
            default_title="Photo",
            status_value="reviewed",
            created_key="created_at",
            updated_key="updated_at",
        )

    if prefix == "prompt":
        return _resolve_owned_summary(
            item_id=item_id,
            user_id=user_id,
            raw_id=raw_id,
            getter=db.get_saved_prompt,
            owner_key="created_by",
            item_type="prompt",
            title_field="title",
            default_title="Saved prompt",
            status_value="active",
            created_key="created_at",
            updated_key="updated_at",
        )

    if prefix == "autotest_run":
        run = db.get_autotest_run(run_id=raw_id, created_by=user_id)
        if not run:
            return None
        return _item_summary(
            item_id=item_id,
            item_type="autotest_run",
            title=str(run.get("project_name", "") or run.get("source_ref", "") or "AutoTest run"),
            status=str(run.get("status", "") or ""),
            created_at=str(run.get("created_at", "") or ""),
            updated_at=str(run.get("updated_at", "") or run.get("created_at", "") or ""),
            source_type=canonicalize_source_type(str(run.get("source_type", "") or "knowledge"))
            if str(run.get("source_type", "") or "").strip() in {"knowledge", "knowledge_entry", "logbook", "logbook_entry", "prompt", "saved_prompt", "document", "photo"}
            else str(run.get("source_type", "") or ""),
            source_ref=str(run.get("source_ref", "") or ""),
        )

    return None


def build_links_response(*, item_id: str, user_id: str) -> ItemLinksResponse:
    normalized_item_id = str(item_id or "").strip()
    if not normalized_item_id or resolve_item_summary(item_id=normalized_item_id, user_id=user_id) is None:
        return ItemLinksResponse(item_id=normalized_item_id, links=[])

    links = db.list_links(normalized_item_id)
    resolved: list[ItemLinkResolved] = []
    for link in links:
        from_item_id = str(link.get("from_item_id", "") or "")
        to_item_id = str(link.get("to_item_id", "") or "")
        if normalized_item_id not in {from_item_id, to_item_id}:
            continue
        other_id = to_item_id if from_item_id == normalized_item_id else from_item_id
        other_item = resolve_item_summary(item_id=other_id, user_id=user_id)
        if other_item is None:
            continue
        resolved.append(
            ItemLinkResolved(
                link_id=str(link.get("link_id", "") or ""),
                from_item_id=from_item_id,
                to_item_id=to_item_id,
                link_type=str(link.get("link_type", "") or "references"),
                created_at=str(link.get("created_at", "") or ""),
                other_item=other_item,
            )
        )
    return ItemLinksResponse(item_id=normalized_item_id, links=resolved)


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


def _internal_item_id_candidate(value: str) -> str | None:
    normalized = str(value or "").strip()
    if not normalized or ":" not in normalized:
        return None
    prefix = normalized.split(":", 1)[0].strip()
    if prefix not in OWNED_ITEM_PREFIXES:
        return None
    return normalized


def validate_related_item_ids_for_user(*, item_ids: list[str], user_id: str) -> list[str]:
    normalized = normalize_related_item_ids(item_ids)
    invalid = [item_id for item_id in normalized if resolve_item_summary(item_id=item_id, user_id=user_id) is None]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or inaccessible related_item_ids: {', '.join(invalid)}",
        )
    return normalized


def list_visible_related_item_ids_for_user(*, item_id: str, user_id: str) -> list[str]:
    visible: list[str] = []
    for related_id in normalize_related_item_ids(db.list_related_item_ids(item_id)):
        if resolve_item_summary(item_id=related_id, user_id=user_id) is not None:
            visible.append(related_id)
    return visible


def validate_source_ref_for_user(*, source_ref: str, user_id: str) -> str:
    try:
        ref = str(source_ref or "").strip()
        candidate = _internal_item_id_candidate(ref)
        if candidate is None:
            return ref
        parse_item_id(candidate)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source_ref item id format.")
    if resolve_item_summary(item_id=candidate, user_id=user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="source_ref points to an inaccessible item."
        )
    return candidate


def maybe_link_source_item(*, from_item_id: str, source_type: str, source_ref: str, user_id: str) -> None:
    st = str(source_type or "").strip()
    if st in {"manual", ""}:
        return
    ref = _internal_item_id_candidate(source_ref)
    if ref is None:
        return
    if resolve_item_summary(item_id=ref, user_id=user_id) is None:
        return
    db.add_link(str(from_item_id), ref, link_type="derived_from")


def sync_source_ref_link(
    *, from_item_id: str, old_source_ref: str, new_source_ref: str, source_type: str, user_id: str
) -> None:
    old_ref = str(old_source_ref or "").strip()
    new_ref = str(new_source_ref or "").strip()
    if _internal_item_id_candidate(old_ref):
        try:
            prefix, _rest = parse_item_id(old_ref)
        except ValueError:
            prefix = ""
        if prefix in OWNED_ITEM_PREFIXES:
            db.delete_links(from_item_id=str(from_item_id), to_item_id=old_ref, link_type="derived_from")

    maybe_link_source_item(from_item_id=from_item_id, source_type=source_type, source_ref=new_ref, user_id=user_id)


def safe_download_filename(value: str) -> str:
    raw_name = str(value or "")
    filtered = "".join(ch for ch in raw_name if not unicodedata.category(ch).startswith("C"))
    normalized = filtered.replace("/", "-").replace("\\", "-").replace('"', "'").strip()
    if not normalized:
        return "file"

    candidate = Path(normalized).name.strip(" .")
    if not candidate:
        return "file"

    suffix = Path(candidate).suffix
    stem = candidate[: -len(suffix)] if suffix else candidate
    safe_stem = stem.strip(" .") or "file"
    safe_suffix = "".join(ch for ch in suffix if ch.isalnum() or ch in {".", "-", "_"}).strip(" .")
    if safe_suffix and not safe_suffix.startswith("."):
        safe_suffix = f".{safe_suffix}"

    max_stem_length = MAX_SAFE_DOWNLOAD_FILENAME_LENGTH - len(safe_suffix)
    if max_stem_length < 1:
        safe_suffix = ""
        max_stem_length = MAX_SAFE_DOWNLOAD_FILENAME_LENGTH
    if len(safe_stem) > max_stem_length:
        safe_stem = safe_stem[:max_stem_length].rstrip(" .") or "file"

    output = f"{safe_stem}{safe_suffix}"
    return output[:MAX_SAFE_DOWNLOAD_FILENAME_LENGTH] or "file"


def guess_media_type(filename: str, default: str = "application/octet-stream") -> str:
    media_type, _encoding = mimetypes.guess_type(str(filename or ""))
    return media_type or default


def side_effect_warning(base_message: str, warning: str | None) -> str:
    detail = str(warning or "").strip()
    if not detail:
        return base_message
    return f"{base_message} Warning: {detail}"


def _detailed_side_effect_warning(*, action: str, label: str, exc: Exception | None = None, fallback: str = "") -> str:
    detail = str(exc or "").strip() or fallback.strip()
    if detail:
        return f"{label} {action} failed: {detail}"
    return f"{label} {action} failed."


def classify_index_failure(exc_or_message: Exception | str | None) -> tuple[str, str]:
    detail = str(exc_or_message or "").strip()
    status_value = "unavailable" if "vector index unavailable" in detail.lower() else "failed"
    return status_value, detail


def run_index_side_effect(
    *,
    label: str,
    item_id: str,
    operation: Callable[[], object],
    on_error: Callable[[str, str], None] | None = None,
) -> str | None:
    try:
        result = operation()
    except Exception as exc:
        if on_error is not None:
            status_value, detail = classify_index_failure(exc)
            on_error(status_value, detail)
        logger.warning("%s indexing failed for %s: %s", label, item_id, exc)
        return _detailed_side_effect_warning(action="indexing", label=label, exc=exc)
    if result is not None and not result:
        if on_error is not None:
            on_error(
                "failed",
                "The vector index is unavailable or the indexing operation returned a degraded status.",
            )
        logger.warning("%s indexing failed for %s without an exception", label, item_id)
        return _detailed_side_effect_warning(
            action="indexing",
            label=label,
            fallback="The vector index is unavailable or the indexing operation returned a degraded status.",
        )
    return None


def run_deindex_side_effect(*, label: str, item_id: str, operation: Callable[[], object]) -> str | None:
    try:
        result = operation()
    except Exception as exc:
        logger.warning("%s de-index failed for %s: %s", label, item_id, exc)
        return _detailed_side_effect_warning(action="de-index", label=label, exc=exc)
    if result is False:
        logger.warning("%s de-index failed for %s without an exception", label, item_id)
        return _detailed_side_effect_warning(
            action="de-index",
            label=label,
            fallback="The vector index is unavailable or the de-index operation returned a degraded status.",
        )
    return None


def detect_project_type(zip_path: Path) -> str:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = {name.lower() for name in archive.namelist()}
    except zipfile.BadZipFile as exc:
        raise ValueError("Uploaded file is not a valid zip archive.") from exc

    if any(name.endswith("package.json") for name in names):
        return "node"
    if any(name.endswith("pyproject.toml") for name in names) or any(
        name.endswith("requirements.txt") for name in names
    ):
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
