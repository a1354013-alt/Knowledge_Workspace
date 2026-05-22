from __future__ import annotations

import sys
from importlib import import_module, util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"


def test_runtime_dependency_manifests_include_httpx():
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    backend_pyproject_text = (BACKEND_DIR / "pyproject.toml").read_text(encoding="utf-8")
    requirements_text = (BACKEND_DIR / "requirements.txt").read_text(encoding="utf-8")
    requirements_dev_text = (BACKEND_DIR / "requirements-dev.txt").read_text(encoding="utf-8")

    assert '    "httpx==0.24.1",' in pyproject_text
    assert '    "httpx==0.24.1",' in backend_pyproject_text
    assert "httpx==0.24.1" in requirements_text
    assert "-r requirements.txt" in requirements_dev_text


def test_runtime_provider_and_app_imports_succeed(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
    monkeypatch.setenv("DATABASE_PATH", ":memory:")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("PHOTO_DIR", str(tmp_path / "photos"))
    monkeypatch.setenv("AUTOTEST_DIR", str(tmp_path / "autotest"))
    monkeypatch.setenv("AUTOTEST_MODE", "simulated")
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173")

    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    providers = import_module("app.llm.providers")
    factory = import_module("app.api.app_factory")
    main = import_module("app.main")

    assert providers.httpx is not None
    assert factory.create_app() is not None
    assert main.app is not None


def test_httpx_is_importable_in_runtime_environment():
    assert util.find_spec("httpx") is not None
