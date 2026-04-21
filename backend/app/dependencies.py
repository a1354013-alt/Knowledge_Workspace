from __future__ import annotations

import logging
from typing import Any

from fastapi import Header

from app.core.security import extract_token_from_header, verify_token

logger = logging.getLogger("knowledge_workspace")


async def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = extract_token_from_header(authorization)
    return verify_token(token)
