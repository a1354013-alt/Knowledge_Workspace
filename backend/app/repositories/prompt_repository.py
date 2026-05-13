# ruff: noqa: E501
from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.repository_utils import (
    utc_now_iso,
)


class PromptRepositoryMixin:
    def add_saved_prompt(self, prompt_id: str, title: str, content: str, tags: str, created_by: str) -> bool:
        now = utc_now_iso()
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO saved_prompts (prompt_id, title, content, tags, created_by, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (prompt_id, title, content, tags, created_by, now, now),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_saved_prompts(self, user_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM saved_prompts
                WHERE created_by = ? AND is_active = 1
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, int(limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_saved_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM saved_prompts WHERE prompt_id = ?", (prompt_id,)).fetchone()
        return dict(row) if row else None

    def delete_saved_prompt(self, prompt_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute("UPDATE saved_prompts SET is_active = 0 WHERE prompt_id = ?", (prompt_id,))
            conn.commit()
            return cursor.rowcount > 0
