# ruff: noqa: E501
from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.repository_utils import (
    INDEX_STATUS_VALUES,
    PHOTO_STATUS_VALUES,
    WORKFLOW_STATUS_VALUES,
    normalize_index_status,
    utc_now_iso,
)


class PhotoRepositoryMixin:
    def add_photo(
        self,
        photo_id: str,
        filename: str,
        saved_filename: str,
        tags: str,
        description: str,
        ocr_text: str,
        file_size: int,
        uploaded_by: str | None,
        ocr_status: str = "completed",
        ocr_error: str = "",
        status: str = "reviewed",
        index_status: str = "pending",
        index_error: str = "",
        indexed_at: str = "",
    ) -> bool:
        if status not in PHOTO_STATUS_VALUES and status not in WORKFLOW_STATUS_VALUES:
            raise ValueError(f"Unsupported photo status: {status}")
        index_status = normalize_index_status(index_status, is_active=1 if status != "archived" else 0, workflow_status=status)
        if index_status not in INDEX_STATUS_VALUES:
            raise ValueError(f"Unsupported photo index_status: {index_status}")
        now = utc_now_iso()
        is_active = 0 if status == "archived" else 1
        ocr_status_value = str(ocr_status or "completed").strip().lower()
        if ocr_status_value not in {"pending", "completed", "failed", "unavailable"}:
            raise ValueError(f"Unsupported photo ocr_status: {ocr_status_value}")
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO photos
                    (photo_id, filename, saved_filename, tags, description, ocr_text, ocr_status, ocr_error, status, uploaded_by, is_active, file_size, index_status, index_error, indexed_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        photo_id,
                        filename,
                        saved_filename,
                        tags,
                        description,
                        ocr_text,
                        ocr_status_value,
                        str(ocr_error or ""),
                        status,
                        uploaded_by,
                        is_active,
                        int(file_size),
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

    def list_photos(
        self, limit: int = 200, offset: int = 0, user_id: str | None = None, include_archived: bool = False
    ) -> list[dict[str, Any]]:
        with self._connection() as conn:
            where: list[str] = []
            params: list[Any] = []
            if user_id:
                where.append("uploaded_by = ?")
                params.append(user_id)
            if not include_archived:
                where.append("is_active = 1")
            params.extend([int(limit), int(offset)])
            sql = "SELECT * FROM photos"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                **dict(row),
                "index_status": normalize_index_status(
                    dict(row).get("index_status"),
                    is_active=dict(row).get("is_active", 1),
                    workflow_status=dict(row).get("status", ""),
                ),
            }
            for row in rows
        ]

    def count_photos(self, user_id: str | None = None, include_archived: bool = False) -> int:
        with self._connection() as conn:
            where: list[str] = []
            params: list[Any] = []
            if user_id:
                where.append("uploaded_by = ?")
                params.append(user_id)
            if not include_archived:
                where.append("is_active = 1")
            sql = "SELECT COUNT(*) FROM photos"
            if where:
                sql += " WHERE " + " AND ".join(where)
            row = conn.execute(sql, tuple(params)).fetchone()
        return int(row[0] or 0)

    def get_photo(self, photo_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM photos WHERE photo_id = ?", (photo_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["index_status"] = normalize_index_status(
            data.get("index_status"),
            is_active=data.get("is_active", 1),
            workflow_status=data.get("status", ""),
        )
        return data

    def update_photo(self, photo_id: str, **updates: Any) -> bool:
        columns: list[str] = []
        params: list[Any] = []
        if "tags" in updates:
            columns.append("tags = ?")
            params.append(str(updates["tags"] or ""))
        if "description" in updates:
            columns.append("description = ?")
            params.append(str(updates["description"] or ""))
        if "ocr_text" in updates:
            columns.append("ocr_text = ?")
            params.append(str(updates["ocr_text"] or ""))
        if "ocr_status" in updates:
            ocr_status_value = str(updates["ocr_status"] or "").strip().lower()
            if ocr_status_value not in {"pending", "completed", "failed", "unavailable"}:
                raise ValueError(f"Unsupported photo ocr_status: {ocr_status_value}")
            columns.append("ocr_status = ?")
            params.append(ocr_status_value)
        if "ocr_error" in updates:
            columns.append("ocr_error = ?")
            params.append(str(updates["ocr_error"] or ""))
        if "status" in updates:
            status_value = str(updates["status"] or "").strip()
            if status_value and status_value not in PHOTO_STATUS_VALUES and status_value not in WORKFLOW_STATUS_VALUES:
                raise ValueError(f"Unsupported photo status: {status_value}")
            if status_value:
                columns.append("status = ?")
                params.append(status_value)
                columns.append("is_active = ?")
                params.append(0 if status_value == "archived" else 1)
                if status_value == "archived":
                    columns.append("index_status = ?")
                    params.append("excluded")
                    columns.append("index_error = ?")
                    params.append("")
                    columns.append("indexed_at = ?")
                    params.append("")
        if "index_status" in updates:
            index_status = normalize_index_status(
                updates["index_status"],
                is_active=updates.get("is_active", 1),
                workflow_status=updates.get("status", ""),
            )
            if index_status not in INDEX_STATUS_VALUES:
                raise ValueError(f"Unsupported photo index_status: {index_status}")
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
        params.append(photo_id)
        with self._connection() as conn:
            cursor = conn.execute(f"UPDATE photos SET {', '.join(columns)} WHERE photo_id = ?", params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_photo(self, photo_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM photos WHERE photo_id = ?", (photo_id,))
            conn.commit()
            return cursor.rowcount > 0
