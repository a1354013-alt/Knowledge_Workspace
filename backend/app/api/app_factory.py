from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import legacy_main
from app.api.errors import handle_http_exception
from app.api.routes import autotest, dashboard, docs, indexing, knowledge, logbook, photos, system
from app.context import APP_VERSION, allow_credentials, allowed_origins


def create_app() -> FastAPI:
    app = FastAPI(
        title="Knowledge Workspace API",
        version=APP_VERSION,
        lifespan=legacy_main.lifespan,
    )

    app.state.limiter = legacy_main.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(ValueError, legacy_main.handle_value_error)
    app.add_exception_handler(legacy_main.RequestValidationError, legacy_main.handle_validation_error)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (
        system.router,
        indexing.router,
        dashboard.router,
        docs.router,
        knowledge.router,
        logbook.router,
        photos.router,
        autotest.router,
    ):
        app.include_router(router)

    return app
