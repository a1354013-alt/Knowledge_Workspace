from __future__ import annotations

import importlib

import pytest


def _seed_many_consistency_rows_for_type(db, item_type: str, *, count: int = 520, user_id: str = "owner") -> None:
    for index in range(count):
        suffix = f"{index:04d}"
        if item_type == "knowledge":
            assert db.add_knowledge_entry(
                entry_id=f"consistency-knowledge-{suffix}",
                title=f"Knowledge {suffix}",
                status="reviewed",
                problem="Problem",
                root_cause="",
                solution="Solution",
                tags="bulk",
                notes="",
                created_by=user_id,
            )
        elif item_type == "logbook":
            assert db.add_logbook_entry(
                entry_id=f"consistency-logbook-{suffix}",
                title=f"Logbook {suffix}",
                status="reviewed",
                run_id="",
                problem="Problem",
                root_cause="",
                solution="Solution",
                tags="bulk",
                source_type="manual",
                created_by=user_id,
            )
        elif item_type == "photo":
            assert db.add_photo(
                photo_id=f"consistency-photo-{suffix}",
                filename=f"photo-{suffix}.png",
                saved_filename=f"photo-{suffix}.png",
                tags="bulk",
                description="Photo",
                ocr_text="",
                file_size=1,
                uploaded_by=user_id,
            )
        else:
            assert db.add_saved_prompt(
                prompt_id=f"consistency-prompt-{suffix}",
                title=f"Prompt {suffix}",
                content="Prompt body",
                tags="bulk",
                created_by=user_id,
            )


@pytest.mark.parametrize(
    ("item_type", "expected_id"),
    [
        ("knowledge", "knowledge:consistency-knowledge-0519"),
        ("logbook", "logbook:consistency-logbook-0519"),
        ("photo", "photo:consistency-photo-0519"),
        ("prompt", "prompt:consistency-prompt-0519"),
    ],
)
def test_index_consistency_report_scans_rows_beyond_500(app_module, item_type, expected_id):
    indexing_service = importlib.import_module("app.services.indexing_service")
    _seed_many_consistency_rows_for_type(app_module.db, item_type, count=520)

    report = indexing_service.get_index_consistency_report(owner_user_id="owner")

    matching = [issue for issue in report if issue["item_type"] == item_type]
    assert len(matching) == 520
    assert any(issue["item_id"] == expected_id and issue["issue"] == "missing_search_content" for issue in matching)


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
