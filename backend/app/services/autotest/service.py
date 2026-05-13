from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import uuid
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


def get_autotest_capabilities() -> AutoTestCapabilitiesResponse:
    return _get_autotest_capabilities()

async def run_autotest(file: UploadFile, current_user: dict) -> AutoTestRunResponse:
    user_id = current_user["sub"]
    if is_real_autotest_requested() and not is_real_autotest_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "AutoTest real mode is disabled. Set KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1 "
                "and run inside an isolated sandbox/container before executing uploaded projects."
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
    project_name = Path(file.filename).stem or "uploaded-project"

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
        summary="AutoTest queued.",
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Autotest run missing after creation.")
    return serialize_autotest_run(run_row, autotest_repository.list_steps(run_id))


def _run_autotest_job_thread(**kwargs: object) -> None:
    try:
        import asyncio

        asyncio.run(execute_autotest_run_job(**kwargs))
    except Exception:
        logger.exception("AutoTest background job failed before service-level failure handling could run.")


def schedule_autotest_run_job(**kwargs: object) -> threading.Thread:
    thread = threading.Thread(target=_run_autotest_job_thread, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


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
    autotest_dir = settings.AUTOTEST_DIR
    work_dir = autotest_dir / f"autotest-{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir = work_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    timeout_seconds = int(settings.AUTOTEST_TIMEOUT_SECONDS)
    commands_by_step: dict[str, str] = {}
    outputs: dict[str, str] = {}
    failed_step_name = ""
    failed_reason = ""

    def refresh_run() -> tuple[dict, list[dict]]:
        run_row = autotest_repository.get_run(run_id=run_id, created_by=user_id)
        if not run_row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Autotest run missing after creation.")
        return run_row, autotest_repository.list_steps(run_id)

    def mark_unfinished_command_steps(*, current_failed_step: str = "") -> None:
        for step in autotest_repository.list_steps(run_id):
            status_value = str(step.get("status", "") or "").lower()
            if status_value in {"passed", "failed", "skipped", "unavailable"}:
                continue
            next_status = "failed" if current_failed_step and str(step.get("name", "")) == current_failed_step else "skipped"
            autotest_repository.update_step(
                str(step.get("step_id", "")),
                status=next_status,
                finished_at=utc_now_iso(),
                output=str(step.get("output", "") or ""),
                success=0 if next_status == "failed" else 1,
                exit_code=1 if next_status == "failed" else 0,
                stdout_summary=str(step.get("stdout_summary", "") or ""),
                stderr_summary=str(step.get("stderr_summary", "") or ""),
                error_type="failed_before_completion" if next_status == "failed" else "skipped_after_failure",
            )

    try:
        autotest_repository.update_run(run_id, status="running", summary="Extracting uploaded ZIP archive.")
        extract_started_at = utc_now_iso()
        timeline = set_timeline_item(timeline, "extracted", status="running", started_at=extract_started_at, message="extracting")
        save_run_timeline(run_id, timeline)
        safe_extract_zip(zip_path, extracted_dir)
        extract_finished_at = utc_now_iso()
        timeline = set_timeline_item(timeline, "extracted", status="success", finished_at=extract_finished_at, message="extracted")
        save_run_timeline(run_id, timeline)

        timeline = set_timeline_item(timeline, "detected_stack", status="running", started_at=utc_now_iso())
        save_run_timeline(run_id, timeline)
        project_type_detected, working_dir = find_project_root_on_disk(extracted_dir)
        working_dir_rel = sanitize_path_for_report(working_dir, base_dir=extracted_dir)
        project_name = working_dir.name or project_name
        autotest_repository.update_run(
            run_id,
            project_type_detected=project_type_detected,
            working_directory=working_dir_rel,
            project_name=project_name,
            project_type=project_type_detected,
            summary=f"Detected {project_type_detected or 'unknown'} project.",
        )
        timeline = set_timeline_item(
            timeline,
            "detected_stack",
            status="success",
            finished_at=utc_now_iso(),
            message=project_type_detected or "unknown",
        )
        save_run_timeline(run_id, timeline)

        commands = autotest_commands(project_type_detected)
        overall_ok = True
        fail_step_marker = (working_dir / ".autotest_fail_step")
        fail_step = fail_step_marker.read_text(encoding="utf-8").strip() if fail_step_marker.exists() else ""

        skipped_steps: list[str] = []
        ran_tests_started_at: str | None = None

        for name, argv in commands.items():
            step_id = step_ids[name]
            command = " ".join(argv)
            commands_by_step[name] = command
            autotest_repository.update_step(step_id, command=command)

            ok = True
            exit_code = 0
            error_type = ""
            output_text = ""
            stdout = ""
            stderr = ""

            if ran_tests_started_at is None:
                ran_tests_started_at = utc_now_iso()
                timeline = set_timeline_item(timeline, "ran_tests", status="running", started_at=ran_tests_started_at)
                save_run_timeline(run_id, timeline)

            if fail_step and fail_step == name:
                started_at = utc_now_iso()
                autotest_repository.update_step(step_id, status="running", started_at=started_at)
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
                should_run, skip_reason = autotest_step_should_run(
                    project_type=project_type_detected,
                    working_dir=working_dir,
                    step_name=name,
                )
                if not should_run:
                    skipped_steps.append(name)
                    started_at = utc_now_iso()
                    output_text = (
                        f"[{name}] command: {command}\n"
                        f"[{name}] project_type_detected: {project_type_detected}\n"
                        f"[{name}] execution_mode: real\n"
                        f"[{name}] working_directory: {working_dir_rel}\n"
                        f"[{name}] skipped: yes\n"
                        f"Reason: {skip_reason}\n"
                    ).strip()
                    outputs[name] = output_text
                    autotest_repository.update_step(
                        step_id,
                        status="skipped",
                        started_at=started_at,
                        finished_at=started_at,
                        output=output_text,
                        success=1,
                        exit_code=0,
                        stdout_summary="",
                        stderr_summary="",
                        error_type="skipped",
                    )
                    continue

                started_at = utc_now_iso()
                autotest_repository.update_step(step_id, status="running", started_at=started_at)
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
                started_at = utc_now_iso()
                autotest_repository.update_step(step_id, status="running", started_at=started_at)
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
            output_text = clamp_output(output_text)
            outputs[name] = output_text
            step_status = "passed" if ok else "failed"
            if error_type == "command_not_found":
                step_status = "unavailable"
            autotest_repository.update_step(
                step_id,
                status=step_status,
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
                failed_reason = output_text or f"AutoTest {name} step failed."
                timeline = set_timeline_item(
                    timeline,
                    "prepared_environment",
                    status="failed" if name == "install" else "success",
                    finished_at=finished_at,
                    message=name,
                )
                timeline = set_timeline_item(
                    timeline,
                    "ran_tests",
                    status="failed",
                    finished_at=finished_at,
                    message=name,
                )
                save_run_timeline(run_id, timeline)
                break

            if name == "install":
                timeline = set_timeline_item(
                    timeline,
                    "prepared_environment",
                    status="success",
                    finished_at=finished_at,
                    message=name,
                )
                save_run_timeline(run_id, timeline)

        if overall_ok:
            timeline = set_timeline_item(timeline, "generated_report", status="running", started_at=utc_now_iso())
            save_run_timeline(run_id, timeline)
            skipped_suffix = f"; skipped: {', '.join(skipped_steps)}" if skipped_steps else ""
            summary = f"Acceptance pipeline passed ({project_type_detected}){skipped_suffix}."
            prompt_output = (
                "AutoTest passed.\n\n"
                f"Project: {project_name}\n"
                "Steps: install, build, test, lint\n"
            )
            if skipped_steps:
                prompt_output += f"Skipped: {', '.join(skipped_steps)}\n"
            prompt_output += "Next: capture any useful learnings into a Knowledge entry."
            autotest_repository.update_run(
                run_id,
                summary=summary,
                prompt_output=prompt_output,
                failed_reason="",
            )

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
                created_by=user_id,
                source_type="autotest-derived",
                source_ref=f"autotest_run:{run_id}",
            )
            if candidate_ok:
                autotest_repository.update_run(run_id, solution_entry_id=knowledge_id)
                db.add_link(f"autotest_run:{run_id}", f"knowledge:{knowledge_id}", link_type="produced")
                db.add_link(f"knowledge:{knowledge_id}", f"autotest_run:{run_id}", link_type="derived_from")
                entry = db.get_knowledge_entry(knowledge_id)
                if entry:
                    _safe_autotest_index_entry(
                        run_id=run_id,
                        item_kind="knowledge",
                        item_id=knowledge_id,
                        entry=entry,
                        indexer=index_knowledge_entry,
                    )
            timeline = set_timeline_item(
                timeline,
                "ran_tests",
                status="success",
                finished_at=utc_now_iso(),
                message="install/build/test/lint completed",
            )
            timeline = set_timeline_item(
                timeline,
                "generated_report",
                status="success",
                finished_at=utc_now_iso(),
                message=summary,
            )
            timeline = set_timeline_item(timeline, "failed_reason", status="skipped", clear_message=True)
            save_run_timeline(run_id, timeline)
            autotest_repository.update_run(run_id, status="passed")
        else:
            failed_step = failed_step_name or "unknown"
            summary = f"Acceptance pipeline failed at step '{failed_step}' ({project_type_detected})."
            failed_output = outputs.get(failed_step, "")
            timeline = set_timeline_item(timeline, "generated_report", status="running", started_at=utc_now_iso())
            save_run_timeline(run_id, timeline)
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
            failed_reason = failed_output or summary
            autotest_repository.update_run(
                run_id,
                summary=summary,
                prompt_output=prompt_output,
                suggestion=suggestion,
                failed_reason=failed_reason,
            )

            logbook_id = str(uuid.uuid4())
            created_problem = db.add_logbook_entry(
                entry_id=logbook_id,
                title=f"AutoTest Failed: {project_name}",
                status="draft",
                run_id=run_id,
                problem=prompt_output,
                root_cause="",
                solution=suggestion,
                tags="autotest,acceptance",
                source_type="autotest-derived",
                created_by=user_id,
                source_ref=f"autotest_run:{run_id}",
            )
            timeline = set_timeline_item(
                timeline,
                "generated_report",
                status="success",
                finished_at=utc_now_iso(),
                message=summary,
            )
            timeline = finalize_autotest_timeline_failure(
                timeline=timeline,
                failed_phase="ran_tests",
                failed_reason=failed_reason,
            )
            save_run_timeline(run_id, timeline)
            if created_problem:
                autotest_repository.update_run(run_id, problem_entry_id=logbook_id, status="failed")
                db.add_link(f"autotest_run:{run_id}", f"logbook:{logbook_id}", link_type="produced")
                db.add_link(f"logbook:{logbook_id}", f"autotest_run:{run_id}", link_type="derived_from")
                entry = db.get_logbook_entry(logbook_id)
                if entry:
                    _safe_autotest_index_entry(
                        run_id=run_id,
                        item_kind="logbook",
                        item_id=logbook_id,
                        entry=entry,
                        indexer=index_logbook_entry,
                    )
            else:
                autotest_repository.update_run(run_id, status="failed")
    except Exception as exc:
        failed_reason = str(exc) or "AutoTest run failed unexpectedly."
        logger.exception("AutoTest run %s failed unexpectedly", run_id)
        autotest_repository.update_run(
            run_id,
            summary=f"AutoTest run failed: {failed_reason}",
            prompt_output="",
            suggestion="",
            failed_reason=failed_reason,
        )
        current_phase = "generated_report" if "report" in failed_reason.lower() else "detected_stack"
        if str(next((item for item in timeline if str(item.get("key")) == "generated_report"), {}).get("status", "")) == "running":
            current_phase = "generated_report"
        elif str(next((item for item in timeline if str(item.get("key")) == "ran_tests"), {}).get("status", "")) == "running":
            current_phase = "ran_tests"
        elif str(next((item for item in timeline if str(item.get("key")) == "prepared_environment"), {}).get("status", "")) == "running":
            current_phase = "prepared_environment"
        elif str(next((item for item in timeline if str(item.get("key")) == "detected_stack"), {}).get("status", "")) == "running":
            current_phase = "detected_stack"
        elif str(next((item for item in timeline if str(item.get("key")) == "extracted"), {}).get("status", "")) == "running":
            current_phase = "extracted"
        timeline = finalize_autotest_timeline_failure(
            timeline=timeline,
            failed_phase=current_phase,
            failed_reason=failed_reason,
        )
        save_run_timeline(run_id, timeline)
        mark_unfinished_command_steps(current_failed_step=failed_step_name)
        autotest_repository.update_run(run_id, status="failed")
    finally:
        safe_unlink(zip_path)
        shutil.rmtree(work_dir, ignore_errors=True)



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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid export format. Use 'md' or 'html'.")
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid GitHub URL. Use https://github.com/{owner}/{repo}.")
    repo_info_data = get_repo_info(repo_url)
    run_id = str(uuid.uuid4())
    summary = "GitHub repository registered for queued analysis. Remote clone and remote test execution are not performed."
    created = autotest_repository.create_run(
        run_id=run_id,
        source_type="github_repo",
        source_ref=str(repo_info_data["url"]),
        execution_mode="simulated",
        project_type_detected="",
        working_directory="",
        project_name=str(repo_info_data["repo"]),
        project_type="github",
        status="queued",
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
    return GitHubAnalyzeResponse(run_id=run_id, status="queued", repo_info=repo_info)
