from __future__ import annotations

try:
    from .generate_api_types import OPENAPI_PATH, OUT_PATH, generate, type_to_ts
except ImportError:  # pragma: no cover - script execution path
    from generate_api_types import OPENAPI_PATH, OUT_PATH, generate, type_to_ts

__all__ = ["generate", "main", "OPENAPI_PATH", "OUT_PATH", "type_to_ts"]


def main() -> int:
    content = generate()
    if not OUT_PATH.exists() or OUT_PATH.read_text(encoding="utf-8") != content:
        raise SystemExit("Generated API types are out of date. Run python scripts/generate_api_types.py.")
    print("OK: generated API types are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
