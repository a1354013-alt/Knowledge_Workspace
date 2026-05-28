from __future__ import annotations


def test_upload_document_reports_vector_degraded_as_success(app_module, client, auth_headers, monkeypatch):
    import importlib

    doc_handlers = importlib.import_module("app.api.handlers.docs")

    def fake_sync_document_index(document):
        item_id = f"document:{document['doc_id']}"
        app_module.db.upsert_search_content(
            item_id=item_id,
            item_type="document",
            owner_user_id=str(document.get("uploaded_by") or ""),
            title=str(document.get("filename") or "Document"),
            content="hello searchable text",
            is_active=1,
            updated_at=str(document.get("updated_at") or document.get("uploaded_at") or ""),
        )
        raise RuntimeError("Vector index unavailable: chromadb is not installed.")

    monkeypatch.setattr(doc_handlers, "_sync_document_index_impl", fake_sync_document_index)

    response = client.post(
        "/api/docs/upload",
        headers=auth_headers,
        files={"file": ("note.txt", b"hello searchable text", "text/plain")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["upload_status"] == "success"
    assert payload["full_text_index_status"] == "indexed"
    assert payload["vector_index_status"] == "degraded"
    assert payload["index_status"] == "unavailable"
    assert "full-text search" in payload["user_message"].lower()
    assert "indexing failed" not in payload["message"].lower()
