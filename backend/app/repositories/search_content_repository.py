from __future__ import annotations

from typing import Any


class SearchContentRepositoryMixin:
    def search_content_store_ready(self) -> bool:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type IN ('table', 'view')
                  AND name = 'item_search_content'
                """
            ).fetchone()
        return row is not None

    def search_content_fts_ready(self) -> bool:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'item_search_fts'
                """
            ).fetchone()
        return row is not None

    def upsert_search_content(
        self,
        *,
        item_id: str,
        item_type: str,
        owner_user_id: str,
        title: str,
        content: str,
        is_active: int,
        updated_at: str,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO item_search_content
                (item_id, item_type, owner_user_id, title, content, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                  item_type = excluded.item_type,
                  owner_user_id = excluded.owner_user_id,
                  title = excluded.title,
                  content = excluded.content,
                  is_active = excluded.is_active,
                  updated_at = excluded.updated_at
                """,
                (
                    item_id,
                    item_type,
                    owner_user_id,
                    title,
                    content,
                    int(is_active),
                    updated_at,
                ),
            )
            if self.search_content_fts_ready():
                conn.execute("DELETE FROM item_search_fts WHERE item_id = ?", (item_id,))
                conn.execute(
                    """
                    INSERT INTO item_search_fts
                    (item_id, item_type, owner_user_id, is_active, updated_at, title, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id,
                        item_type,
                        owner_user_id,
                        int(is_active),
                        updated_at,
                        title,
                        content,
                    ),
                )
            conn.commit()

    def delete_search_content(self, item_id: str) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM item_search_content WHERE item_id = ?", (item_id,))
            if self.search_content_fts_ready():
                conn.execute("DELETE FROM item_search_fts WHERE item_id = ?", (item_id,))
            conn.commit()

    def get_search_content(self, item_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM item_search_content WHERE item_id = ?", (item_id,)).fetchone()
        return dict(row) if row else None

    def search_search_content(
        self,
        *,
        user_id: str,
        query: str,
        limit: int = 5,
        item_types: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        normalized_query = str(query or "").strip()
        if not normalized_query:
            return []

        type_filter_sql = ""
        type_params: list[Any] = []
        normalized_types = tuple(sorted({str(item_type or "").strip() for item_type in item_types if str(item_type or "").strip()}))
        if normalized_types:
            placeholders = ", ".join("?" for _ in normalized_types)
            type_filter_sql = f" AND item_type IN ({placeholders})"
            type_params.extend(normalized_types)

        limit_value = max(1, min(int(limit), 50))
        tokens = [token.strip() for token in normalized_query.replace("\n", " ").split() if token.strip()]
        if self.search_content_fts_ready() and tokens:
            match_query = " OR ".join(f'"{token.replace(chr(34), " ")}"' for token in tokens)
            sql = f"""
                SELECT item_id, item_type, title, content, updated_at
                FROM item_search_fts
                WHERE owner_user_id = ?
                  AND is_active = 1
                  {type_filter_sql}
                  AND item_search_fts MATCH ?
                ORDER BY bm25(item_search_fts), updated_at DESC
                LIMIT ?
            """
            params: list[Any] = [user_id, *type_params, match_query, limit_value]
        else:
            sql = f"""
                SELECT item_id, item_type, title, content, updated_at
                FROM item_search_content
                WHERE owner_user_id = ?
                  AND is_active = 1
                  {type_filter_sql}
                  AND lower(title || ' ' || content) LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """
            params = [user_id, *type_params, f"%{normalized_query.lower()}%", limit_value]

        with self._connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def list_search_content(self, *, user_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM item_search_content"
        params: tuple[Any, ...] = ()
        if user_id is not None:
            sql += " WHERE owner_user_id = ?"
            params = (user_id,)
        sql += " ORDER BY updated_at DESC"
        with self._connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
