from __future__ import annotations

import logging
from typing import Any

from fastapi import Header, HTTPException, status

from app.context import db
from app.core.security import extract_token_from_header, verify_token

logger = logging.getLogger("knowledge_workspace")


async def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = extract_token_from_header(authorization)
    payload = verify_token(token)
    user_id = str(payload.get("sub", "") or "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get_user(user_id)
    if not user or int(user.get("is_active", 0)) != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "sub": user_id,
        "role": str(user.get("role", "") or payload["role"]),
        "display_name": str(user.get("display_name", "") or ""),
        "exp": payload.get("exp"),
    }
