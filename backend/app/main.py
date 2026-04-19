from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import shutil
import subprocess
import tempfile
import zipfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.auth import create_token
from app.database import DocumentDatabase, delete_from_kb_vector_db, delete_from_vector_db
from app.dependencies import get_current_user
from app.kb_index import index_knowledge_entry, index_logbook_entry, index_photo, index_saved_prompt
from app.llm import get_llm_provider, validate_env_vars
from app.models import (
    AutoTestRunListItemResponse,
    AutoTestRunResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    ItemLinksResponse,
    ItemLinkResolved,
    ItemSummary,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    KnowledgeEntryCreateRequest,
    KnowledgeEntryResponse,
    KnowledgeEntryUpdateRequest,
    LoginRequest,
    LoginResponse,
    LogbookEntryCreateRequest,
    LogbookEntryResponse,
    LogbookEntryUpdateRequest,
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
    SettingsLLMResponse,
    UploadDocumentResponse,
    UploadPhotoResponse,
)
from app.ocr_service import extract_text_from_image
from app.services import FORM_TEMPLATES, generate_form, perform_qa, process_file
from app.utils import generate_safe_filename, get_env_list, stream_write_file, validate_file_extension


load_dotenv()


def read_app_version() -> str:
    try:
        repo_root = Path(__file__).resolve().parents[2]
        version_path = repo_root / "VERSION"
        value = version_path.read_text(encoding="utf-8").strip()
        return value or "0.0.0"
    except Exception:
        return "0.0.0"


APP_VERSION = read_app_version()
logger = logging.getLogger("enterprise_ai")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

db = DocumentDatabase(os.getenv("DATABASE_PATH", "documents.db"))

allowed_origins = get_env_list("ALLOWED_ORIGINS", ["http://localhost:5173"])
allow_credentials = "*" not in allowed_origins


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
                link_type=str(link.get("link_type", "") or "related"),
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


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        max_files = int(os.getenv("AUTOTEST_MAX_FILES", "5000"))
        max_unzipped_bytes = int(os.getenv("AUTOTEST_MAX_UNZIPPED_BYTES", str(250 * 1024 * 1024)))
        total_files = 0
        total_bytes = 0
        for member in archive.infolist():
            total_files += 1
            if total_files > max_files:
                raise ValueError("Zip contains too many files.")

            if member.is_dir():
                continue

            total_bytes += int(getattr(member, "file_size", 0) or 0)
            if total_bytes > max_unzipped_bytes:
                raise ValueError("Zip expands beyond allowed size.")

            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("Zip contains unsafe paths.")
            # Block Windows drive-letter / UNC style payloads even on Unix hosts.
            if ":" in member_path.parts[0] or str(member.filename).startswith(("\\\\", "//")):
                raise ValueError("Zip contains unsafe paths.")
            # Block symlinks (zipinfo external attributes can mark symlinks on Unix).
            is_symlink = (member.external_attr >> 16) & 0o170000 == 0o120000
            if is_symlink:
                raise ValueError("Zip contains symlinks, which are not allowed.")
        archive.extractall(dest_dir)


def _run_command(*, argv: list[str], cwd: Path, timeout_seconds: int) -> tuple[int, str, str]:
    if not argv:
        raise ValueError("Missing command argv.")
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=env,
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return int(completed.returncode), stdout, stderr


def _walk_dirs_for_markers(base_dir: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    skip_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "dist",
        "build",
        ".venv",
        "venv",
        ".mypy_cache",
    }
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        files_set = {name.lower() for name in files}
        root_path = Path(root)
        if "package.json" in files_set:
            candidates.append(("node", root_path))
        if "pyproject.toml" in files_set or "requirements.txt" in files_set:
            candidates.append(("python", root_path))
    return candidates


def find_project_root_on_disk(extracted_root: Path) -> tuple[str, Path]:
    candidates = _walk_dirs_for_markers(extracted_root)
    if not candidates:
        return "unknown", extracted_root
    scored: list[tuple[int, int, str, Path]] = []
    for project_type, path in candidates:
        try:
            depth = len(path.relative_to(extracted_root).parts)
        except ValueError:
            depth = 9999
        # prefer node over python only when tie
        tie_breaker = 0 if project_type == "node" else 1
        scored.append((depth, tie_breaker, project_type, path))
    scored.sort(key=lambda row: (row[0], row[1]))
    best = scored[0]
    return best[2], best[3]


AUTOTEST_SUGGEST_SYSTEM_PROMPT = """You are a local-first engineering assistant.

Rules:
1. Do not invent outputs or versions. Use only the provided AutoTest logs.
2. Prefer actionable, reproducible steps (commands, filenames, config keys).
3. If logs are insufficient, say what extra info is needed.
"""


async def suggest_fix_from_autotest(*, project_type: str, failed_step: str, command: str, output: str) -> str:
    provider, _status = get_llm_provider()
    prompt = (
        "AutoTest failure analysis.\n\n"
        f"Project type: {project_type}\n"
        f"Failed step: {failed_step}\n"
        f"Command: {command}\n\n"
        "Output (stdout+stderr):\n"
        f"{output[:6000]}\n\n"
        "Write:\n"
        "- Error summary (1-3 sentences)\n"
        "- Likely root causes (bullets)\n"
        "- Fix plan (numbered steps)\n"
        "- Verification steps (bullets)\n"
        "- Suggested tags (comma-separated)\n"
    )
    try:
        response = await provider.generate(system=AUTOTEST_SUGGEST_SYSTEM_PROMPT, prompt=prompt, temperature=0.2)
        text = (response.text or "").strip()
        if text:
            return text
    except Exception as exc:
        logger.warning("AutoTest suggestion unavailable; using fallback: %s", exc)
    return (
        "Error summary:\n"
        f"- AutoTest failed at '{failed_step}'.\n\n"
        "Fix plan:\n"
        "- Re-run the failed command locally and capture full logs.\n"
        "- Check dependency install/build/test configuration for the project type.\n"
        "- Apply a minimal fix and re-run AutoTest.\n\n"
        "Verification steps:\n"
        "- Re-run AutoTest and confirm all steps pass.\n\n"
        "Suggested tags:\n"
        "autotest,build,test,lint\n"
    )


def autotest_commands(project_type: str) -> dict[str, list[str]]:
    if project_type == "node":
        return {
            "install": ["npm", "ci", "--no-audit", "--no-fund"],
            "build": ["npm", "run", "build"],
            "test": ["npm", "test"],
            "lint": ["npm", "run", "lint"],
        }
    if project_type == "python":
        return {
            "install": ["python", "-m", "pip", "install", "--no-input", "-r", "requirements.txt"],
            "build": ["python", "-m", "compileall", "."],
            "test": ["pytest"],
            "lint": ["python", "-m", "compileall", "."],
        }
    return {
        "install": ["echo", "install (simulated)"],
        "build": ["echo", "build (simulated)"],
        "test": ["echo", "test (simulated)"],
        "lint": ["echo", "lint (simulated)"],
    }


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
        return

    file_path = UPLOAD_DIR / document["saved_filename"]
    if not file_path.exists():
        raise FileNotFoundError(f"Document file is missing: {file_path}")

    await asyncio.to_thread(
        process_file,
        document["doc_id"],
        str(file_path),
        document["filename"],
        str(document.get("uploaded_by") or ""),
        str(document.get("status") or "reviewed"),
        int(document["is_active"]),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate environment variables at startup
    try:
        validate_env_vars()
    except RuntimeError as exc:
        logger.error("Environment validation failed: %s", exc)
        raise
    
    logger.info("Local AI Engineer Workspace API starting.")
    logger.info("CORS origins: %s", allowed_origins)
    
    # Log LLM provider status
    try:
        from app.llm import get_llm_provider
        provider, status_info = get_llm_provider()
        logger.info("LLM Provider: %s (model: %s, fallback: %s)", 
                   status_info["provider"], 
                   status_info["model"],
                   status_info["fallback_mode"])
    except Exception as exc:
        logger.warning("Failed to initialize LLM provider: %s", exc)
    
    yield
    logger.info("Local AI Engineer Workspace API stopped.")


app = FastAPI(
    title="Local AI Engineer Workspace API",
    version=APP_VERSION,
    lifespan=lifespan,
)


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


@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    if not db.verify_password(request.user_id, request.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    user = db.get_user(request.user_id)
    if not user or int(user["is_active"]) != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    return LoginResponse(
        access_token=create_token(
            user_id=request.user_id,
            role=user["role"],
            display_name=user["display_name"],
        )
    )


@app.get("/api/me", response_model=MeResponse)
async def me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    return serialize_me(current_user)


@app.get("/api/settings/llm", response_model=SettingsLLMResponse)
async def llm_settings(current_user: dict = Depends(get_current_user)) -> SettingsLLMResponse:
    _ = current_user
    provider, status_payload = get_llm_provider()
    healthy = await provider.healthcheck()
    return SettingsLLMResponse(
        provider=str(status_payload.get("provider", "")),
        model=str(status_payload.get("model", "")),
        base_url=str(status_payload.get("base_url", "")),
        healthy=bool(healthy),
        fallback_mode=bool(status_payload.get("fallback_mode", False)),
    )


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
    ):
        safe_unlink(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist document.")

    document = db.get_document(doc_id)
    if document:
        await sync_document_index(document)
    logger.info("Uploaded document %s by %s", doc_id, current_user["sub"])
    return UploadDocumentResponse(
        **serialize_document(document).model_dump(),
        message="Document uploaded and indexed.",
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
    await sync_document_index(updated)
    return MessageResponse(message="Document updated.")


@app.delete("/api/docs/{doc_id}", response_model=MessageResponse)
async def delete_own_document(doc_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this document.")

    delete_from_vector_db(doc_id)
    safe_unlink(UPLOAD_DIR / document["saved_filename"])
    db.delete_links(from_item_id=item_id_from_parts("document", doc_id))
    db.delete_links(to_item_id=item_id_from_parts("document", doc_id))
    db.delete_document(doc_id)
    return MessageResponse(message="Document deleted.")


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
        db.set_reference_links(item_id_from_parts("knowledge", entry_id), normalize_related_item_ids(request.related_item_ids))
        maybe_link_source_item(
            from_item_id=item_id_from_parts("knowledge", entry_id),
            source_type=request.source_type,
            source_ref=request.source_ref,
        )
        index_knowledge_entry(entry)
    return MessageResponse(message="Knowledge entry created.")


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
    if not updates and related is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No knowledge fields provided.")
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
    index_knowledge_entry(updated)
    return MessageResponse(message="Knowledge entry updated.")


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
            source_type=row.get("source_type", ""),
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
        index_logbook_entry(entry)
    return MessageResponse(message="Logbook entry created.")


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
    index_logbook_entry(updated)
    return MessageResponse(message="Logbook entry updated.")


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

    # Link: knowledge <-> logbook + carry existing references
    db.add_link(f"knowledge:{knowledge_id}", f"logbook:{entry_id}", link_type="derived_from")
    for related in db.list_related_item_ids(f"logbook:{entry_id}"):
        db.add_link(f"knowledge:{knowledge_id}", related, link_type="references")

    # Archive the original problem draft so it doesn't clutter day-to-day views.
    db.update_logbook_entry(entry_id, status="archived")

    promoted = db.get_knowledge_entry(knowledge_id)
    if promoted:
        index_knowledge_entry(promoted)
    index_logbook_entry(db.get_logbook_entry(entry_id) or logbook)

    # If this logbook was derived from an AutoTest run, mark the run as having a solution.
    run_id = str(logbook.get("run_id") or "").strip()
    if run_id:
        db.update_autotest_run(run_id, solution_entry_id=knowledge_id)

    return PromoteToKnowledgeResponse(message="Promoted to verified knowledge entry.", knowledge_entry_id=knowledge_id)


@app.delete("/api/logbook/entries/{entry_id}", response_model=MessageResponse)
async def delete_logbook_entry(entry_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    user_id = current_user["sub"]
    existing = db.get_logbook_entry(entry_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    if existing.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this logbook entry.")
    item_id = f"logbook:{entry_id}"
    delete_from_kb_vector_db(item_id)
    db.delete_links(from_item_id=item_id)
    db.delete_links(to_item_id=item_id)
    if not db.delete_logbook_entry(entry_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found.")
    return MessageResponse(message="Logbook entry deleted.")


PHOTO_DIR = Path(os.getenv("PHOTO_DIR", "./photos"))
PHOTO_DIR.mkdir(parents=True, exist_ok=True)


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
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    if not validate_image_extension(file.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type.")
    if file.content_type and not str(file.content_type).lower().startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image content type.")

    header = await file.read(32)
    try:
        await file.seek(0)
    except Exception:
        try:
            file.file.seek(0)
        except Exception:
            pass
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
        index_photo(photo)

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
        message="Photo uploaded.",
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
    index_photo(updated)
    return MessageResponse(message="Photo updated.")


@app.delete("/api/photos/{photo_id}", response_model=MessageResponse)
async def delete_photo(photo_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    photo = db.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if photo.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this photo.")
    delete_from_kb_vector_db(item_id_from_parts("photo", photo_id))
    safe_unlink(PHOTO_DIR / photo["saved_filename"])
    db.delete_links(from_item_id=item_id_from_parts("photo", photo_id))
    db.delete_links(to_item_id=item_id_from_parts("photo", photo_id))
    db.delete_photo(photo_id)
    return MessageResponse(message="Photo deleted.")


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
async def qa(request: QARequest, current_user: dict = Depends(get_current_user)) -> QAResponse:
    answer, sources = await perform_qa(request.question, current_user["sub"])
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
        index_saved_prompt(prompt)
    return SavedPromptResponse(
        id=prompt_id,
        title=str(prompt.get("title", "")),
        content=str(prompt.get("content", "")),
        tags=str(prompt.get("tags", "")),
        created_at=str(prompt.get("created_at", "")),
        updated_at=str(prompt.get("updated_at", "")),
    )


@app.delete("/api/prompts/{prompt_id}", response_model=MessageResponse)
async def delete_saved_prompt(prompt_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    user_id = current_user["sub"]
    prompt = db.get_saved_prompt(prompt_id)
    if not prompt or int(prompt.get("is_active", 1)) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found.")
    if prompt.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this prompt.")
    delete_from_kb_vector_db(f"prompt:{prompt_id}")
    db.delete_links(from_item_id=item_id_from_parts("prompt", prompt_id))
    db.delete_links(to_item_id=item_id_from_parts("prompt", prompt_id))
    if not db.delete_saved_prompt(prompt_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete prompt.")
    return MessageResponse(message="Prompt deleted.")


@app.post("/api/autotest/run", response_model=AutoTestRunResponse)
async def run_autotest(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> AutoTestRunResponse:
    user_id = current_user["sub"]
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .zip uploads are supported.")

    autotest_dir = Path(os.getenv("AUTOTEST_DIR", "./autotest_uploads"))
    autotest_dir.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid.uuid4())
    safe_name = f"{run_id}.zip"
    zip_path = autotest_dir / safe_name
    await stream_write_file(file, zip_path, max_size=200 * 1024 * 1024)

    project_name = file.filename
    project_type = detect_project_type(zip_path)
    fail_step = detect_fail_step(zip_path)
    commands = autotest_commands(project_type)
    requested_mode = os.getenv("AUTOTEST_MODE", "real").strip().lower()
    timeout_seconds = int(os.getenv("AUTOTEST_STEP_TIMEOUT_SECONDS", "300"))

    if not db.add_autotest_run(
        run_id=run_id,
        source_type="upload",
        source_ref=file.filename,
        execution_mode="real" if requested_mode == "real" else "simulated",
        project_type_detected=str(project_type),
        working_directory="",
        project_name=project_name,
        project_type=project_type,
        status="queued",
        summary="",
        suggestion="",
        prompt_output="",
        created_by=user_id,
    ):
        safe_unlink(zip_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create autotest run.")

    steps_def: list[tuple[str, list[str]]] = [
        ("install", commands["install"]),
        ("build", commands["build"]),
        ("test", commands["test"]),
        ("lint", commands["lint"]),
    ]
    commands_by_step = {name: " ".join(argv) for name, argv in steps_def}
    step_ids: dict[str, str] = {}
    for name, argv in steps_def:
        step_id = str(uuid.uuid4())
        step_ids[name] = step_id
        db.add_autotest_step(
            step_id=step_id,
            run_id=run_id,
            name=name,
            command=" ".join(argv),
            status="queued",
        )

    db.update_autotest_run(run_id, status="running")

    overall_ok = True
    failed_step_name: str | None = None
    outputs: dict[str, str] = {}
    work_dir = Path(tempfile.mkdtemp(prefix=f"autotest_{run_id}_", dir=str(autotest_dir)))
    extracted_dir = work_dir / "src"
    working_dir = extracted_dir
    project_type_detected = project_type
    execution_mode = "real" if requested_mode == "real" else "simulated"
    try:
        if requested_mode == "real":
            safe_extract_zip(zip_path, extracted_dir)
            project_type_detected, working_dir = find_project_root_on_disk(extracted_dir)
            execution_mode = "real" if project_type_detected in {"node", "python"} else "simulated"
        else:
            execution_mode = "simulated"

        working_dir_rel = "."
        try:
            working_dir_rel = working_dir.relative_to(extracted_dir).as_posix() or "."
        except Exception:
            working_dir_rel = "."

        db.update_autotest_run(
            run_id,
            execution_mode=execution_mode,
            project_type_detected=project_type_detected,
            working_directory=working_dir_rel,
            project_type=project_type_detected,
        )

        for name, argv in steps_def:
            step_id = step_ids[name]
            started_at = utc_now_iso()
            db.update_autotest_step(step_id, status="running", started_at=started_at)

            ok = True
            exit_code = 0
            error_type = ""
            output_text = ""
            stdout = ""
            stderr = ""

            command = " ".join(argv)
            if fail_step and fail_step == name:
                ok = False
                exit_code = 1
                error_type = "simulated_failure"
                output_text = (
                    f"[{name}] command: {command}\n"
                    f"[{name}] project_type_detected: {project_type_detected}\n"
                    f"[{name}] execution_mode: simulated\n"
                    f"[{name}] working_directory: {working_dir_rel}\n"
                    f"[{name}] simulated: FAILED\n"
                    f"Simulated failure requested by zip marker: {fail_step}\n"
                )
            elif execution_mode == "real" and project_type_detected in {"node", "python"}:
                try:
                    exit_code, stdout, stderr = _run_command(argv=argv, cwd=working_dir, timeout_seconds=timeout_seconds)
                    ok = exit_code == 0
                except subprocess.TimeoutExpired:
                    ok = False
                    exit_code = 124
                    error_type = "timeout"
                    output_text = f"[{name}] command timed out after {timeout_seconds}s: {command}"
                except FileNotFoundError:
                    ok = False
                    exit_code = 127
                    error_type = "command_not_found"
                    output_text = f"[{name}] command not found: {command}"
                except Exception as exc:
                    ok = False
                    exit_code = 1
                    error_type = "exception"
                    output_text = f"[{name}] exception while running command: {exc}"
            else:
                output_text = (
                    f"[{name}] command: {command}\n"
                    f"[{name}] project_type_detected: {project_type_detected}\n"
                    f"[{name}] execution_mode: simulated\n"
                    f"[{name}] working_directory: {working_dir_rel}\n"
                    f"[{name}] simulated: ok\n"
                )
            if stdout or stderr:
                output_text = (
                    f"[{name}] command: {command}\n"
                    f"[{name}] project_type_detected: {project_type_detected}\n"
                    f"[{name}] execution_mode: real\n"
                    f"[{name}] working_directory: {working_dir_rel}\n\n"
                    "STDOUT:\n"
                    f"{stdout.strip()}\n\n"
                    "STDERR:\n"
                    f"{stderr.strip()}\n"
                ).strip()

            finished_at = utc_now_iso()
            outputs[name] = output_text
            db.update_autotest_step(
                step_id,
                status="passed" if ok else "failed",
                finished_at=finished_at,
                output=output_text,
                success=1 if ok else 0,
                exit_code=exit_code,
                stdout_summary=(stdout or "")[-800:],
                stderr_summary=(stderr or "")[-800:],
                error_type=error_type,
            )

            if not ok:
                overall_ok = False
                failed_step_name = name
                break

        if overall_ok:
            summary = f"Acceptance pipeline passed ({project_type_detected})."
            prompt_output = (
                "AutoTest passed.\n\n"
                f"Project: {project_name}\n"
                "Steps: install, build, test, lint\n"
                "Next: capture any useful learnings into a Knowledge entry."
            )
            db.update_autotest_run(run_id, status="passed", summary=summary, prompt_output=prompt_output)

            knowledge_id = str(uuid.uuid4())
            candidate_ok = db.add_knowledge_entry(
                entry_id=knowledge_id,
                title=f"AutoTest Passed: {project_name}",
                status="draft",
                problem=summary,
                root_cause="",
                solution=prompt_output,
                tags="autotest,acceptance",
                notes=f"source=autotest\nrun_id={run_id}",
                created_by=current_user["sub"],
                source_type="autotest-derived",
                source_ref=f"autotest_run:{run_id}",
            )
            if candidate_ok:
                db.update_autotest_run(run_id, solution_entry_id=knowledge_id)
                db.add_link(f"autotest_run:{run_id}", f"knowledge:{knowledge_id}", link_type="produced")
                db.add_link(f"knowledge:{knowledge_id}", f"autotest_run:{run_id}", link_type="derived_from")
                entry = db.get_knowledge_entry(knowledge_id)
                if entry:
                    index_knowledge_entry(entry)
        else:
            failed_step = failed_step_name or "unknown"
            summary = f"Acceptance pipeline failed at step '{failed_step}' ({project_type_detected})."
            failed_output = outputs.get(failed_step, "")
            suggestion = await suggest_fix_from_autotest(
                project_type=project_type_detected,
                failed_step=failed_step,
                command=commands_by_step.get(failed_step, ""),
                output=failed_output,
            )
            prompt_output = (
                "AutoTest failed.\n\n"
                f"Project: {project_name}\n"
                f"Failed step: {failed_step}\n\n"
                "Failure output:\n"
                f"{failed_output}\n\n"
                "Please fix the failure, then re-run AutoTest."
            )
            db.update_autotest_run(run_id, status="failed", summary=summary, prompt_output=prompt_output, suggestion=suggestion)

            logbook_id = str(uuid.uuid4())
            created = db.add_logbook_entry(
                entry_id=logbook_id,
                title=f"AutoTest Failed: {project_name}",
                status="draft",
                run_id=run_id,
                problem=prompt_output,
                root_cause="",
                solution=suggestion,
                tags="autotest,acceptance",
                source_type="autotest-derived",
                created_by=current_user["sub"],
                source_ref=f"autotest_run:{run_id}",
            )
            if created:
                db.update_autotest_run(run_id, problem_entry_id=logbook_id)
                db.add_link(f"autotest_run:{run_id}", f"logbook:{logbook_id}", link_type="produced")
                db.add_link(f"logbook:{logbook_id}", f"autotest_run:{run_id}", link_type="derived_from")
                entry = db.get_logbook_entry(logbook_id)
                if entry:
                    index_logbook_entry(entry)

        safe_unlink(zip_path)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    run_row = db.get_autotest_run(run_id=run_id, created_by=user_id)
    if not run_row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Autotest run missing after creation.")
    step_rows = db.list_autotest_steps(run_id)

    return AutoTestRunResponse(
        id=run_row["run_id"],
        source_type=run_row.get("source_type", ""),
        source_ref=run_row.get("source_ref", ""),
        execution_mode=run_row.get("execution_mode", "real") or "real",
        project_type_detected=run_row.get("project_type_detected", "") or run_row.get("project_type", "") or "",
        working_directory=run_row.get("working_directory", "") or "",
        project_name=run_row.get("project_name", "") or run_row.get("source_ref", ""),
        project_type=run_row.get("project_type", ""),
        status=run_row.get("status", ""),
        summary=run_row.get("summary", ""),
        suggestion=run_row.get("suggestion", ""),
        prompt_output=run_row.get("prompt_output", ""),
        problem_entry_id=run_row.get("problem_entry_id", "") or "",
        solution_entry_id=run_row.get("solution_entry_id", "") or "",
        created_at=run_row.get("created_at", ""),
        steps=[
            {
                "step_id": step.get("step_id", ""),
                "name": step.get("name", ""),
                "command": step.get("command", ""),
                "status": step.get("status", ""),
                "started_at": step.get("started_at", ""),
                "finished_at": step.get("finished_at", ""),
                "output": step.get("output", ""),
                "success": int(step.get("success", 0)),
                "exit_code": int(step.get("exit_code", 0)),
                "stdout_summary": step.get("stdout_summary", ""),
                "stderr_summary": step.get("stderr_summary", ""),
                "error_type": step.get("error_type", ""),
                "created_at": step.get("created_at", ""),
            }
            for step in step_rows
        ],
    )


@app.get("/api/autotest/runs", response_model=list[AutoTestRunListItemResponse])
async def list_autotest_runs(current_user: dict = Depends(get_current_user)) -> list[AutoTestRunListItemResponse]:
    user_id = current_user["sub"]
    return [
        AutoTestRunListItemResponse(
            id=row.get("run_id", ""),
            project_name=row.get("project_name", "") or row.get("source_ref", ""),
            status=row.get("status", ""),
            created_at=row.get("created_at", ""),
            summary=row.get("summary", ""),
        )
        for row in db.list_autotest_runs(limit=50, created_by=user_id)
    ]


@app.get("/api/autotest/runs/{run_id}", response_model=AutoTestRunResponse)
async def get_autotest_run(run_id: str, current_user: dict = Depends(get_current_user)) -> AutoTestRunResponse:
    user_id = current_user["sub"]
    run_row = db.get_autotest_run(run_id=run_id, created_by=user_id)
    if not run_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autotest run not found.")
    step_rows = db.list_autotest_steps(run_id)
    return AutoTestRunResponse(
        id=run_row.get("run_id", ""),
        source_type=run_row.get("source_type", ""),
        source_ref=run_row.get("source_ref", ""),
        execution_mode=run_row.get("execution_mode", "real") or "real",
        project_type_detected=run_row.get("project_type_detected", "") or run_row.get("project_type", "") or "",
        working_directory=run_row.get("working_directory", "") or "",
        project_name=run_row.get("project_name", "") or run_row.get("source_ref", ""),
        project_type=run_row.get("project_type", ""),
        status=run_row.get("status", ""),
        summary=run_row.get("summary", ""),
        suggestion=run_row.get("suggestion", ""),
        prompt_output=run_row.get("prompt_output", ""),
        problem_entry_id=run_row.get("problem_entry_id", "") or "",
        solution_entry_id=run_row.get("solution_entry_id", "") or "",
        created_at=run_row.get("created_at", ""),
        steps=[
            {
                "step_id": step.get("step_id", ""),
                "name": step.get("name", ""),
                "command": step.get("command", ""),
                "status": step.get("status", ""),
                "started_at": step.get("started_at", ""),
                "finished_at": step.get("finished_at", ""),
                "output": step.get("output", ""),
                "success": int(step.get("success", 0)),
                "exit_code": int(step.get("exit_code", 0)),
                "stdout_summary": step.get("stdout_summary", ""),
                "stderr_summary": step.get("stderr_summary", ""),
                "error_type": step.get("error_type", ""),
                "created_at": step.get("created_at", ""),
            }
            for step in step_rows
        ],
    )


@app.get("/api/meta/templates")
async def list_templates(current_user: dict = Depends(get_current_user)) -> dict[str, list[dict[str, object]]]:
    _ = current_user
    return {
        "templates": [
            {"value": key, "label": key.replace("_", " ").title(), "fields": value["fields"]}
            for key, value in FORM_TEMPLATES.items()
        ]
    }
