from __future__ import annotations

import importlib
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_main(monkeypatch, tmp_path):
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

    return importlib.import_module("app.main")


def test_node_build_test_lint_are_skipped_when_scripts_missing(monkeypatch, tmp_path):
    main = load_main(monkeypatch, tmp_path)
    working_dir = tmp_path / "nodeproj"
    working_dir.mkdir()
    (working_dir / "package.json").write_text('{"name":"demo","version":"1.0.0","scripts":{"test":"echo ok"}}', encoding="utf-8")

    should_build, reason_build = main._autotest_step_should_run(project_type="node", working_dir=working_dir, step_name="build")
    should_test, reason_test = main._autotest_step_should_run(project_type="node", working_dir=working_dir, step_name="test")
    should_lint, reason_lint = main._autotest_step_should_run(project_type="node", working_dir=working_dir, step_name="lint")

    assert should_build is False
    assert "Missing npm script" in reason_build
    assert should_test is True
    assert reason_test == ""
    assert should_lint is False
    assert "Missing npm script" in reason_lint


def test_python_tests_are_skipped_when_no_tests_detected(monkeypatch, tmp_path):
    main = load_main(monkeypatch, tmp_path)
    working_dir = tmp_path / "pyproj"
    working_dir.mkdir()
    (working_dir / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")

    should_test, reason = main._autotest_step_should_run(project_type="python", working_dir=working_dir, step_name="test")
    assert should_test is False
    assert "skipped" in reason.lower()

