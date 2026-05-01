import json
import logging
import mimetypes
import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile
import re
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from pydantic import BaseModel, Field

from app.context import APP_VERSION, UPLOAD_DIR, allow_credentials, allowed_origins, db, settings
from app.core.security import create_token
from app.database import delete_from_kb_vector_db, delete_from_vector_db
from app.dependencies import get_current_user
from app.kb_index import index_knowledge_entry, index_logbook_entry, index_photo, index_saved_prompt
from app.llm import get_llm_provider, validate_env_vars
from app.models import (
    AutoTestRunListItemResponse,
    AutoTestRunResponse,
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
    SettingsLLMResponse,
    SettingsOCRResponse,
    UploadDocumentResponse,
    UploadPhotoResponse,
)
from app.ocr_service import extract_text_from_image, get_ocr_status
from app.services import FORM_TEMPLATES, generate_form, perform_qa, process_file
from app.services.report_generator import ReportGenerator
import io
from app.utils import (
    generate_safe_filename,
    stream_write_file,
    validate_file_extension,
    validate_file_magic_bytes,
)

logger = logging.getLogger("knowledge_workspace")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

# Helper for time
def utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# --- GitHub Analysis Models ---
class GitHubAnalyzeRequest(BaseModel):
    repo_url: str = Field(..., description="HTTPS URL of the GitHub repository")

class GitHubAnalyzeResponse(BaseModel):
    run_id: str
    status: str
    message: str

# --- GitHub Analysis Logic ---

def validate_github_url(url: str) -> bool:
    # Strict regex for GitHub HTTPS URLs
    pattern = r"^https://github\.com/[\w\-\.]+建设/[\w\-\.]+(?:\.git)?/?$"
    # Correcting pattern to be more permissive for owner/repo but strict on domain
    pattern = r"^https://github\.com/([a-zA-Z0-9\-_.]+)/([a-zA-Z0-9\-_.]+)(?:\.git)?/?$"
    return bool(re.match(pattern, url))

def get_repo_info(url: str) -> tuple[str, str]:
    match = re.match(r"^https://github\.com/([a-zA-Z0-9\-_.]+)/([a-zA-Z0-9\-_.]+?)(?:\.git)?/?$", url)
    if match:
        return match.group(1), match.group(2)
    return "unknown", "unknown"

async def run_autotest_pipeline(run_id: str, working_dir: Path, project_name: str, project_type_detected: str, user_id: str, execution_mode: str):
    # This is a refactored version of the pipeline logic to be reusable
    autotest_dir = settings.AUTOTEST_DIR
    timeout_seconds = int(settings.AUTOTEST_TIMEOUT_SECONDS)
    commands = autotest_commands(project_type_detected)
    
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
    
    try:
        working_dir_rel = "."
        # For GitHub, the working_dir is already the root
        
        skipped_steps: list[str] = []
        for name, argv in steps_def:
            step_id = step_ids[name]
            ok = True
            exit_code = 0
            error_type = ""
            output_text = ""
            stdout = ""
            stderr = ""

            command = " ".join(argv)
            
            # Step skipping logic
            should_run, skip_reason = _autotest_step_should_run(
                project_type=project_type_detected, working_dir=working_dir, step_name=name
            )
            if not should_run:
                skipped_steps.append(name)
                started_at = utc_now_iso()
                finished_at = started_at
                output_text = f"[{name}] skipped: {skip_reason}"
                outputs[name] = output_text
                db.update_autotest_step(
                    step_id, status="skipped", started_at=started_at, finished_at=finished_at,
                    output=output_text, success=1, exit_code=0, error_type="skipped"
                )
                continue

            started_at = utc_now_iso()
            db.update_autotest_step(step_id, status="running", started_at=started_at)
            
            try:
                if execution_mode == "real":
                    exit_code, stdout, stderr = _run_command(argv=argv, cwd=working_dir, timeout_seconds=timeout_seconds)
                    ok = exit_code == 0
                else:
                    output_text = f"[{name}] simulated: ok"
                    ok = True
            except subprocess.TimeoutExpired:
                ok = False
                exit_code = 124
                error_type = "timeout"
                output_text = f"[{name}] command timed out after {timeout_seconds}s"
            except Exception as exc:
                ok = False
                exit_code = 1
                error_type = "exception"
                output_text = f"[{name}] exception: {exc}"

            if stdout or stderr:
                output_text = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"

            finished_at = utc_now_iso()
            outputs[name] = output_text
            db.update_autotest_step(
                step_id, status="passed" if ok else "failed", finished_at=finished_at,
                output=output_text, success=1 if ok else 0, exit_code=exit_code,
                stdout_summary=(stdout or "")[-800:], stderr_summary=(stderr or "")[-800:],
                error_type=error_type
            )

            if not ok:
                overall_ok = False
                failed_step_name = name
                break

        if overall_ok:
            summary = f"Acceptance pipeline passed ({project_type_detected})."
            prompt_output = f"AutoTest passed for {project_name}."
            db.update_autotest_run(run_id, status="passed", summary=summary, prompt_output=prompt_output)
            # (Optional: Knowledge capture logic can be added here as in zip upload)
        else:
            failed_step = failed_step_name or "unknown"
            summary = f"Acceptance pipeline failed at step '{failed_step}' ({project_type_detected})."
            suggestion = await suggest_fix_from_autotest(
                project_type=project_type_detected, failed_step=failed_step,
                command=commands_by_step.get(failed_step, ""), output=outputs.get(failed_step, "")
            )
            db.update_autotest_run(run_id, status="failed", summary=summary, suggestion=suggestion)

    except Exception as e:
        logger.error(f"Pipeline error for {run_id}: {e}")
        db.update_autotest_run(run_id, status="failed", summary=f"Internal error: {str(e)}")
    finally:
        # Cleanup temp working dir
        if working_dir.exists():
            shutil.rmtree(working_dir, ignore_errors=True)

async def github_analyze_task(run_id: str, repo_url: str, user_id: str):
    autotest_dir = settings.AUTOTEST_DIR
    autotest_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix=f"github_{run_id}_", dir=str(autotest_dir)))
    
    try:
        db.update_autotest_run(run_id, status="running", summary="Cloning repository...")
        
        # Security: use list args for subprocess.run
        # Limit clone depth to 1 for speed and size
        clone_cmd = ["git", "clone", "--depth", "1", repo_url, str(work_dir)]
        process = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=120)
        
        if process.returncode != 0:
            db.update_autotest_run(run_id, status="failed", summary=f"Git clone failed: {process.stderr}")
            return

        # Detect tech stack
        project_type, project_root = find_project_root_on_disk(work_dir)
        project_name = get_repo_info(repo_url)[1]
        
        db.update_autotest_run(
            run_id, 
            project_type_detected=project_type,
            project_type=project_type,
            project_name=project_name,
            working_directory=str(project_root.relative_to(work_dir)) if project_root != work_dir else "."
        )
        
        # Execute pipeline
        execution_mode = settings.AUTOTEST_MODE
        await run_autotest_pipeline(run_id, project_root, project_name, project_type, user_id, execution_mode)
        
    except subprocess.TimeoutExpired:
        db.update_autotest_run(run_id, status="failed", summary="Git clone timed out.")
    except Exception as e:
        logger.error(f"GitHub analyze task failed: {e}")
        db.update_autotest_run(run_id, status="failed", summary=f"Analysis failed: {str(e)}")
    finally:
        # Final cleanup is handled inside run_autotest_pipeline or here if it failed early
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

# --- Rest of legacy_main.py (keeping existing functions) ---

def detect_project_type(zip_path: Path) -> str:
    temp_dir = Path(tempfile.mkdtemp(prefix="detect_"))
    try:
        with zipfile.ZipFile(zip_path) as archive:
            # only extract markers to save time
            markers = ["package.json", "requirements.txt", "pyproject.toml", "go.mod", "Dockerfile", "docker-compose.yml"]
            for member in archive.namelist():
                if any(m in member for m in markers):
                    archive.extract(member, temp_dir)
        pt, _ = find_project_root_on_disk(temp_dir)
        return pt
    except Exception:
        return "unknown"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def _walk_dirs_for_markers(base_dir: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", "dist", "build", ".venv", "venv"}
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        files_set = {name.lower() for name in files}
        root_path = Path(root)
        if "package.json" in files_set:
            candidates.append(("node", root_path))
        if "pyproject.toml" in files_set or "requirements.txt" in files_set:
            candidates.append(("python", root_path))
        if "go.mod" in files_set:
            candidates.append(("go", root_path))
        if "dockerfile" in files_set or "docker-compose.yml" in files_set:
            candidates.append(("docker", root_path))
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
        tie_breaker = 0 if project_type == "node" else 1
        scored.append((depth, tie_breaker, project_type, path))
    scored.sort(key=lambda row: (row[0], row[1]))
    best = scored[0]
    return best[2], best[3]

def autotest_commands(project_type: str) -> dict[str, list[str]]:
    if project_type == "node":
        return {
            "install": ["npm", "install"],
            "build": ["npm", "run", "build"],
            "test": ["npm", "test"],
            "lint": ["npm", "run", "lint"],
        }
    if project_type == "python":
        return {
            "install": ["pip", "install", "-r", "requirements.txt"],
            "build": ["python", "-m", "compileall", "."],
            "test": ["pytest"],
            "lint": ["flake8", "."],
        }
    return {
        "install": ["echo", "install"],
        "build": ["echo", "build"],
        "test": ["echo", "test"],
        "lint": ["echo", "lint"],
    }

def _autotest_step_should_run(*, project_type: str, working_dir: Path, step_name: str) -> tuple[bool, str]:
    # Simplified for now
    return True, ""

def _run_command(*, argv: list[str], cwd: Path, timeout_seconds: int) -> tuple[int, str, str]:
    completed = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout_seconds)
    return completed.returncode, completed.stdout, completed.stderr

# --- API App Setup ---
app = FastAPI(title="Knowledge Workspace API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... (Include other existing endpoints like login, health, etc.) ...

@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version=APP_VERSION)

@app.post("/api/autotest/github/analyze", response_model=GitHubAnalyzeResponse)
async def analyze_github_repo(
    request: GitHubAnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    url = request.repo_url.strip()
    if not validate_github_url(url):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL. Must be HTTPS.")
    
    user_id = current_user["sub"]
    run_id = str(uuid.uuid4())
    owner, repo = get_repo_info(url)
    
    # Initialize run in DB
    db.add_autotest_run(
        run_id=run_id,
        source_type="github",
        source_ref=url,
        execution_mode=settings.AUTOTEST_MODE,
        project_name=repo,
        status="queued",
        created_by=user_id
    )
    
    background_tasks.add_task(github_analyze_task, run_id, url, user_id)
    
    return GitHubAnalyzeResponse(
        run_id=run_id,
        status="queued",
        message="GitHub analysis started in background."
    )

# ... (Include existing AutoTest runs list/detail and export endpoints) ...

@app.get("/api/autotest/runs", response_model=list[AutoTestRunListItemResponse])
async def list_autotest_runs(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    return [
        AutoTestRunListItemResponse(
            id=row["run_id"],
            project_name=row.get("project_name", "") or row.get("source_ref", ""),
            status=row.get("status", ""),
            created_at=row.get("created_at", ""),
            summary=row.get("summary", ""),
        )
        for row in db.list_autotest_runs(limit=50, created_by=user_id)
    ]

@app.get("/api/autotest/runs/{run_id}", response_model=AutoTestRunResponse)
async def get_autotest_run(run_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    run_row = db.get_autotest_run(run_id=run_id, created_by=user_id)
    if not run_row:
        raise HTTPException(status_code=404, detail="Run not found.")
    steps = db.list_autotest_steps(run_id)
    return AutoTestRunResponse(
        id=run_row["run_id"],
        source_type=run_row["source_type"],
        source_ref=run_row["source_ref"],
        execution_mode=run_row["execution_mode"],
        project_type_detected=run_row["project_type_detected"],
        working_directory=run_row["working_directory"],
        project_name=run_row["project_name"],
        project_type=run_row["project_type"],
        status=run_row["status"],
        summary=run_row["summary"],
        suggestion=run_row["suggestion"],
        prompt_output=run_row["prompt_output"],
        problem_entry_id=run_row.get("problem_entry_id"),
        solution_entry_id=run_row.get("solution_entry_id"),
        created_at=run_row["created_at"],
        steps=steps
    )

@app.get("/api/autotest/{run_id}/export")
async def export_autotest_report(run_id: str, format: str = "md", current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    run_row = db.get_autotest_run(run_id=run_id, created_by=user_id)
    if not run_row:
        raise HTTPException(status_code=404, detail="Run not found.")
    steps = db.list_autotest_steps(run_id)
    
    generator = ReportGenerator()
    markdown_content = generator.generate_markdown(run_row, steps)
    
    if format == "md":
        return Response(content=markdown_content, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=report_{run_id}.md"})
    elif format == "html":
        html_content = generator.convert_to_html(markdown_content)
        return Response(content=html_content, media_type="text/html", headers={"Content-Disposition": f"attachment; filename=report_{run_id}.html"})
    elif format == "pdf":
        html_content = generator.convert_to_html(markdown_content)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            # Using manus-md-to-pdf via subprocess as a reliable way in this environment
            md_tmp = tmp_path.replace(".pdf", ".md")
            with open(md_tmp, "w") as f:
                f.write(markdown_content)
            subprocess.run(["manus-md-to-pdf", md_tmp, tmp_path], check=True)
            with open(tmp_path, "rb") as f:
                pdf_content = f.read()
            return Response(content=pdf_content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=report_{run_id}.pdf"})
        finally:
            if os.path.exists(tmp_path): os.unlink(tmp_path)
            if os.path.exists(md_tmp): os.unlink(md_tmp)
    return HTTPException(status_code=400, detail="Invalid format")
