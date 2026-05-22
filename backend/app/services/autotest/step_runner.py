from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.context import db
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.execution_plan import PlannedStep
from app.services.autotest.runner import _run_command
from app.services.autotest.timeline import clamp_output, utc_now_iso

logger = logging.getLogger("knowledge_workspace")
autotest_repository = AutoTestRepository(db)


def mark_unfinished_command_steps(*, run_id: str, current_failed_step: str = "") -> None:
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


def _mark_step_running(step_id: str) -> None:
    autotest_repository.update_step(step_id, status="running", started_at=utc_now_iso())


def _simulated_step_output(
    *,
    step: PlannedStep,
    project_type_detected: str,
    working_dir_rel: str,
    failed: bool = False,
    fail_step: str = "",
) -> str:
    lines = [
        f"[{step.name}] command: {step.command}",
        f"[{step.name}] project_type_detected: {project_type_detected}",
        f"[{step.name}] execution_mode: simulated",
        f"[{step.name}] working_directory: {working_dir_rel}",
    ]
    if failed:
        lines.extend(
            [
                f"[{step.name}] simulated: FAILED",
                f"Simulated failure requested by zip marker: {fail_step}",
            ]
        )
    else:
        lines.append(f"[{step.name}] simulated: ok")
    return "\n".join(lines)


def _skipped_step_output(*, step: PlannedStep, project_type_detected: str, working_dir_rel: str) -> str:
    return "\n".join(
        [
            f"[{step.name}] command: {step.command}",
            f"[{step.name}] project_type_detected: {project_type_detected}",
            f"[{step.name}] execution_mode: real",
            f"[{step.name}] working_directory: {working_dir_rel}",
            f"[{step.name}] skipped: yes",
            f"Reason: {step.skip_reason}",
        ]
    ).strip()


def _real_output(*, step: PlannedStep, project_type_detected: str, working_dir_rel: str, stdout: str, stderr: str) -> str:
    return (
        f"[{step.name}] command: {step.command}\n"
        f"[{step.name}] project_type_detected: {project_type_detected}\n"
        f"[{step.name}] execution_mode: real\n"
        f"[{step.name}] working_directory: {working_dir_rel}\n\n"
        "STDOUT:\n"
        f"{stdout.strip()}\n\n"
        "STDERR:\n"
        f"{stderr.strip()}\n"
    ).strip()


def _create_result(
    *,
    ok: bool,
    exit_code: int,
    error_type: str,
    output_text: str,
    stdout: str = "",
    stderr: str = "",
    status: str | None = None,
    finished_at: str | None = None,
) -> dict[str, object]:
    resolved_status = status or ("passed" if ok else "failed")
    if error_type == "command_not_found":
        resolved_status = "unavailable"
    return {
        "ok": ok,
        "exit_code": exit_code,
        "error_type": error_type,
        "output_text": output_text,
        "stdout": stdout,
        "stderr": stderr,
        "status": resolved_status,
        "finished_at": finished_at,
    }


def _validate_step(
    *,
    step: PlannedStep,
    step_id: str,
    fail_step: str,
    project_type_detected: str,
    working_dir_rel: str,
) -> dict[str, object] | None:
    autotest_repository.update_step(step_id, command=step.command)

    if fail_step and fail_step == step.name:
        _mark_step_running(step_id)
        return _create_result(
            ok=False,
            exit_code=1,
            error_type="simulated_failure",
            output_text=_simulated_step_output(
                step=step,
                project_type_detected=project_type_detected,
                working_dir_rel=working_dir_rel,
                failed=True,
                fail_step=fail_step,
            ),
        )

    if not step.uses_real_execution:
        _mark_step_running(step_id)
        return _create_result(
            ok=True,
            exit_code=0,
            error_type="",
            output_text=_simulated_step_output(
                step=step,
                project_type_detected=project_type_detected,
                working_dir_rel=working_dir_rel,
            ),
        )

    if not step.should_run:
        started_at = utc_now_iso()
        output_text = _skipped_step_output(
            step=step,
            project_type_detected=project_type_detected,
            working_dir_rel=working_dir_rel,
        )
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
        return _create_result(
            ok=True,
            exit_code=0,
            error_type="skipped",
            output_text=output_text,
            status="skipped",
            finished_at=started_at,
        )

    return None


def _execute_command(
    *,
    step: PlannedStep,
    working_dir: Path,
    working_dir_rel: str,
    project_type_detected: str,
    timeout_seconds: int,
) -> dict[str, object]:
    try:
        exit_code, stdout, stderr = _run_command(argv=step.argv, cwd=working_dir, timeout_seconds=timeout_seconds)
        return _create_result(
            ok=exit_code == 0,
            exit_code=exit_code,
            error_type="",
            output_text=_real_output(
                step=step,
                project_type_detected=project_type_detected,
                working_dir_rel=working_dir_rel,
                stdout=stdout,
                stderr=stderr,
            ),
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired:
        return _create_result(
            ok=False,
            exit_code=124,
            error_type="timeout",
            output_text=f"[{step.name}] command timed out after {timeout_seconds}s: {step.command}",
        )
    except FileNotFoundError:
        return _create_result(
            ok=False,
            exit_code=127,
            error_type="command_not_found",
            output_text=f"[{step.name}] command not found: {step.command}",
        )
    except OSError as exc:
        logger.warning("AutoTest command execution OS error in step %s: %s", step.name, exc)
        return _create_result(
            ok=False,
            exit_code=1,
            error_type="os_error",
            output_text=f"[{step.name}] exception while running command: {exc}",
        )
    except Exception as exc:
        logger.exception("AutoTest command execution failed unexpectedly in step %s", step.name)
        return _create_result(
            ok=False,
            exit_code=1,
            error_type="exception",
            output_text=f"[{step.name}] exception while running command: {exc}",
        )


def execute_planned_step(
    *,
    step: PlannedStep,
    step_id: str,
    working_dir: Path,
    working_dir_rel: str,
    project_type_detected: str,
    timeout_seconds: int,
    fail_step: str,
) -> dict[str, object]:
    precomputed = _validate_step(
        step=step,
        step_id=step_id,
        fail_step=fail_step,
        project_type_detected=project_type_detected,
        working_dir_rel=working_dir_rel,
    )
    if precomputed is not None:
        return precomputed

    _mark_step_running(step_id)
    return _execute_command(
        step=step,
        working_dir=working_dir,
        working_dir_rel=working_dir_rel,
        project_type_detected=project_type_detected,
        timeout_seconds=timeout_seconds,
    )


def persist_step_result(step_id: str, result: dict[str, object]) -> tuple[str, str]:
    finished_at = str(result.get("finished_at") or utc_now_iso())
    output_text = clamp_output(str(result["output_text"]))
    autotest_repository.update_step(
        step_id,
        status=str(result["status"]),
        finished_at=finished_at,
        output=output_text,
        success=1 if bool(result["ok"]) else 0,
        exit_code=int(result["exit_code"]),
        stdout_summary=str(result["stdout"] or "")[-800:],
        stderr_summary=str(result["stderr"] or "")[-800:],
        error_type=str(result["error_type"] or ""),
    )
    return output_text, finished_at
