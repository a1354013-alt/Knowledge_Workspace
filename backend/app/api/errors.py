from __future__ import annotations

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def handle_value_error(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = "Invalid request."
    try:
        errors = exc.errors()
        if errors:
            detail = errors[0].get("msg") or detail
    except Exception:
        pass
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": detail})

