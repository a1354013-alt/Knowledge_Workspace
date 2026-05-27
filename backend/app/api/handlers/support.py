"""Deprecated handler compatibility exports.

This module intentionally stays small. New code should import concrete
dependencies from `app.api.common`, `app.api.runtime`, `app.dependencies`,
`app.models`, `app.services.*`, or `app.utils` directly.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.common import (
    KNOWLEDGE_REVISION_FIELDS,
    build_links_response,
    classify_index_failure,
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
from app.api.runtime import (
    APP_VERSION,
    PHOTO_DIR,
    UPLOAD_DIR,
    allow_credentials,
    allowed_origins,
    create_token,
    db,
    lifespan,
    limiter,
    logger,
    settings,
    validate_env_vars,
)
from app.database import delete_from_kb_vector_db, delete_from_vector_db
from app.dependencies import get_current_user
from app.kb_index import index_knowledge_entry, index_logbook_entry, index_photo, index_saved_prompt
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
from app.services import process_file
from app.services.core import FORM_TEMPLATES, generate_form, perform_qa
from app.services.indexing_service import sync_document_index, sync_prompt_index
from app.utils import generate_safe_filename, stream_write_file, validate_file_extension, validate_file_magic_bytes

logging = logging


async def sync_document_index_in_background(document: dict) -> None:
    await asyncio.to_thread(sync_document_index, document)


_safe_download_filename = safe_download_filename
_guess_media_type = guess_media_type
_side_effect_warning = side_effect_warning
_run_index_side_effect = run_index_side_effect
_run_deindex_side_effect = run_deindex_side_effect

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
    "asyncio",
    "build_links_response",
    "classify_index_failure",
    "create_token",
    "db",
    "delete_from_kb_vector_db",
    "delete_from_vector_db",
    "extract_text_from_image",
    "generate_form",
    "generate_safe_filename",
    "get_current_user",
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
    "sync_document_index_in_background",
    "sync_prompt_index",
    "sync_source_ref_link",
    "utc_now_iso",
    "uuid",
    "validate_env_vars",
    "validate_file_extension",
    "validate_file_magic_bytes",
)
