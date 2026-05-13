from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


FORBIDDEN_PARTS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".pytest-chroma",
    "pytest_run",
    "pytest_runtime",
    "openapi_runtime",
    ".mypy_cache",
    ".vite",
    "uploads",
    "photos",
    "chroma_db",
    "autotest_uploads",
}

REQUIRED = {
    "knowledge_workspace/README.md",
    "knowledge_workspace/SECURITY_MODEL.md",
    "knowledge_workspace/API_CONTRACT.md",
    "knowledge_workspace/TESTING.md",
    "knowledge_workspace/RELEASE_CHECKLIST.md",
    "knowledge_workspace/docs/AUTOTEST.md",
    "knowledge_workspace/docs/PORTFOLIO_CASE_STUDY.md",
    "knowledge_workspace/docs/KNOWN_LIMITATIONS.md",
}


def verify(zip_path: Path) -> None:
    if not zip_path.exists():
        raise FileNotFoundError(f"Release zip not found: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())

    bad: list[str] = []
    for name in names:
        parts = {part for part in name.split("/") if part}
        if parts & FORBIDDEN_PARTS:
            bad.append(name)
        if name.endswith((".db", ".sqlite", ".sqlite3")) or name.endswith("/.env") or name.endswith(".env"):
            bad.append(name)
    if bad:
        raise SystemExit("Forbidden paths in zip:\n" + "\n".join(sorted(set(bad))[:200]))

    missing = sorted(REQUIRED - names)
    if missing:
        raise SystemExit("Missing required release files:\n" + "\n".join(missing))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify release zip exclusions and required docs.")
    parser.add_argument("zip_path")
    args = parser.parse_args()
    verify(Path(args.zip_path))
    print(f"OK: verified {args.zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
