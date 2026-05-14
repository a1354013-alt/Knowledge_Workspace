from __future__ import annotations

import sys


def main() -> int:
    version = sys.version_info
    if (version.major, version.minor) != (3, 11):
        print(
            "Unsupported Python runtime. Knowledge Workspace backend requires Python 3.11.x; "
            "Python 3.12/3.13 are not officially supported until dependency constraints are updated.",
            file=sys.stderr,
        )
        print(f"Detected: Python {version.major}.{version.minor}.{version.micro}", file=sys.stderr)
        return 1
    print(f"OK: Python {version.major}.{version.minor}.{version.micro}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
