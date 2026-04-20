from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from .test_api_smoke import auth_headers, load_app


def test_source_ref_replacement_removes_old_derived_from(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    uploads_dir = Path(main.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    response = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("source.txt", b"hello", "text/plain")},
        data={"category": "notes", "tags": "demo"},
    )
    assert response.status_code == 200, response.text
    doc_id = response.json()["id"]

    create = client.post(
        "/api/knowledge/entries",
        headers=headers,
        json={
            "title": "Derived entry",
            "problem": "Problem",
            "root_cause": "",
            "solution": "Solution",
            "tags": "",
            "notes": "",
            "status": "draft",
            "source_type": "document-derived",
            "source_ref": f"document:{doc_id}",
            "related_item_ids": [],
        },
    )
    assert create.status_code == 200, create.text

    entries = client.get("/api/knowledge/entries", headers=headers).json()
    entry_id = next(row["id"] for row in entries if row["title"] == "Derived entry")

    links = client.get("/api/item-links", headers=headers, params={"item_id": f"knowledge:{entry_id}"})
    assert links.status_code == 200, links.text
    link_types = {link["link_type"] for link in links.json()["links"]}
    assert "derived_from" in link_types

    patch = client.patch(
        f"/api/knowledge/entries/{entry_id}",
        headers=headers,
        json={"source_ref": ""},
    )
    assert patch.status_code == 200, patch.text

    links2 = client.get("/api/item-links", headers=headers, params={"item_id": f"knowledge:{entry_id}"})
    assert links2.status_code == 200, links2.text
    derived = [
        link
        for link in links2.json()["links"]
        if link["link_type"] == "derived_from" and link["other_item"] and link["other_item"]["item_id"] == f"document:{doc_id}"
    ]
    assert derived == []
