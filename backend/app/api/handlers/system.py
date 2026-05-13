# ruff: noqa: F401,F403,F405
from app.api.handlers.support import *  # noqa: F403


async def handle_value_error(_request, exc: ValueError):
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


async def handle_validation_error(_request, exc: RequestValidationError):
    detail = "Invalid request."
    try:
        errors = exc.errors()
        if errors:
            detail = errors[0].get("msg") or detail
    except Exception:
        pass
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": detail})


async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", version=APP_VERSION)


async def api_healthcheck() -> HealthResponse:
    # CI probes /api/health, while /health is kept for backwards compatibility.
    return await healthcheck()


@limiter.limit("5/minute")  # Rate limit: 5 requests per minute to prevent brute force
async def login(request: Request, payload: LoginRequest) -> LoginResponse:
    _ = request
    if not db.verify_password(payload.user_id, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    user = db.get_user(payload.user_id)
    if not user or int(user["is_active"]) != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    return LoginResponse(
        access_token=create_token(
            user_id=payload.user_id,
            role=user["role"],
            display_name=user["display_name"],
        )
    )


async def me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    return serialize_me(current_user)
