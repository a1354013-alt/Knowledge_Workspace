"""FastAPI application entrypoint."""

from __future__ import annotations

from app.api.app_factory import create_app

app = create_app()

__all__ = ["app", "create_app"]
