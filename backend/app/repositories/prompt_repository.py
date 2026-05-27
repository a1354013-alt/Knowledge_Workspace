# ruff: noqa: E501
from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.repository_utils import (
    INDEX_STATUS_VALUES,
    normalize_index_status,
    utc_now_iso,
)


class PromptRepositoryMixin:
    def add_saved_prompt(
        self,
        prompt_id: str,
        title: str,
        content: str,
        tags: str,
        created_by: str,
        *,
        index_status: str = "pending",
        index_error: str = "",
        indexed_at: str = "",
    ) -> bool:
        index_status = normalize_index_status(index_status, is_active=1, workflow_status="")
        if index_status not in INDEX_STATUS_VALUES:
            raise ValueError(f"Unsupported prompt index_status: {index_status}")
        now = utc_now_iso()
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO saved_prompts (prompt_id, title, content, tags, created_by, is_active, index_status, index_error, indexed_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt_id,
                        title,
                        content,
                        tags,
                        created_by,
                        index_status,
                        str(index_error or ""),
                        str(indexed_at or ""),
                        now,
                        now,
                    ),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_saved_prompts(
        self, user_id: str, limit: int = 200, *, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        with self._connection() as conn:
            if include_inactive:
                rows = conn.execute(
                    """
                    SELECT * FROM saved_prompts
                    WHERE created_by = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (user_id, int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM saved_prompts
                    WHERE created_by = ? AND is_active = 1
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (user_id, int(limit)),
                ).fetchall()
        return [
            {
                **dict(row),
                "index_status": normalize_index_status(dict(row).get("index_status"), is_active=dict(row).get("is_active", 1)),
            }
            for row in rows
        ]

    def get_saved_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM saved_prompts WHERE prompt_id = ?", (prompt_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["index_status"] = normalize_index_status(data.get("index_status"), is_active=data.get("is_active", 1))
        return data

    def delete_saved_prompt(self, prompt_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE saved_prompts
                SET is_active = 0, index_status = 'excluded', index_error = '', indexed_at = '', updated_at = ?
                WHERE prompt_id = ?
                """,
                (utc_now_iso(), prompt_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_saved_prompt_index(
        self, prompt_id: str, *, index_status: str, index_error: str = "", indexed_at: str = ""
    ) -> bool:
        index_status = normalize_index_status(index_status, is_active=1)
        if index_status not in INDEX_STATUS_VALUES:
            raise ValueError(f"Unsupported prompt index_status: {index_status}")
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE saved_prompts
                SET index_status = ?, index_error = ?, indexed_at = ?, updated_at = ?
                WHERE prompt_id = ?
                """,
                (index_status, str(index_error or ""), str(indexed_at or ""), utc_now_iso(), prompt_id),
            )
            conn.commit()
            return cursor.rowcount > 0
