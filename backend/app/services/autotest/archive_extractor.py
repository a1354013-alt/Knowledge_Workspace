from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.context import settings
from app.services.autotest.archive import safe_extract_zip


@dataclass(frozen=True)
class ExtractedArchive:
    work_dir: Path
    extracted_dir: Path
    timeout_seconds: int


def prepare_extracted_archive(*, run_id: str) -> ExtractedArchive:
    autotest_dir = settings.AUTOTEST_DIR
    work_dir = autotest_dir / f"autotest-{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir = work_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    return ExtractedArchive(
        work_dir=work_dir,
        extracted_dir=extracted_dir,
        timeout_seconds=int(settings.AUTOTEST_TIMEOUT_SECONDS),
    )


def extract_uploaded_archive(*, zip_path: Path, extracted_dir: Path) -> None:
    safe_extract_zip(zip_path, extracted_dir)
