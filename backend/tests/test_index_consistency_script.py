from __future__ import annotations

import importlib


def test_index_consistency_report_detects_missing_search_content(app_module):
    indexing_service = importlib.import_module("app.services.indexing_service")
    assert app_module.db.add_knowledge_entry(
        entry_id="consistency-knowledge-1",
        title="Consistency title",
        status="draft",
        problem="Consistency needle",
        root_cause="",
        solution="Consistency solution",
        tags="demo",
        notes="",
        created_by="owner",
    )

    report = indexing_service.get_index_consistency_report(owner_user_id="owner")
    assert any(
        issue["item_id"] == "knowledge:consistency-knowledge-1" and issue["issue"] == "missing_search_content"
        for issue in report
    )


def test_index_consistency_repair_processes_repair_queue(app_module):
    indexing_service = importlib.import_module("app.services.indexing_service")
    assert app_module.db.add_saved_prompt(
        prompt_id="consistency-prompt-1",
        title="Prompt title",
        content="Prompt consistency content",
        tags="demo",
        created_by="owner",
    )
    app_module.db.queue_index_repair(
        item_id="prompt:consistency-prompt-1",
        item_type="prompt",
        action="index",
        owner_user_id="owner",
        last_error="forced repair",
    )

    repaired = indexing_service.repair_index_consistency(owner_user_id="owner")
    assert any(item["item_id"] == "prompt:consistency-prompt-1" and item["status"] == "repaired" for item in repaired)
    assert not app_module.db.list_index_repairs(owner_user_id="owner")
