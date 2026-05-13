from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=BACKEND, check=True)


def main() -> int:
    version = sys.version_info
    if not (version.major == 3 and version.minor == 11):
        print(
            "Backend checks must run on Python 3.11.x "
            f"(current: {version.major}.{version.minor}.{version.micro}).",
            file=sys.stderr,
        )
        return 2

    run(["ruff", "check", "."])
    run([sys.executable, "-m", "compileall", "app", "tests"])
    run([sys.executable, "-m", "pytest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
