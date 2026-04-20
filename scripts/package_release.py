from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Package a clean release zip (cross-platform).")
    parser.add_argument("out_zip", nargs="?", default="knowledge_workspace_release.zip")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[1]
    out_zip = Path(args.out_zip)
    if not out_zip.is_absolute():
        out_zip = root_dir / out_zip

    stage_dir = Path(tempfile.mkdtemp(prefix="kw_release_"))
    try:
        release_root = stage_dir / "knowledge_workspace"
        release_root.mkdir(parents=True, exist_ok=True)

        shutil.copytree(
            root_dir / "backend",
            release_root / "backend",
            ignore=shutil.ignore_patterns(
                "__pycache__",
                ".pytest_cache",
                ".pytest-tmp",
                "uploads",
                "photos",
                "autotest_uploads",
                "chroma_db",
                "*.db",
                ".env",
            ),
        )
        shutil.copytree(
            root_dir / "frontend",
            release_root / "frontend",
            ignore=shutil.ignore_patterns(
                "node_modules",
                "dist",
                ".vite",
                "coverage",
            ),
        )
        shutil.copytree(root_dir / "scripts", release_root / "scripts")

        for name in (
            "VERSION",
            "start_backend.sh",
            "start_frontend.sh",
            "README.md",
            "QUICK_START.md",
            "DELIVERY_CHECKLIST.md",
            "CHANGELOG.md",
            "PROJECT_STRUCTURE.md",
        ):
            shutil.copy2(root_dir / name, release_root / name)

        # Build frontend for the release package (keep dist, exclude node_modules).
        npm = "npm.cmd" if os.name == "nt" else "npm"
        subprocess.run([npm, "ci"], cwd=str(release_root / "frontend"), check=True)
        subprocess.run([npm, "run", "build"], cwd=str(release_root / "frontend"), check=True)
        rm_tree(release_root / "frontend" / "node_modules")

        # Exclusions (must not ship)
        rm_tree(release_root / ".git")
        rm_tree(release_root / "frontend" / "node_modules")
        rm_tree(release_root / "backend" / "uploads")
        rm_tree(release_root / "backend" / "photos")
        rm_tree(release_root / "backend" / "autotest_uploads")
        rm_tree(release_root / "backend" / "chroma_db")
        rm_tree(release_root / "backend" / ".pytest-tmp")
        rm_tree(release_root / "backend" / ".pytest_cache")
        rm_tree(release_root / "frontend" / ".vite")

        # Remove env + sqlite artifacts anywhere
        for candidate in release_root.rglob(".env"):
            rm_tree(candidate)
        for candidate in release_root.rglob("*.db"):
            rm_tree(candidate)

        # Remove caches
        for cache_dir in ("__pycache__", ".pytest_cache", ".mypy_cache"):
            for candidate in release_root.rglob(cache_dir):
                rm_tree(candidate)

        out_zip.parent.mkdir(parents=True, exist_ok=True)
        if out_zip.exists():
            out_zip.unlink()

        forbidden_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
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
                    if filename == ".env" or filename.endswith(".db"):
                        continue
                    path = Path(root) / filename
                    rel = path.relative_to(release_root.parent).as_posix()
                    zf.write(path, rel)

        print(f"Wrote release zip: {out_zip}")
        return 0
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
