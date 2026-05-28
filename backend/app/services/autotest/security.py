from __future__ import annotations

from app.context import settings
from app.models import AutoTestCapabilitiesResponse


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
    return "disabled"


def is_real_autotest_requested() -> bool:
    return current_autotest_runner_mode() == "local_trusted"


def is_real_autotest_enabled() -> bool:
    return bool(settings.KW_AUTOTEST_REAL_MODE)


def current_autotest_execution_mode() -> str:
    runner_mode = current_autotest_runner_mode()
    if runner_mode == "docker_sandbox":
        return "real"
    return "real" if runner_mode == "local_trusted" and is_real_autotest_enabled() else "simulated"


def current_autotest_response_runner_mode() -> str:
    runner_mode = current_autotest_runner_mode()
    if runner_mode == "local_trusted" and not is_real_autotest_enabled():
        return "disabled"
    return runner_mode


def get_autotest_capabilities() -> AutoTestCapabilitiesResponse:
    runner_mode = current_autotest_runner_mode()
    requested = runner_mode == "local_trusted"
    enabled = is_real_autotest_enabled()
    local_available = requested and enabled
    docker_available = runner_mode == "docker_sandbox"
    if docker_available:
        message = "Docker sandbox mode is active. Commands run in a container with network disabled by default."
        safety_note = DOCKER_SANDBOX_SAFETY_NOTE
    elif local_available:
        message = "Local trusted AutoTest mode is enabled. Commands run on this host."
        safety_note = LOCAL_TRUSTED_SAFETY_NOTE
    else:
        message = (
            "AutoTest is disabled for uploaded project command execution. No uploaded project commands will run. "
            "Use AUTOTEST_MODE=local_trusted plus KW_AUTOTEST_REAL_MODE=1 only for trusted local projects, "
            "or AUTOTEST_MODE=docker_sandbox for container execution."
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
        message=message,
    )
