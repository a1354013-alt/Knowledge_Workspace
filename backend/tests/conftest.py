from __future__ import annotations

import importlib
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_RUNTIME_DIR = BACKEND_DIR / "pytest_runtime"
TEST_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
BOOTSTRAP_DIR = TEST_RUNTIME_DIR / f"bootstrap-{uuid.uuid4().hex}"
BOOTSTRAP_DIR.mkdir(parents=True, exist_ok=True)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
os.environ.setdefault("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("UPLOAD_DIR", str(BOOTSTRAP_DIR / "uploads"))
os.environ.setdefault("PHOTO_DIR", str(BOOTSTRAP_DIR / "photos"))
os.environ.setdefault("AUTOTEST_DIR", str(BOOTSTRAP_DIR / "autotest"))
os.environ.setdefault("AUTOTEST_MODE", "simulated")
os.environ.setdefault("CHROMA_DB_PATH", str(BOOTSTRAP_DIR / "chroma"))
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")


def _reload_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
    monkeypatch.setenv("DATABASE_PATH", ":memory:")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("PHOTO_DIR", str(tmp_path / "photos"))
    monkeypatch.setenv("AUTOTEST_DIR", str(tmp_path / "autotest"))
    monkeypatch.setenv("AUTOTEST_MODE", "simulated")
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    main = importlib.import_module("app.main")
    main.legacy_main = importlib.import_module("app.api.legacy_main")
    main.delete_from_vector_db = lambda _doc_id: True
    main.delete_from_kb_vector_db = lambda _item_id: True
    return main


@pytest.fixture
def tmp_path() -> Path:
    path = TEST_RUNTIME_DIR / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def app_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    return _reload_app(monkeypatch, tmp_path)


@pytest.fixture
def client(app_module):
    return TestClient(app_module.app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/login", json={"user_id": "owner", "password": "OwnerPass123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
