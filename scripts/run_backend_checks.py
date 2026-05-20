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
    run([sys.executable, "-m", "ruff", "check", "backend", "scripts"])
    run([sys.executable, str(ROOT / "scripts" / "safe_compileall.py"), "-q", "."])
    run([sys.executable, "-m", "pytest", "-q"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
