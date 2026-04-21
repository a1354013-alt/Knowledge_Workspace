"""Compatibility entrypoint for running the API with uvicorn.

Prefer: `python -m uvicorn app.main:app ...`
"""

from __future__ import annotations

from app.main import app  # noqa: F401
