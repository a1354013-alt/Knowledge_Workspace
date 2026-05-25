"""Security utilities for JWT token management and password hashing."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


class JWTHelper:
    """Helper class for JWT token operations with enhanced security."""

    @staticmethod
    def _algorithm() -> str:
        return get_settings().JWT_ALGORITHM

    @classmethod
    def create_access_token(cls, user_id: str, role: str, display_name: str = "") -> str:
        """Create a short-lived access token."""
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": user_id,
            "role": role,
            "display_name": display_name,
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),  # Unique ID for blacklisting
        }

        return jwt.encode(payload, settings.JWT_SECRET, algorithm=cls._algorithm())

    @classmethod
    def create_refresh_token(cls, user_id: str) -> str:
        """Create a long-lived refresh token."""
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
        }

        return jwt.encode(payload, settings.JWT_SECRET, algorithm=cls._algorithm())

    @classmethod
    def verify_token(cls, token: str, token_type: str = "access") -> dict[str, Any]:
        """Verify and decode a JWT token."""
        settings = get_settings()

        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[cls._algorithm()])

            # Validate token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check expiration (jwt.decode already checks 'exp', but be explicit)
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @classmethod
    def get_token_jti(cls, token: str) -> str | None:
        """Extract the JTI (unique ID) from a token without full verification."""
        settings = get_settings()
        try:
            # Decode without verification to get JTI for blacklisting
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[cls._algorithm()], options={"verify_exp": False}
            )
            return payload.get("jti")
        except jwt.InvalidTokenError:
            return None


def extract_token_from_header(authorization: str | None) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def create_token(*, user_id: str, role: str, display_name: str = "") -> str:
    """Create a short-lived access token for the API."""
    return JWTHelper.create_access_token(user_id=user_id, role=role, display_name=display_name)


def verify_token(token: str) -> dict[str, Any]:
    """Verify and decode an access token payload for request dependencies."""
    payload = JWTHelper.verify_token(token, token_type="access")
    role = payload.get("role")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip() or not isinstance(role, str) or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "sub": subject.strip(),
        "role": role,
        "display_name": str(payload.get("display_name", "") or ""),
        "exp": payload.get("exp"),
    }
