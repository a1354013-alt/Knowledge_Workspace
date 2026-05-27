from __future__ import annotations

import argparse
import glob
from pathlib import Path

try:
    from .verify_release_zip import verify
except ImportError:  # pragma: no cover - script execution path
    from verify_release_zip import verify


def _resolve_zip_path(raw_path: str) -> Path:
    value = str(raw_path or "").strip()
    candidate = Path(value)
    if candidate.exists():
        return candidate

    matches = sorted(Path(path) for path in glob.glob(value))
    if not matches:
        raise SystemExit(f"Release package not found: {value}")
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in matches)
        raise SystemExit(f"Multiple release packages matched '{value}': {joined}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a packaged release zip.")
    parser.add_argument("zip_path", nargs="?", default="dist/knowledge-workspace-*.zip")
    args = parser.parse_args()
    verify(_resolve_zip_path(args.zip_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
