from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_app(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("PHOTO_DIR", str(tmp_path / "photos"))
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


def test_max_file_size_env_is_enforced(monkeypatch, tmp_path):
    monkeypatch.setenv("MAX_FILE_SIZE", "10")  # bytes
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    response = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("manual.txt", b"x" * 20, "text/plain")},
        data={"category": "notes", "tags": "demo"},
    )
    assert response.status_code == 413, response.text


def test_text_encoding_cp950_is_accepted(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    payload = "測試 cp950".encode("cp950")
    response = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("manual.txt", payload, "text/plain")},
        data={"category": "notes", "tags": "encoding"},
    )
    assert response.status_code == 200, response.text


def test_text_with_nul_is_rejected(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    response = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("manual.txt", b"abc\x00def", "text/plain")},
        data={"category": "notes", "tags": "binary"},
    )
    assert response.status_code == 400, response.text


def test_ocr_status_reports_unavailable_when_tesseract_not_runnable(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ENABLED", "1")
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    ocr_service = importlib.import_module("app.ocr_service")

    if getattr(ocr_service, "PYTESSERACT_AVAILABLE", False):
        monkeypatch.setattr(ocr_service, "_resolve_tesseract_cmd", lambda: "tesseract")

        def _boom():
            raise RuntimeError("tesseract missing")

        monkeypatch.setattr(ocr_service.pytesseract, "get_tesseract_version", _boom)

    response = client.get("/api/settings/ocr", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["available"] is False
    assert isinstance(payload.get("details"), str)
