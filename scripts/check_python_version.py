from __future__ import annotations

import sys

SUPPORTED_VERSION = (3, 11)


def main() -> int:
    version = sys.version_info
    if (version.major, version.minor) != SUPPORTED_VERSION:
        detected = f"Python {version.major}.{version.minor}.{version.micro}"
        print(
            "Unsupported Python runtime for Knowledge Workspace.",
            file=sys.stderr,
        )
        print(
            "This project only supports Python 3.11.x for backend validation.",
            file=sys.stderr,
        )
        print(f"Detected: {detected}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Create a Python 3.11 virtual environment and re-run the checks:",
            file=sys.stderr,
        )
        print("  py -3.11 -m venv .venv", file=sys.stderr)
        print(r"  .\.venv\Scripts\Activate.ps1", file=sys.stderr)
        print("  python -m pip install -U pip", file=sys.stderr)
        print('  pip install -e ".[dev]"', file=sys.stderr)
        print("  python scripts/check_python_version.py", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "If you are using Python 3.12/3.13, the failure is a version guard, not a broken dependency install.",
            file=sys.stderr,
        )
        return 1
    print(f"OK: Python {version.major}.{version.minor}.{version.micro}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
