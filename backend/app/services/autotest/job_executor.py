from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from fastapi import HTTPException, status

from app.context import db, settings
from app.kb_index import index_knowledge_entry, index_logbook_entry
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.archive import safe_extract_zip, sanitize_path_for_report
from app.services.autotest.detector import autotest_commands, autotest_step_should_run, find_project_root_on_disk
from app.services.autotest.report_side_effects import create_failed_logbook_draft, create_passed_knowledge_draft
from app.services.autotest.reports import suggest_fix_from_autotest
from app.services.autotest.runner import _run_command
from app.services.autotest.timeline import (
    clamp_output,
    finalize_autotest_timeline_failure,
    save_run_timeline,
    set_timeline_item,
    utc_now_iso,
)
from app.services.autotest.workspace_cleanup import cleanup_autotest_workspace

logger = logging.getLogger("knowledge_workspace")
autotest_repository = AutoTestRepository(db)

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

            create_passed_knowledge_draft(
                run_id=run_id,
                user_id=user_id,
                project_name=project_name,
                summary=summary,
                prompt_output=prompt_output,
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
            logbook_id = create_failed_logbook_draft(
                run_id=run_id,
                user_id=user_id,
                project_name=project_name,
                prompt_output=prompt_output,
                suggestion=suggestion,
                indexer=index_logbook_entry,
            )
            if not logbook_id:
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
        cleanup_autotest_workspace(zip_path=zip_path, work_dir=work_dir)


