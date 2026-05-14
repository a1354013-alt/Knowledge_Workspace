# ruff: noqa: E501
from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.repository_utils import (
    AUTOTEST_STATUS_VALUES,
    AUTOTEST_STEP_STATUS_VALUES,
    int_or_zero,
    utc_now_iso,
)


class AutoTestPersistenceRepositoryMixin:
    def add_autotest_run(
        self,
        run_id: str,
        source_type: str,
        source_ref: str,
        execution_mode: str,
        project_type_detected: str,
        working_directory: str,
        project_name: str,
        project_type: str,
        status: str,
        summary: str,
        suggestion: str,
        prompt_output: str,
        failed_reason: str,
        timeline_json: str,
        created_by: str,
    ) -> bool:
        if status not in AUTOTEST_STATUS_VALUES:
            raise ValueError(f"Unsupported autotest status: {status}")
        now = utc_now_iso()
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO autotest_runs
                    (run_id, source_type, source_ref, execution_mode, project_type_detected, working_directory, project_name, project_type, status, summary, suggestion, prompt_output, failed_reason, timeline_json, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        source_type,
                        source_ref,
                        execution_mode,
                        project_type_detected,
                        working_directory,
                        project_name,
                        project_type,
                        status,
                        summary,
                        suggestion,
                        prompt_output,
                        failed_reason,
                        timeline_json,
                        created_by,
                        now,
                    ),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def add_autotest_step(
        self,
        step_id: str,
        run_id: str,
        name: str,
        command: str,
        status: str,
        started_at: str = "",
        finished_at: str = "",
        output: str = "",
        success: int = 0,
        exit_code: int = 0,
        stdout_summary: str = "",
        stderr_summary: str = "",
        error_type: str = "",
    ) -> bool:
        if status not in AUTOTEST_STEP_STATUS_VALUES:
            raise ValueError(f"Unsupported autotest step status: {status}")
        now = utc_now_iso()
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO autotest_steps
                    (step_id, run_id, name, command, status, started_at, finished_at, output, success, exit_code, stdout_summary, stderr_summary, error_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        step_id,
                        run_id,
                        name,
                        command,
                        status,
                        started_at,
                        finished_at,
                        output,
                        int_or_zero(success),
                        int_or_zero(exit_code),
                        stdout_summary,
                        stderr_summary,
                        error_type,
                        now,
                    ),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_autotest_run(self, run_id: str, **updates: Any) -> bool:
        if not updates:
            return False
        if "status" in updates and str(updates["status"]) not in AUTOTEST_STATUS_VALUES:
            raise ValueError(f"Unsupported autotest status: {updates['status']}")
        columns: list[str] = []
        params: list[Any] = []
        for key in (
            "status",
            "summary",
            "suggestion",
            "prompt_output",
            "failed_reason",
            "timeline_json",
            "project_type",
            "project_name",
            "source_ref",
            "execution_mode",
            "project_type_detected",
            "working_directory",
            "problem_entry_id",
            "solution_entry_id",
        ):
            if key in updates:
                columns.append(f"{key} = ?")
                params.append(str(updates[key]))
        if not columns:
            return False
        params.append(run_id)
        with self._connection() as conn:
            cursor = conn.execute(f"UPDATE autotest_runs SET {', '.join(columns)} WHERE run_id = ?", params)
            conn.commit()
            return cursor.rowcount > 0

    def update_autotest_step(self, step_id: str, **updates: Any) -> bool:
        if not updates:
            return False
        if "status" in updates and str(updates["status"]) not in AUTOTEST_STEP_STATUS_VALUES:
            raise ValueError(f"Unsupported autotest step status: {updates['status']}")
        columns: list[str] = []
        params: list[Any] = []
        for key in (
            "status",
            "started_at",
            "finished_at",
            "output",
            "success",
            "exit_code",
            "stdout_summary",
            "stderr_summary",
            "error_type",
        ):
            if key in updates:
                columns.append(f"{key} = ?")
                if key in {"exit_code", "success"}:
                    params.append(int_or_zero(updates[key]))
                else:
                    params.append(str(updates[key]))
        if not columns:
            return False
        params.append(step_id)
        with self._connection() as conn:
            cursor = conn.execute(f"UPDATE autotest_steps SET {', '.join(columns)} WHERE step_id = ?", params)
            conn.commit()
            return cursor.rowcount > 0

    def list_autotest_runs(self, *, limit: int = 50, created_by: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM autotest_runs WHERE created_by = ? ORDER BY created_at DESC LIMIT ?",
                (created_by, int(limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_unfinished_autotest_runs(self, *, statuses: tuple[str, ...] = ("queued", "running")) -> list[dict[str, Any]]:
        if not statuses:
            return []
        placeholders = ", ".join("?" for _ in statuses)
        with self._connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM autotest_runs WHERE status IN ({placeholders}) ORDER BY created_at ASC",
                tuple(statuses),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_autotest_run(self, *, run_id: str, created_by: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM autotest_runs WHERE run_id = ? AND created_by = ?",
                (run_id, created_by),
            ).fetchone()
        return dict(row) if row else None

    def list_autotest_steps(self, run_id: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM autotest_steps WHERE run_id = ? ORDER BY created_at ASC",
                (str(run_id),),
            ).fetchall()
        return [dict(row) for row in rows]
