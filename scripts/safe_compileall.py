from __future__ import annotations

import argparse
import sys
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".venv311",
    "__pycache__",
    "env",
    "node_modules",
    "openapi_runtime",
    "pytest_run",
    "pytest_runtime",
    "venv",
}
EXCLUDED_PATH_PARTS = {
    "backend/.openapi-runtime",
    "backend/.pytest-chroma",
    "backend/.pytest-tmp",
    "backend/chroma_db",
    "backend/openapi_runtime",
    "backend/pytest_runtime",
    "backend/uploads",
    "frontend/dist",
    "frontend/node_modules",
}


def should_skip(path: Path) -> bool:
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    if any(
        relative == part or relative.startswith(f"{part}/")
        for part in EXCLUDED_PATH_PARTS
    ):
        return True
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def iter_python_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".py" else []

    files: list[Path] = []
    for candidate in path.rglob("*.py"):
        if should_skip(candidate):
            continue
        files.append(candidate)
    return sorted(files)


def compile_paths(paths: list[Path], quiet: bool) -> int:
    failures = 0
    for path in paths:
        try:
            with tokenize.open(path) as handle:
                source = handle.read()
            compile(source, str(path), "exec")
            if not quiet:
                print(f"OK {path.relative_to(ROOT)}")
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            failures += 1
            print(f"FAILED {path.relative_to(ROOT)}", file=sys.stderr)
            print(str(exc), file=sys.stderr)
    if failures:
        return 1
    if quiet:
        print(f"OK: compiled {len(paths)} Python files")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile Python files while skipping runtime and dependency directories."
    )
    parser.add_argument(
        "paths", nargs="*", default=["."], help="Files or directories to compile."
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print a summary unless a compile fails.",
    )
    args = parser.parse_args()

    python_files: list[Path] = []
    seen: set[Path] = set()
    for raw_path in args.paths:
        candidate = (
            (ROOT / raw_path).resolve()
            if not Path(raw_path).is_absolute()
            else Path(raw_path).resolve()
        )
        if not candidate.exists():
            print(f"Missing path: {raw_path}", file=sys.stderr)
            return 2
        for file_path in iter_python_files(candidate):
            if file_path in seen:
                continue
            seen.add(file_path)
            python_files.append(file_path)

    return compile_paths(sorted(python_files), quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
