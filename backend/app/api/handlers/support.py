# ruff: noqa: F401,F403,F405
import asyncio
import logging
import mimetypes
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.context import APP_VERSION, UPLOAD_DIR, allow_credentials, allowed_origins, db, settings
from app.core.security import create_token
from app.database import delete_from_kb_vector_db, delete_from_vector_db
from app.dependencies import get_current_user
from app.kb_index import index_knowledge_entry, index_logbook_entry, index_photo, index_saved_prompt
from app.llm import validate_env_vars
from app.models import (
    DocumentResponse,
    DocumentUpdateRequest,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ItemLinkResolved,
    ItemLinksResponse,
    ItemSummary,
    KnowledgeEntryCreateRequest,
    KnowledgeEntryResponse,
    KnowledgeEntryUpdateRequest,
    KnowledgeRevisionDiffResponse,
    KnowledgeRevisionResponse,
    LogbookEntryCreateRequest,
    LogbookEntryResponse,
    LogbookEntryUpdateRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MessageResponse,
    PhotoResponse,
    PhotoUpdateRequest,
    PromoteToKnowledgeResponse,
    QARequest,
    QAResponse,
    ResolveItemsRequest,
    ResolveItemsResponse,
    SavedPromptCreateRequest,
    SavedPromptResponse,
    UploadDocumentResponse,
    UploadPhotoResponse,
)
from app.ocr_service import extract_text_from_image
from app.services import FORM_TEMPLATES, generate_form, perform_qa, process_file
from app.utils import (
    generate_safe_filename,
    stream_write_file,
    validate_file_extension,
    validate_file_magic_bytes,
)

logger = logging.getLogger("knowledge_workspace")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
PHOTO_DIR = settings.PHOTO_DIR


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
        index_status=str(document.get("index_status", "") or "pending"),
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


def _parse_iso_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_ms(started_at: str | None, finished_at: str | None) -> int | None:
    start = _parse_iso_datetime(started_at)
    end = _parse_iso_datetime(finished_at)
    if not start or not end:
        return None
    return max(int((end - start).total_seconds() * 1000), 0)


def safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        logger.warning("Could not delete file %s because it is locked by the OS.", path)


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


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
            source_type=str(entry.get("source_type", "") or ""),
            source_ref=str(entry.get("source_ref", "") or ""),
        )

    if prefix == "logbook":
        entry = db.get_logbook_entry(raw_id)
        if not entry or str(entry.get("created_by", "")) != user_id:
            return None
        return ItemSummary(
            item_id=item_id,
            item_type="logbook_entry",
            title=str(entry.get("title", "") or "Logbook"),
            status=str(entry.get("status", "") or "draft"),
            created_at=str(entry.get("created_at", "") or ""),
            updated_at=str(entry.get("updated_at", "") or ""),
            source_type=str(entry.get("source_type", "") or ""),
            source_ref=str(entry.get("source_ref", "") or ""),
        )

    if prefix == "document":
        document = db.get_document(raw_id)
        if not document or str(document.get("uploaded_by", "")) != user_id:
            return None
        return ItemSummary(
            item_id=item_id,
            item_type="document",
            title=str(document.get("filename", "") or "Document"),
            status=str(document.get("status", "") or "reviewed"),
            created_at=str(document.get("uploaded_at", "") or ""),
            updated_at=str(document.get("updated_at", "") or ""),
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
            created_at=str(photo.get("created_at", "") or ""),
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

def _safe_download_filename(value: str) -> str:
    name = str(value or "").replace("\r", "").replace("\n", "").strip()
    if not name:
        return "file"
    return name.replace('"', "'")


def _guess_media_type(filename: str, default: str = "application/octet-stream") -> str:
    media_type, _encoding = mimetypes.guess_type(str(filename or ""))
    return media_type or default


async def sync_document_index(document: dict) -> None:
    delete_from_vector_db(document["doc_id"])
    if int(document.get("is_active", 1)) != 1 or str(document.get("status", "")) == "archived":
        db.update_document(
            document["doc_id"],
            index_status="pending",
            index_error="",
            indexed_at="",
        )
        return

    file_path = UPLOAD_DIR / document["saved_filename"]
    if not file_path.exists():
        message = f"Document file is missing: {file_path}"
        db.update_document(
            document["doc_id"],
            index_status="failed",
            index_error=message,
            indexed_at="",
        )
        raise FileNotFoundError(message)

    try:
        await asyncio.to_thread(
            process_file,
            document["doc_id"],
            str(file_path),
            document["filename"],
            str(document.get("uploaded_by") or ""),
            str(document.get("status") or "reviewed"),
            int(document["is_active"]),
        )
    except Exception as exc:
        db.update_document(
            document["doc_id"],
            index_status="failed",
            index_error=str(exc),
            indexed_at="",
        )
        raise
    else:
        db.update_document(
            document["doc_id"],
            index_status="indexed",
            index_error="",
            indexed_at=utc_now_iso(),
        )


def _side_effect_warning(base_message: str, warning: str | None) -> str:
    detail = str(warning or "").strip()
    if not detail:
        return base_message
    return f"{base_message} Warning: {detail}"


def _run_index_side_effect(*, label: str, item_id: str, operation) -> str | None:
    try:
        result = operation()
    except Exception as exc:
        logger.warning("%s indexing failed for %s: %s", label, item_id, exc)
        return f"{label} indexing failed."
    if result is False:
        logger.warning("%s indexing failed for %s without an exception", label, item_id)
        return f"{label} indexing failed."
    return None


def _run_deindex_side_effect(*, label: str, item_id: str, operation) -> str | None:
    try:
        result = operation()
    except Exception as exc:
        logger.warning("%s de-index failed for %s: %s", label, item_id, exc)
        return f"{label} de-index failed."
    if result is False:
        logger.warning("%s de-index failed for %s without an exception", label, item_id)
        return f"{label} de-index failed."
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate environment variables at startup
    try:
        validate_env_vars()
    except RuntimeError as exc:
        logger.error("Environment validation failed: %s", exc)
        raise
    
    logger.info("Knowledge Workspace API starting.")
    logger.info("CORS origins: %s", allowed_origins)
    
    # Log LLM provider status
    try:
        from app.llm import get_llm_provider
        provider, status_info = get_llm_provider()
        logger.info("LLM Provider: %s (model: %s, fallback: %s)", 
                   status_info["primary_provider"], 
                   status_info["model"],
                   status_info["fallback_enabled"])
    except Exception as exc:
        logger.warning("Failed to initialize LLM provider: %s", exc)
    
    yield
    logger.info("Knowledge Workspace API stopped.")


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

__all__ = [name for name in globals() if not name.startswith("__")]
