from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from app.db import schema
from app.passwords import hash_password

logger = logging.getLogger("knowledge_workspace")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_autotest_execution_mode_sql(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        UPDATE autotest_runs
        SET execution_mode = CASE
            WHEN lower(trim(COALESCE(execution_mode, ''))) = 'real' THEN 'real'
            ELSE 'simulated'
        END
        WHERE execution_mode IS NULL
           OR trim(COALESCE(execution_mode, '')) = ''
           OR lower(trim(COALESCE(execution_mode, ''))) NOT IN ('real', 'simulated')
        """
    )


def _autotest_execution_mode_default_is_simulated(cursor: sqlite3.Cursor) -> bool:
    cursor.execute("PRAGMA table_info(autotest_runs)")
    for row in cursor.fetchall():
        if row[1] == "execution_mode":
            default_value = str(row[4] or "").strip().strip("'\"").lower()
            return default_value == "simulated"
    return False


def _rebuild_autotest_runs_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute(
        """
        CREATE TABLE autotest_runs__migrated (
            run_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            execution_mode TEXT NOT NULL DEFAULT 'simulated',
            project_type_detected TEXT NOT NULL DEFAULT '',
            working_directory TEXT NOT NULL DEFAULT '',
            project_name TEXT NOT NULL DEFAULT '',
            project_type TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'queued',
            summary TEXT NOT NULL DEFAULT '',
            suggestion TEXT NOT NULL DEFAULT '',
            prompt_output TEXT NOT NULL DEFAULT '',
            failed_reason TEXT NOT NULL DEFAULT '',
            timeline_json TEXT NOT NULL DEFAULT '',
            problem_entry_id TEXT NOT NULL DEFAULT '',
            solution_entry_id TEXT NOT NULL DEFAULT '',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO autotest_runs__migrated (
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
            failed_reason,
            timeline_json,
            problem_entry_id,
            solution_entry_id,
            created_by,
            created_at,
            updated_at
        )
        SELECT
            run_id,
            source_type,
            source_ref,
            CASE
                WHEN lower(trim(COALESCE(execution_mode, ''))) = 'real' THEN 'real'
                ELSE 'simulated'
            END,
            project_type_detected,
            working_directory,
            project_name,
            project_type,
            status,
            summary,
            suggestion,
            prompt_output,
            failed_reason,
            timeline_json,
            problem_entry_id,
            solution_entry_id,
            created_by,
            created_at,
            updated_at
        FROM autotest_runs
        """
    )
    cursor.execute("DROP TABLE autotest_runs")
    cursor.execute("ALTER TABLE autotest_runs__migrated RENAME TO autotest_runs")
    cursor.execute("PRAGMA foreign_keys = ON")


def migrate_item_links_table(cursor: sqlite3.Cursor) -> None:
    # Older versions used a generic 'related' link_type; normalize it to 'references'.
    cursor.execute(
        """
        UPDATE item_links
        SET link_type = 'references'
        WHERE link_type IN ('related', 'reference', 'ref', '')
        """
    )
    cursor.execute(
        """
        INSERT INTO item_links (link_id, from_item_id, to_item_id, link_type, created_at)
        SELECT
            lower(hex(randomblob(16))),
            normalized_from,
            normalized_to,
            'produced',
            created_at
        FROM (
            SELECT
                link_id,
                from_item_id,
                to_item_id,
                created_at,
                to_item_id AS normalized_from,
                from_item_id AS normalized_to
            FROM item_links
            WHERE from_item_id LIKE 'knowledge:%'
              AND to_item_id LIKE 'logbook:%'
              AND link_type IN ('derived_from', 'produced')
        ) AS legacy_links
        WHERE NOT EXISTS (
            SELECT 1
            FROM item_links AS existing
            WHERE existing.from_item_id = legacy_links.normalized_from
              AND existing.to_item_id = legacy_links.normalized_to
              AND existing.link_type = 'produced'
        )
        """
    )
    cursor.execute(
        """
        DELETE FROM item_links
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM item_links
            GROUP BY from_item_id, to_item_id, link_type
        )
        """
    )


def ensure_query_indexes(cursor: sqlite3.Cursor) -> None:
    for sql in schema.CREATE_INDEXES_SQL:
        cursor.execute(sql)


def ensure_search_support_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute(schema.CREATE_ITEM_SEARCH_CONTENT_TABLE_SQL)
    cursor.execute(schema.CREATE_INDEX_REPAIR_QUEUE_TABLE_SQL)
    try:
        cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS item_search_fts
            USING fts5(
                item_id UNINDEXED,
                item_type UNINDEXED,
                owner_user_id UNINDEXED,
                is_active UNINDEXED,
                updated_at UNINDEXED,
                title,
                content
            )
            """
        )
    except sqlite3.OperationalError as exc:
        logger.warning("SQLite FTS5 is unavailable; search fallback will use LIKE queries only: %s", exc)


def migrate_users_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("UPDATE users SET role = 'owner' WHERE role != 'owner'")


def migrate_documents_table(cursor: sqlite3.Cursor) -> None:
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
        "index_status": "ALTER TABLE documents ADD COLUMN index_status TEXT NOT NULL DEFAULT 'pending'",
        "index_error": "ALTER TABLE documents ADD COLUMN index_error TEXT NOT NULL DEFAULT ''",
        "indexed_at": "ALTER TABLE documents ADD COLUMN indexed_at TEXT NOT NULL DEFAULT ''",
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
    cursor.execute(
        """
        UPDATE documents
        SET index_status = CASE
            WHEN is_active = 0 OR status = 'archived' THEN 'excluded'
            WHEN status IN ('reviewed', 'verified') THEN 'indexed'
            WHEN status = 'draft' THEN 'pending'
            ELSE 'failed'
        END
        WHERE index_status IS NULL OR index_status = ''
        """
    )
    cursor.execute(
        """
        UPDATE documents
        SET indexed_at = uploaded_at
        WHERE index_status = 'indexed' AND (indexed_at IS NULL OR indexed_at = '')
        """
    )


def migrate_photos_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA table_info(photos)")
    columns = {row[1] for row in cursor.fetchall()}
    migrations = {
        "uploaded_by": "ALTER TABLE photos ADD COLUMN uploaded_by TEXT",
        "is_active": "ALTER TABLE photos ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        "updated_at": "ALTER TABLE photos ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
        "file_size": "ALTER TABLE photos ADD COLUMN file_size INTEGER NOT NULL DEFAULT 0",
        "tags": "ALTER TABLE photos ADD COLUMN tags TEXT NOT NULL DEFAULT ''",
        "status": "ALTER TABLE photos ADD COLUMN status TEXT NOT NULL DEFAULT 'reviewed'",
        "description": "ALTER TABLE photos ADD COLUMN description TEXT NOT NULL DEFAULT ''",
        "ocr_text": "ALTER TABLE photos ADD COLUMN ocr_text TEXT NOT NULL DEFAULT ''",
        "created_at": "ALTER TABLE photos ADD COLUMN created_at TEXT NOT NULL DEFAULT ''",
        "index_status": "ALTER TABLE photos ADD COLUMN index_status TEXT NOT NULL DEFAULT 'pending'",
        "index_error": "ALTER TABLE photos ADD COLUMN index_error TEXT NOT NULL DEFAULT ''",
        "indexed_at": "ALTER TABLE photos ADD COLUMN indexed_at TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migrations.items():
        if column not in columns:
            cursor.execute(sql)

    # Normalize timestamps from older schemas.
    if "uploaded_at" in columns:
        cursor.execute("UPDATE photos SET created_at = uploaded_at WHERE created_at = ''")
        cursor.execute("UPDATE photos SET updated_at = uploaded_at WHERE updated_at = ''")
    else:
        cursor.execute("UPDATE photos SET created_at = updated_at WHERE created_at = ''")

    # Older photos schemas sometimes carried these document-like columns; keep them but ensure sane values.
    if "allowed_roles" in columns:
        cursor.execute("UPDATE photos SET allowed_roles = 'owner' WHERE allowed_roles = '' OR allowed_roles IS NULL")
    if "approved" in columns:
        cursor.execute("UPDATE photos SET approved = 1 WHERE approved = 0")

    cursor.execute("UPDATE photos SET status = 'archived' WHERE is_active = 0 AND status != 'archived'")
    cursor.execute("UPDATE photos SET status = 'reviewed' WHERE is_active = 1 AND status = ''")
    cursor.execute("UPDATE photos SET uploaded_by = 'owner' WHERE uploaded_by IS NULL OR uploaded_by = ''")
    cursor.execute(
        """
        UPDATE photos
        SET index_status = CASE
            WHEN is_active = 0 OR status = 'archived' THEN 'excluded'
            ELSE 'indexed'
        END
        WHERE index_status IS NULL OR index_status = ''
        """
    )
    cursor.execute("UPDATE photos SET index_status = 'excluded', index_error = '', indexed_at = '' WHERE is_active = 0 OR status = 'archived'")
    cursor.execute(
        """
        UPDATE photos
        SET indexed_at = created_at
        WHERE index_status = 'indexed' AND (indexed_at IS NULL OR indexed_at = '')
        """
    )


def migrate_knowledge_entries_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA table_info(knowledge_entries)")
    columns = {row[1] for row in cursor.fetchall()}
    migrations = {
        "title": "ALTER TABLE knowledge_entries ADD COLUMN title TEXT NOT NULL DEFAULT ''",
        "root_cause": "ALTER TABLE knowledge_entries ADD COLUMN root_cause TEXT NOT NULL DEFAULT ''",
        "tags": "ALTER TABLE knowledge_entries ADD COLUMN tags TEXT NOT NULL DEFAULT ''",
        "notes": "ALTER TABLE knowledge_entries ADD COLUMN notes TEXT NOT NULL DEFAULT ''",
        "source_type": "ALTER TABLE knowledge_entries ADD COLUMN source_type TEXT NOT NULL DEFAULT 'manual'",
        "source_ref": "ALTER TABLE knowledge_entries ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",
        "created_by": "ALTER TABLE knowledge_entries ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
        "is_active": "ALTER TABLE knowledge_entries ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        "updated_at": "ALTER TABLE knowledge_entries ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
        "index_status": "ALTER TABLE knowledge_entries ADD COLUMN index_status TEXT NOT NULL DEFAULT 'pending'",
        "index_error": "ALTER TABLE knowledge_entries ADD COLUMN index_error TEXT NOT NULL DEFAULT ''",
        "indexed_at": "ALTER TABLE knowledge_entries ADD COLUMN indexed_at TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migrations.items():
        if column not in columns:
            cursor.execute(sql)
    cursor.execute("UPDATE knowledge_entries SET updated_at = created_at WHERE updated_at = ''")
    cursor.execute(
        """
        UPDATE knowledge_entries
        SET index_status = CASE
            WHEN is_active = 0 OR status = 'archived' THEN 'excluded'
            ELSE 'indexed'
        END
        WHERE index_status IS NULL OR index_status = ''
        """
    )
    cursor.execute("UPDATE knowledge_entries SET index_status = 'excluded', index_error = '', indexed_at = '' WHERE is_active = 0 OR status = 'archived'")
    cursor.execute(
        """
        UPDATE knowledge_entries
        SET indexed_at = created_at
        WHERE index_status = 'indexed' AND (indexed_at IS NULL OR indexed_at = '')
        """
    )


def migrate_logbook_entries_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA table_info(logbook_entries)")
    columns = {row[1] for row in cursor.fetchall()}
    migrations = {
        "run_id": "ALTER TABLE logbook_entries ADD COLUMN run_id TEXT NOT NULL DEFAULT ''",
        "root_cause": "ALTER TABLE logbook_entries ADD COLUMN root_cause TEXT NOT NULL DEFAULT ''",
        "tags": "ALTER TABLE logbook_entries ADD COLUMN tags TEXT NOT NULL DEFAULT ''",
        "source_type": "ALTER TABLE logbook_entries ADD COLUMN source_type TEXT NOT NULL DEFAULT 'manual'",
        "source_ref": "ALTER TABLE logbook_entries ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",
        "created_by": "ALTER TABLE logbook_entries ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
        "is_active": "ALTER TABLE logbook_entries ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        "updated_at": "ALTER TABLE logbook_entries ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
        "index_status": "ALTER TABLE logbook_entries ADD COLUMN index_status TEXT NOT NULL DEFAULT 'pending'",
        "index_error": "ALTER TABLE logbook_entries ADD COLUMN index_error TEXT NOT NULL DEFAULT ''",
        "indexed_at": "ALTER TABLE logbook_entries ADD COLUMN indexed_at TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migrations.items():
        if column not in columns:
            cursor.execute(sql)
    cursor.execute("UPDATE logbook_entries SET updated_at = created_at WHERE updated_at = ''")
    cursor.execute(
        """
        UPDATE logbook_entries
        SET index_status = CASE
            WHEN is_active = 0 OR status = 'archived' THEN 'excluded'
            ELSE 'indexed'
        END
        WHERE index_status IS NULL OR index_status = ''
        """
    )
    cursor.execute("UPDATE logbook_entries SET index_status = 'excluded', index_error = '', indexed_at = '' WHERE is_active = 0 OR status = 'archived'")
    cursor.execute(
        """
        UPDATE logbook_entries
        SET indexed_at = created_at
        WHERE index_status = 'indexed' AND (indexed_at IS NULL OR indexed_at = '')
        """
    )


def migrate_saved_prompts_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA table_info(saved_prompts)")
    columns = {row[1] for row in cursor.fetchall()}
    migrations = {
        "tags": "ALTER TABLE saved_prompts ADD COLUMN tags TEXT NOT NULL DEFAULT ''",
        "created_by": "ALTER TABLE saved_prompts ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
        "is_active": "ALTER TABLE saved_prompts ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        "updated_at": "ALTER TABLE saved_prompts ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
        "index_status": "ALTER TABLE saved_prompts ADD COLUMN index_status TEXT NOT NULL DEFAULT 'pending'",
        "index_error": "ALTER TABLE saved_prompts ADD COLUMN index_error TEXT NOT NULL DEFAULT ''",
        "indexed_at": "ALTER TABLE saved_prompts ADD COLUMN indexed_at TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migrations.items():
        if column not in columns:
            cursor.execute(sql)
    cursor.execute("UPDATE saved_prompts SET updated_at = created_at WHERE updated_at = ''")
    cursor.execute(
        """
        UPDATE saved_prompts
        SET index_status = CASE
            WHEN is_active = 0 THEN 'excluded'
            ELSE 'indexed'
        END
        WHERE index_status IS NULL OR index_status = ''
        """
    )
    cursor.execute("UPDATE saved_prompts SET index_status = 'excluded', index_error = '', indexed_at = '' WHERE is_active = 0")
    cursor.execute(
        """
        UPDATE saved_prompts
        SET indexed_at = created_at
        WHERE index_status = 'indexed' AND (indexed_at IS NULL OR indexed_at = '')
        """
    )


def migrate_autotest_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA table_info(autotest_runs)")
    run_columns = {row[1] for row in cursor.fetchall()}
    run_migrations = {
        "execution_mode": "ALTER TABLE autotest_runs ADD COLUMN execution_mode TEXT NOT NULL DEFAULT 'simulated'",
        "project_type_detected": "ALTER TABLE autotest_runs ADD COLUMN project_type_detected TEXT NOT NULL DEFAULT ''",
        "working_directory": "ALTER TABLE autotest_runs ADD COLUMN working_directory TEXT NOT NULL DEFAULT ''",
        "project_name": "ALTER TABLE autotest_runs ADD COLUMN project_name TEXT NOT NULL DEFAULT ''",
        "project_type": "ALTER TABLE autotest_runs ADD COLUMN project_type TEXT NOT NULL DEFAULT ''",
        "status": "ALTER TABLE autotest_runs ADD COLUMN status TEXT NOT NULL DEFAULT 'queued'",
        "summary": "ALTER TABLE autotest_runs ADD COLUMN summary TEXT NOT NULL DEFAULT ''",
        "suggestion": "ALTER TABLE autotest_runs ADD COLUMN suggestion TEXT NOT NULL DEFAULT ''",
        "prompt_output": "ALTER TABLE autotest_runs ADD COLUMN prompt_output TEXT NOT NULL DEFAULT ''",
        "failed_reason": "ALTER TABLE autotest_runs ADD COLUMN failed_reason TEXT NOT NULL DEFAULT ''",
        "timeline_json": "ALTER TABLE autotest_runs ADD COLUMN timeline_json TEXT NOT NULL DEFAULT ''",
        "problem_entry_id": "ALTER TABLE autotest_runs ADD COLUMN problem_entry_id TEXT NOT NULL DEFAULT ''",
        "solution_entry_id": "ALTER TABLE autotest_runs ADD COLUMN solution_entry_id TEXT NOT NULL DEFAULT ''",
        "created_by": "ALTER TABLE autotest_runs ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
        "updated_at": "ALTER TABLE autotest_runs ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in run_migrations.items():
        if column not in run_columns:
            cursor.execute(sql)

    # Some older schemas used a freeform 'unknown' status; normalize to queued to satisfy API contracts.
    cursor.execute(
        """
        UPDATE autotest_runs
        SET status = 'queued'
        WHERE status IS NULL OR status IN ('', 'unknown')
        """
    )
    _normalize_autotest_execution_mode_sql(cursor)
    if "project_name" in run_columns:
        cursor.execute("UPDATE autotest_runs SET project_name = source_ref WHERE project_name = ''")
    cursor.execute("UPDATE autotest_runs SET created_by = 'owner' WHERE created_by = ''")
    cursor.execute("UPDATE autotest_runs SET updated_at = created_at WHERE updated_at = ''")
    if not _autotest_execution_mode_default_is_simulated(cursor):
        _rebuild_autotest_runs_table(cursor)

    cursor.execute("PRAGMA table_info(autotest_steps)")
    step_columns = {row[1] for row in cursor.fetchall()}
    if "stdout_summary" not in step_columns:
        cursor.execute("ALTER TABLE autotest_steps ADD COLUMN stdout_summary TEXT NOT NULL DEFAULT ''")
    if "stderr_summary" not in step_columns:
        cursor.execute("ALTER TABLE autotest_steps ADD COLUMN stderr_summary TEXT NOT NULL DEFAULT ''")
    if "error_type" not in step_columns:
        cursor.execute("ALTER TABLE autotest_steps ADD COLUMN error_type TEXT NOT NULL DEFAULT ''")


def migrate_knowledge_revisions_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA table_info(knowledge_revisions)")
    columns = {row[1] for row in cursor.fetchall()}
    migrations = {
        "title": "ALTER TABLE knowledge_revisions ADD COLUMN title TEXT NOT NULL DEFAULT ''",
        "status": "ALTER TABLE knowledge_revisions ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'",
        "problem": "ALTER TABLE knowledge_revisions ADD COLUMN problem TEXT NOT NULL DEFAULT ''",
        "root_cause": "ALTER TABLE knowledge_revisions ADD COLUMN root_cause TEXT NOT NULL DEFAULT ''",
        "solution": "ALTER TABLE knowledge_revisions ADD COLUMN solution TEXT NOT NULL DEFAULT ''",
        "tags": "ALTER TABLE knowledge_revisions ADD COLUMN tags TEXT NOT NULL DEFAULT ''",
        "notes": "ALTER TABLE knowledge_revisions ADD COLUMN notes TEXT NOT NULL DEFAULT ''",
        "source_type": "ALTER TABLE knowledge_revisions ADD COLUMN source_type TEXT NOT NULL DEFAULT 'manual'",
        "source_ref": "ALTER TABLE knowledge_revisions ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",
        "change_note": "ALTER TABLE knowledge_revisions ADD COLUMN change_note TEXT NOT NULL DEFAULT ''",
        "created_by": "ALTER TABLE knowledge_revisions ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migrations.items():
        if column not in columns:
            cursor.execute(sql)


def seed_owner_user(cursor: sqlite3.Cursor) -> None:
    password = str(os.getenv("DEFAULT_OWNER_PASSWORD", "")).strip()
    if not password:
        logger.warning("DEFAULT_OWNER_PASSWORD is not set; skipping owner seed.")
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    count = int(cursor.fetchone()[0])
    if count > 0:
        return

    now = utc_now_iso()
    cursor.execute(
        """
        INSERT INTO users (user_id, password_hash, display_name, role, is_active, created_at, updated_at)
        VALUES (?, ?, ?, 'owner', 1, ?, ?)
        """,
        ("owner", hash_password(password), "Owner", now, now),
    )


def ensure_owner_password_is_current(cursor: sqlite3.Cursor) -> None:
    password = str(os.getenv("DEFAULT_OWNER_PASSWORD", "")).strip()
    if not password:
        return
    # If the DB already has an owner user, do not overwrite the password (security boundary).
    cursor.execute("SELECT user_id FROM users WHERE user_id = 'owner'")
    row = cursor.fetchone()
    if not row:
        return
    # No-op by design.


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
