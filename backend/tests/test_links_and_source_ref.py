from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from .test_api_smoke import auth_headers, load_app


def _create_document_for_user(main, *, doc_id: str, user_id: str, filename: str = "source.txt") -> None:
    assert main.db.add_document(
        doc_id=doc_id,
        filename=filename,
        saved_filename=f"{doc_id}.txt",
        file_size=5,
        uploaded_by=user_id,
        category="notes",
        tags="demo",
        status="reviewed",
        index_status="indexed",
        index_error="",
        indexed_at="2026-01-01T00:00:00+00:00",
    )


def _seed_other_user(main) -> None:
    assert main.db.add_user("other", "OtherPass123!", "Other User", "owner")


def test_source_ref_replacement_removes_old_derived_from(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    with TestClient(main.app) as client:
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
            if link["link_type"] == "derived_from"
            and link["other_item"]
            and link["other_item"]["item_id"] == f"document:{doc_id}"
        ]
        assert derived == []


def test_item_links_requires_owned_item(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    _seed_other_user(main)
    foreign_id = "foreign-knowledge"
    assert main.db.add_knowledge_entry(
        entry_id=foreign_id,
        title="Other note",
        status="draft",
        problem="Hidden",
        root_cause="",
        solution="Hidden",
        tags="",
        notes="",
        created_by="other",
    )

    with TestClient(main.app) as client:
        headers = auth_headers(client)

        owned_create = client.post(
            "/api/knowledge/entries",
            headers=headers,
            json={
                "title": "Owned entry",
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
        assert owned_create.status_code == 200, owned_create.text
        owned_entry = next(item["id"] for item in client.get("/api/knowledge/entries", headers=headers).json())

        ok = client.get("/api/item-links", headers=headers, params={"item_id": f"knowledge:{owned_entry}"})
        missing = client.get("/api/item-links", headers=headers, params={"item_id": "knowledge:missing"})
        foreign = client.get("/api/item-links", headers=headers, params={"item_id": f"knowledge:{foreign_id}"})

        assert ok.status_code == 200, ok.text
        assert missing.status_code == 404, missing.text
        assert foreign.status_code == 404, foreign.text


def test_item_links_filters_foreign_related_items_and_link_metadata(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    _seed_other_user(main)

    assert main.db.add_knowledge_entry(
        entry_id="foreign-knowledge",
        title="Other knowledge",
        status="draft",
        problem="Other",
        root_cause="",
        solution="Other",
        tags="",
        notes="",
        created_by="other",
    )
    _create_document_for_user(main, doc_id="owner-doc", user_id="owner")

    with TestClient(main.app) as client:
        headers = auth_headers(client)
        create = client.post(
            "/api/knowledge/entries",
            headers=headers,
            json={
                "title": "Owned entry",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "notes": "",
                "status": "draft",
                "source_type": "manual",
                "source_ref": "",
                "related_item_ids": ["document:owner-doc"],
            },
        )
        assert create.status_code == 200, create.text
        owned_entry = next(item["id"] for item in client.get("/api/knowledge/entries", headers=headers).json())

        assert main.db.add_link(f"knowledge:{owned_entry}", "knowledge:foreign-knowledge", link_type="references")

        links = client.get("/api/item-links", headers=headers, params={"item_id": f"knowledge:{owned_entry}"})
        assert links.status_code == 200, links.text

        payload = links.json()["links"]
        assert len(payload) == 1
        assert payload[0]["from_item_id"] == f"knowledge:{owned_entry}"
        assert payload[0]["to_item_id"] == "document:owner-doc"
        assert payload[0]["other_item"]["item_id"] == "document:owner-doc"
        assert all(
            link["other_item"]["item_id"] != "knowledge:foreign-knowledge" for link in payload if link["other_item"]
        )
        assert all(link["to_item_id"] != "knowledge:foreign-knowledge" for link in payload)
        assert all(link["from_item_id"] != "knowledge:foreign-knowledge" for link in payload)


def test_knowledge_create_rejects_foreign_related_item_ids(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    _seed_other_user(main)
    _create_document_for_user(main, doc_id="foreign-doc", user_id="other")

    with TestClient(main.app) as client:
        headers = auth_headers(client)
        response = client.post(
            "/api/knowledge/entries",
            headers=headers,
            json={
                "title": "Owned entry",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "notes": "",
                "status": "draft",
                "source_type": "manual",
                "source_ref": "",
                "related_item_ids": ["document:foreign-doc"],
            },
        )
        assert response.status_code == 400, response.text
        assert client.get("/api/knowledge/entries", headers=headers).json() == []


def test_knowledge_update_rejects_foreign_related_item_ids(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    _seed_other_user(main)
    _create_document_for_user(main, doc_id="owner-doc", user_id="owner")
    _create_document_for_user(main, doc_id="foreign-doc", user_id="other")

    with TestClient(main.app) as client:
        headers = auth_headers(client)
        create = client.post(
            "/api/knowledge/entries",
            headers=headers,
            json={
                "title": "Owned entry",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "notes": "",
                "status": "draft",
                "source_type": "manual",
                "source_ref": "",
                "related_item_ids": ["document:owner-doc"],
            },
        )
        assert create.status_code == 200, create.text
        entry = client.get("/api/knowledge/entries", headers=headers).json()[0]

        patch = client.patch(
            f"/api/knowledge/entries/{entry['id']}",
            headers=headers,
            json={"related_item_ids": ["document:foreign-doc"]},
        )
        assert patch.status_code == 400, patch.text

        links = client.get("/api/item-links", headers=headers, params={"item_id": f"knowledge:{entry['id']}"})
        assert links.status_code == 200, links.text
        assert [link["other_item"]["item_id"] for link in links.json()["links"] if link["other_item"]] == [
            "document:owner-doc"
        ]


def test_logbook_create_and_update_reject_foreign_related_item_ids(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    _seed_other_user(main)
    _create_document_for_user(main, doc_id="owner-doc", user_id="owner")
    _create_document_for_user(main, doc_id="foreign-doc", user_id="other")

    with TestClient(main.app) as client:
        headers = auth_headers(client)

        create_foreign = client.post(
            "/api/logbook/entries",
            headers=headers,
            json={
                "title": "Owned logbook",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "status": "draft",
                "source_type": "manual",
                "source_ref": "",
                "related_item_ids": ["document:foreign-doc"],
            },
        )
        assert create_foreign.status_code == 400, create_foreign.text
        assert client.get("/api/logbook/entries", headers=headers).json() == []

        create_ok = client.post(
            "/api/logbook/entries",
            headers=headers,
            json={
                "title": "Owned logbook",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "status": "draft",
                "source_type": "manual",
                "source_ref": "",
                "related_item_ids": ["document:owner-doc"],
            },
        )
        assert create_ok.status_code == 200, create_ok.text
        entry = client.get("/api/logbook/entries", headers=headers).json()[0]

        patch = client.patch(
            f"/api/logbook/entries/{entry['id']}",
            headers=headers,
            json={"related_item_ids": ["document:foreign-doc"]},
        )
        assert patch.status_code == 400, patch.text

        links = client.get("/api/item-links", headers=headers, params={"item_id": f"logbook:{entry['id']}"})
        assert links.status_code == 200, links.text
        assert [link["other_item"]["item_id"] for link in links.json()["links"] if link["other_item"]] == [
            "document:owner-doc"
        ]


def test_source_ref_to_foreign_item_is_rejected(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    _seed_other_user(main)
    _create_document_for_user(main, doc_id="foreign-doc", user_id="other")
    _create_document_for_user(main, doc_id="owner-doc", user_id="owner")

    with TestClient(main.app) as client:
        headers = auth_headers(client)

        create = client.post(
            "/api/knowledge/entries",
            headers=headers,
            json={
                "title": "Bad source ref",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "notes": "",
                "status": "draft",
                "source_type": "document-derived",
                "source_ref": "document:foreign-doc",
                "related_item_ids": [],
            },
        )
        assert create.status_code == 400, create.text

        good = client.post(
            "/api/logbook/entries",
            headers=headers,
            json={
                "title": "Good logbook",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "status": "draft",
                "source_type": "document-derived",
                "source_ref": "document:owner-doc",
                "related_item_ids": [],
            },
        )
        assert good.status_code == 200, good.text
        entry = client.get("/api/logbook/entries", headers=headers).json()[0]

        patch = client.patch(
            f"/api/logbook/entries/{entry['id']}",
            headers=headers,
            json={"source_ref": "document:foreign-doc"},
        )
        assert patch.status_code == 400, patch.text

        links = client.get("/api/item-links", headers=headers, params={"item_id": f"logbook:{entry['id']}"})
        assert links.status_code == 200, links.text
        assert [link["other_item"]["item_id"] for link in links.json()["links"] if link["other_item"]] == [
            "document:owner-doc"
        ]


def test_deleting_document_cleans_up_item_links(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    _create_document_for_user(main, doc_id="doc-cleanup", user_id="owner")

    with TestClient(main.app) as client:
        headers = auth_headers(client)
        create = client.post(
            "/api/knowledge/entries",
            headers=headers,
            json={
                "title": "Linked note",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "notes": "",
                "status": "draft",
                "source_type": "manual",
                "source_ref": "",
                "related_item_ids": ["document:doc-cleanup"],
            },
        )
        assert create.status_code == 200, create.text
        entry = client.get("/api/knowledge/entries", headers=headers).json()[0]

        deleted = client.delete("/api/docs/doc-cleanup", headers=headers)
        assert deleted.status_code == 200, deleted.text

        links = client.get("/api/item-links", headers=headers, params={"item_id": f"knowledge:{entry['id']}"})
        assert links.status_code == 200, links.text
        assert links.json()["links"] == []


def test_deleting_logbook_cleans_up_item_links(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    _create_document_for_user(main, doc_id="doc-linked", user_id="owner")

    with TestClient(main.app) as client:
        headers = auth_headers(client)
        create = client.post(
            "/api/logbook/entries",
            headers=headers,
            json={
                "title": "Linked logbook",
                "problem": "Problem",
                "root_cause": "",
                "solution": "Solution",
                "tags": "",
                "status": "draft",
                "source_type": "manual",
                "source_ref": "",
                "related_item_ids": ["document:doc-linked"],
            },
        )
        assert create.status_code == 200, create.text
        entry = client.get("/api/logbook/entries", headers=headers).json()[0]

        deleted = client.delete(f"/api/logbook/entries/{entry['id']}", headers=headers)
        assert deleted.status_code == 200, deleted.text

        links = client.get("/api/item-links", headers=headers, params={"item_id": "document:doc-linked"})
        assert links.status_code == 200, links.text
        assert links.json()["links"] == []
