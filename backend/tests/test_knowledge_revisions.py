import sys

from fastapi.testclient import TestClient


def test_knowledge_revision_flow(app_module, client: TestClient, auth_headers: dict[str, str]):
    # 1. Create a knowledge entry
    entry_data = {
        "title": "Initial Title",
        "problem": "Initial Problem",
        "solution": "Initial Solution",
        "status": "draft",
        "tags": "test",
    }
    resp = client.post("/api/knowledge/entries", json=entry_data, headers=auth_headers)
    assert resp.status_code == 200

    # Get the ID
    entries = client.get("/api/knowledge/entries", headers=auth_headers).json()
    entry_id = entries[0]["id"]

    # 2. Check initial revision
    resp = client.get(f"/api/knowledge/{entry_id}/revisions", headers=auth_headers)
    assert resp.status_code == 200
    revs = resp.json()
    assert len(revs) == 1
    assert revs[0]["version_number"] == 1
    assert revs[0]["title"] == "Initial Title"
    assert revs[0]["change_note"] == "Initial version"

    # 3. Update the entry
    update_data = {"title": "Updated Title", "change_note": "Changed title for testing"}
    resp = client.patch(f"/api/knowledge/entries/{entry_id}", json=update_data, headers=auth_headers)
    assert resp.status_code == 200

    # 4. Check revisions after update
    revs = client.get(f"/api/knowledge/{entry_id}/revisions", headers=auth_headers).json()
    assert len(revs) == 2
    assert revs[0]["version_number"] == 2
    assert revs[0]["title"] == "Initial Title"  # The revision is created BEFORE the update
    assert revs[0]["change_note"] == "Changed title for testing"

    # 5. Check diff
    rev_id = revs[0]["revision_id"]
    diff = client.get(f"/api/knowledge/{entry_id}/revisions/{rev_id}/diff", headers=auth_headers).json()
    assert len(diff["changed"]) > 0
    title_diff = next(d for d in diff["changed"] if d["field"] == "title")
    assert title_diff["old_value"] == "Initial Title"
    assert title_diff["new_value"] == "Updated Title"

    # 6. Restore
    resp = client.post(f"/api/knowledge/{entry_id}/revisions/{rev_id}/restore", headers=auth_headers)
    assert resp.status_code == 200

    # Verify current state is restored
    entries = client.get("/api/knowledge/entries", headers=auth_headers).json()
    restored_entry = next(e for e in entries if e["id"] == entry_id)
    assert restored_entry["title"] == "Initial Title"
    restored_row = app_module.db.get_knowledge_entry(entry_id)
    assert restored_row is not None
    assert restored_row["index_status"] == "indexed"
    search_content = app_module.db.get_search_content(f"knowledge:{entry_id}")
    assert search_content is not None
    assert "Initial Title" in search_content["content"]

    # Verify a new revision was created before restore
    revs = client.get(f"/api/knowledge/{entry_id}/revisions", headers=auth_headers).json()
    assert len(revs) == 3
    assert "Pre-restore snapshot" in revs[0]["change_note"]


def test_restore_revision_queues_repair_when_indexing_fails(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    created = client.post(
        "/api/knowledge/entries",
        json={
            "title": "Restore me",
            "problem": "Initial Problem",
            "solution": "Initial Solution",
            "status": "draft",
            "tags": "test",
        },
        headers=auth_headers,
    )
    assert created.status_code == 200

    entry_id = client.get("/api/knowledge/entries", headers=auth_headers).json()[0]["id"]
    updated = client.patch(
        f"/api/knowledge/entries/{entry_id}",
        json={"title": "Updated", "change_note": "update before restore"},
        headers=auth_headers,
    )
    assert updated.status_code == 200

    revisions = client.get(f"/api/knowledge/{entry_id}/revisions", headers=auth_headers).json()
    revision_id = revisions[0]["revision_id"]

    monkeypatch.setattr(
        sys.modules["app.api.handlers.knowledge"],
        "sync_knowledge_entry_index",
        lambda entry: (_ for _ in ()).throw(RuntimeError("restore index failed")),
    )

    restored = client.post(f"/api/knowledge/{entry_id}/revisions/{revision_id}/restore", headers=auth_headers)
    assert restored.status_code == 200, restored.text
    assert "indexing failed" in restored.json()["message"].lower()

    entry = app_module.db.get_knowledge_entry(entry_id)
    assert entry is not None
    assert entry["title"] == "Restore me"
    assert entry["index_status"] == "failed"
    assert "restore index failed" in entry["index_error"]
    repairs = app_module.db.list_index_repairs(owner_user_id="owner")
    assert any(row["item_id"] == f"knowledge:{entry_id}" and row["action"] == "index" for row in repairs)
