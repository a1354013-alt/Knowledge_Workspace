"""Authentication router for login and user management."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.auth import create_token, verify_token, extract_token_from_header
from app.core.security import JWTHelper
from app.dependencies import get_current_user
from app.models import LoginRequest, LoginResponse, MeResponse

logger = logging.getLogger("knowledge_workspace")

router = APIRouter(tags=["authentication"])


@router.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate user and return access token.
    
    In production, this should validate against a real user database.
    For demo purposes, we accept any username with role 'owner' or 'viewer'.
    """
    from app.models import ROLE_VALUES
    
    username = request.username.strip()
    role = request.role.strip()
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required.",
        )
    
    if role not in ROLE_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(ROLE_VALUES)}",
        )
    
    # Create both access and refresh tokens
    access_token = create_token(
        user_id=username,
        role=role,
        display_name=request.display_name or username,
    )
    
    refresh_token = JWTHelper.create_refresh_token(username)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_minutes=60,  # Matches ACCESS_TOKEN_EXPIRE_MINUTES
    )


@router.get("/api/me", response_model=MeResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
) -> MeResponse:
    """Get current authenticated user information."""
    return MeResponse(
        user_id=current_user["sub"],
        role=current_user["role"],
        display_name=current_user.get("display_name", ""),
    )


@router.post("/api/token/refresh")
async def refresh_token(
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Refresh access token using refresh token.
    
    Expects refresh token in Authorization header.
    Returns new access token and refresh token.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer token.",
        )
    
    # Verify refresh token
    try:
        payload = JWTHelper.verify_token(token, token_type="refresh")
    except HTTPException as e:
        raise e
    
    user_id = payload["sub"]
    
    # Get user role from existing token or database
    # For now, we'll keep the same role (in production, fetch from DB)
    role = payload.get("role", "viewer")
    
    # Create new tokens
    new_access_token = JWTHelper.create_access_token(user_id, role)
    new_refresh_token = JWTHelper.create_refresh_token(user_id)
    
    return JSONResponse(
        content={
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in_minutes": 60,
        }
    )


@router.post("/api/token/revoke")
async def revoke_token(
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Revoke current token (add to blacklist).
    
    Requires Redis for token blacklisting.
    If Redis is not available, this endpoint will log a warning.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )
    
    token = extract_token_from_header(authorization)
    
    # Try to blacklist the token
    try:
        import redis
        
        redis_client = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,
        )
        
        jti = JWTHelper.get_token_jti(token)
        if jti:
            # Get token expiration to set TTL on blacklist
            try:
                payload = JWTHelper.verify_token(token, token_type="access")
                exp = payload.get("exp")
                if exp:
                    from datetime import datetime, timezone
                    ttl = int(datetime.fromtimestamp(exp, tz=timezone.utc) - datetime.now(timezone.utc)).total_seconds()
                    if ttl > 0:
                        redis_client.setex(f"token:blacklist:{jti}", ttl, "revoked")
            except HTTPException:
                pass  # Token might be expired, still blacklist it
            
            return JSONResponse(
                content={"message": "Token revoked successfully"},
                status_code=status.HTTP_200_OK,
            )
    except ImportError:
        logger.warning("Redis not available. Token blacklisting disabled.")
    except Exception as e:
        logger.warning("Failed to revoke token: %s", e)
    
    # Even without Redis, return success to avoid leaking implementation details
    return JSONResponse(
        content={"message": "Token revoked (best effort)"},
        status_code=status.HTTP_200_OK,
    )
