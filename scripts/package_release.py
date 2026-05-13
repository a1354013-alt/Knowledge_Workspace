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
    ".pytest-*",
    ".pytest-chroma",
    ".mypy_cache",
    "*.pyc",
    "*.pyo",
)
BACKEND_IGNORE_PATTERNS = COMMON_IGNORE_PATTERNS + (
    "uploads",
    "photos",
    "autotest_uploads",
    "chroma_db",
    "*.db",
    "*.sqlite3",
    "*.sqlite",
    "chroma.sqlite3",
    ".env",
)
FRONTEND_IGNORE_PATTERNS = COMMON_IGNORE_PATTERNS + (
    "node_modules",
    "dist",
    ".vite",
    "coverage",
)
DOCS_IGNORE_PATTERNS = COMMON_IGNORE_PATTERNS + (
    "node_modules",
)
ROOT_RELEASE_FILES = (
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


def copy_release_tree(root_dir: Path, release_root: Path, *, build_frontend: bool = True) -> None:
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
        subprocess.run([npm, "run", "build"], cwd=str(release_root / "frontend"), check=True)
        rm_tree(release_root / "frontend" / "node_modules")

    prune_release_tree(release_root)


def prune_release_tree(release_root: Path) -> None:
    # Exclusions (must not ship)
    rm_tree(release_root / ".git")
    rm_tree(release_root / "frontend" / "node_modules")
    rm_tree(release_root / "backend" / "uploads")
    rm_tree(release_root / "backend" / "photos")
    rm_tree(release_root / "backend" / "autotest_uploads")
    rm_tree(release_root / "backend" / "chroma_db")
    rm_tree(release_root / "backend" / ".pytest-chroma")
    rm_tree(release_root / "backend" / ".pytest-tmp")
    rm_tree(release_root / "backend" / "pytest_run")
    rm_tree(release_root / "backend" / "pytest_runtime")
    rm_tree(release_root / "backend" / "openapi_runtime")
    rm_tree(release_root / "backend" / ".pytest_cache")
    rm_tree(release_root / "frontend" / ".vite")

    # Remove env + sqlite artifacts anywhere
    for candidate in release_root.rglob(".env"):
        rm_tree(candidate)
    for candidate in release_root.rglob("*.db"):
        rm_tree(candidate)
    for pattern in ("*.sqlite3", "*.sqlite", "chroma.sqlite3"):
        for candidate in release_root.rglob(pattern):
            rm_tree(candidate)
    for pattern in (".pytest-*",):
        for candidate in release_root.rglob(pattern):
            rm_tree(candidate)

    # Remove caches
    for cache_dir in ("__pycache__", ".pytest_cache", ".mypy_cache"):
        for candidate in release_root.rglob(cache_dir):
            rm_tree(candidate)


def build_release_zip(release_root: Path, out_zip: Path) -> None:
    forbidden_dirs = {
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

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(release_root):
            dirs[:] = [d for d in dirs if d not in forbidden_dirs]
            for filename in files:
                if (
                    filename == ".env"
                    or filename.endswith(".db")
                    or filename.endswith(".sqlite3")
                    or filename.endswith(".sqlite")
                ):
                    continue
                path = Path(root) / filename
                rel = path.relative_to(release_root.parent).as_posix()
                zf.write(path, rel)


def validate_required_release_docs(release_root: Path) -> None:
    missing = [rel_path for rel_path in REQUIRED_RELEASE_DOCS if not (release_root / rel_path).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required release docs: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Package a clean release zip (cross-platform).")
    parser.add_argument("out_zip", nargs="?", default="knowledge_workspace_release.zip")
    parser.add_argument("--output", "-o", dest="output_dir", default="", help="Directory for the default release zip name.")
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
        copy_release_tree(root_dir, release_root)
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
