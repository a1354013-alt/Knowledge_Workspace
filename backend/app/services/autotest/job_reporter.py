from __future__ import annotations

import logging

from app.context import db
from app.kb_index import index_knowledge_entry, index_logbook_entry
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.report_side_effects import create_failed_logbook_draft, create_passed_knowledge_draft
from app.services.autotest.reports import suggest_fix_from_autotest
from app.services.autotest.timeline import (
    finalize_autotest_timeline_failure,
    save_run_timeline,
    set_timeline_item,
    utc_now_iso,
)

autotest_repository = AutoTestRepository(db)
logger = logging.getLogger("knowledge_workspace")


def _save_timeline(timeline: list[dict[str, object]], *, run_id: str) -> list[dict[str, object]]:
    save_run_timeline(run_id, timeline)
    return timeline


def _mark_generated_report_running(*, timeline: list[dict[str, object]], run_id: str) -> list[dict[str, object]]:
    timeline = set_timeline_item(timeline, "generated_report", status="running", started_at=utc_now_iso())
    return _save_timeline(timeline, run_id=run_id)


def _persist_terminal_run(
    *,
    run_id: str,
    status: str,
    summary: str,
    prompt_output: str,
    suggestion: str,
    failed_reason: str,
) -> None:
    autotest_repository.update_run(
        run_id,
        status=status,
        summary=summary,
        prompt_output=prompt_output,
        suggestion=suggestion,
        failed_reason=failed_reason,
    )


def _finalize_passed_timeline(*, timeline: list[dict[str, object]], run_id: str, summary: str) -> list[dict[str, object]]:
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
    return _save_timeline(timeline, run_id=run_id)


def _finalize_failed_timeline(
    *,
    timeline: list[dict[str, object]],
    run_id: str,
    summary: str,
    failed_reason: str,
) -> list[dict[str, object]]:
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
    return _save_timeline(timeline, run_id=run_id)


def mark_prepare_phase_success(*, timeline: list[dict[str, object]], run_id: str, step_name: str, finished_at: str) -> list[dict[str, object]]:
    if step_name != "install":
        return timeline
    timeline = set_timeline_item(
        timeline,
        "prepared_environment",
        status="success",
        finished_at=finished_at,
        message=step_name,
    )
    save_run_timeline(run_id, timeline)
    return timeline


def mark_prepare_phase_skipped(*, timeline: list[dict[str, object]], run_id: str, step_name: str) -> list[dict[str, object]]:
    if step_name != "install":
        return timeline
    timeline = set_timeline_item(
        timeline,
        "prepared_environment",
        status="success",
        finished_at=utc_now_iso(),
        message="install skipped",
    )
    save_run_timeline(run_id, timeline)
    return timeline


def mark_failed_phase(*, timeline: list[dict[str, object]], run_id: str, step_name: str, finished_at: str) -> list[dict[str, object]]:
    timeline = set_timeline_item(
        timeline,
        "prepared_environment",
        status="failed" if step_name == "install" else "success",
        finished_at=finished_at,
        message=step_name,
    )
    timeline = set_timeline_item(
        timeline,
        "ran_tests",
        status="failed",
        finished_at=finished_at,
        message=step_name,
    )
    save_run_timeline(run_id, timeline)
    return timeline


async def finalize_passed_run(
    *,
    run_id: str,
    user_id: str,
    timeline: list[dict[str, object]],
    project_name: str,
    project_type_detected: str,
    skipped_steps: list[str],
) -> None:
    timeline = _mark_generated_report_running(timeline=timeline, run_id=run_id)
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
    _persist_terminal_run(
        run_id=run_id,
        status="passed",
        summary=summary,
        prompt_output=prompt_output,
        suggestion="",
        failed_reason="",
    )
    _finalize_passed_timeline(timeline=timeline, run_id=run_id, summary=summary)
    try:
        knowledge_id = create_passed_knowledge_draft(
            run_id=run_id,
            user_id=user_id,
            project_name=project_name,
            summary=summary,
            prompt_output=prompt_output,
            indexer=index_knowledge_entry,
        )
    except Exception as exc:
        logger.warning("AutoTest run %s passed but knowledge draft side effect failed: %s", run_id, exc)
        knowledge_id = ""
    if not knowledge_id:
        logger.warning("AutoTest run %s passed but knowledge draft side effect did not create an entry.", run_id)


async def finalize_failed_run(
    *,
    run_id: str,
    user_id: str,
    timeline: list[dict[str, object]],
    project_name: str,
    project_type_detected: str,
    commands_by_step: dict[str, str],
    outputs: dict[str, str],
    failed_step_name: str,
) -> None:
    failed_step = failed_step_name or "unknown"
    summary = f"Acceptance pipeline failed at step '{failed_step}' ({project_type_detected})."
    failed_output = outputs.get(failed_step, "")
    timeline = _mark_generated_report_running(timeline=timeline, run_id=run_id)
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
    _persist_terminal_run(
        run_id=run_id,
        status="failed",
        summary=summary,
        prompt_output=prompt_output,
        suggestion=suggestion,
        failed_reason=failed_reason,
    )
    _finalize_failed_timeline(
        timeline=timeline,
        run_id=run_id,
        summary=summary,
        failed_reason=failed_reason,
    )
    try:
        logbook_id = create_failed_logbook_draft(
            run_id=run_id,
            user_id=user_id,
            project_name=project_name,
            prompt_output=prompt_output,
            suggestion=suggestion,
            indexer=index_logbook_entry,
        )
    except Exception as exc:
        logger.warning("AutoTest run %s failed and logbook draft side effect failed: %s", run_id, exc)
        logbook_id = ""
    if not logbook_id:
        logger.warning("AutoTest run %s failed but logbook draft side effect did not create an entry.", run_id)


def current_failed_phase(timeline: list[dict[str, object]], failed_reason: str) -> str:
    current_phase = "generated_report" if "report" in failed_reason.lower() else "detected_stack"
    if str(next((item for item in timeline if str(item.get("key")) == "generated_report"), {}).get("status", "")) == "running":
        return "generated_report"
    if str(next((item for item in timeline if str(item.get("key")) == "ran_tests"), {}).get("status", "")) == "running":
        return "ran_tests"
    if str(next((item for item in timeline if str(item.get("key")) == "prepared_environment"), {}).get("status", "")) == "running":
        return "prepared_environment"
    if str(next((item for item in timeline if str(item.get("key")) == "detected_stack"), {}).get("status", "")) == "running":
        return "detected_stack"
    if str(next((item for item in timeline if str(item.get("key")) == "extracted"), {}).get("status", "")) == "running":
        return "extracted"
    return current_phase
