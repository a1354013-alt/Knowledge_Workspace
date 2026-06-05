from __future__ import annotations

from pathlib import Path

import pytest


def _seed_many_index_rows(db, *, count: int = 520, user_id: str = "owner") -> None:
    for index in range(count):
        suffix = f"{index:04d}"
        assert db.add_knowledge_entry(
            entry_id=f"bulk-knowledge-{suffix}",
            title=f"Knowledge {suffix}",
            status="reviewed",
            problem="Problem",
            root_cause="",
            solution="Solution",
            tags="bulk",
            notes="",
            created_by=user_id,
        )
        assert db.add_logbook_entry(
            entry_id=f"bulk-logbook-{suffix}",
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
        assert db.add_photo(
            photo_id=f"bulk-photo-{suffix}",
            filename=f"photo-{suffix}.png",
            saved_filename=f"photo-{suffix}.png",
            tags="bulk",
            description="Photo",
            ocr_text="",
            file_size=1,
            uploaded_by=user_id,
        )
        assert db.add_saved_prompt(
            prompt_id=f"bulk-prompt-{suffix}",
            title=f"Prompt {suffix}",
            content="Prompt body",
            tags="bulk",
            created_by=user_id,
        )


def _seed_many_index_rows_for_type(db, item_type: str, *, count: int = 520, user_id: str = "owner") -> None:
    for index in range(count):
        suffix = f"{index:04d}"
        if item_type == "knowledge":
            assert db.add_knowledge_entry(
                entry_id=f"rebuild-knowledge-{suffix}",
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
                entry_id=f"rebuild-logbook-{suffix}",
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
                photo_id=f"rebuild-photo-{suffix}",
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
                prompt_id=f"rebuild-prompt-{suffix}",
                title=f"Prompt {suffix}",
                content="Prompt body",
                tags="bulk",
                created_by=user_id,
            )


def test_index_status_scans_all_kb_item_types_beyond_500(app_module, client, auth_headers):
    _seed_many_index_rows(app_module.db, count=520)

    response = client.get("/api/index/status", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["summary"]["knowledge"]["total"] == 520
    assert payload["summary"]["logbook"]["total"] == 520
    assert payload["summary"]["photo"]["total"] == 520
    assert payload["summary"]["prompt"]["total"] == 520
    failed_ids = {(item["item_type"], item["item_id"]) for item in payload["failed_items"]}
    assert ("knowledge", "bulk-knowledge-0519") in failed_ids
    assert ("logbook", "bulk-logbook-0519") in failed_ids
    assert ("photo", "bulk-photo-0519") in failed_ids
    assert ("prompt", "bulk-prompt-0519") in failed_ids


@pytest.mark.parametrize(
    ("item_type", "sync_name", "expected_id"),
    [
        ("knowledge", "sync_knowledge_entry_index", "rebuild-knowledge-0519"),
        ("logbook", "sync_logbook_entry_index", "rebuild-logbook-0519"),
        ("photo", "sync_photo_index", "rebuild-photo-0519"),
        ("prompt", "sync_prompt_index", "rebuild-prompt-0519"),
    ],
)
def test_rebuild_single_item_type_processes_rows_beyond_500(
    app_module, monkeypatch, item_type, sync_name, expected_id
):
    from app.services import indexing_service

    _seed_many_index_rows_for_type(app_module.db, item_type, count=520)
    processed: list[str] = []

    def record_rebuild(row):
        id_key = "photo_id" if item_type == "photo" else "prompt_id" if item_type == "prompt" else "entry_id"
        processed.append(str(row[id_key]))

    monkeypatch.setattr(indexing_service, sync_name, record_rebuild)

    response = indexing_service.rebuild_single_item_type({"sub": "owner"}, item_type)

    assert response.rebuilt == 520
    assert response.failed == 0
    assert len(processed) == 520
    assert expected_id in processed
    assert response.items[-1].item_id == expected_id

def test_index_status_reports_provider_and_failed_items(app_module, client, auth_headers, monkeypatch):
    uploads_dir = Path(app_module.legacy_main.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "broken.txt").write_text("demo", encoding="utf-8")
    assert app_module.db.add_document(
        doc_id="doc-index-status",
        filename="broken.txt",
        saved_filename="broken.txt",
        file_size=4,
        uploaded_by="owner",
        status="reviewed",
        index_status="failed",
        index_error="vector offline",
    )

    response = client.get("/api/index/status", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider"]["active_provider"] == "demo-fallback"
    assert payload["provider"]["demo_mode"] is True
    assert payload["summary"]["document"]["failed"] >= 1
    assert any(item["item_id"] == "doc-index-status" for item in payload["failed_items"])


def test_rebuild_single_document_index_updates_status(app_module, client, auth_headers, monkeypatch):
    from app.services import indexing_service

    uploads_dir = Path(app_module.legacy_main.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "doc.txt").write_text("hello world", encoding="utf-8")
    assert app_module.db.add_document(
        doc_id="doc-rebuild",
        filename="doc.txt",
        saved_filename="doc.txt",
        file_size=11,
        uploaded_by="owner",
        status="reviewed",
        index_status="failed",
        index_error="previous failure",
    )

    monkeypatch.setattr(indexing_service, "process_file", lambda *args, **kwargs: "doc-rebuild")

    response = client.post("/api/index/rebuild/document/doc-rebuild", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["message"] == "Rebuilt document:doc-rebuild."
    assert payload["rebuilt"] == 1
    assert payload["failed"] == 0
    updated = app_module.db.get_document("doc-rebuild")
    assert updated["index_status"] == "indexed"
    assert updated["index_error"] == ""
    assert not app_module.db.list_index_repairs(owner_user_id="owner")


def test_rebuild_single_document_index_reports_failure_message(app_module, client, auth_headers, monkeypatch):
    from app.services import indexing_service

    uploads_dir = Path(app_module.legacy_main.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "doc-fail.txt").write_text("hello world", encoding="utf-8")
    assert app_module.db.add_document(
        doc_id="doc-rebuild-fail",
        filename="doc-fail.txt",
        saved_filename="doc-fail.txt",
        file_size=11,
        uploaded_by="owner",
        status="reviewed",
        index_status="failed",
        index_error="previous failure",
    )

    monkeypatch.setattr(
        indexing_service,
        "process_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("vector provider missing")),
    )

    response = client.post("/api/index/rebuild/document/doc-rebuild-fail", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["message"] == "Failed to rebuild document:doc-rebuild-fail."
    assert payload["rebuilt"] == 0
    assert payload["failed"] == 1
    assert payload["items"][0]["status"] == "failed"


def test_rebuild_all_indexes_marks_failures(app_module, client, auth_headers, monkeypatch):
    from app.services import indexing_service

    assert app_module.db.add_saved_prompt(
        prompt_id="prompt-rebuild",
        title="Prompt",
        content="Body",
        tags="demo",
        created_by="owner",
        index_status="failed",
        index_error="old failure",
    )

    monkeypatch.setattr(
        indexing_service,
        "index_saved_prompt",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("vector provider missing")),
    )

    response = client.post("/api/index/rebuild", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "completed with failures" in payload["message"].lower()
    assert payload["failed"] >= 1
    prompt = app_module.db.get_saved_prompt("prompt-rebuild")
    assert prompt is not None
    assert prompt["index_status"] == "failed"
    assert "vector provider missing" in prompt["index_error"]


def test_index_status_excludes_archived_and_inactive_items_from_pending_summary(app_module, client, auth_headers):
    assert app_module.db.add_document(
        doc_id="doc-archived-excluded",
        filename="archived.txt",
        saved_filename="archived.txt",
        file_size=1,
        uploaded_by="owner",
        status="archived",
        index_status="excluded",
    )
    assert app_module.db.add_saved_prompt(
        prompt_id="prompt-excluded",
        title="Archived prompt",
        content="Body",
        tags="demo",
        created_by="owner",
        index_status="excluded",
    )
    assert app_module.db.delete_saved_prompt("prompt-excluded")

    response = client.get("/api/index/status", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["summary"]["document"]["pending"] == 0
    assert payload["summary"]["document"]["excluded"] >= 1
    assert payload["summary"]["prompt"]["excluded"] >= 1
    assert all(item["status"] != "excluded" for item in payload["failed_items"])
