from __future__ import annotations

from pathlib import Path

from app.services.autotest.runner import _run_command


def run_command_step(*, argv: list[str], cwd: Path, timeout_seconds: int) -> tuple[int, str, str]:
    return _run_command(argv=argv, cwd=cwd, timeout_seconds=timeout_seconds)
