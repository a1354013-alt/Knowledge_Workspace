from __future__ import annotations

from app.db import schema


def test_query_indexes_are_created(app_module):
    expected = {
        "documents": {"idx_documents_owner_active_status"},
        "knowledge_entries": {"idx_knowledge_owner_active_status_updated"},
        "logbook_entries": {"idx_logbook_owner_active_status_created"},
        "autotest_runs": {"idx_autotest_runs_owner_status_created"},
        "item_links": {"idx_item_links_from_item_id", "idx_item_links_to_item_id"},
    }

    with app_module.legacy_main.db._connection() as conn:
        for table, index_names in expected.items():
            rows = conn.execute(f"PRAGMA index_list({table})").fetchall()
            actual = {row["name"] for row in rows}
            assert index_names <= actual

    assert len(schema.CREATE_INDEXES_SQL) == sum(len(value) for value in expected.values())
