from __future__ import annotations

"""SQLite + vector DB persistence layer."""

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:  # pragma: no cover - optional runtime dependency
    chromadb = None
    embedding_functions = None


logger = logging.getLogger("knowledge_workspace")

_EMBEDDING_FUNCTION = None
_COLLECTION = None
_KB_COLLECTION = None
_PASSWORD_ITERATIONS = 120000
LINK_TYPE_VALUES = ("references", "derived_from", "produced")
WORKFLOW_STATUS_VALUES = ("draft", "reviewed", "verified", "archived")
KNOWLEDGE_STATUS_VALUES = WORKFLOW_STATUS_VALUES
LOGBOOK_STATUS_VALUES = WORKFLOW_STATUS_VALUES
DOC_STATUS_VALUES = WORKFLOW_STATUS_VALUES
PHOTO_STATUS_VALUES = WORKFLOW_STATUS_VALUES
AUTOTEST_STATUS_VALUES = ("queued", "running", "passed", "failed")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), _PASSWORD_ITERATIONS)
    return f'{salt}${derived.hex()}'


def verify_password_hash(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split('$', 1)
    except ValueError:
        return False
    computed = hash_password(password, salt).split('$', 1)[1]
    return hmac.compare_digest(computed, expected)


def get_embedding_function():
    global _EMBEDDING_FUNCTION
    if _EMBEDDING_FUNCTION is not None:
        return _EMBEDDING_FUNCTION
    if embedding_functions is None:
        raise RuntimeError('chromadb is not installed.')

    _EMBEDDING_FUNCTION = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    logger.info("Using sentence-transformers embeddings.")
    return _EMBEDDING_FUNCTION


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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'owner',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    saved_filename TEXT NOT NULL,
                    allowed_roles TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'reviewed',
                    uploaded_by TEXT,
                    uploaded_at TEXT NOT NULL,
                    file_size INTEGER NOT NULL DEFAULT 0,
                    approved INTEGER NOT NULL DEFAULT 1,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    entry_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'draft',
                    problem TEXT NOT NULL,
                    root_cause TEXT NOT NULL DEFAULT '',
                    solution TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL DEFAULT 'manual',
                    source_ref TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS logbook_entries (
                    entry_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    run_id TEXT NOT NULL DEFAULT '',
                    problem TEXT NOT NULL,
                    root_cause TEXT NOT NULL DEFAULT '',
                    solution TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL DEFAULT 'manual',
                    source_ref TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS photos (
                    photo_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    saved_filename TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    ocr_text TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'reviewed',
                    uploaded_by TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    file_size INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS autotest_runs (
                    run_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    execution_mode TEXT NOT NULL DEFAULT 'real',
                    project_type_detected TEXT NOT NULL DEFAULT '',
                    working_directory TEXT NOT NULL DEFAULT '',
                    project_name TEXT NOT NULL DEFAULT '',
                    project_type TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'unknown',
                    summary TEXT NOT NULL DEFAULT '',
                    suggestion TEXT NOT NULL DEFAULT '',
                    prompt_output TEXT NOT NULL DEFAULT '',
                    problem_entry_id TEXT NOT NULL DEFAULT '',
                    solution_entry_id TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS autotest_steps (
                    step_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    command TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL DEFAULT '',
                    output TEXT NOT NULL DEFAULT '',
                    success INTEGER NOT NULL DEFAULT 0,
                    exit_code INTEGER NOT NULL DEFAULT 0,
                    stdout_summary TEXT NOT NULL DEFAULT '',
                    stderr_summary TEXT NOT NULL DEFAULT '',
                    error_type TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES autotest_runs(run_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS item_links (
                    link_id TEXT PRIMARY KEY,
                    from_item_id TEXT NOT NULL,
                    to_item_id TEXT NOT NULL,
                    link_type TEXT NOT NULL DEFAULT 'references',
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_prompts (
                    prompt_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._migrate_documents_table(cursor)
            self._migrate_users_table(cursor)
            self._migrate_knowledge_entries_table(cursor)
            self._migrate_logbook_entries_table(cursor)
            self._migrate_photos_table(cursor)
            self._migrate_saved_prompts_table(cursor)
            self._migrate_autotest_tables(cursor)
            self._migrate_item_links_table(cursor)
            self._seed_owner_user(cursor)
            conn.commit()

    def _migrate_item_links_table(self, cursor: sqlite3.Cursor) -> None:
        # Older versions used a generic 'related' link_type; normalize it to 'references'.
        cursor.execute(
            """
            UPDATE item_links
            SET link_type = 'references'
            WHERE link_type IN ('related', 'reference', 'ref', '')
            """
        )

    def _migrate_users_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("UPDATE users SET role = 'owner' WHERE role != 'owner'")

    def _migrate_documents_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA table_info(documents)")
        columns = {row[1] for row in cursor.fetchall()}
        migrations = {
            "uploaded_by": "ALTER TABLE documents ADD COLUMN uploaded_by TEXT",
            "approved": "ALTER TABLE documents ADD COLUMN approved INTEGER NOT NULL DEFAULT 0",
            "is_active": "ALTER TABLE documents ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
            "updated_at": "ALTER TABLE documents ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
            "file_size": "ALTER TABLE documents ADD COLUMN file_size INTEGER NOT NULL DEFAULT 0",
            "category": "ALTER TABLE documents ADD COLUMN category TEXT NOT NULL DEFAULT ''",
            "tags": "ALTER TABLE documents ADD COLUMN tags TEXT NOT NULL DEFAULT ''",
            "status": "ALTER TABLE documents ADD COLUMN status TEXT NOT NULL DEFAULT 'reviewed'",
        }
        for column, sql in migrations.items():
            if column not in columns:
                cursor.execute(sql)
        cursor.execute("UPDATE documents SET updated_at = uploaded_at WHERE updated_at = ''")
        cursor.execute("UPDATE documents SET allowed_roles = 'owner' WHERE allowed_roles = '' OR allowed_roles IS NULL")
        cursor.execute("UPDATE documents SET approved = 1 WHERE approved = 0")
        cursor.execute("UPDATE documents SET status = 'archived' WHERE is_active = 0 AND status != 'archived'")
        cursor.execute("UPDATE documents SET status = 'reviewed' WHERE is_active = 1 AND status = ''")
        cursor.execute("UPDATE documents SET uploaded_by = 'owner' WHERE uploaded_by IS NULL OR uploaded_by = ''")

    def _migrate_autotest_tables(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA table_info(autotest_runs)")
        run_columns = {row[1] for row in cursor.fetchall()}
        if "execution_mode" not in run_columns:
            cursor.execute("ALTER TABLE autotest_runs ADD COLUMN execution_mode TEXT NOT NULL DEFAULT 'real'")
        if "project_type_detected" not in run_columns:
            cursor.execute("ALTER TABLE autotest_runs ADD COLUMN project_type_detected TEXT NOT NULL DEFAULT ''")
        if "working_directory" not in run_columns:
            cursor.execute("ALTER TABLE autotest_runs ADD COLUMN working_directory TEXT NOT NULL DEFAULT ''")
        if "project_name" not in run_columns:
            cursor.execute("ALTER TABLE autotest_runs ADD COLUMN project_name TEXT NOT NULL DEFAULT ''")
        cursor.execute("UPDATE autotest_runs SET project_name = source_ref WHERE project_name = ''")
        if "problem_entry_id" not in run_columns:
            cursor.execute("ALTER TABLE autotest_runs ADD COLUMN problem_entry_id TEXT NOT NULL DEFAULT ''")
        if "solution_entry_id" not in run_columns:
            cursor.execute("ALTER TABLE autotest_runs ADD COLUMN solution_entry_id TEXT NOT NULL DEFAULT ''")
        if "created_by" not in run_columns:
            cursor.execute("ALTER TABLE autotest_runs ADD COLUMN created_by TEXT NOT NULL DEFAULT ''")
        cursor.execute("UPDATE autotest_runs SET created_by = 'owner' WHERE created_by = ''")

        cursor.execute("PRAGMA table_info(autotest_steps)")
        step_columns = {row[1] for row in cursor.fetchall()}
        migrations = {
            "started_at": "ALTER TABLE autotest_steps ADD COLUMN started_at TEXT NOT NULL DEFAULT ''",
            "finished_at": "ALTER TABLE autotest_steps ADD COLUMN finished_at TEXT NOT NULL DEFAULT ''",
            "output": "ALTER TABLE autotest_steps ADD COLUMN output TEXT NOT NULL DEFAULT ''",
            "success": "ALTER TABLE autotest_steps ADD COLUMN success INTEGER NOT NULL DEFAULT 0",
        }
        for column, sql in migrations.items():
            if column not in step_columns:
                cursor.execute(sql)
        cursor.execute("UPDATE autotest_steps SET success = 1 WHERE status = 'passed' AND success = 0")

    def _migrate_knowledge_entries_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA table_info(knowledge_entries)")
        columns = {row[1] for row in cursor.fetchall()}
        migrations = {
            "status": "ALTER TABLE knowledge_entries ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'",
            "source_type": "ALTER TABLE knowledge_entries ADD COLUMN source_type TEXT NOT NULL DEFAULT 'manual'",
            "source_ref": "ALTER TABLE knowledge_entries ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",
            "created_by": "ALTER TABLE knowledge_entries ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
            "is_active": "ALTER TABLE knowledge_entries ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        }
        for column, sql in migrations.items():
            if column not in columns:
                cursor.execute(sql)

        cursor.execute("UPDATE knowledge_entries SET status = 'draft' WHERE status = ''")
        cursor.execute("UPDATE knowledge_entries SET status = 'reviewed' WHERE status = 'published'")
        cursor.execute("UPDATE knowledge_entries SET is_active = 0 WHERE status = 'archived'")
        cursor.execute("UPDATE knowledge_entries SET is_active = 1 WHERE status != 'archived'")
        cursor.execute("UPDATE knowledge_entries SET created_by = 'owner' WHERE created_by = ''")

    def _migrate_logbook_entries_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA table_info(logbook_entries)")
        columns = {row[1] for row in cursor.fetchall()}
        migrations = {
            "status": "ALTER TABLE logbook_entries ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'",
            "run_id": "ALTER TABLE logbook_entries ADD COLUMN run_id TEXT NOT NULL DEFAULT ''",
            "source_ref": "ALTER TABLE logbook_entries ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",
            "created_by": "ALTER TABLE logbook_entries ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
            "is_active": "ALTER TABLE logbook_entries ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        }
        for column, sql in migrations.items():
            if column not in columns:
                cursor.execute(sql)
        cursor.execute("UPDATE logbook_entries SET status = 'draft' WHERE status = '' OR status = 'open'")
        cursor.execute("UPDATE logbook_entries SET status = 'archived' WHERE status = 'obsolete'")
        cursor.execute("UPDATE logbook_entries SET is_active = 0 WHERE status = 'archived'")
        cursor.execute("UPDATE logbook_entries SET is_active = 1 WHERE status != 'archived'")
        cursor.execute("UPDATE logbook_entries SET created_by = 'owner' WHERE created_by = ''")

    def _migrate_photos_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA table_info(photos)")
        columns = {row[1] for row in cursor.fetchall()}
        migrations = {
            "status": "ALTER TABLE photos ADD COLUMN status TEXT NOT NULL DEFAULT 'reviewed'",
            "uploaded_by": "ALTER TABLE photos ADD COLUMN uploaded_by TEXT",
            "is_active": "ALTER TABLE photos ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        }
        for column, sql in migrations.items():
            if column not in columns:
                cursor.execute(sql)
        cursor.execute("UPDATE photos SET uploaded_by = 'owner' WHERE uploaded_by IS NULL OR uploaded_by = ''")

    def _migrate_saved_prompts_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA table_info(saved_prompts)")
        columns = {row[1] for row in cursor.fetchall()}
        migrations = {
            "tags": "ALTER TABLE saved_prompts ADD COLUMN tags TEXT NOT NULL DEFAULT ''",
            "created_by": "ALTER TABLE saved_prompts ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
            "is_active": "ALTER TABLE saved_prompts ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
            "updated_at": "ALTER TABLE saved_prompts ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
        }
        for column, sql in migrations.items():
            if column not in columns:
                cursor.execute(sql)
        cursor.execute("UPDATE saved_prompts SET created_by = 'owner' WHERE created_by = ''")

    def _seed_owner_user(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] > 0:
            return

        default_password = os.getenv("DEFAULT_OWNER_PASSWORD") or os.getenv("DEFAULT_ADMIN_PASSWORD")
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
        if status not in AUTOTEST_STATUS_VALUES and status not in {"passed", "failed"}:
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
        if "status" in updates and str(updates["status"]) not in AUTOTEST_STATUS_VALUES and str(updates["status"]) not in {"passed", "failed"}:
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


def get_collection():
    global _COLLECTION
    if _COLLECTION is not None:
        return _COLLECTION
    if chromadb is None:
        raise RuntimeError('chromadb is not installed.')

    settings = get_settings()
    client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_PATH))
    _COLLECTION = client.get_or_create_collection(
        name="documents",
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )
    return _COLLECTION


def get_kb_collection():
    global _KB_COLLECTION
    if _KB_COLLECTION is not None:
        return _KB_COLLECTION
    if chromadb is None:
        raise RuntimeError('chromadb is not installed.')

    settings = get_settings()
    client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_PATH))
    _KB_COLLECTION = client.get_or_create_collection(
        name="knowledge",
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )
    return _KB_COLLECTION


def add_to_vector_db(
    doc_id: str,
    chunks: list[str],
    metadata_list: list[dict[str, Any]],
) -> bool:
    if chromadb is None:
        logger.warning('chromadb not installed; skipping vector indexing for %s.', doc_id)
        return True
    try:
        collection = get_collection()
        ids = [f"{doc_id}_{index}" for index in range(len(chunks))]

        collection.add(ids=ids, documents=chunks, metadatas=metadata_list)
        return True
    except Exception as exc:
        logger.error("Failed to add document %s to vector DB: %s", doc_id, exc)
        return False


def query_vector_db(question: str, user_id: str, n_results: int = 5) -> list[tuple[str, str, dict[str, Any]]]:
    if chromadb is None:
        logger.warning('chromadb not installed; QA search is disabled.')
        return []
    try:
        collection = get_collection()
        where_filter: dict[str, Any] = {"$and": [{"is_active": 1}, {"owner_user_id": user_id}]}

        results = collection.query(query_texts=[question], n_results=n_results, where=where_filter)
        output: list[tuple[str, str, dict[str, Any]]] = []
        for index, document in enumerate(results.get("documents", [[]])[0]):
            metadata = results.get("metadatas", [[]])[0][index]
            output.append((metadata.get("doc_id", ""), document, metadata))
        return output
    except Exception as exc:
        logger.error("Failed to query vector DB: %s", exc)
        return []


def add_to_kb_vector_db(
    item_id: str,
    chunks: list[str],
    metadata_list: list[dict[str, Any]],
) -> bool:
    if chromadb is None:
        logger.warning('chromadb not installed; skipping kb vector indexing for %s.', item_id)
        return True
    try:
        collection = get_kb_collection()
        ids = [f"{item_id}_{index}" for index in range(len(chunks))]

        collection.add(ids=ids, documents=chunks, metadatas=metadata_list)
        return True
    except Exception as exc:
        logger.error("Failed to add KB item %s to vector DB: %s", item_id, exc)
        return False


def query_kb_vector_db(question: str, user_id: str, n_results: int = 5) -> list[tuple[str, str, dict[str, Any]]]:
    if chromadb is None:
        logger.warning('chromadb not installed; KB search is disabled.')
        return []
    try:
        collection = get_kb_collection()
        where_filter: dict[str, Any] = {"$and": [{"is_active": 1}, {"owner_user_id": user_id}]}

        results = collection.query(query_texts=[question], n_results=n_results, where=where_filter)
        output: list[tuple[str, str, dict[str, Any]]] = []
        for index, document in enumerate(results.get("documents", [[]])[0]):
            metadata = results.get("metadatas", [[]])[0][index]
            output.append((metadata.get("item_id", ""), document, metadata))
        return output
    except Exception as exc:
        logger.error("Failed to query KB vector DB: %s", exc)
        return []


def delete_from_vector_db(doc_id: str) -> bool:
    if chromadb is None:
        logger.warning('chromadb not installed; nothing to delete for %s.', doc_id)
        return True
    try:
        collection = get_collection()
        collection.delete(where={"doc_id": doc_id})
        return True
    except Exception as exc:
        logger.error("Failed to delete document %s from vector DB: %s", doc_id, exc)
        return False


def delete_from_kb_vector_db(item_id: str) -> bool:
    if chromadb is None:
        logger.warning('chromadb not installed; nothing to delete for %s.', item_id)
        return True
    try:
        collection = get_kb_collection()
        collection.delete(where={"item_id": item_id})
        return True
    except Exception as exc:
        logger.error("Failed to delete KB item %s from vector DB: %s", item_id, exc)
        return False
