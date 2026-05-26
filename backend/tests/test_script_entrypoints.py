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

    assert "from safe_compileall import main" in safe_compile
    assert "from verify_release_zip import main" in verify_release
