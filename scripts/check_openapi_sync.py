from __future__ import annotations

try:
    from .check_openapi_types_sync import main
except ImportError:  # pragma: no cover - script execution path
    from check_openapi_types_sync import main


if __name__ == "__main__":
    raise SystemExit(main())
