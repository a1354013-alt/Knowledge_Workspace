from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = ROOT / "docs" / "RUNBOOK.md"
FRONTEND_PACKAGE_JSON = ROOT / "frontend" / "package.json"


def test_runbook_exists_and_mentions_supported_toolchains():
    content = RUNBOOK_PATH.read_text(encoding="utf-8")
    assert "Python `3.11.x`" in content
    assert "Node `20 LTS`" in content
    assert "py -3.11 -m venv .venv" in content
    assert "npm ci" in content
    assert "trusted local workspace" in content
    assert "not a public sandbox" in content


def test_runbook_lists_main_verification_and_release_commands():
    content = RUNBOOK_PATH.read_text(encoding="utf-8")
    for command in (
        "python scripts/safe_compile.py",
        "python scripts/check_version_consistency.py",
        "python scripts/check_index_consistency.py",
        "pytest",
        "npm run lint",
        "npm run typecheck",
        "npm run test",
        "npm run build",
        "python scripts/export_openapi.py",
        "python scripts/generate_api_types.py",
        "python scripts/generate_api_types.py --check",
        "python scripts/package_release.py",
        "python scripts/verify_release.py",
    ):
        assert command in content


def test_runbook_frontend_commands_match_package_scripts():
    content = RUNBOOK_PATH.read_text(encoding="utf-8")
    package_data = json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))
    scripts = package_data["scripts"]
    for script_name in ("lint", "typecheck", "test", "build"):
        assert f"npm run {script_name}" in content
        assert script_name in scripts
