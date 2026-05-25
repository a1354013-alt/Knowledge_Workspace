from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def validate_python_version() -> None:
    version = sys.version_info
    if (version.major, version.minor) != (3, 11):
        raise SystemExit(
            "Unsupported Python runtime for OpenAPI export. "
            "Use Python 3.11.x so docs/openapi.json matches the supported backend dependency set."
        )


def main() -> int:
    validate_python_version()
    os.environ.setdefault("JWT_SECRET", "openapi-secret-openapi-secret-123456")
    os.environ.setdefault("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
    runtime_dir = BACKEND / "openapi_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DATABASE_PATH", ":memory:")
    os.environ.setdefault("UPLOAD_DIR", str(runtime_dir / "uploads"))
    os.environ.setdefault("PHOTO_DIR", str(runtime_dir / "photos"))
    os.environ.setdefault("AUTOTEST_DIR", str(runtime_dir / "autotest"))
    os.environ.setdefault("CHROMA_DB_PATH", str(runtime_dir / "chroma"))
    os.environ.setdefault("AUTOTEST_MODE", "simulated")
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    from app.main import app

    out_path = ROOT / "docs" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
