from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

COMMON_IGNORE_PATTERNS = (
    "__pycache__",
    ".pytest_cache",
    ".pytest-tmp",
    "pytest_run",
    "pytest_runtime",
    "openapi_runtime",
    ".openapi-runtime",
    ".pytest-*",
    ".pytest-chroma",
    ".mypy_cache",
    ".ruff_cache",
    "*.pyc",
    "*.pyo",
    "*.db",
    "*.db-journal",
    "*.sqlite",
    "*.sqlite3",
    "*.sqlite-journal",
    "*.sqlite3-journal",
    ".env",
    ".env.*",
    "knowledge_workspace_release.zip",
    "release-validation.zip",
    "tmp_release*.zip",
    "tmp_release_verify*.zip",
    "tmp_release_ci*.zip",
    "ci_backend.*",
    "ci_documents.db",
    "ci_test.db",
)
BACKEND_IGNORE_PATTERNS = COMMON_IGNORE_PATTERNS + (
    "uploads",
    "photos",
    "autotest_uploads",
    "chroma_db",
    "chroma.sqlite3",
)
FRONTEND_IGNORE_PATTERNS = COMMON_IGNORE_PATTERNS + (
    "node_modules",
    "dist",
    ".vite",
    "coverage",
    "playwright-report",
    "test-results",
)
DOCS_IGNORE_PATTERNS = COMMON_IGNORE_PATTERNS + ("node_modules",)
FORBIDDEN_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".openapi-runtime",
    "openapi-runtime",
    "openapi_runtime",
    ".pytest_cache",
    ".pytest-chroma",
    ".pytest-tmp",
    ".ruff_cache",
    ".mypy_cache",
    ".vite",
    "pytest_run",
    "pytest_runtime",
    "uploads",
    "photos",
    "chroma_db",
    "autotest_uploads",
    "node_modules",
    "dist",
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
FORBIDDEN_FILE_SUFFIXES = (
    ".db",
    ".db-journal",
    ".sqlite",
    ".sqlite3",
    ".sqlite-journal",
    ".sqlite3-journal",
)
ROOT_RELEASE_FILES = (
    ".python-version",
    ".env.example",
    "VERSION",
    "start_backend.sh",
    "start_frontend.sh",
    "README.md",
    "QUICK_START.md",
    "DELIVERY_CHECKLIST.md",
    "CHANGELOG.md",
    "PROJECT_STRUCTURE.md",
    "ARCHITECTURE.md",
    "API_CONTRACT.md",
    "TESTING.md",
    "SECURITY_MODEL.md",
    "RELEASE_CHECKLIST.md",
)
REQUIRED_RELEASE_DOCS = (
    "docs/AUTOTEST.md",
    "docs/PORTFOLIO_CASE_STUDY.md",
    "docs/KNOWN_LIMITATIONS.md",
)


def rm_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or path.is_file():
        try:
            path.unlink()
        except FileNotFoundError:
            return
        return
    shutil.rmtree(path, ignore_errors=True)


def copy_release_tree(
    root_dir: Path, release_root: Path, *, build_frontend: bool = False
) -> None:
    shutil.copytree(
        root_dir / "backend",
        release_root / "backend",
        ignore=shutil.ignore_patterns(*BACKEND_IGNORE_PATTERNS),
    )
    shutil.copytree(
        root_dir / "frontend",
        release_root / "frontend",
        ignore=shutil.ignore_patterns(*FRONTEND_IGNORE_PATTERNS),
    )
    shutil.copytree(
        root_dir / "scripts",
        release_root / "scripts",
        ignore=shutil.ignore_patterns(*COMMON_IGNORE_PATTERNS, "node_modules"),
    )

    docs_dir = root_dir / "docs"
    if docs_dir.exists():
        shutil.copytree(
            docs_dir,
            release_root / "docs",
            ignore=shutil.ignore_patterns(*DOCS_IGNORE_PATTERNS),
        )

    for name in ROOT_RELEASE_FILES:
        source = root_dir / name
        if source.exists():
            shutil.copy2(source, release_root / name)

    if build_frontend:
        npm = "npm.cmd" if os.name == "nt" else "npm"
        subprocess.run([npm, "ci"], cwd=str(release_root / "frontend"), check=True)
        subprocess.run(
            [npm, "run", "build"], cwd=str(release_root / "frontend"), check=True
        )
        rm_tree(release_root / "frontend" / "node_modules")

    prune_release_tree(release_root)


def prune_release_tree(release_root: Path) -> None:
    # Exclusions (must not ship)
    for dir_name in FORBIDDEN_DIR_NAMES:
        for candidate in release_root.rglob(dir_name):
            rm_tree(candidate)

    # Remove env, database, journal, and pytest scratch artifacts anywhere.
    for candidate in release_root.rglob("*"):
        if not candidate.exists():
            continue
        name = candidate.name
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            rm_tree(candidate)
            continue
        if name.startswith(".pytest-"):
            rm_tree(candidate)
            continue
        if candidate.is_file() and name.endswith(FORBIDDEN_FILE_SUFFIXES):
            rm_tree(candidate)


def build_release_zip(release_root: Path, out_zip: Path) -> None:
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(release_root):
            dirs[:] = [
                d
                for d in dirs
                if d not in FORBIDDEN_DIR_NAMES and not d.startswith(".pytest-")
            ]
            for filename in files:
                if filename == ".env" or (
                    filename.startswith(".env.") and filename != ".env.example"
                ):
                    continue
                if filename in FORBIDDEN_FILE_NAMES:
                    continue
                if filename.endswith(FORBIDDEN_FILE_SUFFIXES):
                    continue
                path = Path(root) / filename
                rel = path.relative_to(release_root.parent).as_posix()
                zf.write(path, rel)


def validate_required_release_docs(release_root: Path) -> None:
    missing = [
        rel_path
        for rel_path in REQUIRED_RELEASE_DOCS
        if not (release_root / rel_path).exists()
    ]
    if missing:
        raise FileNotFoundError(f"Missing required release docs: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package a clean release zip (cross-platform)."
    )
    parser.add_argument("out_zip", nargs="?", default="knowledge_workspace_release.zip")
    parser.add_argument(
        "--output",
        "-o",
        dest="output_dir",
        default="",
        help="Directory for the default release zip name.",
    )
    parser.add_argument(
        "--build-frontend",
        action="store_true",
        help="Build frontend assets during staging even though the source release still excludes frontend/dist.",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[1]
    out_zip = Path(args.out_zip)
    if args.output_dir and args.out_zip == "knowledge_workspace_release.zip":
        out_zip = Path(args.output_dir) / "knowledge_workspace_release.zip"
    if not out_zip.is_absolute():
        out_zip = root_dir / out_zip

    stage_dir = Path(tempfile.mkdtemp(prefix="kw_release_"))
    try:
        release_root = stage_dir / "knowledge_workspace"
        release_root.mkdir(parents=True, exist_ok=True)
        copy_release_tree(root_dir, release_root, build_frontend=args.build_frontend)
        validate_required_release_docs(release_root)

        out_zip.parent.mkdir(parents=True, exist_ok=True)
        if out_zip.exists():
            out_zip.unlink()
        build_release_zip(release_root, out_zip)

        print(f"Wrote release zip: {out_zip}")
        return 0
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
