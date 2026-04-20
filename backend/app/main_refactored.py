"""Main FastAPI application entry point.

This module has been refactored to use modular routers.
All business logic has been moved to dedicated router modules.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.lifespan import lifespan
from app.routers import auth, documents

load_dotenv()

logger = logging.getLogger("knowledge_workspace")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if "*" in settings.ALLOWED_ORIGINS else settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Rate limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Exception handlers
    @app.exception_handler(ValueError)
    async def handle_value_error(_request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "value_error"}
        )
    
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError):
        detail = "Invalid request."
        try:
            errors = exc.errors()
            if errors:
                detail = errors[0].get("msg") or detail
        except Exception:
            pass
        return JSONResponse(
            status_code=400,
            content={"detail": detail, "type": "validation_error"}
        )
    
    # Register routers
    app.include_router(auth.router)
    app.include_router(documents.router)
    
    # TODO: Include other routers as they are refactored
    # from app.routers import knowledge, logbook, photos, autotest, qa, search
    # app.include_router(knowledge.router)
    # app.include_router(logbook.router)
    # app.include_router(photos.router)
    # app.include_router(autotest.router)
    # app.include_router(qa.router)
    # app.include_router(search.router)
    
    logger.info("FastAPI application created successfully")
    return app


# Create app instance
app = create_app()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "name": settings.APP_NAME,
    }
