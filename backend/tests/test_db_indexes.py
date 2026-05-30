from __future__ import annotations

from app.db import schema


def test_query_indexes_are_created(app_module):
    expected = {
        "documents": {"idx_documents_owner_active_status", "idx_documents_index_status"},
        "knowledge_entries": {"idx_knowledge_owner_active_status_updated", "idx_knowledge_index_status"},
        "logbook_entries": {"idx_logbook_owner_active_status_created", "idx_logbook_index_status"},
        "autotest_runs": {"idx_autotest_runs_owner_status_created"},
        "photos": {"idx_photos_index_status"},
        "saved_prompts": {"idx_saved_prompts_index_status"},
        "item_search_content": {"idx_item_search_content_owner_active_type_updated"},
        "index_repair_queue": {"idx_index_repair_queue_owner_updated"},
        "item_links": {"idx_item_links_from_item_id", "idx_item_links_to_item_id", "uq_item_links_from_to_type"},
    }

    with app_module.legacy_main.db._connection() as conn:
        for table, index_names in expected.items():
            rows = conn.execute(f"PRAGMA index_list({table})").fetchall()
            actual = {row["name"] for row in rows}
            assert index_names <= actual

    assert len(schema.CREATE_INDEXES_SQL) == sum(len(value) for value in expected.values())


def test_index_repair_queue_is_unique_per_owner(app_module):
    app_module.db.queue_index_repair(
        item_id="knowledge:item-1",
        item_type="knowledge",
        action="index",
        owner_user_id="owner",
        last_error="first",
    )
    app_module.db.queue_index_repair(
        item_id="knowledge:item-1",
        item_type="knowledge",
        action="index",
        owner_user_id="owner",
        last_error="updated",
    )
    app_module.db.queue_index_repair(
        item_id="knowledge:item-1",
        item_type="knowledge",
        action="index",
        owner_user_id="alice",
        last_error="other owner",
    )

    owner_repairs = app_module.db.list_index_repairs(owner_user_id="owner")
    alice_repairs = app_module.db.list_index_repairs(owner_user_id="alice")

    assert len(owner_repairs) == 1
    assert owner_repairs[0]["last_error"] == "updated"
    assert len(alice_repairs) == 1


def test_index_repair_queue_migration_upgrades_old_unique_key(tmp_path, monkeypatch):
    import sqlite3

    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")

    from app.db import DocumentDatabase

    db_path = tmp_path / "repair-queue.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE index_repair_queue (
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
    )
    conn.execute(
        """
        INSERT INTO index_repair_queue (item_id, item_type, action, owner_user_id, last_error)
        VALUES ('knowledge:item-1', 'knowledge', 'index', 'owner', 'legacy')
        """
    )
    conn.commit()
    conn.close()

    migrated_db = DocumentDatabase(str(db_path))
    migrated_db.queue_index_repair(
        item_id="knowledge:item-1",
        item_type="knowledge",
        action="index",
        owner_user_id="alice",
        last_error="new owner",
    )

    assert len(migrated_db.list_index_repairs(owner_user_id="owner")) == 1
    assert len(migrated_db.list_index_repairs(owner_user_id="alice")) == 1
