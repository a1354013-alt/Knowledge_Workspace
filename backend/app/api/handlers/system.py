from app.api.errors import api_error, handle_validation_error, handle_value_error
from fastapi import Depends, Request, status

from app.api.common import serialize_me
from app.api.runtime import APP_VERSION, create_token, db, limiter
from app.dependencies import get_current_user
from app.models import HealthResponse, LoginRequest, LoginResponse, MeResponse

__all__ = [
    "api_healthcheck",
    "handle_validation_error",
    "handle_value_error",
    "healthcheck",
    "login",
    "me",
]


async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", version=APP_VERSION)


async def api_healthcheck() -> HealthResponse:
    # CI probes /api/health, while /health is kept for backwards compatibility.
    return await healthcheck()


@limiter.limit("5/minute")  # Rate limit: 5 requests per minute to prevent brute force
async def login(request: Request, payload: LoginRequest) -> LoginResponse:
    _ = request
    if not db.verify_password(payload.user_id, payload.password):
        raise api_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
            message="Invalid credentials.",
        )

    user = db.get_user(payload.user_id)
    if not user or int(user["is_active"]) != 1:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="inactive_user",
            message="User account is inactive.",
        )

    return LoginResponse(
        access_token=create_token(
            user_id=payload.user_id,
            role=user["role"],
            display_name=user["display_name"],
        )
    )


async def me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    return serialize_me(current_user)
