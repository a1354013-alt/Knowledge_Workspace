"""FastAPI application entrypoint.

This file is intentionally small: it exposes `app` for uvicorn and keeps stable
imports used by tests/clients. The route implementations currently live in
`app.api.legacy_main` while they are being incrementally split into routers.
"""

from __future__ import annotations

from app.api.legacy_main import (  # noqa: F401
    APP_VERSION,
    UPLOAD_DIR,
    _autotest_step_should_run,
    app,
    db,
    delete_from_kb_vector_db,
    delete_from_vector_db,
    perform_qa,
    process_file,
)

__all__ = [
    "app",
    "db",
    "UPLOAD_DIR",
    "APP_VERSION",
    "process_file",
    "perform_qa",
    "delete_from_vector_db",
    "delete_from_kb_vector_db",
    "_autotest_step_should_run",
]
