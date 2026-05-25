# ruff: noqa: E501
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from app.repositories.repository_utils import (
    INDEX_STATUS_VALUES,
    KNOWLEDGE_STATUS_VALUES,
    utc_now_iso,
)


class KnowledgeRepositoryMixin:
    def add_knowledge_entry(
        self,
        entry_id: str,
        title: str,
        status: str,
        problem: str,
        root_cause: str,
        solution: str,
        tags: str,
        notes: str,
        created_by: str,
        source_type: str = "manual",
        source_ref: str = "",
        index_status: str = "pending",
        index_error: str = "",
        indexed_at: str = "",
    ) -> bool:
        if status not in KNOWLEDGE_STATUS_VALUES:
            raise ValueError(f"Unsupported knowledge status: {status}")
        if index_status not in INDEX_STATUS_VALUES:
            raise ValueError(f"Unsupported knowledge index_status: {index_status}")
        now = utc_now_iso()
        is_active = 0 if status == "archived" else 1
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO knowledge_entries
                    (entry_id, title, status, problem, root_cause, solution, tags, notes, source_type, source_ref, created_by, is_active, index_status, index_error, indexed_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry_id,
                        title,
                        status,
                        problem,
                        root_cause,
                        solution,
                        tags,
                        notes,
                        source_type,
                        source_ref,
                        created_by,
                        is_active,
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

    def list_knowledge_entries(
        self,
        limit: int = 50,
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
            sql = "SELECT * FROM knowledge_entries"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY updated_at DESC LIMIT ?"
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def get_knowledge_entry(self, entry_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM knowledge_entries WHERE entry_id = ?", (entry_id,)).fetchone()
        return dict(row) if row else None

    def update_knowledge_entry(self, entry_id: str, **updates: Any) -> bool:
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
        if "notes" in updates:
            columns.append("notes = ?")
            params.append(str(updates["notes"] or ""))
        if "source_type" in updates:
            columns.append("source_type = ?")
            params.append(str(updates["source_type"] or "manual"))
        if "source_ref" in updates:
            columns.append("source_ref = ?")
            params.append(str(updates["source_ref"] or ""))
        if "status" in updates:
            status_value = str(updates["status"] or "").strip()
            if status_value and status_value not in KNOWLEDGE_STATUS_VALUES:
                raise ValueError(f"Unsupported knowledge status: {status_value}")
            if status_value:
                columns.append("status = ?")
                params.append(status_value)
                columns.append("is_active = ?")
                params.append(0 if status_value == "archived" else 1)
        if "index_status" in updates:
            index_status = str(updates["index_status"] or "").strip()
            if index_status not in INDEX_STATUS_VALUES:
                raise ValueError(f"Unsupported knowledge index_status: {index_status}")
            columns.append("index_status = ?")
            params.append(index_status)
        if "index_error" in updates:
            columns.append("index_error = ?")
            params.append(str(updates["index_error"] or ""))
        if "indexed_at" in updates:
            columns.append("indexed_at = ?")
            params.append(str(updates["indexed_at"] or ""))
        if not columns:
            return False

        columns.append("updated_at = ?")
        params.append(utc_now_iso())
        params.append(entry_id)
        with self._connection() as conn:
            cursor = conn.execute(f"UPDATE knowledge_entries SET {', '.join(columns)} WHERE entry_id = ?", params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_knowledge_entry(self, entry_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM knowledge_entries WHERE entry_id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def add_knowledge_revision(
        self,
        *,
        entry_id: str,
        snapshot: dict[str, Any],
        change_note: str,
        created_by: str,
    ) -> str | None:
        now = utc_now_iso()
        revision_id = str(uuid.uuid4())
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) FROM knowledge_revisions WHERE entry_id = ?",
                (entry_id,),
            ).fetchone()
            version_number = int(row[0] or 0) + 1
            try:
                conn.execute(
                    """
                    INSERT INTO knowledge_revisions
                    (revision_id, entry_id, version_number, title, status, problem, root_cause, solution, tags, notes, source_type, source_ref, change_note, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision_id,
                        entry_id,
                        version_number,
                        str(snapshot.get("title", "") or ""),
                        str(snapshot.get("status", "draft") or "draft"),
                        str(snapshot.get("problem", "") or ""),
                        str(snapshot.get("root_cause", "") or ""),
                        str(snapshot.get("solution", "") or ""),
                        str(snapshot.get("tags", "") or ""),
                        str(snapshot.get("notes", "") or ""),
                        str(snapshot.get("source_type", "manual") or "manual"),
                        str(snapshot.get("source_ref", "") or ""),
                        str(change_note or "").strip() or "Revision snapshot",
                        created_by,
                        now,
                    ),
                )
                conn.commit()
                return revision_id
            except sqlite3.IntegrityError:
                return None

    def list_knowledge_revisions(self, entry_id: str, *, created_by: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_revisions
                WHERE entry_id = ? AND created_by = ?
                ORDER BY version_number DESC, created_at DESC
                """,
                (entry_id, created_by),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_knowledge_revision(self, revision_id: str, *, entry_id: str, created_by: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM knowledge_revisions
                WHERE revision_id = ? AND entry_id = ? AND created_by = ?
                """,
                (revision_id, entry_id, created_by),
            ).fetchone()
        return dict(row) if row else None
