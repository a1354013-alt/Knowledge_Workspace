from __future__ import annotations

import shutil
from pathlib import Path

from app.services.autotest.archive import safe_unlink


def cleanup_autotest_workspace(*, zip_path: Path, work_dir: Path) -> None:
    safe_unlink(zip_path)
    shutil.rmtree(work_dir, ignore_errors=True)
