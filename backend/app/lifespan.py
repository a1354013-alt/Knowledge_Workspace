"""Lifespan management for FastAPI application startup and shutdown."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

logger = logging.getLogger("knowledge_workspace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    # Startup
    logger.info("Starting Knowledge Workspace API...")
    
    # Ensure upload directory exists
    from app.core.config import get_settings
    
    try:
        settings = get_settings()
        upload_dir = settings.UPLOAD_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Upload directory ready: %s", upload_dir)
    except Exception as e:
        logger.warning("Failed to configure upload directory: %s", e)
        # Fallback to default
        upload_dir = Path("./uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate LLM environment variables
    try:
        from app.llm import validate_env_vars
        missing = validate_env_vars()
        if missing:
            logger.warning("Missing LLM environment variables: %s", missing)
    except Exception as e:
        logger.warning("Failed to validate LLM config: %s", e)
    
    # Initialize database
    try:
        from app.database import DocumentDatabase
        db = DocumentDatabase(settings.DATABASE_PATH if 'settings' in locals() else "./documents.db")
        # Database tables are created in __init__, no separate initialize() method needed
        logger.info("Database initialized: %s", db.db_path)
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise
    
    logger.info("Application startup complete.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Knowledge Workspace API...")
    # Cleanup tasks can be added here if needed
    logger.info("Application shutdown complete.")
