"""Compatibility shim for the AutoTest service package."""

from __future__ import annotations

import sys

from app.services.autotest import service as _service

sys.modules[__name__] = _service
