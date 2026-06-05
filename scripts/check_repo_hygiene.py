from __future__ import annotations

import sys

sys.dont_write_bytecode = True

try:
    from .verify_repo_hygiene import main
except ImportError:  # pragma: no cover - script execution path
    from verify_repo_hygiene import main


if __name__ == "__main__":
    raise SystemExit(main())
