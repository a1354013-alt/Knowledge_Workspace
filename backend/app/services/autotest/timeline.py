from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.context import db
from app.models import AutoTestRunResponse, AutoTestTimelineItemResponse
from app.repositories.autotest_repository import AutoTestRepository

logger = logging.getLogger("knowledge_workspace")
autotest_repository = AutoTestRepository(db)

TIMELINE_LABELS: tuple[tuple[str, str], ...] = (
    ("uploaded", "Uploaded"),
    ("extracted", "Extracted"),
    ("detected_stack", "Detected stack"),
    ("prepared_environment", "Installed dependencies / Prepared environment"),
    ("ran_tests", "Ran tests"),
    ("generated_report", "Generated report"),
    ("failed_reason", "Failed reason"),
)

TIMELINE_KEYS = {key for key, _label in TIMELINE_LABELS}

AUTOTEST_OUTPUT_LIMIT = 12_000


def clamp_output(value: str, *, limit: int = AUTOTEST_OUTPUT_LIMIT) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated to {limit} characters]"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def int_or_zero(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def int_or_duration(value: object, *, started_at: object = None, finished_at: object = None) -> int | None:
    if value is None:
        return _duration_ms(
            str(started_at or "") or None,
            str(finished_at or "") or None,
        )
    try:
        return int(value)
    except (TypeError, ValueError):
        return _duration_ms(
            str(started_at or "") or None,
            str(finished_at or "") or None,
        )


def _normalize_timeline_status(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"passed", "done", "success"}:
        return "success"
    if normalized == "failed":
        return "failed"
    if normalized in {"skipped", "unavailable"}:
        return "skipped"
    if normalized == "running":
        return "running"
    return "pending"


def _new_timeline_item(
    key: str,
    label: str,
    *,
    status: str = "pending",
    message: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "name": label,
        "status": _normalize_timeline_status(status),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": _duration_ms(started_at, finished_at),
        "message": message,
    }


def initial_autotest_timeline(*, source_ref: str, created_at: str) -> list[dict[str, object]]:
    items = [_new_timeline_item(key, label) for key, label in TIMELINE_LABELS]
    items[0] = _new_timeline_item(
        "uploaded",
        "Uploaded",
        status="success",
        message=source_ref or None,
        started_at=created_at,
        finished_at=created_at,
    )
    return items


def save_run_timeline(run_id: str, timeline: list[dict[str, object]]) -> None:
    autotest_repository.update_run(run_id, timeline_json=json.dumps(timeline, ensure_ascii=True))


def set_timeline_item(
    timeline: list[dict[str, object]],
    key: str,
    *,
    status: str | None = None,
    message: str | None = None,
    clear_message: bool = False,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> list[dict[str, object]]:
    updated: list[dict[str, object]] = []
    for item in timeline:
        if str(item.get("key")) != key:
            updated.append(item)
            continue
        next_item = dict(item)
        if status is not None:
            next_item["status"] = _normalize_timeline_status(status)
        if clear_message:
            next_item["message"] = None
        elif message is not None:
            next_item["message"] = message
        if started_at is not None:
            next_item["started_at"] = started_at
        if finished_at is not None:
            next_item["finished_at"] = finished_at
        next_item["duration_ms"] = _duration_ms(
            str(next_item.get("started_at") or "") or None,
            str(next_item.get("finished_at") or "") or None,
        )
        updated.append(next_item)
    return updated


def finalize_autotest_timeline_failure(
    *,
    timeline: list[dict[str, object]],
    failed_phase: str,
    failed_reason: str,
) -> list[dict[str, object]]:
    output = timeline
    phase_found = False
    failed_at = utc_now_iso()
    for key, _label in TIMELINE_LABELS:
        if key == failed_phase:
            phase_found = True
            output = set_timeline_item(
                output,
                key,
                status="failed",
                finished_at=failed_at,
                message=failed_reason,
            )
            continue
        current_item = next((item for item in output if str(item.get("key")) == key), None)
        if not current_item:
            continue
        current_status = str(current_item.get("status", "") or "")
        if phase_found and current_status == "pending":
            output = set_timeline_item(output, key, status="skipped")
    output = set_timeline_item(
        output,
        "failed_reason",
        status="failed",
        started_at=failed_at,
        finished_at=failed_at,
        message=failed_reason,
    )
    return output


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


def build_autotest_timeline(run_row: dict, step_rows: list[dict]) -> list[AutoTestTimelineItemResponse]:
    timeline_json = str(run_row.get("timeline_json", "") or "").strip()
    if timeline_json:
        try:
            items = json.loads(timeline_json)
            if isinstance(items, list):
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
                            status=_normalize_timeline_status(str(raw.get("status", "") or "pending")),
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
                if normalized:
                    return normalized
        except json.JSONDecodeError:
            logger.warning("Invalid timeline_json for AutoTest run %s", run_row.get("run_id", ""))

    run_status = str(run_row.get("status", "") or "").lower()
    created_at = str(run_row.get("created_at", "") or "") or None
    has_workdir = bool(str(run_row.get("working_directory", "") or "").strip())
    detected_stack = str(run_row.get("project_type_detected", "") or run_row.get("project_type", "") or "").strip()
    has_report = any(str(run_row.get(field, "") or "").strip() for field in ("summary", "suggestion", "prompt_output"))
    has_started_steps = any(str(step.get("status", "") or "").lower() not in {"queued", "pending", ""} for step in step_rows)
    failed_step = next((step for step in step_rows if str(step.get("status", "")).lower() == "failed"), None)
    latest_step = step_rows[-1] if step_rows else None

    ran_tests_status = "pending"
    if failed_step:
        ran_tests_status = "failed"
    elif run_status == "running" or any(str(step.get("status", "")).lower() == "running" for step in step_rows):
        ran_tests_status = "running"
    elif step_rows and all(str(step.get("status", "")).lower() in {"passed", "skipped", "unavailable"} for step in step_rows):
        ran_tests_status = "done"
    elif has_started_steps:
        ran_tests_status = "running"

    generated_report_status = "pending"
    if run_status == "running" and has_report:
        generated_report_status = "running"
    elif run_status in {"passed", "failed"} and has_report:
        generated_report_status = "done"

    extracted_status = "done" if has_workdir else ("running" if run_status == "running" else "pending")
    detected_status = "done" if detected_stack else ("running" if extracted_status in {"done", "running"} and run_status == "running" else "pending")
    failed_reason_status = "failed" if run_status == "failed" else ("skipped" if run_status == "passed" else "pending")

    failed_message = None
    if failed_step:
        failed_message = str(
            failed_step.get("stderr_summary")
            or failed_step.get("output")
            or run_row.get("failed_reason")
            or run_row.get("summary")
            or "AutoTest run failed."
        )
    elif run_status == "failed":
        failed_message = str(run_row.get("failed_reason") or run_row.get("summary") or "AutoTest run failed.")

    def build_item(
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
            status=_normalize_timeline_status(status),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=_duration_ms(started_at, finished_at),
            message=message,
        )

    items = {
        "uploaded": build_item(
            "uploaded",
            "Uploaded",
            status="success",
            started_at=created_at,
            finished_at=created_at,
            message=str(run_row.get("source_ref", "") or "") or None,
        ),
        "extracted": build_item(
            "extracted",
            "Extracted",
            status=extracted_status,
            started_at=created_at if has_workdir else None,
            finished_at=created_at if has_workdir else None,
            message=str(run_row.get("working_directory", "") or "") or None,
        ),
        "detected_stack": build_item(
            "detected_stack",
            "Detected stack",
            status=detected_status,
            started_at=created_at if detected_stack else None,
            finished_at=created_at if detected_stack else None,
            message=detected_stack or None,
        ),
        "prepared_environment": build_item(
            "prepared_environment",
            "Installed dependencies / Prepared environment",
            status="success" if step_rows else ("running" if run_status == "running" else "pending"),
            started_at=str((step_rows[0] if step_rows else {}).get("started_at", "") or "") or None,
            finished_at=str((step_rows[0] if step_rows else {}).get("finished_at", "") or "") or None,
            message=str((step_rows[0] if step_rows else {}).get("name", "") or "") or None,
        ),
        "ran_tests": build_item(
            "ran_tests",
            "Ran tests",
            status=ran_tests_status,
            started_at=str((step_rows[0] if step_rows else {}).get("started_at", "") or "") or None,
            finished_at=str((failed_step or latest_step or {}).get("finished_at") or (latest_step or {}).get("started_at") or "") or None,
            message=str((failed_step or latest_step or {}).get("name", "") or "") or None,
        ),
        "generated_report": build_item(
            "generated_report",
            "Generated report",
            status=generated_report_status,
            started_at=created_at if has_report else None,
            finished_at=created_at if has_report else None,
            message=str(run_row.get("summary", "") or "") or None,
        ),
        "failed_reason": build_item(
            "failed_reason",
            "Failed reason",
            status=failed_reason_status,
            started_at=str((failed_step or {}).get("finished_at", "") or "") or created_at if run_status == "failed" else None,
            finished_at=str((failed_step or {}).get("finished_at", "") or "") or created_at if run_status == "failed" else None,
            message=failed_message,
        ),
    }
    return [items[key] for key, _label in TIMELINE_LABELS]


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


def _safe_autotest_index_entry(*, run_id: str, item_kind: str, item_id: str, entry: dict | None, indexer) -> bool:
    if not entry:
        return False
    try:
        result = indexer(entry)
    except Exception as exc:
        logger.warning(
            "AutoTest run %s saved %s %s but indexing failed: %s",
            run_id,
            item_kind,
            item_id,
            exc,
        )
        return False
    if result is False:
        logger.warning(
            "AutoTest run %s saved %s %s but indexing returned failure without an exception",
            run_id,
            item_kind,
            item_id,
        )
        return False
    return True


