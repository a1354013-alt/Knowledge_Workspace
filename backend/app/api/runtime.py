from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.context import APP_VERSION, UPLOAD_DIR, allow_credentials, allowed_origins, db, settings
from app.core.security import create_token
from app.llm import validate_env_vars

logger = logging.getLogger("knowledge_workspace")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
PHOTO_DIR = settings.PHOTO_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app
    try:
        validate_env_vars()
    except RuntimeError as exc:
        logger.error("Environment validation failed: %s", exc)
        raise

    logger.info("Knowledge Workspace API starting.")
    logger.info("CORS origins: %s", allowed_origins)

    try:
        from app.llm import get_llm_provider

        provider, status_info = get_llm_provider()
        logger.info(
            "LLM Provider: %s (model: %s, fallback: %s)",
            status_info["primary_provider"],
            status_info["model"],
            status_info["fallback_enabled"],
        )
        _ = provider
    except Exception as exc:
        logger.warning("Failed to initialize LLM provider: %s", exc)

    try:
        from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

        recovered = recover_interrupted_autotest_runs()
        if recovered:
            logger.warning("Recovered %s stale AutoTest run(s) after startup.", recovered)
    except Exception as exc:
        logger.warning("AutoTest startup recovery failed: %s", exc)

    yield
    try:
        from app.services.autotest import shutdown_autotest_workers

        shutdown_autotest_workers()
    except Exception as exc:
        logger.warning("AutoTest worker shutdown failed: %s", exc)
    logger.info("Knowledge Workspace API stopped.")


limiter = Limiter(key_func=get_remote_address)

__all__ = [
    "APP_VERSION",
    "PHOTO_DIR",
    "UPLOAD_DIR",
    "allow_credentials",
    "allowed_origins",
    "asynccontextmanager",
    "asyncio",
    "create_token",
    "db",
    "lifespan",
    "limiter",
    "logger",
    "logging",
    "settings",
    "validate_env_vars",
]
