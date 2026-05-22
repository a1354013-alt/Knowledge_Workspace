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


def _is_unsafe_zip_member_name(name: str) -> bool:
    normalized = str(name or "").replace("\\", "/").strip()
    if not normalized:
        return True
    if normalized.startswith(("/", "\\")):
        return True
    path = Path(normalized)
    if path.is_absolute() or ".." in path.parts:
        return True
    first_part = path.parts[0] if path.parts else ""
    if first_part.startswith("\\\\") or first_part.startswith("//"):
        return True
    if ":" in first_part:
        return True
    return False


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
            if _is_unsafe_zip_member_name(member.filename):
                raise ValueError("Zip contains unsafe paths.")
            is_symlink = (member.external_attr >> 16) & 0o170000 == 0o120000
            if is_symlink:
                raise ValueError("Zip contains symlinks, which are not allowed.")
        dest_root = dest_dir.resolve()
        for member in members:
            if _is_unsafe_zip_member_name(member.filename):
                raise ValueError("Zip contains unsafe paths.")
            target_path = (dest_dir / member.filename).resolve()
            try:
                target_path.relative_to(dest_root)
            except ValueError as exc:
                raise ValueError("Zip contains unsafe paths.") from exc
        archive.extractall(dest_dir)


