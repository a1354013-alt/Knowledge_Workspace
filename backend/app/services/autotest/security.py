from __future__ import annotations

from app.context import settings
from app.models import AutoTestCapabilitiesResponse


def is_real_autotest_requested() -> bool:
    return str(settings.AUTOTEST_MODE or "").strip().lower() == "real"


def is_real_autotest_enabled() -> bool:
    return bool(settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST)


def current_autotest_execution_mode() -> str:
    return "real" if is_real_autotest_requested() and is_real_autotest_enabled() else "simulated"


def get_autotest_capabilities() -> AutoTestCapabilitiesResponse:
    requested = is_real_autotest_requested()
    enabled = is_real_autotest_enabled()
    available = requested and enabled
    message = (
        "Real AutoTest mode is enabled. Run only trusted projects inside a sandbox/container."
        if available
        else "Safe simulated mode is active. Real command execution requires AUTOTEST_MODE=real and KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1."
    )
    return AutoTestCapabilitiesResponse(
        mode="real" if available else "simulated",
        real_mode_requested=requested,
        real_mode_enabled=enabled,
        real_mode_available=available,
        message=message,
    )


