from __future__ import annotations

import sys

sys.dont_write_bytecode = True

try:
    from .package_release import main
except ImportError:  # pragma: no cover - script execution path
    from package_release import main


if __name__ == "__main__":
    raise SystemExit(main())
