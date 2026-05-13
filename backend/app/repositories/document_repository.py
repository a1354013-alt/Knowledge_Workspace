# ruff: noqa: E501
from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.repository_utils import (
    DOC_STATUS_VALUES,
    WORKFLOW_STATUS_VALUES,
    utc_now_iso,
)


class DocumentRepositoryMixin:
    def add_document(
        self,
        doc_id: str,
        filename: str,
        saved_filename: str,
        file_size: int,
        uploaded_by: str | None,
        category: str = "",
        tags: str = "",
        status: str = "reviewed",
        index_status: str = "pending",
        index_error: str = "",
        indexed_at: str = "",
    ) -> bool:
        if status not in DOC_STATUS_VALUES and status not in WORKFLOW_STATUS_VALUES:
            raise ValueError(f"Unsupported document status: {status}")
        if index_status not in {"pending", "indexed", "failed"}:
            raise ValueError(f"Unsupported document index_status: {index_status}")
        now = utc_now_iso()
        is_active = 0 if status == "archived" else 1
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO documents
                    (doc_id, filename, saved_filename, allowed_roles, category, tags, status, uploaded_by, uploaded_at, file_size, approved, is_active, index_status, index_error, indexed_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        filename,
                        saved_filename,
                        "owner",
                        category,
                        tags,
                        status,
                        uploaded_by,
                        now,
                        file_size,
                        is_active,
                        index_status,
                        str(index_error or ""),
                        str(indexed_at or ""),
                        now,
                    ),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def _normalize_document_row(self, row: sqlite3.Row) -> dict[str, Any]:
        document = dict(row)
        document["allowed_roles"] = [role for role in document["allowed_roles"].split(",") if role]
        document["approved"] = int(document["approved"])
        document["is_active"] = int(document["is_active"])
        document["status"] = str(document.get("status", "") or "reviewed")
        document["category"] = str(document.get("category", "") or "")
        document["tags"] = str(document.get("tags", "") or "")
        document["index_status"] = str(document.get("index_status", "") or "pending")
        document["index_error"] = str(document.get("index_error", "") or "")
        document["indexed_at"] = str(document.get("indexed_at", "") or "")
        return document

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        return self._normalize_document_row(row) if row else None

    def list_documents(self, user_id: str | None = None, include_archived: bool = False) -> list[dict[str, Any]]:
        with self._connection() as conn:
            where: list[str] = []
            params: list[Any] = []
            if user_id:
                where.append("uploaded_by = ?")
                params.append(user_id)
            if not include_archived:
                where.append("is_active = 1")
            sql = "SELECT * FROM documents"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY uploaded_at DESC"
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [self._normalize_document_row(row) for row in rows]

    def update_document(self, doc_id: str, **updates: Any) -> bool:
        columns: list[str] = []
        params: list[Any] = []
        if "category" in updates:
            columns.append("category = ?")
            params.append(str(updates["category"] or ""))
        if "tags" in updates:
            columns.append("tags = ?")
            params.append(str(updates["tags"] or ""))
        if "status" in updates:
            status_value = str(updates["status"] or "").strip()
            if status_value and status_value not in DOC_STATUS_VALUES and status_value not in WORKFLOW_STATUS_VALUES:
                raise ValueError(f"Unsupported document status: {status_value}")
            if status_value:
                columns.append("status = ?")
                params.append(status_value)
                columns.append("is_active = ?")
                params.append(0 if status_value == "archived" else 1)
        if "index_status" in updates:
            index_status = str(updates["index_status"] or "").strip()
            if index_status not in {"pending", "indexed", "failed"}:
                raise ValueError(f"Unsupported document index_status: {index_status}")
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
        params.append(doc_id)

        with self._connection() as conn:
            cursor = conn.execute(
                f"UPDATE documents SET {', '.join(columns)} WHERE doc_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_document(self, doc_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0
