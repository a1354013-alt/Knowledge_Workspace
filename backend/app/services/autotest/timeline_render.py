from __future__ import annotations

import json
import logging

from app.models import AutoTestRunResponse, AutoTestTimelineItemResponse
from app.services.autotest.timeline_events import (
    TIMELINE_KEYS,
    TIMELINE_LABELS,
    duration_ms,
    int_or_duration,
    int_or_zero,
    normalize_timeline_status,
)

logger = logging.getLogger("knowledge_workspace")


def serialize_autotest_step(step: dict) -> dict[str, object]:
    return {
        "step_id": step.get("step_id", ""),
        "name": step.get("name", ""),
        "command": step.get("command", ""),
        "status": step.get("status", ""),
        "started_at": step.get("started_at", ""),
        "finished_at": step.get("finished_at", ""),
        "output": step.get("output", ""),
        "success": int_or_zero(step.get("success")),
        "exit_code": int_or_zero(step.get("exit_code")),
        "stdout_summary": step.get("stdout_summary", ""),
        "stderr_summary": step.get("stderr_summary", ""),
        "error_type": step.get("error_type", ""),
        "created_at": step.get("created_at", ""),
    }


def _build_item(
    key: str,
    label: str,
    *,
    status: str,
    started_at: str | None = None,
    finished_at: str | None = None,
    message: str | None = None,
) -> AutoTestTimelineItemResponse:
    return AutoTestTimelineItemResponse(
        key=key,
        label=label,
        name=label,
        status=normalize_timeline_status(status),
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms(started_at, finished_at),
        message=message,
    )


def _normalize_json_timeline(items: object) -> list[AutoTestTimelineItemResponse]:
    if not isinstance(items, list):
        return []
    normalized: list[AutoTestTimelineItemResponse] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key", "") or "")
        label = str(raw.get("label", "") or raw.get("name", "") or "")
        if not key or not label:
            continue
        normalized.append(
            AutoTestTimelineItemResponse(
                key=key,
                label=label,
                name=str(raw.get("name", "") or label),
                status=normalize_timeline_status(str(raw.get("status", "") or "pending")),
                started_at=str(raw.get("started_at", "") or "") or None,
                finished_at=str(raw.get("finished_at", "") or "") or None,
                duration_ms=int_or_duration(
                    raw.get("duration_ms"),
                    started_at=raw.get("started_at"),
                    finished_at=raw.get("finished_at"),
                ),
                message=str(raw.get("message", "") or "") or None,
            )
        )
    return normalized


def _timeline_from_json(run_row: dict) -> list[AutoTestTimelineItemResponse]:
    timeline_json = str(run_row.get("timeline_json", "") or "").strip()
    if not timeline_json:
        return []
    try:
        return _normalize_json_timeline(json.loads(timeline_json))
    except json.JSONDecodeError:
        logger.warning("Invalid timeline_json for AutoTest run %s", run_row.get("run_id", ""))
        return []


def _derived_run_state(run_row: dict, step_rows: list[dict]) -> dict[str, object]:
    run_status = str(run_row.get("status", "") or "").lower()
    created_at = str(run_row.get("created_at", "") or "") or None
    has_workdir = bool(str(run_row.get("working_directory", "") or "").strip())
    detected_stack = str(run_row.get("project_type_detected", "") or run_row.get("project_type", "") or "").strip()
    has_report = any(str(run_row.get(field, "") or "").strip() for field in ("summary", "suggestion", "prompt_output"))
    has_started_steps = any(str(step.get("status", "") or "").lower() not in {"queued", "pending", ""} for step in step_rows)
    failed_step = next((step for step in step_rows if str(step.get("status", "")).lower() == "failed"), None)
    latest_step = step_rows[-1] if step_rows else None
    return {
        "run_status": run_status,
        "created_at": created_at,
        "has_workdir": has_workdir,
        "detected_stack": detected_stack,
        "has_report": has_report,
        "has_started_steps": has_started_steps,
        "failed_step": failed_step,
        "latest_step": latest_step,
    }


def _ran_tests_status(*, run_status: str, step_rows: list[dict], failed_step: dict | None, has_started_steps: bool) -> str:
    if failed_step:
        return "failed"
    if run_status == "running" or any(str(step.get("status", "")).lower() == "running" for step in step_rows):
        return "running"
    if step_rows and all(str(step.get("status", "")).lower() in {"passed", "skipped", "unavailable"} for step in step_rows):
        return "done"
    if has_started_steps:
        return "running"
    return "pending"


def _generated_report_status(*, run_status: str, has_report: bool) -> str:
    if run_status == "running" and has_report:
        return "running"
    if run_status in {"passed", "failed"} and has_report:
        return "done"
    return "pending"


def _failed_message(*, run_row: dict, run_status: str, failed_step: dict | None) -> str | None:
    if failed_step:
        return str(
            failed_step.get("stderr_summary")
            or failed_step.get("output")
            or run_row.get("failed_reason")
            or run_row.get("summary")
            or "AutoTest run failed."
        )
    if run_status == "failed":
        return str(run_row.get("failed_reason") or run_row.get("summary") or "AutoTest run failed.")
    return None


def _fallback_timeline(run_row: dict, step_rows: list[dict]) -> list[AutoTestTimelineItemResponse]:
    state = _derived_run_state(run_row, step_rows)
    run_status = str(state["run_status"])
    created_at = state["created_at"]
    has_workdir = bool(state["has_workdir"])
    detected_stack = str(state["detected_stack"])
    has_report = bool(state["has_report"])
    has_started_steps = bool(state["has_started_steps"])
    failed_step = state["failed_step"]
    latest_step = state["latest_step"]

    ran_tests_status = _ran_tests_status(
        run_status=run_status,
        step_rows=step_rows,
        failed_step=failed_step,
        has_started_steps=has_started_steps,
    )
    generated_report_status = _generated_report_status(run_status=run_status, has_report=has_report)
    extracted_status = "done" if has_workdir else ("running" if run_status == "running" else "pending")
    detected_status = "done" if detected_stack else ("running" if extracted_status in {"done", "running"} and run_status == "running" else "pending")
    failed_reason_status = "failed" if run_status == "failed" else ("skipped" if run_status == "passed" else "pending")
    failed_message = _failed_message(run_row=run_row, run_status=run_status, failed_step=failed_step)

    items = {
        "uploaded": _build_item(
            "uploaded",
            "Uploaded",
            status="success",
            started_at=created_at,
            finished_at=created_at,
            message=str(run_row.get("source_ref", "") or "") or None,
        ),
        "extracted": _build_item(
            "extracted",
            "Extracted",
            status=extracted_status,
            started_at=created_at if has_workdir else None,
            finished_at=created_at if has_workdir else None,
            message=str(run_row.get("working_directory", "") or "") or None,
        ),
        "detected_stack": _build_item(
            "detected_stack",
            "Detected stack",
            status=detected_status,
            started_at=created_at if detected_stack else None,
            finished_at=created_at if detected_stack else None,
            message=detected_stack or None,
        ),
        "prepared_environment": _build_item(
            "prepared_environment",
            "Installed dependencies / Prepared environment",
            status="success" if step_rows else ("running" if run_status == "running" else "pending"),
            started_at=str((step_rows[0] if step_rows else {}).get("started_at", "") or "") or None,
            finished_at=str((step_rows[0] if step_rows else {}).get("finished_at", "") or "") or None,
            message=str((step_rows[0] if step_rows else {}).get("name", "") or "") or None,
        ),
        "ran_tests": _build_item(
            "ran_tests",
            "Ran tests",
            status=ran_tests_status,
            started_at=str((step_rows[0] if step_rows else {}).get("started_at", "") or "") or None,
            finished_at=str((failed_step or latest_step or {}).get("finished_at") or (latest_step or {}).get("started_at") or "") or None,
            message=str((failed_step or latest_step or {}).get("name", "") or "") or None,
        ),
        "generated_report": _build_item(
            "generated_report",
            "Generated report",
            status=generated_report_status,
            started_at=created_at if has_report else None,
            finished_at=created_at if has_report else None,
            message=str(run_row.get("summary", "") or "") or None,
        ),
        "failed_reason": _build_item(
            "failed_reason",
            "Failed reason",
            status=failed_reason_status,
            started_at=str((failed_step or {}).get("finished_at", "") or "") or created_at if run_status == "failed" else None,
            finished_at=str((failed_step or {}).get("finished_at", "") or "") or created_at if run_status == "failed" else None,
            message=failed_message,
        ),
    }
    return [items[key] for key, _label in TIMELINE_LABELS]


def build_autotest_timeline(run_row: dict, step_rows: list[dict]) -> list[AutoTestTimelineItemResponse]:
    parsed_timeline = _timeline_from_json(run_row)
    if parsed_timeline:
        return parsed_timeline
    return _fallback_timeline(run_row, step_rows)


def serialize_autotest_run(run_row: dict, step_rows: list[dict]) -> AutoTestRunResponse:
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
        failed_reason=run_row.get("failed_reason", "") or "",
        problem_entry_id=run_row.get("problem_entry_id", "") or "",
        solution_entry_id=run_row.get("solution_entry_id", "") or "",
        created_at=run_row.get("created_at", ""),
        steps=[serialize_autotest_step(step) for step in step_rows if str(step.get("name", "")) not in TIMELINE_KEYS],
        timeline=build_autotest_timeline(run_row, step_rows),
    )
