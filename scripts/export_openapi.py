from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PY311_CANDIDATES = (
    ROOT / ".venv311" / "Scripts" / "python.exe",
    ROOT / ".venv311_clean" / "Scripts" / "python.exe",
)


def validate_python_version() -> None:
    version = sys.version_info
    if (version.major, version.minor) != (3, 11):
        raise SystemExit(
            "Unsupported Python runtime for OpenAPI export. "
            "Use Python 3.11.x so docs/openapi.json matches the supported backend dependency set."
        )


def _delegate_to_python311() -> int | None:
    version = sys.version_info
    if (version.major, version.minor) == (3, 11):
        return None
    if os.environ.get("KNOWLEDGE_WORKSPACE_OPENAPI_DELEGATED") == "1":
        return None

    for candidate in PY311_CANDIDATES:
        if not candidate.exists():
            continue
        env = {**os.environ, "KNOWLEDGE_WORKSPACE_OPENAPI_DELEGATED": "1"}
        result = subprocess.run([str(candidate), __file__, *sys.argv[1:]], cwd=ROOT, env=env, check=False)
        return int(result.returncode)
    return None


def generate_openapi_json() -> str:
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

    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    delegated = _delegate_to_python311()
    if delegated is not None:
        return delegated

    parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI schema to docs/openapi.json.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    out_path = ROOT / "docs" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_openapi_json()
    if args.check:
        if not out_path.exists() or out_path.read_text(encoding="utf-8") != content:
            raise SystemExit("docs/openapi.json is out of date. Run python scripts/export_openapi.py.")
        print("OK: docs/openapi.json is up to date")
        return 0
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
