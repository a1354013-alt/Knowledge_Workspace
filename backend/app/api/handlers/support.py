import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.common import (
    KNOWLEDGE_REVISION_FIELDS,
    build_links_response,
    guess_media_type,
    item_id_from_parts,
    knowledge_revision_snapshot,
    maybe_link_source_item,
    normalize_related_item_ids,
    resolve_item_summary,
    run_deindex_side_effect,
    run_index_side_effect,
    safe_download_filename,
    safe_unlink,
    serialize_document,
    serialize_knowledge_revision,
    serialize_me,
    side_effect_warning,
    sync_source_ref_link,
    utc_now_iso,
)
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

_safe_download_filename = safe_download_filename
_guess_media_type = guess_media_type


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

_side_effect_warning = side_effect_warning
_run_index_side_effect = run_index_side_effect
_run_deindex_side_effect = run_deindex_side_effect


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

    try:
        from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

        recovered = recover_interrupted_autotest_runs()
        if recovered:
            logger.warning("Recovered %s stale AutoTest run(s) after startup.", recovered)
    except Exception as exc:
        logger.warning("AutoTest startup recovery failed: %s", exc)
    
    yield
    try:
        from app.services.autotest import shutdown_autotest_workers

        shutdown_autotest_workers()
    except Exception as exc:
        logger.warning("AutoTest worker shutdown failed: %s", exc)
    logger.info("Knowledge Workspace API stopped.")


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
__all__ = (
    "APP_VERSION",
    "CORSMiddleware",
    "Depends",
    "DocumentResponse",
    "DocumentUpdateRequest",
    "FORM_TEMPLATES",
    "FastAPI",
    "File",
    "FileResponse",
    "Form",
    "GenerateRequest",
    "GenerateResponse",
    "HTTPException",
    "HealthResponse",
    "ItemLinkResolved",
    "ItemLinksResponse",
    "ItemSummary",
    "JSONResponse",
    "KNOWLEDGE_REVISION_FIELDS",
    "KnowledgeEntryCreateRequest",
    "KnowledgeEntryResponse",
    "KnowledgeEntryUpdateRequest",
    "KnowledgeRevisionDiffResponse",
    "KnowledgeRevisionResponse",
    "Limiter",
    "LogbookEntryCreateRequest",
    "LogbookEntryResponse",
    "LogbookEntryUpdateRequest",
    "LoginRequest",
    "LoginResponse",
    "MeResponse",
    "MessageResponse",
    "PHOTO_DIR",
    "Path",
    "PhotoResponse",
    "PhotoUpdateRequest",
    "PromoteToKnowledgeResponse",
    "QARequest",
    "QAResponse",
    "RateLimitExceeded",
    "Request",
    "RequestValidationError",
    "ResolveItemsRequest",
    "ResolveItemsResponse",
    "SavedPromptCreateRequest",
    "SavedPromptResponse",
    "UPLOAD_DIR",
    "UploadDocumentResponse",
    "UploadFile",
    "UploadPhotoResponse",
    "_guess_media_type",
    "_rate_limit_exceeded_handler",
    "_run_deindex_side_effect",
    "_run_index_side_effect",
    "_safe_download_filename",
    "_side_effect_warning",
    "allow_credentials",
    "allowed_origins",
    "asynccontextmanager",
    "asyncio",
    "build_links_response",
    "create_token",
    "db",
    "delete_from_kb_vector_db",
    "delete_from_vector_db",
    "extract_text_from_image",
    "generate_form",
    "generate_safe_filename",
    "get_current_user",
    "get_remote_address",
    "guess_media_type",
    "index_knowledge_entry",
    "index_logbook_entry",
    "index_photo",
    "index_saved_prompt",
    "item_id_from_parts",
    "knowledge_revision_snapshot",
    "lifespan",
    "limiter",
    "logger",
    "logging",
    "maybe_link_source_item",
    "normalize_related_item_ids",
    "perform_qa",
    "process_file",
    "resolve_item_summary",
    "run_deindex_side_effect",
    "run_index_side_effect",
    "safe_download_filename",
    "safe_unlink",
    "serialize_document",
    "serialize_knowledge_revision",
    "serialize_me",
    "settings",
    "side_effect_warning",
    "status",
    "stream_write_file",
    "sync_document_index",
    "sync_source_ref_link",
    "utc_now_iso",
    "uuid",
    "validate_env_vars",
    "validate_file_extension",
    "validate_file_magic_bytes",
)
