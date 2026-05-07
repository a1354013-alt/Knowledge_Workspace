from __future__ import annotations

import sys
import zipfile
from importlib import import_module
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_release_package_includes_docs_and_excludes_cache(tmp_path: Path):
    package_release = import_module("scripts.package_release")
    root_dir = tmp_path / "workspace"
    release_root = tmp_path / "stage" / "knowledge_workspace"

    (root_dir / "backend" / "app").mkdir(parents=True)
    (root_dir / "frontend" / "src").mkdir(parents=True)
    (root_dir / "scripts").mkdir(parents=True)
    (root_dir / "docs").mkdir(parents=True)

    (root_dir / "backend" / "app" / "__pycache__").mkdir(parents=True)
    (root_dir / "frontend" / "node_modules").mkdir(parents=True)
    (root_dir / "scripts" / "__pycache__").mkdir(parents=True)

    (root_dir / "backend" / "app" / "main.py").write_text("print('backend')\n", encoding="utf-8")
    (root_dir / "backend" / "app" / "__pycache__" / "main.pyc").write_text("cache", encoding="utf-8")
    (root_dir / "frontend" / "src" / "main.ts").write_text("console.log('frontend')\n", encoding="utf-8")
    (root_dir / "frontend" / "node_modules" / "leftpad.js").write_text("module.exports = {}\n", encoding="utf-8")
    (root_dir / "scripts" / "helper.py").write_text("print('helper')\n", encoding="utf-8")
    (root_dir / "scripts" / "__pycache__" / "helper.pyc").write_text("cache", encoding="utf-8")
    (root_dir / "docs" / "AUTOTEST.md").write_text("# AutoTest\n", encoding="utf-8")
    (root_dir / "docs" / "PORTFOLIO_CASE_STUDY.md").write_text("# Case Study\n", encoding="utf-8")
    (root_dir / "README.md").write_text(
        "See [AutoTest](docs/AUTOTEST.md) and [Case Study](docs/PORTFOLIO_CASE_STUDY.md).\n",
        encoding="utf-8",
    )

    for name in (
        "VERSION",
        "start_backend.sh",
        "start_frontend.sh",
        "QUICK_START.md",
        "DELIVERY_CHECKLIST.md",
        "CHANGELOG.md",
        "PROJECT_STRUCTURE.md",
    ):
        (root_dir / name).write_text(f"{name}\n", encoding="utf-8")

    package_release.copy_release_tree(root_dir, release_root, build_frontend=False)

    assert (release_root / "docs" / "AUTOTEST.md").exists()
    assert (release_root / "docs" / "PORTFOLIO_CASE_STUDY.md").exists()
    assert not (release_root / "frontend" / "node_modules").exists()
    assert not list(release_root.rglob("__pycache__"))

    out_zip = tmp_path / "knowledge_workspace_release.zip"
    package_release.build_release_zip(release_root, out_zip)

    with zipfile.ZipFile(out_zip) as archive:
        names = set(archive.namelist())
        readme = archive.read("knowledge_workspace/README.md").decode("utf-8")

    assert "knowledge_workspace/docs/AUTOTEST.md" in names
    assert "knowledge_workspace/docs/PORTFOLIO_CASE_STUDY.md" in names
    assert "C:\\" not in readme
    assert "D:\\" not in readme
    assert "docs/AUTOTEST.md" in readme
    assert "docs/PORTFOLIO_CASE_STUDY.md" in readme
