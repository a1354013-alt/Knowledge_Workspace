from __future__ import annotations

import logging
from pathlib import Path

from app.context import db
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.archive import safe_extract_zip
from app.services.autotest.archive_extractor import prepare_extracted_archive
from app.services.autotest.execution_plan import build_execution_plan
from app.services.autotest.job_reporter import (
    current_failed_phase,
    finalize_failed_run,
    finalize_passed_run,
    mark_failed_phase,
    mark_prepare_phase_skipped,
    mark_prepare_phase_success,
)
from app.services.autotest.project_detector import detect_project
from app.services.autotest.step_runner import (
    execute_planned_step,
    mark_unfinished_command_steps,
    persist_step_result,
)
from app.services.autotest.timeline import (
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
    extracted_archive = prepare_extracted_archive(run_id=run_id)
    commands_by_step: dict[str, str] = {}
    outputs: dict[str, str] = {}
    failed_step_name = ""

    try:
        autotest_repository.update_run(run_id, status="running", summary="Extracting uploaded ZIP archive.")
        timeline = set_timeline_item(timeline, "extracted", status="running", started_at=utc_now_iso(), message="extracting")
        save_run_timeline(run_id, timeline)
        safe_extract_zip(zip_path, extracted_archive.extracted_dir)
        timeline = set_timeline_item(timeline, "extracted", status="success", finished_at=utc_now_iso(), message="extracted")
        save_run_timeline(run_id, timeline)

        timeline = set_timeline_item(timeline, "detected_stack", status="running", started_at=utc_now_iso())
        save_run_timeline(run_id, timeline)
        detected_project = detect_project(
            extracted_dir=extracted_archive.extracted_dir,
            fallback_project_name=project_name,
        )
        project_name = detected_project.project_name
        autotest_repository.update_run(
            run_id,
            project_type_detected=detected_project.project_type_detected,
            working_directory=detected_project.working_dir_rel,
            project_name=project_name,
            project_type=detected_project.project_type_detected,
            summary=f"Detected {detected_project.project_type_detected or 'unknown'} project.",
        )
        timeline = set_timeline_item(
            timeline,
            "detected_stack",
            status="success",
            finished_at=utc_now_iso(),
            message=detected_project.project_type_detected or "unknown",
        )
        save_run_timeline(run_id, timeline)

        fail_step_marker = detected_project.working_dir / ".autotest_fail_step"
        fail_step = fail_step_marker.read_text(encoding="utf-8").strip() if fail_step_marker.exists() else ""
        execution_plan = build_execution_plan(
            project_type_detected=detected_project.project_type_detected,
            working_dir=detected_project.working_dir,
            execution_mode=execution_mode,
        )

        skipped_steps: list[str] = []
        ran_tests_started_at: str | None = None
        overall_ok = True

        for step in execution_plan:
            step_id = step_ids[step.name]
            commands_by_step[step.name] = step.command

            if ran_tests_started_at is None:
                ran_tests_started_at = utc_now_iso()
                timeline = set_timeline_item(timeline, "ran_tests", status="running", started_at=ran_tests_started_at)
                save_run_timeline(run_id, timeline)

            result = execute_planned_step(
                step=step,
                step_id=step_id,
                working_dir=detected_project.working_dir,
                working_dir_rel=detected_project.working_dir_rel,
                project_type_detected=detected_project.project_type_detected,
                timeout_seconds=extracted_archive.timeout_seconds,
                fail_step=fail_step,
            )
            if str(result["status"]) == "skipped":
                skipped_steps.append(step.name)
                outputs[step.name] = str(result["output_text"])
                if step.name == "install":
                    timeline = mark_prepare_phase_skipped(timeline=timeline, run_id=run_id, step_name=step.name)
                continue

            outputs[step.name], finished_at = persist_step_result(step_id, result)

            if not bool(result["ok"]):
                overall_ok = False
                failed_step_name = step.name
                timeline = mark_failed_phase(timeline=timeline, run_id=run_id, step_name=step.name, finished_at=finished_at)
                break

            timeline = mark_prepare_phase_success(timeline=timeline, run_id=run_id, step_name=step.name, finished_at=finished_at)

        if overall_ok:
            await finalize_passed_run(
                run_id=run_id,
                user_id=user_id,
                timeline=timeline,
                project_name=project_name,
                project_type_detected=detected_project.project_type_detected,
                skipped_steps=skipped_steps,
            )
        else:
            await finalize_failed_run(
                run_id=run_id,
                user_id=user_id,
                timeline=timeline,
                project_name=project_name,
                project_type_detected=detected_project.project_type_detected,
                commands_by_step=commands_by_step,
                outputs=outputs,
                failed_step_name=failed_step_name,
            )
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
        timeline = finalize_autotest_timeline_failure(
            timeline=timeline,
            failed_phase=current_failed_phase(timeline, failed_reason),
            failed_reason=failed_reason,
        )
        save_run_timeline(run_id, timeline)
        mark_unfinished_command_steps(run_id=run_id, current_failed_step=failed_step_name)
        autotest_repository.update_run(run_id, status="failed")
    finally:
        cleanup_autotest_workspace(zip_path=zip_path, work_dir=extracted_archive.work_dir)
