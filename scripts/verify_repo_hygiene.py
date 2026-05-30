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
IGNORE_PREFIXES = {".git"}


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


def main() -> int:
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if not relative.parts:
            continue
        if relative.parts[0] in IGNORE_PREFIXES:
            continue
        if path.is_dir() and _is_forbidden_dir(path):
            violations.append(relative.as_posix() + "/")
            continue
        if _matches_forbidden_pattern(relative.as_posix()):
            violations.append(relative.as_posix())

    if violations:
        print("Forbidden repo artifacts detected:", file=sys.stderr)
        for item in sorted(set(violations)):
            print(f"- {item}", file=sys.stderr)
        return 1

    print("OK: repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
