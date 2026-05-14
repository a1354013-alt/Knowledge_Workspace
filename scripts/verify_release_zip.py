from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


FORBIDDEN_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "__pycache__",
    ".openapi-runtime",
    "openapi-runtime",
    "openapi_runtime",
    ".pytest_cache",
    ".pytest-chroma",
    ".pytest-tmp",
    ".ruff_cache",
    "pytest_run",
    "pytest_runtime",
    ".mypy_cache",
    ".vite",
    "uploads",
    "photos",
    "chroma_db",
    "autotest_uploads",
    "coverage",
    "playwright-report",
    "test-results",
}
FORBIDDEN_SUFFIXES = (
    ".db",
    ".db-journal",
    ".sqlite",
    ".sqlite3",
    ".sqlite-journal",
    ".sqlite3-journal",
)

REQUIRED = {
    "knowledge_workspace/.python-version",
    "knowledge_workspace/.env.example",
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
        basename = Path(name).name
        if basename == ".env" or (basename.startswith(".env.") and basename != ".env.example"):
            bad.append(name)
        if name.endswith(FORBIDDEN_SUFFIXES):
            bad.append(name)
    if bad:
        raise SystemExit("Forbidden paths in zip:\n" + "\n".join(sorted(set(bad))[:200]))

    missing = sorted(REQUIRED - names)
    if missing:
        raise SystemExit("Missing required release files:\n" + "\n".join(missing))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify release zip exclusions and required docs.")
    parser.add_argument("zip_path", nargs="?", default="knowledge_workspace_release.zip")
    args = parser.parse_args()
    verify(Path(args.zip_path))
    print(f"OK: verified {args.zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
