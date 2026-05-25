from __future__ import annotations

import base64
import sys
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency in tests
    Image = None


def _handler_module(name: str):
    return sys.modules[f"app.api.handlers.{name}"]


def test_document_update_keeps_success_when_indexing_fails(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    async def fail_sync_document_index(*args, **kwargs):
        raise RuntimeError("vector offline")

    uploads_dir = Path(app_module.legacy_main.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / "doc.txt"
    file_path.write_text("hello world", encoding="utf-8")

    assert app_module.db.add_document(
        doc_id="doc-side-effect",
        filename="doc.txt",
        saved_filename="doc.txt",
        file_size=11,
        uploaded_by="owner",
        category="notes",
        tags="before",
        status="reviewed",
        index_status="indexed",
        indexed_at="2026-05-07T00:00:00+00:00",
    )

    monkeypatch.setattr(
        _handler_module("docs"),
        "sync_document_index",
        fail_sync_document_index,
    )

    response = client.patch(
        "/api/docs/doc-side-effect",
        headers=auth_headers,
        json={"tags": "after"},
    )
    assert response.status_code == 200, response.text
    assert "indexing failed" in response.json()["message"].lower()

    document = app_module.db.get_document("doc-side-effect")
    assert document is not None
    assert document["tags"] == "after"
    assert document["index_status"] == "failed"
    assert "vector offline" in document["index_error"]


def test_document_upload_reports_vector_index_unavailable(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    async def fail_sync_document_index(*args, **kwargs):
        raise RuntimeError("Vector index unavailable: chromadb is not installed.")

    monkeypatch.setattr(
        _handler_module("docs"),
        "sync_document_index",
        fail_sync_document_index,
    )

    response = client.post(
        "/api/docs/upload",
        headers=auth_headers,
        files={"file": ("demo.txt", b"hello world", "text/plain")},
        data={"category": "notes", "tags": "demo"},
    )
    assert response.status_code == 200, response.text
    assert "vector index unavailable" in response.json()["message"].lower()

    documents = app_module.db.list_documents(user_id="owner", include_archived=False)
    assert documents[0]["index_status"] == "unavailable"
    assert "chromadb is not installed" in documents[0]["index_error"].lower()


def test_document_delete_keeps_success_when_deindex_fails(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    uploads_dir = Path(app_module.legacy_main.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / "doc-delete.txt"
    file_path.write_text("delete me", encoding="utf-8")

    assert app_module.db.add_document(
        doc_id="doc-delete-side-effect",
        filename="doc-delete.txt",
        saved_filename="doc-delete.txt",
        file_size=9,
        uploaded_by="owner",
        status="reviewed",
    )

    monkeypatch.setattr(
        app_module.legacy_main,
        "delete_from_vector_db",
        lambda doc_id: (_ for _ in ()).throw(RuntimeError(f"cannot deindex {doc_id}")),
    )

    response = client.delete("/api/docs/doc-delete-side-effect", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert "de-index failed" in response.json()["message"].lower()
    assert app_module.db.get_document("doc-delete-side-effect") is None


def test_knowledge_create_keeps_success_when_indexing_fails(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    monkeypatch.setattr(
        _handler_module("knowledge"),
        "sync_knowledge_entry_index",
        lambda entry: (_ for _ in ()).throw(RuntimeError("kb index unavailable")),
    )

    response = client.post(
        "/api/knowledge/entries",
        headers=auth_headers,
        json={
            "title": "Safe create",
            "problem": "Problem",
            "root_cause": "",
            "solution": "Solution",
            "tags": "",
            "notes": "",
            "status": "draft",
            "source_type": "manual",
            "source_ref": "",
            "related_item_ids": [],
        },
    )
    assert response.status_code == 200, response.text
    assert "indexing failed" in response.json()["message"].lower()
    assert len(app_module.db.list_knowledge_entries(user_id="owner", include_archived=False)) == 1


def test_logbook_promote_keeps_success_when_indexing_fails(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    create_logbook = client.post(
        "/api/logbook/entries",
        headers=auth_headers,
        json={
            "title": "Promote me",
            "problem": "Problem",
            "root_cause": "",
            "solution": "Solution",
            "tags": "",
            "status": "draft",
            "source_type": "manual",
            "source_ref": "",
            "related_item_ids": [],
        },
    )
    assert create_logbook.status_code == 200, create_logbook.text
    logbook_id = app_module.db.list_logbook_entries(user_id="owner", include_archived=False)[0]["entry_id"]

    monkeypatch.setattr(
        _handler_module("logbook"),
        "sync_knowledge_entry_index",
        lambda entry: (_ for _ in ()).throw(RuntimeError("knowledge index down")),
    )
    monkeypatch.setattr(
        _handler_module("logbook"),
        "sync_logbook_entry_index",
        lambda entry: (_ for _ in ()).throw(RuntimeError("logbook index down")),
    )

    response = client.post(f"/api/logbook/entries/{logbook_id}/promote-to-knowledge", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert "indexing failed" in response.json()["message"].lower()
    assert response.json()["knowledge_entry_id"]


def test_photo_upload_keeps_success_when_indexing_fails(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    monkeypatch.setattr(app_module.legacy_main, "extract_text_from_image", lambda path: "")
    monkeypatch.setattr(
        _handler_module("photos"),
        "sync_photo_index",
        lambda photo: (_ for _ in ()).throw(RuntimeError("photo index down")),
    )

    if Image is None:
        png_bytes = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")
    else:
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color=(255, 255, 255)).save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
    response = client.post(
        "/api/photos/upload",
        headers=auth_headers,
        files={"file": ("demo.png", png_bytes, "image/png")},
        data={"tags": "demo", "description": "desc"},
    )
    assert response.status_code == 200, response.text
    assert "indexing failed" in response.json()["message"].lower()
    assert len(app_module.db.list_photos(user_id="owner", include_archived=False)) == 1


def test_saved_prompt_create_keeps_success_when_indexing_fails(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    monkeypatch.setattr(
        _handler_module("prompts"),
        "sync_prompt_index",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("prompt index down")),
    )

    response = client.post(
        "/api/prompts",
        headers=auth_headers,
        json={"title": "Prompt", "content": "Body", "tags": "demo"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["index_status"] == "failed"
    assert "prompt index down" in payload["index_error"].lower()

    prompts = app_module.db.list_saved_prompts(user_id="owner", limit=200)
    assert len(prompts) == 1


def test_saved_prompt_create_reports_unavailable_vector_index(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    monkeypatch.setattr(
        _handler_module("prompts"),
        "sync_prompt_index",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("Vector index unavailable: chromadb is not installed.")),
    )

    response = client.post(
        "/api/prompts",
        headers=auth_headers,
        json={"title": "Prompt", "content": "Body", "tags": "demo"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["index_status"] == "unavailable"
    assert "vector index unavailable" in payload["index_error"].lower()


def test_saved_prompt_delete_keeps_success_when_deindex_fails(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    created = client.post(
        "/api/prompts",
        headers=auth_headers,
        json={"title": "Prompt", "content": "Body", "tags": "demo"},
    )
    assert created.status_code == 200, created.text
    prompt_id = created.json()["id"]

    monkeypatch.setattr(
        app_module.legacy_main,
        "delete_from_kb_vector_db",
        lambda item_id: (_ for _ in ()).throw(RuntimeError(f"cannot remove {item_id}")),
    )

    deleted = client.delete(f"/api/prompts/{prompt_id}", headers=auth_headers)
    assert deleted.status_code == 200, deleted.text
    assert "de-index failed" in deleted.json()["message"].lower()
    prompt = app_module.db.get_saved_prompt(prompt_id)
    assert prompt is not None
    assert int(prompt["is_active"]) == 0
