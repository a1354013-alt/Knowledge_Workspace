"""SQLite + vector DB persistence layer (legacy implementation).

This module is kept as the stable behavior reference while `app/db/schema.py`
and `app/db/migrations.py` are introduced. New code should import the public
facade: `from app.db import DocumentDatabase`.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.db import migrations, schema
from app.passwords import hash_password, verify_password_hash

logger = logging.getLogger("knowledge_workspace")

LINK_TYPE_VALUES = schema.LINK_TYPE_VALUES
WORKFLOW_STATUS_VALUES = schema.WORKFLOW_STATUS_VALUES
KNOWLEDGE_STATUS_VALUES = schema.KNOWLEDGE_STATUS_VALUES
LOGBOOK_STATUS_VALUES = schema.LOGBOOK_STATUS_VALUES
DOC_STATUS_VALUES = schema.DOC_STATUS_VALUES
PHOTO_STATUS_VALUES = schema.PHOTO_STATUS_VALUES
AUTOTEST_RUN_STATUS_VALUES = schema.AUTOTEST_RUN_STATUS_VALUES
AUTOTEST_STEP_STATUS_VALUES = schema.AUTOTEST_STEP_STATUS_VALUES
AUTOTEST_STATUS_VALUES = schema.AUTOTEST_STATUS_VALUES


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentDatabase:
    def __init__(self, db_path: str = "documents.db"):
        self.db_path = db_path
        self._memory_conn: sqlite3.Connection | None = None
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        if self.db_path == ':memory:':
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(':memory:', check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self) -> sqlite3.Connection:
        conn = self._connect()
        try:
            yield conn
        finally:
            if self.db_path != ':memory:':
                conn.close()

    def init_db(self) -> None:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(schema.CREATE_USERS_TABLE_SQL)
            cursor.execute(schema.CREATE_DOCUMENTS_TABLE_SQL)
            cursor.execute(schema.CREATE_KNOWLEDGE_ENTRIES_TABLE_SQL)
            cursor.execute(schema.CREATE_LOGBOOK_ENTRIES_TABLE_SQL)
            cursor.execute(schema.CREATE_PHOTOS_TABLE_SQL)
            cursor.execute(schema.CREATE_AUTOTEST_RUNS_TABLE_SQL)
            cursor.execute(schema.CREATE_AUTOTEST_STEPS_TABLE_SQL)
            cursor.execute(schema.CREATE_ITEM_LINKS_TABLE_SQL)
            cursor.execute(schema.CREATE_SAVED_PROMPTS_TABLE_SQL)
            cursor.execute(schema.CREATE_KNOWLEDGE_REVISIONS_TABLE_SQL)
            self._migrate_documents_table(cursor)
            self._migrate_users_table(cursor)
            self._migrate_knowledge_entries_table(cursor)
            self._migrate_logbook_entries_table(cursor)
            self._migrate_photos_table(cursor)
            self._migrate_saved_prompts_table(cursor)
            self._migrate_autotest_tables(cursor)
            self._migrate_knowledge_revisions_table(cursor)
            self._migrate_item_links_table(cursor)
            self._seed_owner_user(cursor)
            conn.commit()

    def _migrate_item_links_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_item_links_table(cursor)

    def _migrate_users_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_users_table(cursor)

    def _migrate_documents_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_documents_table(cursor)

    def _migrate_autotest_tables(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_autotest_tables(cursor)

    def _migrate_knowledge_entries_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_knowledge_entries_table(cursor)

    def _migrate_logbook_entries_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_logbook_entries_table(cursor)

    def _migrate_photos_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_photos_table(cursor)

    def _migrate_saved_prompts_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_saved_prompts_table(cursor)

    def _migrate_knowledge_revisions_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_knowledge_revisions_table(cursor)

    def _seed_owner_user(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] > 0:
            return

        default_password = os.getenv("DEFAULT_OWNER_PASSWORD")
        if not default_password:
            raise RuntimeError(
                "DEFAULT_OWNER_PASSWORD must be set to seed the initial 'owner' account "
                "(or create users in the database before starting the app)."
            )
        now = utc_now_iso()
        password_hash = hash_password(default_password)
        cursor.execute(
            """
            INSERT INTO users (user_id, password_hash, display_name, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("owner", password_hash, "Owner", "owner", 1, now, now),
        )
        logger.warning("Seeded initial owner account 'owner'. Change DEFAULT_OWNER_PASSWORD for production.")

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def verify_password(self, user_id: str, password: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        return verify_password_hash(password, user["password_hash"])

    def list_users(self) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT user_id, display_name, role, is_active, created_at, updated_at
                FROM users
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def add_user(self, user_id: str, password: str, display_name: str, role: str, is_active: int = 1) -> bool:
        now = utc_now_iso()
        password_hash = hash_password(password)
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO users (user_id, password_hash, display_name, role, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, password_hash, display_name, role, is_active, now, now),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_user(self, user_id: str, **updates: Any) -> bool:
        columns: list[str] = []
        params: list[Any] = []

        if "display_name" in updates:
            columns.append("display_name = ?")
            params.append(updates["display_name"])
        if "role" in updates:
            columns.append("role = ?")
            params.append(updates["role"])
        if "is_active" in updates:
            columns.append("is_active = ?")
            params.append(updates["is_active"])
        if "password" in updates:
            columns.append("password_hash = ?")
            params.append(hash_password(updates["password"]))
        if not columns:
            return False

        columns.append("updated_at = ?")
        params.append(utc_now_iso())
        params.append(user_id)

        with self._connection() as conn:
            cursor = conn.execute(
                f"UPDATE users SET {', '.join(columns)} WHERE user_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0

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
    ) -> bool:
        if status not in DOC_STATUS_VALUES and status not in WORKFLOW_STATUS_VALUES:
            raise ValueError(f"Unsupported document status: {status}")
        now = utc_now_iso()
        is_active = 0 if status == "archived" else 1
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO documents
                    (doc_id, filename, saved_filename, allowed_roles, category, tags, status, uploaded_by, uploaded_at, file_size, approved, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
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
    ) -> bool:
        if status not in KNOWLEDGE_STATUS_VALUES:
            raise ValueError(f"Unsupported knowledge status: {status}")
        now = utc_now_iso()
        is_active = 0 if status == "archived" else 1
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO knowledge_entries
                    (entry_id, title, status, problem, root_cause, solution, tags, notes, source_type, source_ref, created_by, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        knowledge_id: str,
        changed_by: str,
        change_note: str = "",
        version_number: int | None = None,
    ) -> str | None:
        entry = self.get_knowledge_entry(knowledge_id)
        if not entry:
            return None

        if version_number is None:
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT MAX(version_number) FROM knowledge_revisions WHERE knowledge_id = ?", (knowledge_id,)
                ).fetchone()
                current_max = row[0] if row and row[0] is not None else 0
                version_number = current_max + 1

        revision_id = str(uuid.uuid4())
        now = utc_now_iso()
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO knowledge_revisions
                    (revision_id, knowledge_id, version_number, title, status, problem, root_cause, solution, tags, notes, source_type, source_ref, changed_by, change_note, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision_id,
                        knowledge_id,
                        version_number,
                        entry.get("title", ""),
                        entry.get("status", ""),
                        entry.get("problem", ""),
                        entry.get("root_cause", ""),
                        entry.get("solution", ""),
                        entry.get("tags", ""),
                        entry.get("notes", ""),
                        entry.get("source_type", ""),
                        entry.get("source_ref", ""),
                        changed_by,
                        change_note,
                        now,
                    ),
                )
                conn.commit()
            return revision_id
        except sqlite3.Error as e:
            logger.error(f"Failed to add knowledge revision: {e}")
            return None

    def list_knowledge_revisions(self, knowledge_id: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM knowledge_revisions WHERE knowledge_id = ? ORDER BY version_number DESC",
                (knowledge_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_knowledge_revision(self, revision_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM knowledge_revisions WHERE revision_id = ?", (revision_id,)).fetchone()
        return dict(row) if row else None

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
        status: str = "reviewed",
    ) -> bool:
        if status not in PHOTO_STATUS_VALUES and status not in WORKFLOW_STATUS_VALUES:
            raise ValueError(f"Unsupported photo status: {status}")
        now = utc_now_iso()
        is_active = 0 if status == "archived" else 1
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO photos
                    (photo_id, filename, saved_filename, tags, description, ocr_text, status, uploaded_by, is_active, file_size, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        photo_id,
                        filename,
                        saved_filename,
                        tags,
                        description,
                        ocr_text,
                        status,
                        uploaded_by,
                        is_active,
                        int(file_size),
                        now,
                        now,
                    ),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_photos(self, limit: int = 200, user_id: str | None = None, include_archived: bool = False) -> list[dict[str, Any]]:
        with self._connection() as conn:
            where: list[str] = []
            params: list[Any] = []
            if user_id:
                where.append("uploaded_by = ?")
                params.append(user_id)
            if not include_archived:
                where.append("is_active = 1")
            params.append(int(limit))
            sql = "SELECT * FROM photos"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY created_at DESC LIMIT ?"
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def get_photo(self, photo_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM photos WHERE photo_id = ?", (photo_id,)).fetchone()
        return dict(row) if row else None

    def update_photo(self, photo_id: str, **updates: Any) -> bool:
        columns: list[str] = []
        params: list[Any] = []
        if "tags" in updates:
            columns.append("tags = ?")
            params.append(str(updates["tags"] or ""))
        if "description" in updates:
            columns.append("description = ?")
            params.append(str(updates["description"] or ""))
        if "status" in updates:
            status_value = str(updates["status"] or "").strip()
            if status_value and status_value not in PHOTO_STATUS_VALUES and status_value not in WORKFLOW_STATUS_VALUES:
                raise ValueError(f"Unsupported photo status: {status_value}")
            if status_value:
                columns.append("status = ?")
                params.append(status_value)
                columns.append("is_active = ?")
                params.append(0 if status_value == "archived" else 1)
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
                    (run_id, source_type, source_ref, execution_mode, project_type_detected, working_directory, project_name, project_type, status, summary, suggestion, prompt_output, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        int(success),
                        int(exit_code),
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
                    params.append(int(updates[key]))
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
                (run_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def search_items(
        self,
        *,
        user_id: str,
        keyword: str = "",
        item_types: list[str] | None = None,
        status: str = "",
        tag: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        keyword = str(keyword or "").strip().lower()
        status = str(status or "").strip()
        tag = str(tag or "").strip()
        date_from = str(date_from or "").strip()
        date_to = str(date_to or "").strip()
        limit = max(1, min(int(limit), 500))

        supported = {"knowledge", "logbook", "document", "photo", "prompt", "autotest_run"}
        selected = [t for t in (item_types or []) if t in supported]
        if not selected:
            selected = sorted(supported)

        clauses_common: list[str] = []
        params_common: list[Any] = []

        if keyword:
            clauses_common.append("haystack LIKE ?")
            params_common.append(f"%{keyword}%")
        if status:
            clauses_common.append("status = ?")
            params_common.append(status)
        if tag:
            clauses_common.append("tags LIKE ?")
            params_common.append(f"%{tag}%")
        if date_from:
            clauses_common.append("updated_at >= ?")
            params_common.append(date_from)
        if date_to:
            clauses_common.append("updated_at <= ?")
            params_common.append(date_to)

        def build_query(table: str, id_col: str, title_col: str, status_col: str, tags_expr: str, haystack_expr: str, created_col: str, updated_col: str, extra_where: str, extra_params: list[Any], item_type: str, source_type_expr: str, source_ref_expr: str) -> tuple[str, list[Any]]:
            where_parts = [extra_where] if extra_where else []
            if clauses_common:
                where_parts.append(" AND ".join(clauses_common))
            where_sql = " AND ".join([part for part in where_parts if part])
            if where_sql:
                where_sql = "WHERE " + where_sql
            sql = f"""
            SELECT
              '{item_type}' AS item_type,
              {id_col} AS item_id,
              {title_col} AS title,
              {status_col} AS status,
              {created_col} AS created_at,
              {updated_col} AS updated_at,
              {source_type_expr} AS source_type,
              {source_ref_expr} AS source_ref,
              {tags_expr} AS tags,
              {haystack_expr} AS haystack
            FROM {table}
            {where_sql}
            """
            return sql, [*extra_params, *params_common]

        queries: list[tuple[str, list[Any]]] = []

        if "knowledge" in selected:
            sql, params = build_query(
                "knowledge_entries",
                "entry_id",
                "COALESCE(NULLIF(title,''), substr(problem,1,80))",
                "status",
                "tags",
                "lower(title || ' ' || problem || ' ' || solution || ' ' || tags || ' ' || source_type || ' ' || source_ref)",
                "created_at",
                "updated_at",
                "created_by = ? AND is_active = 1",
                [user_id],
                "knowledge",
                "source_type",
                "source_ref",
            )
            queries.append((sql, params))

        if "logbook" in selected:
            sql, params = build_query(
                "logbook_entries",
                "entry_id",
                "COALESCE(NULLIF(title,''), substr(problem,1,80))",
                "status",
                "tags",
                "lower(title || ' ' || problem || ' ' || solution || ' ' || tags || ' ' || source_type || ' ' || source_ref)",
                "created_at",
                "updated_at",
                "created_by = ? AND is_active = 1",
                [user_id],
                "logbook",
                "source_type",
                "source_ref",
            )
            queries.append((sql, params))

        if "document" in selected:
            sql, params = build_query(
                "documents",
                "doc_id",
                "filename",
                "status",
                "tags",
                "lower(filename || ' ' || category || ' ' || tags)",
                "uploaded_at",
                "updated_at",
                "uploaded_by = ? AND is_active = 1",
                [user_id],
                "document",
                "''",
                "''",
            )
            queries.append((sql, params))

        if "photo" in selected:
            sql, params = build_query(
                "photos",
                "photo_id",
                "filename",
                "status",
                "tags",
                "lower(filename || ' ' || tags || ' ' || description || ' ' || ocr_text)",
                "created_at",
                "updated_at",
                "uploaded_by = ? AND is_active = 1",
                [user_id],
                "photo",
                "''",
                "''",
            )
            queries.append((sql, params))

        if "prompt" in selected:
            sql, params = build_query(
                "saved_prompts",
                "prompt_id",
                "title",
                "CASE WHEN is_active = 1 THEN 'active' ELSE 'archived' END",
                "tags",
                "lower(title || ' ' || tags || ' ' || content)",
                "created_at",
                "updated_at",
                "created_by = ? AND is_active = 1",
                [user_id],
                "prompt",
                "''",
                "''",
            )
            queries.append((sql, params))

        if "autotest_run" in selected:
            sql, params = build_query(
                "autotest_runs",
                "run_id",
                "COALESCE(NULLIF(project_name,''), source_ref)",
                "status",
                "''",
                "lower(project_name || ' ' || source_ref || ' ' || summary || ' ' || suggestion)",
                "created_at",
                "created_at",
                "created_by = ?",
                [user_id],
                "autotest_run",
                "source_type",
                "source_ref",
            )
            queries.append((sql, params))

        union_sql = " UNION ALL ".join([q[0] for q in queries])
        sql = f"""
        SELECT item_type, item_id, title, status, created_at, updated_at, source_type, source_ref
        FROM (
          {union_sql}
        )
        ORDER BY updated_at DESC
        LIMIT ?
        """
        all_params: list[Any] = []
        for _q, params in queries:
            all_params.extend(params)
        all_params.append(limit)

        with self._connection() as conn:
            rows = conn.execute(sql, all_params).fetchall()
        return [dict(row) for row in rows]
