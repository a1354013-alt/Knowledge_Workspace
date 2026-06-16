from __future__ import annotations

import logging
from pathlib import Path

from app.context import db
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.archive import safe_extract_zip
from app.services.autotest.archive_extractor import prepare_extracted_archive
from app.services.autotest.detector import find_project_root_on_disk
from app.services.autotest.execution_plan import PlannedStep, build_execution_plan
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


def _touch_run(run_id: str) -> None:
    autotest_repository.touch_run(run_id, updated_at=utc_now_iso())


def _persist_run_update(run_id: str, **updates: object) -> None:
    autotest_repository.update_run(run_id, **updates)
    _touch_run(run_id)


def _save_timeline(run_id: str, timeline: list[dict[str, object]]) -> None:
    save_run_timeline(run_id, timeline)
    _touch_run(run_id)


def _set_timeline(
    run_id: str,
    timeline: list[dict[str, object]],
    key: str,
    **updates: object,
) -> list[dict[str, object]]:
    timeline = set_timeline_item(timeline, key, **updates)
    _save_timeline(run_id, timeline)
    return timeline


def _mark_run_running(run_id: str) -> None:
    _persist_run_update(run_id, status="running", summary="AutoTest worker started.")


def _extract_archive(
    *, run_id: str, timeline: list[dict[str, object]], zip_path: Path, destination: Path
) -> list[dict[str, object]]:
    _persist_run_update(run_id, summary="Extracting uploaded ZIP archive.")
    timeline = _set_timeline(
        run_id,
        timeline,
        "extracted",
        status="running",
        started_at=utc_now_iso(),
        message="extracting",
    )
    safe_extract_zip(zip_path, destination)
    return _set_timeline(
        run_id,
        timeline,
        "extracted",
        status="success",
        finished_at=utc_now_iso(),
        message="extracted",
    )


def _detect_project(
    *,
    run_id: str,
    timeline: list[dict[str, object]],
    extracted_dir: Path,
    project_name: str,
) -> tuple[list[dict[str, object]], object]:
    timeline = _set_timeline(run_id, timeline, "detected_stack", status="running", started_at=utc_now_iso())
    detected_project = detect_project(
        extracted_dir=extracted_dir,
        fallback_project_name=project_name,
        root_finder=find_project_root_on_disk,
    )
    _persist_run_update(
        run_id,
        project_type_detected=detected_project.project_type_detected,
        working_directory=detected_project.working_dir_rel,
        project_name=detected_project.project_name,
        project_type=detected_project.project_type_detected,
        summary=f"Detected {detected_project.project_type_detected or 'unknown'} project.",
    )
    timeline = _set_timeline(
        run_id,
        timeline,
        "detected_stack",
        status="success",
        finished_at=utc_now_iso(),
        message=detected_project.project_type_detected or "unknown",
    )
    return timeline, detected_project


def _load_fail_step_marker(marker_path: Path) -> str:
    if not marker_path.exists():
        return ""
    return marker_path.read_text(encoding="utf-8").strip()


def _mark_ran_tests_running(run_id: str, timeline: list[dict[str, object]]) -> list[dict[str, object]]:
    return _set_timeline(
        run_id,
        timeline,
        "ran_tests",
        status="running",
        started_at=utc_now_iso(),
    )


def _record_skipped_step(
    *,
    run_id: str,
    timeline: list[dict[str, object]],
    step: PlannedStep,
) -> list[dict[str, object]]:
    if step.name == "install":
        return mark_prepare_phase_skipped(timeline=timeline, run_id=run_id, step_name=step.name)
    _touch_run(run_id)
    return timeline


def _record_finished_step(
    *,
    run_id: str,
    timeline: list[dict[str, object]],
    step: PlannedStep,
    finished_at: str,
) -> list[dict[str, object]]:
    timeline = mark_prepare_phase_success(
        timeline=timeline,
        run_id=run_id,
        step_name=step.name,
        finished_at=finished_at,
    )
    _touch_run(run_id)
    return timeline


def _record_failed_step(
    *,
    run_id: str,
    timeline: list[dict[str, object]],
    step: PlannedStep,
    finished_at: str,
) -> list[dict[str, object]]:
    timeline = mark_failed_phase(
        timeline=timeline,
        run_id=run_id,
        step_name=step.name,
        finished_at=finished_at,
    )
    _touch_run(run_id)
    return timeline


def _persist_unexpected_failure(
    *,
    run_id: str,
    timeline: list[dict[str, object]],
    failed_reason: str,
    failed_step_name: str,
) -> None:
    failed_phase = current_failed_phase(timeline, failed_reason)
    timeline = finalize_autotest_timeline_failure(
        timeline=timeline,
        failed_phase=failed_phase,
        failed_reason=failed_reason,
    )
    _save_timeline(run_id, timeline)
    if failed_phase == "detected_stack":
        summary = f"AutoTest stack detection failed: {failed_reason}"
    else:
        summary = f"AutoTest run failed: {failed_reason}"
    _persist_run_update(
        run_id,
        status="failed",
        summary=summary,
        prompt_output="",
        suggestion="",
        failed_reason=failed_reason,
    )
    mark_unfinished_command_steps(
        run_id=run_id,
        current_failed_step=failed_step_name,
        failure_summary=failed_reason,
    )


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
        _mark_run_running(run_id)
        timeline = _extract_archive(
            run_id=run_id,
            timeline=timeline,
            zip_path=zip_path,
            destination=extracted_archive.extracted_dir,
        )
        timeline, detected_project = _detect_project(
            run_id=run_id,
            timeline=timeline,
            extracted_dir=extracted_archive.extracted_dir,
            project_name=project_name,
        )
        project_name = detected_project.project_name
        fail_step = _load_fail_step_marker(detected_project.working_dir / ".autotest_fail_step")
        execution_plan = build_execution_plan(
            project_type_detected=detected_project.project_type_detected,
            working_dir=detected_project.working_dir,
            execution_mode=execution_mode,
        )

        skipped_steps: list[str] = []
        ran_tests_started = False
        overall_ok = True

        for step in execution_plan:
            step_id = step_ids[step.name]
            commands_by_step[step.name] = step.command

            if not ran_tests_started:
                timeline = _mark_ran_tests_running(run_id, timeline)
                ran_tests_started = True

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
                timeline = _record_skipped_step(run_id=run_id, timeline=timeline, step=step)
                continue

            outputs[step.name], finished_at = persist_step_result(step_id, result)
            _touch_run(run_id)

            if not bool(result["ok"]):
                overall_ok = False
                failed_step_name = step.name
                timeline = _record_failed_step(
                    run_id=run_id,
                    timeline=timeline,
                    step=step,
                    finished_at=finished_at,
                )
                break

            timeline = _record_finished_step(
                run_id=run_id,
                timeline=timeline,
                step=step,
                finished_at=finished_at,
            )

        if overall_ok:
            await finalize_passed_run(
                run_id=run_id,
                user_id=user_id,
                timeline=timeline,
                project_name=project_name,
                project_type_detected=detected_project.project_type_detected,
                skipped_steps=skipped_steps,
            )
            _touch_run(run_id)
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
            _touch_run(run_id)
    except Exception as exc:
        failed_reason = str(exc) or "AutoTest run failed unexpectedly."
        logger.exception("AutoTest run %s failed unexpectedly", run_id)
        _persist_unexpected_failure(
            run_id=run_id,
            timeline=timeline,
            failed_reason=failed_reason,
            failed_step_name=failed_step_name,
        )
    finally:
        cleanup_autotest_workspace(zip_path=zip_path, work_dir=extracted_archive.work_dir)
