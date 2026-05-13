from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from app.context import settings

logger = logging.getLogger("knowledge_workspace")


def sanitize_path_for_report(path: Path, *, base_dir: Path) -> str:
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix() or "."
    except ValueError:
        return "<sanitized-path>"


def safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        logger.warning("Could not delete file %s because it is locked by the OS.", path)


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    max_files = int(settings.AUTOTEST_MAX_FILES)
    max_unzipped_bytes = int(settings.AUTOTEST_MAX_UNZIPPED_BYTES)
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) > max_files:
            raise ValueError("Zip contains too many files.")
        total_bytes = 0
        for member in members:
            if member.is_dir():
                continue
            total_bytes += int(getattr(member, "file_size", 0) or 0)
            if total_bytes > max_unzipped_bytes:
                raise ValueError("Zip expands beyond allowed size.")
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("Zip contains unsafe paths.")
            if ":" in member_path.parts[0] or str(member.filename).startswith(("\\\\", "//")):
                raise ValueError("Zip contains unsafe paths.")
            is_symlink = (member.external_attr >> 16) & 0o170000 == 0o120000
            if is_symlink:
                raise ValueError("Zip contains symlinks, which are not allowed.")
        archive.extractall(dest_dir)


