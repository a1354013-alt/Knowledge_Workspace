from __future__ import annotations

import subprocess
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    subprocess.run([sys.executable, "scripts/export_openapi.py", "--check"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/generate_api_types.py", "--check"], cwd=ROOT, check=True)
    print("OK: OpenAPI schema and generated frontend API types are in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
