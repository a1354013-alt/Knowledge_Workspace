from __future__ import annotations

import fnmatch
import sys
from pathlib import Path


def _detect_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "scripts").exists() and (cwd / "backend").exists() and (cwd / "frontend").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _detect_root()
FORBIDDEN_DIRS = {
    "ci_chroma",
    ".chroma",
    "chroma",
    "runtime",
    "index",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
}
FORBIDDEN_PATH_PATTERNS = (
    "temp",
    "temp/**",
    "temp/merge-conflict-backup",
    "temp/merge-conflict-backup/**",
    "*.patch",
    "*.rej",
    "*.orig",
    "data/index",
    "ci_uploads",
    "ci_photos",
    "ci_autotest",
    "knowledge_workspace_release.zip",
    "test_release.zip",
    "ci_*.db",
    "ci_*.sqlite",
    "ci_*.sqlite3",
    "ci_*.log",
    "ci_*.pid",
    "*.sqlite-shm",
    "*.sqlite-wal",
)
IGNORE_PREFIXES = {".git", ".venv", ".venv", ".venv_clean"}
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}
TEXT_FILENAMES = {".gitattributes", ".gitignore", ".nvmrc", ".python-version", "Makefile", "VERSION"}


def _is_ignored_path(relative: Path) -> bool:
    if not relative.parts:
        return True
    if relative.parts[0] in IGNORE_PREFIXES:
        return True
    if len(relative.parts) >= 2 and relative.parts[:2] == ("frontend", "node_modules"):
        return True
    if len(relative.parts) >= 2 and relative.parts[:2] == ("backend", ".pytest-tmp"):
        return True
    return False


def _is_forbidden_dir(path: Path) -> bool:
    name = path.name
    if name in FORBIDDEN_DIRS:
        if name != "index":
            return True
        parent = path.parent.as_posix().lower()
        return parent.endswith("data")
    return False


def _matches_forbidden_pattern(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in FORBIDDEN_PATH_PATTERNS)


def _should_scan_text(path: Path) -> bool:
    return path.name in TEXT_FILENAMES or path.suffix.lower() in TEXT_SUFFIXES


def _find_conflict_markers(path: Path) -> list[str]:
    if not _should_scan_text(path):
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    relative = path.relative_to(ROOT).as_posix()
    issues: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped in CONFLICT_MARKERS or any(stripped.startswith(marker + " ") for marker in CONFLICT_MARKERS):
            issues.append(f"{relative}:{line_number}: merge conflict marker '{stripped}'")
    return issues


def main() -> int:
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if _is_ignored_path(relative):
            continue
        if path.is_dir() and _is_forbidden_dir(path):
            violations.append(relative.as_posix() + "/")
            continue
        if _matches_forbidden_pattern(relative.as_posix()):
            violations.append(relative.as_posix())
            continue
        if path.is_file():
            violations.extend(_find_conflict_markers(path))

    if violations:
        print("Forbidden repo artifacts detected:", file=sys.stderr)
        for item in sorted(set(violations)):
            print(f"- {item}", file=sys.stderr)
        return 1

    print("OK: repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
