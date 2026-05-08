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


app = FastAPI(
    title="Knowledge Workspace API",
    version=APP_VERSION,
    lifespan=lifespan,
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/api/search", response_model=ResolveItemsResponse)
async def global_search(
    q: str = "",
    types: str = "",
    status_filter: str = "",
    tag: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 200,
    current_user: dict = Depends(get_current_user),
) -> ResolveItemsResponse:
    """
    Global search across workspace entities.

    Query params:
    - q: keyword substring match
    - types: comma-separated list: knowledge,logbook,document,photo,prompt,autotest_run
    - status_filter: exact status match (e.g. draft/reviewed/verified/archived/passed/failed)
    - tag: tags substring match (where applicable)
    - date_from/date_to: ISO prefix comparisons (e.g. 2026-04-01)
    """
    user_id = current_user["sub"]
    requested_types = [part.strip() for part in str(types or "").split(",") if part.strip()]
    rows = db.search_items(
        user_id=user_id,
        keyword=q,
        item_types=requested_types,
        status=status_filter,
        tag=tag,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    items = [
        ItemSummary(
            item_id=f"{row.get('item_type')}:{row.get('item_id')}",
            item_type=str(row.get("item_type") or ""),
            title=str(row.get("title") or ""),
            status=str(row.get("status") or ""),
            created_at=str(row.get("created_at") or ""),
            updated_at=str(row.get("updated_at") or ""),
            source_type=str(row.get("source_type") or ""),
            source_ref=str(row.get("source_ref") or ""),
        )
        for row in rows
    ]
    return ResolveItemsResponse(items=items)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in allowed_origins else allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def handle_value_error(_request, exc: ValueError):
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request, exc: RequestValidationError):
    detail = "Invalid request."
    try:
        errors = exc.errors()
        if errors:
            detail = errors[0].get("msg") or detail
    except Exception:
        pass
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": detail})


@app.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", version=APP_VERSION)


@app.get("/api/health", response_model=HealthResponse)
async def api_healthcheck() -> HealthResponse:
    # CI probes /api/health, while /health is kept for backwards compatibility.
    return await healthcheck()


@app.post("/api/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Rate limit: 5 requests per minute to prevent brute force
async def login(request: Request, payload: LoginRequest) -> LoginResponse:
    _ = request
    if not db.verify_password(payload.user_id, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    user = db.get_user(payload.user_id)
    if not user or int(user["is_active"]) != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    return LoginResponse(
        access_token=create_token(
            user_id=payload.user_id,
            role=user["role"],
            display_name=user["display_name"],
        )
    )


@app.get("/api/me", response_model=MeResponse)
async def me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    return serialize_me(current_user)


@app.post("/api/docs/upload", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(""),
    tags: str = Form(""),
    current_user: dict = Depends(get_current_user),
) -> UploadDocumentResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    if not validate_file_extension(file.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")

    # Validate content using a small prefix sample (avoid reading large uploads into RAM).
    # - binary signatures: first bytes are sufficient
    # - text/markdown: validate using a bounded sample prefix
    prefix_limit = 64 * 1024 if Path(file.filename).suffix.lower() in (".txt", ".md") else 32
    file_prefix = await file.read(prefix_limit)
    await file.seek(0)
    validate_file_magic_bytes(file_prefix, file.filename)

    safe_filename = generate_safe_filename(file.filename)
    file_path = UPLOAD_DIR / safe_filename
    file_size = await stream_write_file(file, file_path)

    doc_id = str(uuid.uuid4())
    if not db.add_document(
        doc_id=doc_id,
        filename=file.filename,
        saved_filename=safe_filename,
        file_size=file_size,
        uploaded_by=current_user["sub"],
        category=str(category or ""),
        tags=str(tags or ""),
        status="reviewed",
        index_status="pending",
        index_error="",
        indexed_at="",
    ):
        safe_unlink(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist document.")

    document = db.get_document(doc_id)
    message = "Document uploaded and indexed."
    if document:
        try:
            await sync_document_index(document)
        except Exception as exc:
            logger.warning("Document indexing failed for %s: %s", doc_id, exc)
            message = "Document uploaded, but indexing failed."
        document = db.get_document(doc_id) or document
    logger.info("Uploaded document %s by %s", doc_id, current_user["sub"])
    return UploadDocumentResponse(
        **serialize_document(document).model_dump(),
        message=message,
    )


@app.get("/api/docs", response_model=list[DocumentResponse])
async def list_documents(current_user: dict = Depends(get_current_user)) -> list[DocumentResponse]:
    return [serialize_document(document) for document in db.list_documents(user_id=current_user["sub"], include_archived=False)]


@app.get("/api/docs/{doc_id}/download")
async def download_document(doc_id: str, inline: int = 0, current_user: dict = Depends(get_current_user)):
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this document.")
    file_path = UPLOAD_DIR / document["saved_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file missing on disk.")

    disposition = "inline" if int(inline) == 1 else "attachment"
    safe_name = _safe_download_filename(str(document.get("filename") or "document"))
    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type=_guess_media_type(safe_name),
        headers={"Content-Disposition": f'{disposition}; filename="{safe_name}"'},
    )


@app.get("/api/docs/{doc_id}/references", response_model=ItemLinksResponse)
async def list_document_references(doc_id: str, current_user: dict = Depends(get_current_user)) -> ItemLinksResponse:
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this document.")
    return build_links_response(item_id=item_id_from_parts("document", doc_id), user_id=current_user["sub"])


@app.patch("/api/docs/{doc_id}", response_model=MessageResponse)
async def update_document(doc_id: str, request: DocumentUpdateRequest, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    original = db.get_document(doc_id)
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if original.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit this document.")

    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No document fields provided.")

    if not db.update_document(doc_id, **updates):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update document.")

    updated = db.get_document(doc_id) or original
    warning = None
    try:
        await sync_document_index(updated)
    except Exception:
        warning = "Document indexing failed."
    return MessageResponse(message=_side_effect_warning("Document updated.", warning))


@app.delete("/api/docs/{doc_id}", response_model=MessageResponse)
async def delete_own_document(doc_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this document.")

    warning = _run_deindex_side_effect(
        label="Document",
        item_id=doc_id,
        operation=lambda: delete_from_vector_db(doc_id),
    )
    safe_unlink(UPLOAD_DIR / document["saved_filename"])
    db.delete_links(from_item_id=item_id_from_parts("document", doc_id))
    db.delete_links(to_item_id=item_id_from_parts("document", doc_id))
    db.delete_document(doc_id)
    return MessageResponse(message=_side_effect_warning("Document deleted.", warning))


@app.get("/api/knowledge/entries", response_model=list[KnowledgeEntryResponse])
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
            related_item_ids=db.list_related_item_ids(f"knowledge:{row['entry_id']}"),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
        for row in db.list_knowledge_entries(limit=50, user_id=user_id, include_archived=False)
    ]


@app.post("/api/knowledge/entries", response_model=MessageResponse)
async def create_knowledge_entry(
    request: KnowledgeEntryCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    user_id = current_user["sub"]
    entry_id = str(uuid.uuid4())
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
        source_ref=request.source_ref,
    )
    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create knowledge entry.")

    entry = db.get_knowledge_entry(entry_id)
    if entry:
        db.add_knowledge_revision(
            entry_id=entry_id,
            snapshot=knowledge_revision_snapshot(entry),
            change_note="Initial version",
            created_by=user_id,
        )
        db.set_reference_links(item_id_from_parts("knowledge", entry_id), normalize_related_item_ids(request.related_item_ids))
        maybe_link_source_item(
            from_item_id=item_id_from_parts("knowledge", entry_id),
            source_type=request.source_type,
            source_ref=request.source_ref,
        )
        warning = _run_index_side_effect(
            label="Knowledge entry",
            item_id=entry_id,
            operation=lambda: index_knowledge_entry(entry),
        )
    else:
        warning = None
    return MessageResponse(message=_side_effect_warning("Knowledge entry created.", warning))


@app.patch("/api/knowledge/entries/{entry_id}", response_model=MessageResponse)
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
    if updates:
        db.add_knowledge_revision(
            entry_id=entry_id,
            snapshot=knowledge_revision_snapshot(existing),
            change_note=change_note or "Updated knowledge entry",
            created_by=user_id,
        )
    if updates and not db.update_knowledge_entry(entry_id, **updates):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update knowledge entry.")
    if related is not None:
        db.set_reference_links(item_id_from_parts("knowledge", entry_id), normalize_related_item_ids(related))
    if "source_type" in updates or "source_ref" in updates:
        source_type = updates.get("source_type", existing.get("source_type", "manual"))
        source_ref = updates.get("source_ref", existing.get("source_ref", ""))
        sync_source_ref_link(
            from_item_id=item_id_from_parts("knowledge", entry_id),
            old_source_ref=str(existing.get("source_ref", "")),
            new_source_ref=str(source_ref),
            source_type=str(source_type),
        )

    updated = db.get_knowledge_entry(entry_id) or existing
    warning = _run_index_side_effect(
        label="Knowledge entry",
        item_id=entry_id,
        operation=lambda: index_knowledge_entry(updated),
    )
    return MessageResponse(message=_side_effect_warning("Knowledge entry updated.", warning))


@app.get("/api/knowledge/{entry_id}/revisions", response_model=list[KnowledgeRevisionResponse])
async def list_knowledge_revisions(entry_id: str, current_user: dict = Depends(get_current_user)) -> list[KnowledgeRevisionResponse]:
    entry = db.get_knowledge_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found.")
    if entry.get("created_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access these revisions.")
    return [serialize_knowledge_revision(row) for row in db.list_knowledge_revisions(entry_id, created_by=current_user["sub"])]


@app.get("/api/knowledge/{entry_id}/revisions/{revision_id}/diff", response_model=KnowledgeRevisionDiffResponse)
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


@app.post("/api/knowledge/{entry_id}/revisions/{revision_id}/restore", response_model=MessageResponse)
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore knowledge revision.")

    restored = db.get_knowledge_entry(entry_id) or entry
    warning = _run_index_side_effect(
        label="Knowledge entry",
        item_id=entry_id,
        operation=lambda: index_knowledge_entry(restored),
    )
    return MessageResponse(message=_side_effect_warning("Knowledge revision restored.", warning))


@app.get("/api/logbook/entries", response_model=list[LogbookEntryResponse])
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
            related_item_ids=db.list_related_item_ids(f"logbook:{row['entry_id']}"),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
        for row in db.list_logbook_entries(limit=100, user_id=user_id, include_archived=False)
    ]


@app.post("/api/logbook/entries", response_model=MessageResponse)
async def create_logbook_entry(
    request: LogbookEntryCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    user_id = current_user["sub"]
    entry_id = str(uuid.uuid4())
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
        source_ref=request.source_ref,
        created_by=user_id,
    )
    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create logbook entry.")

    entry = db.get_logbook_entry(entry_id)
    if entry:
        db.set_reference_links(item_id_from_parts("logbook", entry_id), normalize_related_item_ids(request.related_item_ids))
        maybe_link_source_item(
            from_item_id=item_id_from_parts("logbook", entry_id),
            source_type=request.source_type,
            source_ref=request.source_ref,
        )
        warning = _run_index_side_effect(
            label="Logbook entry",
            item_id=entry_id,
            operation=lambda: index_logbook_entry(entry),
        )
    else:
        warning = None
    return MessageResponse(message=_side_effect_warning("Logbook entry created.", warning))


@app.patch("/api/logbook/entries/{entry_id}", response_model=MessageResponse)
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
    if updates and not db.update_logbook_entry(entry_id, **updates):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update logbook entry.")
    if related is not None:
        db.set_reference_links(item_id_from_parts("logbook", entry_id), normalize_related_item_ids(related))
    if "source_type" in updates or "source_ref" in updates:
        source_type = updates.get("source_type", existing.get("source_type", "manual"))
        source_ref = updates.get("source_ref", existing.get("source_ref", ""))
        sync_source_ref_link(
            from_item_id=item_id_from_parts("logbook", entry_id),
            old_source_ref=str(existing.get("source_ref", "")),
            new_source_ref=str(source_ref),
            source_type=str(source_type),
        )

    updated = db.get_logbook_entry(entry_id) or existing
    warning = _run_index_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: index_logbook_entry(updated),
    )
    return MessageResponse(message=_side_effect_warning("Logbook entry updated.", warning))


@app.post("/api/logbook/entries/{entry_id}/promote-to-knowledge", response_model=PromoteToKnowledgeResponse)
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

    # Canonical promote contract: logbook -> knowledge is the produced direction.
    db.add_link(f"logbook:{entry_id}", f"knowledge:{knowledge_id}", link_type="produced")
    # Keep the reverse relation for traceability and backwards compatibility.
    db.add_link(f"knowledge:{knowledge_id}", f"logbook:{entry_id}", link_type="derived_from")
    for related in db.list_related_item_ids(f"logbook:{entry_id}"):
        db.add_link(f"knowledge:{knowledge_id}", related, link_type="references")

    # Archive the original problem draft so it doesn't clutter day-to-day views.
    db.update_logbook_entry(entry_id, status="archived")

    # Delete the old logbook entry from vector index to prevent search pollution
    # (archived entries should not appear in search results)
    warnings: list[str] = []
    logbook_warning = _run_deindex_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: delete_from_kb_vector_db(f"logbook:{entry_id}"),
    )
    if logbook_warning:
        warnings.append(logbook_warning)

    promoted = db.get_knowledge_entry(knowledge_id)
    if promoted:
        knowledge_warning = _run_index_side_effect(
            label="Knowledge entry",
            item_id=knowledge_id,
            operation=lambda: index_knowledge_entry(promoted),
        )
        if knowledge_warning:
            warnings.append(knowledge_warning)
    # Re-index the archived logbook (with updated status) for completeness
    archived_logbook = db.get_logbook_entry(entry_id) or logbook
    archived_warning = _run_index_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: index_logbook_entry(archived_logbook),
    )
    if archived_warning:
        warnings.append(archived_warning)

    # If this logbook was derived from an AutoTest run, mark the run as having a solution.
    run_id = str(logbook.get("run_id") or "").strip()
    if run_id:
        db.update_autotest_run(run_id, solution_entry_id=knowledge_id)

    return PromoteToKnowledgeResponse(
        message=_side_effect_warning("Promoted to verified knowledge entry.", " ".join(warnings)),
        knowledge_entry_id=knowledge_id,
    )


@app.delete("/api/logbook/entries/{entry_id}", response_model=MessageResponse)
async def delete_logbook_entry(entry_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    user_id = current_user["sub"]
    existing = db.get_logbook_entry(entry_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    if existing.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this logbook entry.")
    item_id = f"logbook:{entry_id}"
    warning = _run_deindex_side_effect(
        label="Logbook entry",
        item_id=entry_id,
        operation=lambda: delete_from_kb_vector_db(item_id),
    )
    db.delete_links(from_item_id=item_id)
    db.delete_links(to_item_id=item_id)
    if not db.delete_logbook_entry(entry_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    return MessageResponse(message=_side_effect_warning("Logbook entry deleted.", warning))


PHOTO_DIR = settings.PHOTO_DIR


def validate_image_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def sniff_image_type(header: bytes) -> str | None:
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "gif"
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "webp"
    return None


@app.post("/api/photos/upload", response_model=UploadPhotoResponse)
async def upload_photo(
    file: UploadFile = File(...),
    tags: str = Form(""),
    description: str = Form(""),
    current_user: dict = Depends(get_current_user),
) -> UploadPhotoResponse:
    user_id = current_user["sub"]
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    if not validate_image_extension(file.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type.")
    if file.content_type and not str(file.content_type).lower().startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image content type.")

    # Validate image using magic bytes (more robust than extension check alone),
    # using only a small header prefix to avoid loading large uploads into RAM.
    header = await file.read(32)
    await file.seek(0)
    if sniff_image_type(header) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file does not look like an image.")

    safe_filename = generate_safe_filename(file.filename)
    file_path = PHOTO_DIR / safe_filename
    file_size = await stream_write_file(file, file_path)

    # Extract text from image using OCR
    ocr_text = extract_text_from_image(file_path)

    photo_id = str(uuid.uuid4())
    if not db.add_photo(
        photo_id=photo_id,
        filename=file.filename,
        saved_filename=safe_filename,
        tags=str(tags or ""),
        description=str(description or ""),
        ocr_text=ocr_text,
        file_size=file_size,
        uploaded_by=user_id,
        status="reviewed",
    ):
        safe_unlink(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist photo.")

    photo = db.get_photo(photo_id)
    if photo:
        warning = _run_index_side_effect(
            label="Photo",
            item_id=photo_id,
            operation=lambda: index_photo(photo),
        )
    else:
        warning = None

    photo_row = db.get_photo(photo_id) or {}
    return UploadPhotoResponse(
        id=photo_id,
        filename=str(photo_row.get("filename", "")),
        tags=str(photo_row.get("tags", "")),
        description=str(photo_row.get("description", "")),
        ocr_text=str(photo_row.get("ocr_text", "")),
        status=str(photo_row.get("status", "reviewed") or "reviewed"),
        uploaded_by=str(photo_row.get("uploaded_by") or ""),
        file_size=int(photo_row.get("file_size", 0)),
        created_at=str(photo_row.get("created_at", "")),
        updated_at=str(photo_row.get("updated_at", "")),
        message=_side_effect_warning("Photo uploaded.", warning),
    )


@app.get("/api/photos", response_model=list[PhotoResponse])
async def list_photos(current_user: dict = Depends(get_current_user)) -> list[PhotoResponse]:
    user_id = current_user["sub"]
    return [
        PhotoResponse(
            id=row["photo_id"],
            filename=row.get("filename", ""),
            tags=row.get("tags", ""),
            description=row.get("description", ""),
            ocr_text=row.get("ocr_text", ""),
            status=row.get("status", "reviewed") or "reviewed",
            uploaded_by=row.get("uploaded_by"),
            file_size=int(row.get("file_size", 0)),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
        for row in db.list_photos(limit=200, user_id=user_id, include_archived=False)
    ]


@app.get("/api/photos/{photo_id}/download")
async def download_photo(photo_id: str, inline: int = 1, current_user: dict = Depends(get_current_user)):
    photo = db.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if photo.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this photo.")
    file_path = PHOTO_DIR / photo["saved_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo file missing on disk.")

    disposition = "inline" if int(inline) == 1 else "attachment"
    safe_name = _safe_download_filename(str(photo.get("filename") or "photo"))
    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type=_guess_media_type(safe_name),
        headers={"Content-Disposition": f'{disposition}; filename="{safe_name}"'},
    )


@app.patch("/api/photos/{photo_id}", response_model=MessageResponse)
async def update_photo(photo_id: str, request: PhotoUpdateRequest, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    original = db.get_photo(photo_id)
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if original.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit this photo.")

    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No photo fields provided.")
    if not db.update_photo(photo_id, **updates):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update photo.")

    updated = db.get_photo(photo_id) or original
    warning = _run_index_side_effect(
        label="Photo",
        item_id=photo_id,
        operation=lambda: index_photo(updated),
    )
    return MessageResponse(message=_side_effect_warning("Photo updated.", warning))


@app.delete("/api/photos/{photo_id}", response_model=MessageResponse)
async def delete_photo(photo_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    photo = db.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if photo.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this photo.")
    warning = _run_deindex_side_effect(
        label="Photo",
        item_id=photo_id,
        operation=lambda: delete_from_kb_vector_db(item_id_from_parts("photo", photo_id)),
    )
    safe_unlink(PHOTO_DIR / photo["saved_filename"])
    db.delete_links(from_item_id=item_id_from_parts("photo", photo_id))
    db.delete_links(to_item_id=item_id_from_parts("photo", photo_id))
    db.delete_photo(photo_id)
    return MessageResponse(message=_side_effect_warning("Photo deleted.", warning))


@app.get("/api/photos/{photo_id}/references", response_model=ItemLinksResponse)
async def list_photo_references(photo_id: str, current_user: dict = Depends(get_current_user)) -> ItemLinksResponse:
    photo = db.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if photo.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this photo.")
    return build_links_response(item_id=item_id_from_parts("photo", photo_id), user_id=current_user["sub"])


@app.get("/api/item-links", response_model=ItemLinksResponse)
async def list_item_links(item_id: str, current_user: dict = Depends(get_current_user)) -> ItemLinksResponse:
    return build_links_response(item_id=str(item_id or "").strip(), user_id=current_user["sub"])


@app.post("/api/items/resolve", response_model=ResolveItemsResponse)
async def resolve_items(request: ResolveItemsRequest, current_user: dict = Depends(get_current_user)) -> ResolveItemsResponse:
    user_id = current_user["sub"]
    items: list[ItemSummary] = []
    for item_id in normalize_related_item_ids(request.item_ids):
        summary = resolve_item_summary(item_id=item_id, user_id=user_id)
        if summary:
            items.append(summary)
    return ResolveItemsResponse(items=items)


@app.post("/api/qa", response_model=QAResponse)
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute to prevent abuse
async def qa(request: Request, payload: QARequest, current_user: dict = Depends(get_current_user)) -> QAResponse:
    _ = request
    answer, sources = await perform_qa(payload.question, current_user["sub"], db)
    logger.info("QA request by %s returned %s sources", current_user["sub"], len(sources))
    return QAResponse(answer=answer, sources=sources)


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, current_user: dict = Depends(get_current_user)) -> GenerateResponse:
    content = await generate_form(request.template_type, request.inputs, current_user["sub"])
    return GenerateResponse(content=content)


@app.get("/api/prompts", response_model=list[SavedPromptResponse])
async def list_saved_prompts(current_user: dict = Depends(get_current_user)) -> list[SavedPromptResponse]:
    user_id = current_user["sub"]
    return [
        SavedPromptResponse(
            id=row.get("prompt_id", ""),
            title=row.get("title", ""),
            content=row.get("content", ""),
            tags=row.get("tags", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
            index_status="indexed",
            index_error="",
        )
        for row in db.list_saved_prompts(user_id=user_id, limit=200)
    ]


@app.post("/api/prompts", response_model=SavedPromptResponse)
async def create_saved_prompt(request: SavedPromptCreateRequest, current_user: dict = Depends(get_current_user)) -> SavedPromptResponse:
    user_id = current_user["sub"]
    prompt_id = str(uuid.uuid4())
    ok = db.add_saved_prompt(
        prompt_id=prompt_id,
        title=request.title,
        content=request.content,
        tags=request.tags,
        created_by=user_id,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create prompt.")
    prompt = db.get_saved_prompt(prompt_id) or {}
    if prompt:
        warning = _run_index_side_effect(
            label="Prompt",
            item_id=prompt_id,
            operation=lambda: index_saved_prompt(prompt),
        )
    else:
        warning = None
    return SavedPromptResponse(
        id=prompt_id,
        title=str(prompt.get("title", "")),
        content=str(prompt.get("content", "")),
        tags=str(prompt.get("tags", "")),
        created_at=str(prompt.get("created_at", "")),
        updated_at=str(prompt.get("updated_at", "")),
        index_status="failed" if warning else "indexed",
        index_error=str(warning or ""),
    )


@app.delete("/api/prompts/{prompt_id}", response_model=MessageResponse)
async def delete_saved_prompt(prompt_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    user_id = current_user["sub"]
    prompt = db.get_saved_prompt(prompt_id)
    if not prompt or int(prompt.get("is_active", 1)) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found.")
    if prompt.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this prompt.")
    warning = _run_deindex_side_effect(
        label="Prompt",
        item_id=prompt_id,
        operation=lambda: delete_from_kb_vector_db(f"prompt:{prompt_id}"),
    )
    db.delete_links(from_item_id=item_id_from_parts("prompt", prompt_id))
    db.delete_links(to_item_id=item_id_from_parts("prompt", prompt_id))
    if not db.delete_saved_prompt(prompt_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete prompt.")
    return MessageResponse(message=_side_effect_warning("Prompt deleted.", warning))


@app.get("/api/meta/templates")
async def list_templates(current_user: dict = Depends(get_current_user)) -> dict[str, list[dict[str, object]]]:
    _ = current_user
    return {
        "templates": [
            {"value": key, "label": key.replace("_", " ").title(), "fields": value["fields"]}
            for key, value in FORM_TEMPLATES.items()
        ]
    }
