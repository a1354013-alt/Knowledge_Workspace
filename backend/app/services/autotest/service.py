from __future__ import annotations

import json
import logging
import subprocess
import threading
import uuid
from contextlib import suppress
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from app.context import db, settings
from app.kb_index import index_knowledge_entry, index_logbook_entry
from app.models import (
    AutoTestCapabilitiesResponse,
    AutoTestExportFormat,
    AutoTestRunListItemResponse,
    AutoTestRunResponse,
    GitHubAnalyzeRequest,
    GitHubAnalyzeResponse,
    GitHubRepoInfoResponse,
)
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.archive import safe_extract_zip, safe_unlink, sanitize_path_for_report
from app.services.autotest.detector import autotest_commands, autotest_step_should_run, find_project_root_on_disk
from app.services.autotest.github import get_repo_info, validate_github_url
from app.services.autotest.reports import _safe_autotest_index_entry, _safe_download_filename, suggest_fix_from_autotest
from app.services.autotest.runner import _run_command
from app.services.autotest.security import (
    current_autotest_execution_mode,
    current_autotest_response_runner_mode,
    is_real_autotest_enabled,
    is_real_autotest_requested,
)
from app.services.autotest.security import (
    get_autotest_capabilities as _get_autotest_capabilities,
)
from app.services.autotest.timeline import (
    clamp_output,
    finalize_autotest_timeline_failure,
    initial_autotest_timeline,
    save_run_timeline,
    serialize_autotest_run,
    set_timeline_item,
    utc_now_iso,
)
from app.services.report_generator import ReportGenerator
from app.utils import generate_safe_filename, stream_write_file

logger = logging.getLogger("knowledge_workspace")
autotest_repository = AutoTestRepository(db)
_worker_threads_lock = threading.Lock()
_worker_threads: set[threading.Thread] = set()

__all__ = [
    "analyze_github_repo",
    "autotest_commands",
    "autotest_step_should_run",
    "clamp_output",
    "execute_autotest_run_job",
    "export_autotest_report",
    "finalize_autotest_timeline_failure",
    "find_project_root_on_disk",
    "get_autotest_capabilities",
    "get_autotest_run",
    "index_knowledge_entry",
    "index_logbook_entry",
    "initial_autotest_timeline",
    "list_autotest_runs",
    "run_autotest",
    "safe_extract_zip",
    "sanitize_path_for_report",
    "schedule_autotest_run_job",
    "snapshot_autotest_worker_threads",
    "shutdown_autotest_workers",
    "save_run_timeline",
    "set_timeline_item",
    "subprocess",
    "suggest_fix_from_autotest",
    "_safe_autotest_index_entry",
    "_run_command",
]


def get_autotest_capabilities() -> AutoTestCapabilitiesResponse:
    return _get_autotest_capabilities()


async def run_autotest(file: UploadFile, current_user: dict) -> AutoTestRunResponse:
    user_id = current_user["sub"]
    if is_real_autotest_requested() and not is_real_autotest_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "AutoTest local trusted mode is disabled. Set AUTOTEST_MODE=local_trusted and KW_AUTOTEST_REAL_MODE=1 "
                "only for local trusted projects. Do not execute untrusted ZIP uploads. "
                "Use AUTOTEST_MODE=docker_sandbox for container execution."
            ),
        )
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    if Path(file.filename).suffix.lower() != ".zip":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AutoTest only accepts .zip uploads.")

    autotest_dir = settings.AUTOTEST_DIR
    autotest_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = generate_safe_filename(file.filename)
    zip_path = autotest_dir / safe_filename
    file_size = await stream_write_file(file, zip_path)
    if file_size <= 0:
        safe_unlink(zip_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded zip is empty.")

    run_id = str(uuid.uuid4())
    created_at = utc_now_iso()
    source_ref = file.filename
    timeline = initial_autotest_timeline(source_ref=source_ref, created_at=created_at)
    execution_mode = current_autotest_execution_mode()
    runner_mode = current_autotest_response_runner_mode()
    project_name = Path(file.filename).stem or "uploaded-project"
    if runner_mode == "docker_sandbox":
        summary = "AutoTest queued in Docker sandbox mode. Commands will run in a constrained container."
    elif runner_mode == "local_trusted":
        summary = "AutoTest queued in local trusted mode. Commands run on this host; use only trusted projects."
    else:
        summary = "AutoTest queued in simulated mode (runner disabled). No uploaded project commands will run."

    created = autotest_repository.create_run(
        run_id=run_id,
        source_type="zip_upload",
        source_ref=source_ref,
        execution_mode=execution_mode,
        project_type_detected="",
        working_directory="",
        project_name=project_name,
        project_type="zip",
        status="queued",
        summary=summary,
        suggestion="",
        prompt_output="",
        failed_reason="",
        timeline_json=json.dumps(timeline, ensure_ascii=True),
        created_by=user_id,
    )
    if not created:
        safe_unlink(zip_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create AutoTest run.")

    step_ids = {name: str(uuid.uuid4()) for name in ("install", "build", "test", "lint")}
    for name in ("install", "build", "test", "lint"):
        autotest_repository.create_step(
            step_id=step_ids[name],
            run_id=run_id,
            name=name,
            command="",
            status="queued",
            started_at="",
            finished_at="",
            output="",
            success=0,
            exit_code=0,
            stdout_summary="",
            stderr_summary="",
            error_type="",
        )

    schedule_autotest_run_job(
        run_id=run_id,
        user_id=user_id,
        zip_path=zip_path,
        step_ids=step_ids,
        timeline=timeline,
        execution_mode=execution_mode,
        project_name=project_name,
    )

    run_row = autotest_repository.get_run(run_id=run_id, created_by=user_id)
    if not run_row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Autotest run missing after creation."
        )
    return serialize_autotest_run(run_row, autotest_repository.list_steps(run_id))


def _run_autotest_job_thread(**kwargs: object) -> None:
    current_thread = threading.current_thread()
    try:
        import asyncio

        asyncio.run(execute_autotest_run_job(**kwargs))
    except Exception:
        logger.exception("AutoTest background job failed before service-level failure handling could run.")
    finally:
        with suppress(RuntimeError):
            with _worker_threads_lock:
                _worker_threads.discard(current_thread)


def schedule_autotest_run_job(**kwargs: object) -> threading.Thread:
    thread = threading.Thread(target=_run_autotest_job_thread, kwargs=kwargs, daemon=True)
    with _worker_threads_lock:
        _worker_threads.add(thread)
    thread.start()
    return thread


def shutdown_autotest_workers(*, join_timeout_seconds: float = 5.0) -> None:
    with _worker_threads_lock:
        threads = [thread for thread in _worker_threads if thread.is_alive()]

    for thread in threads:
        thread.join(timeout=join_timeout_seconds)

    still_running = [thread.name for thread in threads if thread.is_alive()]
    if still_running:
        logger.warning("AutoTest worker thread(s) still running during shutdown: %s", ", ".join(still_running))


def snapshot_autotest_worker_threads() -> list[str]:
    with _worker_threads_lock:
        return [thread.name for thread in _worker_threads if thread.is_alive()]


async def execute_autotest_run_job(
    *,
    run_id: str,
    user_id: str,
    zip_path: Path,
    step_ids: dict[str, str],
    timeline: list[dict[str, object]],
    execution_mode: str,
    project_name: str,
) -> None:
    from app.services.autotest import job_executor, step_runner

    # Keep the facade monkeypatch-compatible for existing tests and older callers.
    job_executor.safe_extract_zip = safe_extract_zip
    job_executor.find_project_root_on_disk = find_project_root_on_disk
    job_executor.index_knowledge_entry = index_knowledge_entry
    job_executor.index_logbook_entry = index_logbook_entry
    job_executor._run_command = _run_command
    step_runner._run_command = _run_command
    await job_executor.execute_autotest_run_job(
        run_id=run_id,
        user_id=user_id,
        zip_path=zip_path,
        step_ids=step_ids,
        timeline=timeline,
        execution_mode=execution_mode,
        project_name=project_name,
    )


def list_autotest_runs(current_user: dict) -> list[AutoTestRunListItemResponse]:
    user_id = current_user["sub"]
    return [
        AutoTestRunListItemResponse(
            id=row.get("run_id", ""),
            project_name=row.get("project_name", "") or row.get("source_ref", ""),
            status=row.get("status", ""),
            created_at=row.get("created_at", ""),
            summary=row.get("summary", ""),
        )
        for row in autotest_repository.list_runs(created_by=user_id, limit=50)
    ]


def get_autotest_run(run_id: str, current_user: dict) -> AutoTestRunResponse:
    user_id = current_user["sub"]
    run_row = autotest_repository.get_run(run_id=run_id, created_by=user_id)
    if not run_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autotest run not found.")
    step_rows = autotest_repository.list_steps(run_id)
    return serialize_autotest_run(run_row, step_rows)


def export_autotest_report(run_id: str, requested_format: str, current_user: dict) -> Response:
    export_format_value = str(requested_format or "").strip().lower()
    if export_format_value not in {"md", "html"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid export format. Use 'md' or 'html'."
        )
    export_format: AutoTestExportFormat = export_format_value
    run_row = autotest_repository.get_run(run_id=run_id, created_by=current_user["sub"])
    if not run_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autotest run not found.")
    step_rows = autotest_repository.list_steps(run_id)
    markdown_report = ReportGenerator.generate_markdown(run_row, step_rows)
    filename_base = _safe_download_filename(f"autotest-report-{run_id}")
    if export_format == "md":
        return PlainTextResponse(
            content=markdown_report,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.md"'},
        )
    html_report = ReportGenerator.convert_to_html(markdown_report)
    return HTMLResponse(
        content=html_report,
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.html"'},
    )


def analyze_github_repo(payload: GitHubAnalyzeRequest, current_user: dict) -> GitHubAnalyzeResponse:
    repo_url = str(payload.repo_url or "").strip()
    if not validate_github_url(repo_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid GitHub URL. Use https://github.com/{owner}/{repo}."
        )
    repo_info_data = get_repo_info(repo_url)
    run_id = str(uuid.uuid4())
    summary = (
        "GitHub repository registered for intake-only analysis metadata. "
        "It is not queued for execution; remote clone, remote test execution, and full repository scan are not performed."
    )
    created = autotest_repository.create_run(
        run_id=run_id,
        source_type="github_repo",
        source_ref=str(repo_info_data["url"]),
        execution_mode="simulated",
        project_type_detected="",
        working_directory="",
        project_name=str(repo_info_data["repo"]),
        project_type="github",
        status="registered",
        summary=summary,
        suggestion="",
        prompt_output="",
        failed_reason="",
        timeline_json="",
        created_by=current_user["sub"],
    )
    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create AutoTest run.")
    repo_info = GitHubRepoInfoResponse(**repo_info_data)
    return GitHubAnalyzeResponse(
        run_id=run_id,
        status="registered",
        execution_mode="simulated",
        analysis_scope="intake_only",
        remote_clone_performed=False,
        report_ready=False,
        message=summary,
        repo_info=repo_info,
    )
