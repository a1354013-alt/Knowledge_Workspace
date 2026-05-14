"""SQLite + vector DB persistence layer (legacy implementation).

This module is kept as the stable behavior reference while `app/db/schema.py`
and `app/db/migrations.py` are introduced. New code should import the public
facade: `from app.db import DocumentDatabase`.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import Any

from app.db import migrations, schema
from app.passwords import hash_password, verify_password_hash
from app.repositories.autotest_persistence_repository import AutoTestPersistenceRepositoryMixin
from app.repositories.document_repository import DocumentRepositoryMixin
from app.repositories.knowledge_repository import KnowledgeRepositoryMixin
from app.repositories.link_repository import LinkRepositoryMixin
from app.repositories.logbook_repository import LogbookRepositoryMixin
from app.repositories.photo_repository import PhotoRepositoryMixin
from app.repositories.prompt_repository import PromptRepositoryMixin
from app.repositories.repository_utils import (
    AUTOTEST_RUN_STATUS_VALUES,
    AUTOTEST_STATUS_VALUES,
    AUTOTEST_STEP_STATUS_VALUES,
    DOC_STATUS_VALUES,
    KNOWLEDGE_STATUS_VALUES,
    LINK_TYPE_VALUES,
    LOGBOOK_STATUS_VALUES,
    PHOTO_STATUS_VALUES,
    WORKFLOW_STATUS_VALUES,
    utc_now_iso,
)
from app.repositories.search_repository import SearchRepositoryMixin

logger = logging.getLogger("knowledge_workspace")

__all__ = [
    "AUTOTEST_RUN_STATUS_VALUES",
    "AUTOTEST_STATUS_VALUES",
    "AUTOTEST_STEP_STATUS_VALUES",
    "DOC_STATUS_VALUES",
    "DocumentDatabase",
    "KNOWLEDGE_STATUS_VALUES",
    "LINK_TYPE_VALUES",
    "LOGBOOK_STATUS_VALUES",
    "PHOTO_STATUS_VALUES",
    "WORKFLOW_STATUS_VALUES",
    "utc_now_iso",
]


class DocumentDatabase(
    DocumentRepositoryMixin,
    KnowledgeRepositoryMixin,
    LogbookRepositoryMixin,
    LinkRepositoryMixin,
    PromptRepositoryMixin,
    PhotoRepositoryMixin,
    AutoTestPersistenceRepositoryMixin,
    SearchRepositoryMixin,
):
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
            cursor.execute(schema.CREATE_KNOWLEDGE_REVISIONS_TABLE_SQL)
            cursor.execute(schema.CREATE_LOGBOOK_ENTRIES_TABLE_SQL)
            cursor.execute(schema.CREATE_PHOTOS_TABLE_SQL)
            cursor.execute(schema.CREATE_AUTOTEST_RUNS_TABLE_SQL)
            cursor.execute(schema.CREATE_AUTOTEST_STEPS_TABLE_SQL)
            cursor.execute(schema.CREATE_ITEM_LINKS_TABLE_SQL)
            cursor.execute(schema.CREATE_SAVED_PROMPTS_TABLE_SQL)
            self._migrate_documents_table(cursor)
            self._migrate_users_table(cursor)
            self._migrate_knowledge_entries_table(cursor)
            self._migrate_knowledge_revisions_table(cursor)
            self._migrate_logbook_entries_table(cursor)
            self._migrate_photos_table(cursor)
            self._migrate_saved_prompts_table(cursor)
            self._migrate_autotest_tables(cursor)
            self._migrate_item_links_table(cursor)
            self._ensure_query_indexes(cursor)
            self._seed_owner_user(cursor)
            conn.commit()

    def _migrate_item_links_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_item_links_table(cursor)

    def _ensure_query_indexes(self, cursor: sqlite3.Cursor) -> None:
        migrations.ensure_query_indexes(cursor)

    def _migrate_users_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_users_table(cursor)

    def _migrate_documents_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_documents_table(cursor)

    def _migrate_autotest_tables(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_autotest_tables(cursor)

    def _migrate_knowledge_entries_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_knowledge_entries_table(cursor)

    def _migrate_knowledge_revisions_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_knowledge_revisions_table(cursor)

    def _migrate_logbook_entries_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_logbook_entries_table(cursor)

    def _migrate_photos_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_photos_table(cursor)

    def _migrate_saved_prompts_table(self, cursor: sqlite3.Cursor) -> None:
        migrations.migrate_saved_prompts_table(cursor)

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
