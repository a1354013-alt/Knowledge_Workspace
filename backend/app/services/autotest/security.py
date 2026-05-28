from __future__ import annotations

from app.context import settings
from app.models import AutoTestCapabilitiesResponse


def is_real_autotest_requested() -> bool:
    return str(settings.AUTOTEST_MODE or "").strip().lower() == "real"


def is_real_autotest_enabled() -> bool:
    return bool(settings.KW_AUTOTEST_REAL_MODE)


def current_autotest_execution_mode() -> str:
    return "real" if is_real_autotest_requested() and is_real_autotest_enabled() else "simulated"


def get_autotest_capabilities() -> AutoTestCapabilitiesResponse:
    requested = is_real_autotest_requested()
    enabled = is_real_autotest_enabled()
    available = requested and enabled
    message = (
        "Real AutoTest mode is enabled. This is local trusted-workspace execution, not a Docker sandbox. "
        "Run only trusted projects inside your own isolated environment."
        if available
        else "Safe simulated mode is active. No uploaded project commands will run. "
        "Real command execution requires AUTOTEST_MODE=real and KW_AUTOTEST_REAL_MODE=1. "
        "Use real mode only for trusted local projects; do not run untrusted ZIP uploads. "
        "Production use requires Docker sandboxing or equivalent isolation."
    )
    return AutoTestCapabilitiesResponse(
        mode="real" if available else "simulated",
        real_mode_requested=requested,
        real_mode_enabled=enabled,
        real_mode_available=available,
        message=message,
    )
