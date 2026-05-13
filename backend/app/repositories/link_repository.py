# ruff: noqa: E501
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from app.repositories.repository_utils import (
    LINK_TYPE_VALUES,
    utc_now_iso,
)


class LinkRepositoryMixin:
    def add_link(self, from_item_id: str, to_item_id: str, link_type: str = "references") -> bool:
        now = utc_now_iso()
        link_id = uuid.uuid4().hex
        normalized_type = str(link_type or "").strip() or "references"
        if normalized_type not in LINK_TYPE_VALUES:
            raise ValueError(f"Unsupported link_type: {normalized_type}")
        with self._connection() as conn:
            exists = conn.execute(
                """
                SELECT 1 FROM item_links
                WHERE from_item_id = ? AND to_item_id = ? AND link_type = ?
                LIMIT 1
                """,
                (str(from_item_id), str(to_item_id), normalized_type),
            ).fetchone()
            if exists:
                return False
            try:
                conn.execute(
                    """
                    INSERT INTO item_links (link_id, from_item_id, to_item_id, link_type, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (link_id, from_item_id, to_item_id, normalized_type, now),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def delete_links(self, *, from_item_id: str | None = None, to_item_id: str | None = None, link_type: str | None = None) -> int:
        where: list[str] = []
        params: list[Any] = []
        if from_item_id is not None:
            where.append("from_item_id = ?")
            params.append(str(from_item_id))
        if to_item_id is not None:
            where.append("to_item_id = ?")
            params.append(str(to_item_id))
        if link_type is not None:
            where.append("link_type = ?")
            params.append(str(link_type))
        if not where:
            raise ValueError("delete_links requires at least one filter.")
        sql = "DELETE FROM item_links WHERE " + " AND ".join(where)
        with self._connection() as conn:
            cursor = conn.execute(sql, tuple(params))
            conn.commit()
            return int(cursor.rowcount or 0)

    def set_reference_links(self, from_item_id: str, related_item_ids: list[str]) -> None:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in related_item_ids:
            value = str(raw or "").strip()
            if not value:
                continue
            if value in seen:
                continue
            seen.add(value)
            cleaned.append(value)

        self.delete_links(from_item_id=str(from_item_id), link_type="references")
        for target in cleaned:
            self.add_link(str(from_item_id), str(target), link_type="references")

    def list_links(self, item_id: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT link_id, from_item_id, to_item_id, link_type, created_at
                FROM item_links
                WHERE from_item_id = ? OR to_item_id = ?
                ORDER BY created_at DESC
                """,
                (item_id, item_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_related_item_ids(self, item_id: str) -> list[str]:
        links = self.list_links(item_id)
        related: list[str] = []
        for link in links:
            if link.get("from_item_id") == item_id and link.get("to_item_id"):
                related.append(str(link["to_item_id"]))
            elif link.get("to_item_id") == item_id and link.get("from_item_id"):
                related.append(str(link["from_item_id"]))
        # de-dupe while keeping order
        seen: set[str] = set()
        output: list[str] = []
        for value in related:
            if value in seen:
                continue
            seen.add(value)
            output.append(value)
        return output
