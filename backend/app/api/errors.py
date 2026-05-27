from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_payload(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | str | None = None,
) -> dict[str, Any]:
    return {
        "code": str(code),
        "message": str(message),
        "details": details,
    }


def api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | str | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=error_payload(code=code, message=message, details=details),
    )


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code=code, message=message, details=details),
    )


def normalize_http_exception(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and {"code", "message", "details"} <= set(detail.keys()):
        payload = detail
    elif isinstance(detail, dict) and {"code", "message"} <= set(detail.keys()):
        payload = {
            "code": str(detail["code"]),
            "message": str(detail["message"]),
            "details": detail.get("details"),
        }
    else:
        payload = error_payload(
            code="http_error",
            message=str(detail or "Request failed."),
            details=None,
        )
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers or None)


async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
    return normalize_http_exception(exc)


async def handle_value_error(_request: Request, exc: ValueError) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        message=str(exc),
    )


async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    message = "Invalid request."
    errors: list[Any] = []
    try:
        errors = exc.errors()
        if errors:
            message = str(errors[0].get("msg") or message)
    except (AttributeError, TypeError, ValueError):
        errors = []
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message=message,
        details=errors,
    )
