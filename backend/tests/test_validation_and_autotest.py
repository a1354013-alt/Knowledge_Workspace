from __future__ import annotations

import importlib
import io
import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_app(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUTOTEST_DIR", str(tmp_path / "autotest"))
    monkeypatch.setenv("AUTOTEST_MODE", "simulated")
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    main = importlib.import_module("app.main")
    main.delete_from_vector_db = lambda doc_id: True
    main.delete_from_kb_vector_db = lambda item_id: True
    return main


def auth_headers(client: TestClient, user_id: str = "owner", password: str = "OwnerPass123!") -> dict[str, str]:
    response = client.post("/api/login", json={"user_id": user_id, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def build_zip(*, marker_fail_step: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("package.json", '{"name":"demo","version":"1.0.0"}')
        archive.writestr("README.md", "# Demo")
        if marker_fail_step:
            archive.writestr(".autotest_fail_step", marker_fail_step)
    return buffer.getvalue()


def test_invalid_template_returns_400(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    response = client.post("/api/generate", headers=headers, json={"template_type": "nope", "inputs": {}})
    assert response.status_code == 400


def test_missing_field_returns_400(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = client.post("/api/login", json={"user_id": "owner"})
    assert response.status_code == 400


def test_autotest_run_success_creates_knowledge_draft(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    payload = build_zip()
    response = client.post(
        "/api/autotest/run",
        headers=headers,
        files={"file": ("demo.zip", payload, "application/zip")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "passed"
    assert data.get("execution_mode") in {"real", "simulated"}
    assert isinstance(data.get("project_type_detected"), str)
    assert isinstance(data.get("working_directory"), str)

    runs = client.get("/api/autotest/runs", headers=headers)
    assert runs.status_code == 200
    assert any(item["id"] == data["id"] for item in runs.json())

    knowledge = client.get("/api/knowledge/entries", headers=headers)
    assert knowledge.status_code == 200
    assert any(entry.get("status") == "draft" and "AutoTest Passed" in entry.get("title", "") for entry in knowledge.json())


def test_autotest_run_failure_creates_logbook_entry(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    payload = build_zip(marker_fail_step="test")
    response = client.post(
        "/api/autotest/run",
        headers=headers,
        files={"file": ("demo.zip", payload, "application/zip")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "failed"
    assert data.get("execution_mode") in {"real", "simulated"}
    assert isinstance(data.get("project_type_detected"), str)
    assert isinstance(data.get("working_directory"), str)

    logbook = client.get("/api/logbook/entries", headers=headers)
    assert logbook.status_code == 200
    entries = logbook.json()
    assert any("AutoTest Failed" in entry.get("title", "") and entry.get("run_id") == data["id"] for entry in entries)


def test_autotest_run_is_filtered_by_owner(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)

    # create a second user directly via DB (no public API for this)
    assert main.db.add_user("alice", "AlicePass123!", "Alice", "owner")

    owner_headers = auth_headers(client, user_id="owner", password="OwnerPass123!")
    alice_headers = auth_headers(client, user_id="alice", password="AlicePass123!")

    payload = build_zip()
    response = client.post(
        "/api/autotest/run",
        headers=owner_headers,
        files={"file": ("demo.zip", payload, "application/zip")},
    )
    assert response.status_code == 200, response.text
    run_id = response.json()["id"]

    owner_runs = client.get("/api/autotest/runs", headers=owner_headers)
    assert owner_runs.status_code == 200
    assert any(item["id"] == run_id for item in owner_runs.json())

    alice_runs = client.get("/api/autotest/runs", headers=alice_headers)
    assert alice_runs.status_code == 200
    assert all(item["id"] != run_id for item in alice_runs.json())

    alice_detail = client.get(f"/api/autotest/runs/{run_id}", headers=alice_headers)
    assert alice_detail.status_code == 404
