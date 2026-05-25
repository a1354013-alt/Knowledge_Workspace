from __future__ import annotations

from typing import Any


class IndexRepairRepositoryMixin:
    def queue_index_repair(
        self,
        *,
        item_id: str,
        item_type: str,
        action: str,
        owner_user_id: str,
        last_error: str,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO index_repair_queue
                (item_id, item_type, action, owner_user_id, last_error, attempts, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(item_id, action) DO UPDATE SET
                  item_type = excluded.item_type,
                  owner_user_id = excluded.owner_user_id,
                  last_error = excluded.last_error,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (
                    item_id,
                    item_type,
                    action,
                    owner_user_id,
                    str(last_error or ""),
                ),
            )
            conn.commit()

    def resolve_index_repair(self, *, item_id: str, action: str | None = None) -> None:
        with self._connection() as conn:
            if action:
                conn.execute("DELETE FROM index_repair_queue WHERE item_id = ? AND action = ?", (item_id, action))
            else:
                conn.execute("DELETE FROM index_repair_queue WHERE item_id = ?", (item_id,))
            conn.commit()

    def record_index_repair_attempt(self, *, item_id: str, action: str, last_error: str) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE index_repair_queue
                SET attempts = attempts + 1,
                    last_error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE item_id = ? AND action = ?
                """,
                (str(last_error or ""), item_id, action),
            )
            conn.commit()

    def list_index_repairs(self, *, owner_user_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM index_repair_queue"
        params: tuple[Any, ...] = ()
        if owner_user_id is not None:
            sql += " WHERE owner_user_id = ?"
            params = (owner_user_id,)
        sql += " ORDER BY updated_at ASC"
        with self._connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
