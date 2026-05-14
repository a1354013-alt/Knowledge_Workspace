from __future__ import annotations

from datetime import datetime, timezone

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


def parse_iso_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def duration_ms(started_at: str | None, finished_at: str | None) -> int | None:
    start = parse_iso_datetime(started_at)
    end = parse_iso_datetime(finished_at)
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
        return duration_ms(
            str(started_at or "") or None,
            str(finished_at or "") or None,
        )
    try:
        return int(value)
    except (TypeError, ValueError):
        return duration_ms(
            str(started_at or "") or None,
            str(finished_at or "") or None,
        )


def normalize_timeline_status(value: str) -> str:
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


def new_timeline_item(
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
        "status": normalize_timeline_status(status),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms(started_at, finished_at),
        "message": message,
    }


def initial_autotest_timeline(*, source_ref: str, created_at: str) -> list[dict[str, object]]:
    items = [new_timeline_item(key, label) for key, label in TIMELINE_LABELS]
    items[0] = new_timeline_item(
        "uploaded",
        "Uploaded",
        status="success",
        message=source_ref or None,
        started_at=created_at,
        finished_at=created_at,
    )
    return items


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
            next_item["status"] = normalize_timeline_status(status)
        if clear_message:
            next_item["message"] = None
        elif message is not None:
            next_item["message"] = message
        if started_at is not None:
            next_item["started_at"] = started_at
        if finished_at is not None:
            next_item["finished_at"] = finished_at
        next_item["duration_ms"] = duration_ms(
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
