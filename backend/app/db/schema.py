from __future__ import annotations

"""SQLite schema definitions.

This module is intentionally dumb: it only contains constants and CREATE TABLE
statements so the schema is auditable and reusable from tests.
"""

LINK_TYPE_VALUES = ("references", "derived_from", "produced")
WORKFLOW_STATUS_VALUES = ("draft", "reviewed", "verified", "archived")
KNOWLEDGE_STATUS_VALUES = WORKFLOW_STATUS_VALUES
LOGBOOK_STATUS_VALUES = WORKFLOW_STATUS_VALUES
DOC_STATUS_VALUES = WORKFLOW_STATUS_VALUES
PHOTO_STATUS_VALUES = WORKFLOW_STATUS_VALUES
AUTOTEST_RUN_STATUS_VALUES = ("queued", "running", "passed", "failed")
AUTOTEST_STEP_STATUS_VALUES = ("queued", "running", "passed", "failed", "skipped", "unavailable")
AUTOTEST_STATUS_VALUES = AUTOTEST_RUN_STATUS_VALUES

CREATE_USERS_TABLE_SQL = """
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

CREATE_DOCUMENTS_TABLE_SQL = """
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
    index_status TEXT NOT NULL DEFAULT 'pending',
    index_error TEXT NOT NULL DEFAULT '',
    indexed_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
)
"""

CREATE_KNOWLEDGE_ENTRIES_TABLE_SQL = """
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
    index_status TEXT NOT NULL DEFAULT 'pending',
    index_error TEXT NOT NULL DEFAULT '',
    indexed_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_LOGBOOK_ENTRIES_TABLE_SQL = """
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
    index_status TEXT NOT NULL DEFAULT 'pending',
    index_error TEXT NOT NULL DEFAULT '',
    indexed_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_KNOWLEDGE_REVISIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_revisions (
    revision_id TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    problem TEXT NOT NULL DEFAULT '',
    root_cause TEXT NOT NULL DEFAULT '',
    solution TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'manual',
    source_ref TEXT NOT NULL DEFAULT '',
    change_note TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(entry_id) REFERENCES knowledge_entries(entry_id) ON DELETE CASCADE
)
"""

CREATE_PHOTOS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS photos (
    photo_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    saved_filename TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    ocr_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'reviewed',
    uploaded_by TEXT,
    file_size INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    index_status TEXT NOT NULL DEFAULT 'pending',
    index_error TEXT NOT NULL DEFAULT '',
    indexed_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_AUTOTEST_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS autotest_runs (
    run_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    execution_mode TEXT NOT NULL DEFAULT 'real',
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

CREATE_AUTOTEST_STEPS_TABLE_SQL = """
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
    FOREIGN KEY(run_id) REFERENCES autotest_runs(run_id) ON DELETE CASCADE
)
"""

CREATE_ITEM_LINKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS item_links (
    link_id TEXT PRIMARY KEY,
    from_item_id TEXT NOT NULL,
    to_item_id TEXT NOT NULL,
    link_type TEXT NOT NULL DEFAULT 'references',
    created_at TEXT NOT NULL
)
"""

CREATE_SAVED_PROMPTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS saved_prompts (
    prompt_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    index_status TEXT NOT NULL DEFAULT 'pending',
    index_error TEXT NOT NULL DEFAULT '',
    indexed_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_ITEM_SEARCH_CONTENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS item_search_content (
    item_id TEXT PRIMARY KEY,
    item_type TEXT NOT NULL,
    owner_user_id TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT ''
)
"""

CREATE_INDEX_REPAIR_QUEUE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS index_repair_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    action TEXT NOT NULL,
    owner_user_id TEXT NOT NULL DEFAULT '',
    last_error TEXT NOT NULL DEFAULT '',
    attempts INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(item_id, action)
)
"""

CREATE_INDEXES_SQL = (
    """
    CREATE INDEX IF NOT EXISTS idx_documents_owner_active_status
    ON documents (uploaded_by, is_active, status)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_knowledge_owner_active_status_updated
    ON knowledge_entries (created_by, is_active, status, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_knowledge_index_status
    ON knowledge_entries (created_by, index_status, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_logbook_owner_active_status_created
    ON logbook_entries (created_by, is_active, status, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_logbook_index_status
    ON logbook_entries (created_by, index_status, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_autotest_runs_owner_status_created
    ON autotest_runs (created_by, status, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_documents_index_status
    ON documents (uploaded_by, index_status, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_photos_index_status
    ON photos (uploaded_by, index_status, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_saved_prompts_index_status
    ON saved_prompts (created_by, index_status, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_item_search_content_owner_active_type_updated
    ON item_search_content (owner_user_id, is_active, item_type, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_index_repair_queue_owner_updated
    ON index_repair_queue (owner_user_id, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_item_links_from_item_id
    ON item_links (from_item_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_item_links_to_item_id
    ON item_links (to_item_id)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_item_links_from_to_type
    ON item_links (from_item_id, to_item_id, link_type)
    """,
)
