from __future__ import annotations

import os
import signal
import shutil
import subprocess
import sys
from contextlib import suppress
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 180
TAIL_LINE_COUNT = 40
PYTEST_BASETEMP = ROOT / "backend" / ".pytest-tmp" / "wrapper-basetemp"


def _tail(text: str, *, lines: int = TAIL_LINE_COUNT) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    return "\n".join(stripped.splitlines()[-lines:])


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            check=False,
            capture_output=True,
            text=True,
        )
        return

    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)


def main() -> int:
    timeout_seconds = int(os.environ.get("KNOWLEDGE_WORKSPACE_PYTEST_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
    command = [sys.executable, "-m", "pytest", "-q", "--basetemp", str(PYTEST_BASETEMP)]
    print(f"+ {' '.join(command)}")
    env = os.environ.copy()
    if PYTEST_BASETEMP.exists():
        shutil.rmtree(PYTEST_BASETEMP, ignore_errors=True)
    PYTEST_BASETEMP.parent.mkdir(parents=True, exist_ok=True)
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    preexec_fn = os.setsid if os.name != "nt" else None
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creationflags,
        env=env,
        preexec_fn=preexec_fn,
    )

    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        stdout, stderr = process.communicate()
        print(
            f"ERROR: pytest did not exit within {timeout_seconds}s. "
            "This usually means a background worker, TestClient lifespan, or subprocess was left open.",
            file=sys.stderr,
        )
        stdout_tail = _tail(stdout)
        stderr_tail = _tail(stderr)
        if stdout_tail:
            print("----- pytest stdout tail -----", file=sys.stderr)
            print(stdout_tail, file=sys.stderr)
        if stderr_tail:
            print("----- pytest stderr tail -----", file=sys.stderr)
            print(stderr_tail, file=sys.stderr)
        return 124

    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)
    return int(process.returncode or 0)

if __name__ == "__main__":
    raise SystemExit(main())
