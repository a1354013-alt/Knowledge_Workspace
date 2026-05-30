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


def test_index_consistency_report_marks_vector_unavailable_repairs(app_module):
    indexing_service = importlib.import_module("app.services.indexing_service")
    app_module.db.queue_index_repair(
        item_id="prompt:consistency-prompt-2",
        item_type="prompt",
        action="index",
        owner_user_id="owner",
        last_error="Vector index unavailable: chromadb is not installed.",
    )

    report = indexing_service.get_index_consistency_report(owner_user_id="owner")
    queue_issue = next(item for item in report if item["item_id"] == "prompt:consistency-prompt-2")
    assert queue_issue["repair_status"] == "index_unavailable"
    assert queue_issue["issue"] == "repair_queue:index:index_unavailable"


def test_index_consistency_repair_distinguishes_unavailable_from_failed(app_module, monkeypatch):
    indexing_service = importlib.import_module("app.services.indexing_service")
    assert app_module.db.add_saved_prompt(
        prompt_id="prompt-repair-status",
        title="Prompt title",
        content="Prompt body",
        tags="demo",
        created_by="owner",
    )
    app_module.db.queue_index_repair(
        item_id="prompt:prompt-repair-status",
        item_type="prompt",
        action="index",
        owner_user_id="owner",
        last_error="queued",
    )

    monkeypatch.setattr(
        indexing_service,
        "index_saved_prompt",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("Vector index unavailable: chromadb is not installed.")),
    )
    repaired = indexing_service.repair_index_consistency(owner_user_id="owner")
    assert repaired[0]["status"] == "index_unavailable"
    assert app_module.db.list_index_repairs(owner_user_id="owner")

    monkeypatch.setattr(
        indexing_service,
        "index_saved_prompt",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("repair exploded")),
    )
    repaired = indexing_service.repair_index_consistency(owner_user_id="owner")
    assert repaired[0]["status"] == "failed"
