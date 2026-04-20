"""Authentication utilities using the new security module.

This module is deprecated. Please use app.core.security instead.
Kept for backward compatibility during refactoring.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status

from app.core.security import JWTHelper
from app.models import ROLE_VALUES


logger = logging.getLogger("knowledge_workspace")

ALLOWED_ROLES = set(ROLE_VALUES)


def create_token(
    user_id: str,
    role: str,
    display_name: str = "",
    expires_in_hours: int | None = None,  # Deprecated parameter
) -> str:
    """Create an access token.
    
    Args:
        user_id: User identifier
        role: User role (must be in ROLE_VALUES)
        display_name: Optional display name
        expires_in_hours: Deprecated - use ACCESS_TOKEN_EXPIRE_MINUTES in config
        
    Returns:
        JWT access token string
    """
    if expires_in_hours is not None:
        logger.warning(
            "expires_in_hours parameter is deprecated. "
            "Use ACCESS_TOKEN_EXPIRE_MINUTES in environment config."
        )
    
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Unsupported role: {role}")
    
    return JWTHelper.create_access_token(user_id, role, display_name)


def verify_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload with sub, role, display_name
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    payload = JWTHelper.verify_token(token, token_type="access")
    
    # Ensure role is valid
    role = payload.get("role")
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )
    
    return {
        "sub": payload["sub"],
        "role": role,
        "display_name": payload.get("display_name", ""),
        "exp": payload.get("exp"),
    }


def extract_token_from_header(authorization: str | None) -> str:
    """Extract Bearer token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token string
        
    Raises:
        HTTPException: If header is missing or malformed
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
    return token
