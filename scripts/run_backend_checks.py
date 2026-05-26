from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, str(ROOT / "scripts" / "check_python_version.py")])
    run([sys.executable, str(ROOT / "scripts" / "safe_compile.py"), "-q", "."])
    run([sys.executable, "-m", "ruff", "check", "backend", "scripts"])
    run([sys.executable, str(ROOT / "scripts" / "run_backend_tests.py")])
    run([sys.executable, str(ROOT / "scripts" / "export_openapi.py")])
    run([sys.executable, str(ROOT / "scripts" / "generate_api_types.py"), "--check"])
    run([sys.executable, str(ROOT / "scripts" / "check_version_consistency.py")])
    run([sys.executable, str(ROOT / "scripts" / "check_index_consistency.py")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
