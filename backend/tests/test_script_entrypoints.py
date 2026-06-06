from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_check_index_consistency_runs_from_repo_root(tmp_path: Path):
    command = [sys.executable, "scripts/check_index_consistency.py"]
    env = {
        **os.environ,
        "JWT_SECRET": "test-secret-test-secret-test-secret-1234",
        "DEFAULT_OWNER_PASSWORD": "OwnerPass123!",
        "DATABASE_PATH": str(tmp_path / "documents.db"),
        "UPLOAD_DIR": str(tmp_path / "uploads"),
        "PHOTO_DIR": str(tmp_path / "photos"),
        "CHROMA_DB_PATH": str(tmp_path / "chroma"),
        "AUTOTEST_DIR": str(tmp_path / "autotest"),
        "AUTOTEST_MODE": "simulated",
        "ALLOWED_ORIGINS": "http://localhost:5173",
    }
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"status": "ok"' in result.stdout


def test_wrapper_scripts_delegate_to_existing_modules():
    safe_compile = (ROOT / "scripts" / "safe_compile.py").read_text(encoding="utf-8")
    verify_release = (ROOT / "scripts" / "verify_release.py").read_text(encoding="utf-8")
    check_text_encoding = (ROOT / "scripts" / "check_text_encoding.py").read_text(
        encoding="utf-8"
    )

    assert "from safe_compileall import main" in safe_compile
    assert "from verify_release_zip import main" in verify_release
    assert "UTF-8 BOM detected" in check_text_encoding
    assert "SKIP_FILENAMES" in check_text_encoding
    assert '"package-lock.json"' in check_text_encoding
    assert '".env.example"' in check_text_encoding


def test_export_openapi_check_runs_from_repo_root(tmp_path: Path):
    python311 = ROOT / ".venv311" / "Scripts" / "python.exe"
    command = [str(python311 if python311.exists() else Path(sys.executable)), "scripts/export_openapi.py", "--check"]
    env = {
        **os.environ,
        "JWT_SECRET": "test-secret-test-secret-test-secret-1234",
        "DEFAULT_OWNER_PASSWORD": "OwnerPass123!",
        "DATABASE_PATH": str(tmp_path / "documents.db"),
        "UPLOAD_DIR": str(tmp_path / "uploads"),
        "PHOTO_DIR": str(tmp_path / "photos"),
        "CHROMA_DB_PATH": str(tmp_path / "chroma"),
        "AUTOTEST_DIR": str(tmp_path / "autotest"),
        "AUTOTEST_MODE": "simulated",
        "ALLOWED_ORIGINS": "http://localhost:5173",
    }
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "up to date" in result.stdout.lower()


def test_verify_release_zip_defaults_to_versioned_dist_zip(tmp_path: Path):
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    dist_dir = ROOT / "dist"
    zip_path = dist_dir / f"knowledge-workspace-{version}.zip"
    dist_dir.mkdir(parents=True, exist_ok=True)

    import zipfile

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("knowledge_workspace/.python-version", "3.11\n")
        archive.writestr("knowledge_workspace/.nvmrc", "20.19.0\n")
        archive.writestr("knowledge_workspace/.env.example", "JWT_SECRET=replace-me\n")
        archive.writestr("knowledge_workspace/README.md", "# README\n")
        archive.writestr("knowledge_workspace/SECURITY_MODEL.md", "# Security\n")
        archive.writestr("knowledge_workspace/API_CONTRACT.md", "# API\n")
        archive.writestr("knowledge_workspace/TESTING.md", "# Testing\n")
        archive.writestr("knowledge_workspace/RELEASE_CHECKLIST.md", "# Release\n")
        archive.writestr("knowledge_workspace/docs/AUTOTEST.md", "# AutoTest\n")
        archive.writestr("knowledge_workspace/docs/PORTFOLIO_CASE_STUDY.md", "# Case Study\n")
        archive.writestr("knowledge_workspace/docs/KNOWN_LIMITATIONS.md", "# Known Limitations\n")
        archive.writestr("knowledge_workspace/docs/RUNBOOK.md", "# Runbook\n")
        archive.writestr("knowledge_workspace/backend/app/main.py", "print('ok')\n")
        archive.writestr("knowledge_workspace/frontend/src/main.ts", "console.log('ok')\n")

    try:
        result = subprocess.run(
            [sys.executable, "scripts/verify_release_zip.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "verified" in result.stdout.lower()
    finally:
        zip_path.unlink(missing_ok=True)
