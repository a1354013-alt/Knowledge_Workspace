from __future__ import annotations

import sqlite3
from pathlib import Path


def test_every_connection_enables_foreign_keys(app_module):
    with app_module.db._connection() as conn:
        value = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert value == 1


def test_item_links_unique_constraint_blocks_duplicate_links(app_module):
    assert app_module.db.add_link("knowledge:k1", "document:d1", "references") is True
    assert app_module.db.add_link("knowledge:k1", "document:d1", "references") is False
    links = app_module.db.list_links("knowledge:k1")
    assert len(links) == 1


def test_migration_deduplicates_legacy_item_links(tmp_path, monkeypatch):
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
    db_path = tmp_path / "legacy-links.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE users (
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
    conn.execute(
        """
        CREATE TABLE documents (
            doc_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            saved_filename TEXT NOT NULL,
            allowed_roles TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE item_links (
            link_id TEXT PRIMARY KEY,
            from_item_id TEXT NOT NULL,
            to_item_id TEXT NOT NULL,
            link_type TEXT NOT NULL DEFAULT 'references',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO item_links (link_id, from_item_id, to_item_id, link_type, created_at)
        VALUES
            ('a', 'knowledge:k1', 'document:d1', 'references', '2026-05-01T00:00:00+00:00'),
            ('b', 'knowledge:k1', 'document:d1', 'references', '2026-05-01T00:00:01+00:00')
        """
    )
    conn.commit()
    conn.close()

    from app.db import DocumentDatabase

    migrated = DocumentDatabase(str(Path(db_path)))
    with migrated._connection() as conn2:  # noqa: SLF001 - test-only DB inspection
        count = conn2.execute("SELECT COUNT(*) FROM item_links").fetchone()[0]
        indexes = {row["name"] for row in conn2.execute("PRAGMA index_list(item_links)").fetchall()}
    assert count == 1
    assert "uq_item_links_from_to_type" in indexes


def test_knowledge_revision_foreign_key_cascades_on_entry_delete(app_module):
    assert app_module.db.add_knowledge_entry(
        entry_id="k-delete",
        title="title",
        status="reviewed",
        problem="problem",
        root_cause="root",
        solution="solution",
        tags="",
        notes="",
        created_by="owner",
    )
    assert app_module.db.add_knowledge_revision(
        entry_id="k-delete",
        snapshot={
            "title": "title",
            "status": "reviewed",
            "problem": "problem",
            "root_cause": "root",
            "solution": "solution",
            "tags": "",
            "notes": "",
            "source_type": "manual",
            "source_ref": "",
        },
        change_note="seed",
        created_by="owner",
    )
    assert app_module.db.delete_knowledge_entry("k-delete") is True
    with app_module.db._connection() as conn:  # noqa: SLF001 - test-only DB inspection
        count = conn.execute("SELECT COUNT(*) FROM knowledge_revisions WHERE entry_id = 'k-delete'").fetchone()[0]
    assert count == 0


def test_autotest_step_foreign_key_cascades_on_run_delete(app_module):
    assert app_module.db.add_autotest_run(
        run_id="run-delete",
        source_type="zip_upload",
        source_ref="demo.zip",
        execution_mode="simulated",
        project_type_detected="node",
        working_directory=".",
        project_name="demo",
        project_type="node",
        status="queued",
        summary="",
        suggestion="",
        prompt_output="",
        failed_reason="",
        timeline_json="[]",
        created_by="owner",
    )
    assert app_module.db.add_autotest_step(
        step_id="step-delete",
        run_id="run-delete",
        name="test",
        command="npm test",
        status="queued",
    )
    with app_module.db._connection() as conn:  # noqa: SLF001 - test-only DB inspection
        conn.execute("DELETE FROM autotest_runs WHERE run_id = 'run-delete'")
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM autotest_steps WHERE run_id = 'run-delete'").fetchone()[0]
    assert count == 0
