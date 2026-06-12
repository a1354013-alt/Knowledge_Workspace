from __future__ import annotations

import base64
from pathlib import Path

from fastapi.testclient import TestClient


def test_public_api_contract_smoke(client: TestClient, auth_headers: dict[str, str], app_module, monkeypatch):
    uploads_dir = Path(app_module.legacy_main.UPLOAD_DIR)
    photo_dir = Path(app_module.legacy_main.PHOTO_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    photo_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("app.api.handlers.photos.extract_text_from_image", lambda _path: "")

    login_me = client.get("/api/me", headers=auth_headers)
    assert login_me.status_code == 200, login_me.text
    assert login_me.json()["user_id"] == "owner"

    doc_upload = client.post(
        "/api/docs/upload",
        headers=auth_headers,
        files={"file": ("contract.txt", b"hello contract", "text/plain")},
        data={"category": "notes", "tags": "contract"},
    )
    assert doc_upload.status_code == 200, doc_upload.text
    doc_id = doc_upload.json()["id"]

    doc_list = client.get("/api/docs", headers=auth_headers)
    assert doc_list.status_code == 200, doc_list.text
    assert any(item["id"] == doc_id for item in doc_list.json())

    doc_download = client.get(f"/api/docs/{doc_id}/download", headers=auth_headers)
    assert doc_download.status_code == 200, doc_download.text
    assert doc_download.content == b"hello contract"

    doc_refs = client.get(f"/api/docs/{doc_id}/references", headers=auth_headers)
    assert doc_refs.status_code == 200, doc_refs.text
    assert "links" in doc_refs.json()

    png_bytes = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")
    photo_upload = client.post(
        "/api/photos/upload",
        headers=auth_headers,
        files={"file": ("contract.gif", png_bytes, "image/gif")},
        data={"tags": "contract", "description": "contract image"},
    )
    assert photo_upload.status_code == 200, photo_upload.text
    photo_id = photo_upload.json()["id"]

    photo_list = client.get("/api/photos", headers=auth_headers)
    assert photo_list.status_code == 200, photo_list.text
    assert any(item["id"] == photo_id for item in photo_list.json()["items"])

    photo_download = client.get(f"/api/photos/{photo_id}/download", headers=auth_headers)
    assert photo_download.status_code == 200, photo_download.text
    assert photo_download.content

    photo_refs = client.get(f"/api/photos/{photo_id}/references", headers=auth_headers)
    assert photo_refs.status_code == 200, photo_refs.text
    assert "links" in photo_refs.json()

    knowledge_create = client.post(
        "/api/knowledge/entries",
        headers=auth_headers,
        json={
            "title": "Contract knowledge",
            "problem": "Contract problem",
            "root_cause": "",
            "solution": "Contract solution",
            "tags": "contract",
            "notes": "",
            "status": "draft",
            "source_type": "manual",
            "source_ref": f"document:{doc_id}",
            "related_item_ids": [f"document:{doc_id}", f"photo:{photo_id}"],
        },
    )
    assert knowledge_create.status_code == 200, knowledge_create.text
    knowledge_id = app_module.db.list_knowledge_entries(user_id="owner", include_archived=False)[0]["entry_id"]

    knowledge_list = client.get("/api/knowledge/entries", headers=auth_headers)
    assert knowledge_list.status_code == 200, knowledge_list.text
    assert any(item["id"] == knowledge_id for item in knowledge_list.json()["items"])

    knowledge_update = client.patch(
        f"/api/knowledge/entries/{knowledge_id}",
        headers=auth_headers,
        json={"status": "reviewed", "tags": "contract,updated"},
    )
    assert knowledge_update.status_code == 200, knowledge_update.text

    logbook_create = client.post(
        "/api/logbook/entries",
        headers=auth_headers,
        json={
            "title": "Contract logbook",
            "problem": "Observed issue",
            "root_cause": "",
            "solution": "Investigated fix",
            "tags": "contract",
            "status": "draft",
            "source_type": "manual",
            "source_ref": f"photo:{photo_id}",
            "related_item_ids": [f"photo:{photo_id}"],
        },
    )
    assert logbook_create.status_code == 200, logbook_create.text
    logbook_id = app_module.db.list_logbook_entries(user_id="owner", include_archived=False)[0]["entry_id"]

    logbook_list = client.get("/api/logbook/entries", headers=auth_headers)
    assert logbook_list.status_code == 200, logbook_list.text
    assert any(item["id"] == logbook_id for item in logbook_list.json()["items"])

    promote = client.post(f"/api/logbook/entries/{logbook_id}/promote-to-knowledge", headers=auth_headers)
    assert promote.status_code == 200, promote.text
    assert promote.json()["knowledge_entry_id"]

    search = client.get("/api/search", headers=auth_headers, params={"q": "Contract", "types": "knowledge,logbook"})
    assert search.status_code == 200, search.text
    assert search.json()["items"]

    dashboard = client.get("/api/dashboard/health", headers=auth_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert "documents" in dashboard.json()

    autotest_capabilities = client.get("/api/autotest/capabilities", headers=auth_headers)
    assert autotest_capabilities.status_code == 200, autotest_capabilities.text
    assert "mode" in autotest_capabilities.json()

    autotest_runs = client.get("/api/autotest/runs", headers=auth_headers)
    assert autotest_runs.status_code == 200, autotest_runs.text
    assert isinstance(autotest_runs.json(), list)
