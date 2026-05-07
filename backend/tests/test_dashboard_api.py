from __future__ import annotations

from fastapi.testclient import TestClient


def test_dashboard_health_no_data(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/dashboard/health", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["knowledge"]["total"] == 0
    assert data["logbook"]["total"] == 0
    assert data["logbook"]["promoted_to_knowledge"] == 0
    assert data["autotest"]["total_runs"] == 0
    assert data["documents"]["indexed"] == 0
    assert data["documents"]["pending"] == 0
    assert data["documents"]["failed_documents"] == 0
    assert data["documents"]["archived_documents"] == 0


def test_dashboard_promote_counts_canonical_logbook_to_knowledge_link(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    create_logbook = client.post(
        "/api/logbook/entries",
        headers=auth_headers,
        json={
            "title": "Promotion source",
            "problem": "Problem",
            "root_cause": "",
            "solution": "Solution",
            "tags": "demo",
            "status": "reviewed",
            "source_type": "manual",
            "source_ref": "",
            "related_item_ids": [],
        },
    )
    assert create_logbook.status_code == 200, create_logbook.text

    entries = client.get("/api/logbook/entries", headers=auth_headers)
    assert entries.status_code == 200, entries.text
    entry_id = entries.json()[0]["id"]

    promote = client.post(f"/api/logbook/entries/{entry_id}/promote-to-knowledge", headers=auth_headers)
    assert promote.status_code == 200, promote.text

    dashboard = client.get("/api/dashboard/health", headers=auth_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["logbook"]["promoted_to_knowledge"] == 1

    links = app_module.db.list_links(f"logbook:{entry_id}")
    produced = [
        link for link in links if link["from_item_id"] == f"logbook:{entry_id}" and link["link_type"] == "produced"
    ]
    assert len(produced) == 1
    assert produced[0]["to_item_id"].startswith("knowledge:")
    knowledge_id = produced[0]["to_item_id"].split(":", maxsplit=1)[1]

    reverse_links = app_module.db.list_links(f"knowledge:{knowledge_id}")
    derived_from = [
        link
        for link in reverse_links
        if link["from_item_id"] == f"knowledge:{knowledge_id}"
        and link["to_item_id"] == f"logbook:{entry_id}"
        and link["link_type"] == "derived_from"
    ]
    assert len(derived_from) == 1

    dashboard_after_reverse = client.get("/api/dashboard/health", headers=auth_headers)
    assert dashboard_after_reverse.status_code == 200, dashboard_after_reverse.text
    assert dashboard_after_reverse.json()["logbook"]["promoted_to_knowledge"] == 1


def test_dashboard_document_index_metrics_are_based_on_index_status(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    db = app_module.db
    assert db.add_document(
        doc_id="doc-indexed",
        filename="indexed.txt",
        saved_filename="indexed.txt",
        file_size=1,
        uploaded_by="owner",
        status="reviewed",
        index_status="indexed",
        indexed_at="2026-05-07T00:00:00+00:00",
    )
    assert db.add_document(
        doc_id="doc-failed",
        filename="failed.txt",
        saved_filename="failed.txt",
        file_size=1,
        uploaded_by="owner",
        status="reviewed",
        index_status="failed",
        index_error="vector db unavailable",
    )
    assert db.add_document(
        doc_id="doc-pending",
        filename="pending.txt",
        saved_filename="pending.txt",
        file_size=1,
        uploaded_by="owner",
        status="reviewed",
        index_status="pending",
    )

    response = client.get("/api/dashboard/health", headers=auth_headers)
    assert response.status_code == 200, response.text
    documents = response.json()["documents"]
    assert documents["indexed"] == 1
    assert documents["failed_documents"] == 1
    assert documents["pending"] == 1
