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
    assert "skipped" not in data["autotest"]
    assert data["documents"]["indexed"] == 0
    assert data["documents"]["pending"] == 0
    assert data["documents"]["failed_documents"] == 0
    assert data["documents"]["archived_documents"] == 0
    assert "qa_count" not in data["recent_activity"]


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
    entry_id = entries.json()["items"][0]["id"]

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
    assert derived_from == []


def test_item_links_keeps_legacy_reverse_promote_link_readable(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    assert app_module.db.add_logbook_entry(
        entry_id="log-legacy",
        title="Legacy logbook",
        status="reviewed",
        run_id="",
        problem="Problem",
        root_cause="",
        solution="Solution",
        tags="legacy",
        source_type="manual",
        source_ref="",
        created_by="owner",
    )
    assert app_module.db.add_knowledge_entry(
        entry_id="kb-legacy",
        title="Legacy knowledge",
        status="verified",
        problem="Problem",
        root_cause="",
        solution="Solution",
        tags="legacy",
        notes="",
        created_by="owner",
    )
    assert app_module.db.add_link("knowledge:kb-legacy", "logbook:log-legacy", "derived_from")

    response = client.get("/api/item-links", headers=auth_headers, params={"item_id": "logbook:log-legacy"})
    assert response.status_code == 200, response.text
    assert any(link["other_item"]["item_id"] == "knowledge:kb-legacy" for link in response.json()["links"])


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


def test_dashboard_document_metrics_do_not_count_archived_items_as_pending(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    db = app_module.db
    assert db.add_document(
        doc_id="doc-archived",
        filename="archived.txt",
        saved_filename="archived.txt",
        file_size=1,
        uploaded_by="owner",
        status="archived",
        index_status="excluded",
    )

    response = client.get("/api/dashboard/health", headers=auth_headers)
    assert response.status_code == 200, response.text
    documents = response.json()["documents"]
    assert documents["pending"] == 0
    assert documents["failed_documents"] == 0
    assert documents["archived_documents"] >= 1
