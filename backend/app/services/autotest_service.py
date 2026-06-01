"""Compatibility shim for the AutoTest service package.

Kept for older tests, runbooks, and extension imports that still reference
`app.services.autotest_service`. New code must import from
`app.services.autotest.service` or `app.services.autotest` directly.

Removal target: after the next minor release once tests and docs no longer
depend on this module-level aliasing behavior.
"""

from __future__ import annotations

import sys

from app.services.autotest import service as _service

sys.modules[__name__] = _service
