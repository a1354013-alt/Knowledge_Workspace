"""FastAPI application entrypoint."""

from __future__ import annotations

from app.api.app_factory import create_app
from app.api import legacy_main
from app.api.legacy_main import (
    APP_VERSION,
    UPLOAD_DIR,
    db,
    delete_from_kb_vector_db,
    delete_from_vector_db,
    perform_qa,
    process_file,
)
from app.services import autotest_service, dashboard_service

_autotest_step_should_run = autotest_service.autotest_step_should_run

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
    "legacy_main",
    "autotest_service",
    "dashboard_service",
]
