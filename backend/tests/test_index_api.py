from __future__ import annotations

from pathlib import Path


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
    assert payload["rebuilt"] == 1
    updated = app_module.db.get_document("doc-rebuild")
    assert updated["index_status"] == "indexed"
    assert updated["index_error"] == ""
    assert not app_module.db.list_index_repairs(owner_user_id="owner")


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
    assert payload["failed"] >= 1
    prompt = app_module.db.get_saved_prompt("prompt-rebuild")
    assert prompt is not None
    assert prompt["index_status"] == "failed"
    assert "vector provider missing" in prompt["index_error"]
