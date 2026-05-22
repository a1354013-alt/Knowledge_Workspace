from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.context import db, settings
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.timeline import (
    finalize_autotest_timeline_failure,
    load_run_timeline,
    save_run_timeline,
    utc_now_iso,
)

autotest_repository = AutoTestRepository(db)


def _parse_iso_datetime(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_activity_at(run_row: dict, step_rows: list[dict]) -> datetime | None:
    candidates = [
        _parse_iso_datetime(run_row.get("updated_at")),
        _parse_iso_datetime(run_row.get("created_at")),
    ]
    for step in step_rows:
        candidates.append(_parse_iso_datetime(step.get("started_at")))
        candidates.append(_parse_iso_datetime(step.get("finished_at")))
        candidates.append(_parse_iso_datetime(step.get("created_at")))
    valid = [candidate for candidate in candidates if candidate is not None]
    return max(valid) if valid else None


def recover_interrupted_autotest_runs(*, now: datetime | None = None, stale_after_minutes: int | None = None) -> int:
    """Fail stale in-process AutoTest runs after a server restart.

    AutoTest intentionally uses a single-process background thread. If the
    process exits mid-run, there is no durable worker to resume it, so startup
    recovery marks stale queued/running records failed instead of leaving them
    permanently active.
    """

    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stale_minutes = int(stale_after_minutes if stale_after_minutes is not None else settings.AUTOTEST_STALE_RUN_MINUTES)
    cutoff = current_time - timedelta(minutes=stale_minutes)
    recovered = 0

    for run_row in autotest_repository.list_unfinished_runs():
        run_id = str(run_row.get("run_id", "") or "")
        if not run_id:
            continue
        step_rows = autotest_repository.list_steps(run_id)
        last_activity = _latest_activity_at(run_row, step_rows)
        if last_activity and last_activity > cutoff:
            continue

        status = str(run_row.get("status", "") or "").lower()
        stale_kind = "stale_running_job" if status == "running" else "stale_queued_job"
        failed_reason = f"worker_interrupted: server_restarted: {stale_kind}"
        summary = "AutoTest run failed because the in-process worker was interrupted by a server restart."
        timeline = finalize_autotest_timeline_failure(
            timeline=load_run_timeline(run_row),
            failed_phase="ran_tests" if status == "running" else "prepared_environment",
            failed_reason=failed_reason,
        )
        save_run_timeline(run_id, timeline)
        for step in step_rows:
            step_status = str(step.get("status", "") or "").lower()
            if step_status in {"passed", "failed", "skipped", "unavailable"}:
                continue
            autotest_repository.update_step(
                str(step.get("step_id", "") or ""),
                status="failed" if step_status == "running" else "skipped",
                finished_at=utc_now_iso(),
                output=str(step.get("output", "") or ""),
                success=0,
                exit_code=1 if step_status == "running" else 0,
                stdout_summary=str(step.get("stdout_summary", "") or ""),
                stderr_summary=str(step.get("stderr_summary", "") or ""),
                error_type=stale_kind,
            )
        autotest_repository.update_run(
            run_id,
            status="failed",
            summary=summary,
            failed_reason=failed_reason,
            suggestion="",
        )
        recovered += 1
    return recovered
