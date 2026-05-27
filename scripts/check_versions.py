from __future__ import annotations

try:
    from .check_version_consistency import main, read_versions
except ImportError:  # pragma: no cover - script execution path
    from check_version_consistency import main, read_versions

__all__ = ["main", "read_versions"]


if __name__ == "__main__":
    raise SystemExit(main())
