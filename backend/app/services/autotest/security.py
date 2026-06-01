from __future__ import annotations

import shutil
import subprocess

from app.context import settings
from app.models import AutoTestCapabilitiesResponse

SUPPORTED_SANDBOX_BACKENDS = {"disabled", "local_trusted", "docker_sandbox"}


LOCAL_TRUSTED_SAFETY_NOTE = (
    "Local trusted mode executes uploaded project commands on this host. Use it only for projects you trust; "
    "it is not safe for arbitrary or unfamiliar ZIP uploads."
)
DOCKER_SANDBOX_SAFETY_NOTE = (
    "Docker sandbox mode runs commands through docker with timeout, CPU/memory limits, artifact logs, "
    "and network disabled by default."
)


def current_autotest_runner_mode() -> str:
    mode = str(settings.AUTOTEST_MODE or "").strip().lower().replace("-", "_")
    if mode in {"real", "local", "local_trusted"}:
        return "local_trusted"
    if mode in {"docker", "docker_sandbox"}:
        return "docker_sandbox"
    if mode == "simulated":
        return "simulated"
    return "disabled"


def is_real_autotest_requested() -> bool:
    return current_autotest_runner_mode() == "local_trusted"


def is_real_autotest_enabled() -> bool:
    return bool(settings.KW_AUTOTEST_REAL_MODE) or bool(settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST)


def configured_sandbox_backend() -> str:
    backend = str(settings.AUTOTEST_SANDBOX_BACKEND or "").strip().lower().replace("-", "_")
    if backend == "docker":
        return "docker_sandbox"
    return backend if backend in SUPPORTED_SANDBOX_BACKENDS else "disabled"


def is_real_autotest_backend_ready() -> bool:
    return configured_sandbox_backend() == "local_trusted"


def docker_sandbox_unavailable_reason() -> str:
    docker_executable = shutil.which("docker")
    if not docker_executable:
        return "Docker executable was not found on PATH."
    try:
        completed = subprocess.run(
            [docker_executable, "info", "--format", "{{json .ServerVersion}}"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Docker daemon preflight timed out while running 'docker info'."
    except OSError as exc:
        return f"Docker preflight failed: {exc}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return f"Docker daemon is not available. {detail}".strip()
    return ""


def is_docker_sandbox_ready() -> bool:
    return docker_sandbox_unavailable_reason() == ""


def real_autotest_block_reason() -> str | None:
    if not is_real_autotest_requested():
        return None
    if not is_real_autotest_enabled():
        return (
            "AutoTest real mode is disabled by default. Set KW_AUTOTEST_REAL_MODE=1 or "
            "KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1, and set "
            "AUTOTEST_SANDBOX_BACKEND=local_trusted only for trusted local projects. "
            "Local trusted execution is host execution, not a safe sandbox."
        )

    backend = configured_sandbox_backend()
    if backend == "local_trusted":
        return None
    return (
        "AutoTest real mode requires AUTOTEST_SANDBOX_BACKEND=local_trusted. "
        "No supported sandbox backend is enabled, so host execution stays blocked."
    )


def autotest_run_block_reason() -> str | None:
    runner_mode = current_autotest_runner_mode()
    if runner_mode == "local_trusted":
        return real_autotest_block_reason()
    if runner_mode == "docker_sandbox":
        reason = docker_sandbox_unavailable_reason()
        if reason:
            return f"AutoTest docker_sandbox mode is unavailable: {reason}"
    return None


def current_autotest_execution_mode() -> str:
    runner_mode = current_autotest_runner_mode()
    if runner_mode == "docker_sandbox":
        return "real" if is_docker_sandbox_ready() else "simulated"
    return "real" if runner_mode == "local_trusted" and real_autotest_block_reason() is None else "simulated"


def current_autotest_response_runner_mode() -> str:
    runner_mode = current_autotest_runner_mode()
    if runner_mode == "local_trusted" and real_autotest_block_reason() is not None:
        return "disabled"
    return runner_mode


def get_autotest_capabilities() -> AutoTestCapabilitiesResponse:
    runner_mode = current_autotest_runner_mode()
    requested = runner_mode == "local_trusted"
    enabled = is_real_autotest_enabled()
    backend = "docker_sandbox" if runner_mode == "docker_sandbox" else configured_sandbox_backend()
    docker_unavailable_reason = docker_sandbox_unavailable_reason() if runner_mode == "docker_sandbox" else ""
    backend_ready = is_real_autotest_backend_ready() or (runner_mode == "docker_sandbox" and not docker_unavailable_reason)
    block_reason = real_autotest_block_reason()
    local_available = requested and block_reason is None
    docker_available = runner_mode == "docker_sandbox" and not docker_unavailable_reason
    if docker_available:
        message = "Docker sandbox mode is active. Commands run in a container with network disabled by default."
        safety_note = DOCKER_SANDBOX_SAFETY_NOTE
    elif runner_mode == "docker_sandbox":
        message = f"Docker sandbox mode was requested but is unavailable: {docker_unavailable_reason}"
        safety_note = DOCKER_SANDBOX_SAFETY_NOTE
    elif local_available:
        message = "Local trusted AutoTest mode is enabled. Commands run on this host."
        safety_note = LOCAL_TRUSTED_SAFETY_NOTE
    elif runner_mode == "simulated":
        message = "Safe simulated mode is active. No uploaded project commands will run."
        safety_note = "Simulated mode records and simulates runs without executing uploaded project commands."
    else:
        message = (
            "Safe simulated mode is active. No uploaded project commands will run. "
            f"{block_reason or 'Use AUTOTEST_MODE=local_trusted with an explicit enable flag, or AUTOTEST_MODE=docker_sandbox for container execution.'}"
        )
        safety_note = "Disabled mode records and simulates runs without executing uploaded project commands."
    return AutoTestCapabilitiesResponse(
        mode="real" if (local_available or docker_available) else "simulated",
        runner_mode=current_autotest_response_runner_mode(),
        real_mode_requested=requested,
        real_mode_enabled=enabled,
        real_mode_available=local_available,
        docker_sandbox_available=docker_available,
        network_enabled=bool(settings.AUTOTEST_DOCKER_NETWORK) if docker_available else False,
        safety_note=safety_note,
        sandbox_backend=backend,
        sandbox_backend_ready=backend_ready,
        docker_sandbox_unavailable_reason=docker_unavailable_reason,
        message=message,
    )
