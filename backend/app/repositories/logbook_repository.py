# ruff: noqa: E501
from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.repository_utils import (
    LOGBOOK_STATUS_VALUES,
    utc_now_iso,
)


class LogbookRepositoryMixin:
    def add_logbook_entry(
        self,
        entry_id: str,
        title: str,
        status: str,
        run_id: str,
        problem: str,
        root_cause: str,
        solution: str,
        tags: str,
        source_type: str,
        created_by: str,
        source_ref: str = "",
    ) -> bool:
        if status not in LOGBOOK_STATUS_VALUES:
            raise ValueError(f"Unsupported logbook status: {status}")
        now = utc_now_iso()
        is_active = 0 if status == "archived" else 1
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO logbook_entries
                    (entry_id, title, status, run_id, problem, root_cause, solution, tags, source_type, source_ref, created_by, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry_id,
                        title,
                        status,
                        run_id,
                        problem,
                        root_cause,
                        solution,
                        tags,
                        source_type,
                        source_ref,
                        created_by,
                        is_active,
                        now,
                        now,
                    ),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_logbook_entries(
        self,
        limit: int = 100,
        user_id: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        with self._connection() as conn:
            where: list[str] = []
            params: list[Any] = []
            if user_id is not None:
                where.append("created_by = ?")
                params.append(user_id)
            if not include_archived:
                where.append("is_active = 1")
            params.append(int(limit))
            sql = "SELECT * FROM logbook_entries"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY updated_at DESC LIMIT ?"
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def get_logbook_entry(self, entry_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM logbook_entries WHERE entry_id = ?", (entry_id,)).fetchone()
        return dict(row) if row else None

    def update_logbook_entry(self, entry_id: str, **updates: Any) -> bool:
        columns: list[str] = []
        params: list[Any] = []
        if "title" in updates:
            columns.append("title = ?")
            params.append(str(updates["title"] or ""))
        if "problem" in updates:
            columns.append("problem = ?")
            params.append(str(updates["problem"] or ""))
        if "root_cause" in updates:
            columns.append("root_cause = ?")
            params.append(str(updates["root_cause"] or ""))
        if "solution" in updates:
            columns.append("solution = ?")
            params.append(str(updates["solution"] or ""))
        if "tags" in updates:
            columns.append("tags = ?")
            params.append(str(updates["tags"] or ""))
        if "source_type" in updates:
            columns.append("source_type = ?")
            params.append(str(updates["source_type"] or "manual"))
        if "source_ref" in updates:
            columns.append("source_ref = ?")
            params.append(str(updates["source_ref"] or ""))
        if "status" in updates:
            status_value = str(updates["status"] or "").strip()
            if status_value and status_value not in LOGBOOK_STATUS_VALUES:
                raise ValueError(f"Unsupported logbook status: {status_value}")
            if status_value:
                columns.append("status = ?")
                params.append(status_value)
                columns.append("is_active = ?")
                params.append(0 if status_value == "archived" else 1)
        if not columns:
            return False

        columns.append("updated_at = ?")
        params.append(utc_now_iso())
        params.append(entry_id)
        with self._connection() as conn:
            cursor = conn.execute(f"UPDATE logbook_entries SET {', '.join(columns)} WHERE entry_id = ?", params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_logbook_entry(self, entry_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM logbook_entries WHERE entry_id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0
