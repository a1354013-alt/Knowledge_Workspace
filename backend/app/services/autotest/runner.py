from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from app.context import settings
from app.services.autotest.security import current_autotest_execution_mode
from app.services.autotest.timeline import clamp_output

logger = logging.getLogger("knowledge_workspace")


def _run_command(*, argv: list[str], cwd: Path, timeout_seconds: int) -> tuple[int, str, str]:
    if not argv:
        raise ValueError("Missing command argv.")
    env = os.environ.copy()
    if current_autotest_execution_mode() == "real":
        sensitive_tokens = ("TOKEN", "KEY", "SECRET", "PASSWORD", "DATABASE_URL")
        for key in list(env):
            normalized = key.upper()
            if any(token in normalized for token in sensitive_tokens):
                env.pop(key, None)
    env.setdefault("CI", "true")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    preexec_fn = None
    if os.name == "posix":
        try:
            import resource

            cpu_limit = int(settings.AUTOTEST_RLIMIT_CPU_SECONDS)
            as_limit_mb = int(settings.AUTOTEST_RLIMIT_AS_MB)
            fsize_mb = int(settings.AUTOTEST_RLIMIT_FSIZE_MB)

            def _apply_limits():
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
                resource.setrlimit(resource.RLIMIT_AS, (as_limit_mb * 1024 * 1024, as_limit_mb * 1024 * 1024))
                resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_mb * 1024 * 1024, fsize_mb * 1024 * 1024))

            preexec_fn = _apply_limits
        except Exception as exc:
            logger.warning("AutoTest resource limits unavailable: %s", exc)
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=env,
        preexec_fn=preexec_fn,
    )
    return int(completed.returncode), clamp_output(completed.stdout or ""), clamp_output(completed.stderr or "")


