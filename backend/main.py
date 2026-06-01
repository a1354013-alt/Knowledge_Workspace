"""Compatibility entrypoint for running the API with uvicorn.

Prefer: `python -m uvicorn app.main:app ...`
Do not add new runtime dependencies here; this file remains only for older
launch configs and can be removed after the documented legacy window closes.
"""

from __future__ import annotations

from app.main import app  # noqa: F401
