from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_version_consistency.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("check_version_consistency", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_consistency_reads_all_expected_sources():
    module = _load_script_module()
    versions = module.read_versions()

    assert "VERSION" in versions
    assert "frontend/package.json" in versions
    assert "backend/pyproject.toml" in versions
    assert "pyproject.toml" in versions
    assert "docs/openapi.json" in versions
    assert len(set(versions.values())) == 1
