"""FastAPI application entrypoint."""

from __future__ import annotations

from app.api.app_factory import create_app
from app.api.legacy_main import (
    APP_VERSION,
    UPLOAD_DIR,
    _autotest_step_should_run,
    db,
    delete_from_kb_vector_db,
    delete_from_vector_db,
    perform_qa,
    process_file,
)

app = create_app()

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
