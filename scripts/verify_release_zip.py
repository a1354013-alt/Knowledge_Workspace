from __future__ import annotations

import argparse
import shutil
import tempfile
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
    "ci_chroma",
    "ci_uploads",
    "ci_photos",
    "ci_autotest",
}
FORBIDDEN_FILE_NAMES = {
    "ci_documents.db",
    "ci_test.db",
    "knowledge_workspace_release.zip",
    "release-validation.zip",
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
    "knowledge_workspace/docs/RUNBOOK.md",
}


def _default_release_zip(root_dir: Path) -> Path:
    version = (root_dir / "VERSION").read_text(encoding="utf-8").strip() or "unknown"
    return root_dir / "dist" / f"knowledge-workspace-{version}.zip"


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
        if basename == ".env" or (
            basename.startswith(".env.") and basename != ".env.example"
        ):
            bad.append(name)
        if basename in FORBIDDEN_FILE_NAMES:
            bad.append(name)
        if name.endswith(FORBIDDEN_SUFFIXES):
            bad.append(name)
        if any(part.endswith(".egg-info") or part.endswith(".dist-info") for part in parts):
            bad.append(name)
    if bad:
        raise SystemExit(
            "Forbidden paths in zip:\n" + "\n".join(sorted(set(bad))[:200])
        )

    missing = sorted(REQUIRED - names)
    if missing:
        raise SystemExit("Missing required release files:\n" + "\n".join(missing))

    extract_root = Path(tempfile.mkdtemp(prefix="kw_release_verify_"))
    try:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_root)
        extracted_release = extract_root / "knowledge_workspace"
        if not extracted_release.exists():
            raise SystemExit("Extracted release root is missing.")
        for forbidden in FORBIDDEN_PARTS:
            if list(extracted_release.rglob(forbidden)):
                raise SystemExit(f"Forbidden extracted path found: {forbidden}")
        for candidate in extracted_release.rglob("*"):
            name = candidate.name
            if name.endswith(".egg-info") or name.endswith(".dist-info"):
                raise SystemExit(f"Forbidden extracted packaging artifact found: {candidate}")
            if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
                raise SystemExit(f"Forbidden extracted secret file found: {candidate}")
            if name in FORBIDDEN_FILE_NAMES:
                raise SystemExit(f"Forbidden extracted runtime file found: {candidate}")
            if candidate.is_file() and any(
                name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES
            ):
                raise SystemExit(f"Forbidden extracted database found: {candidate}")
    finally:
        shutil.rmtree(extract_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify release zip exclusions and required docs."
    )
    parser.add_argument("zip_path", nargs="?", default="")
    args = parser.parse_args()
    root_dir = Path(__file__).resolve().parents[1]
    zip_path = _default_release_zip(root_dir) if not args.zip_path else Path(args.zip_path)
    if not zip_path.is_absolute():
        zip_path = root_dir / zip_path
    verify(zip_path)
    print(f"OK: verified {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
