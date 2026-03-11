"""
JWT 身分驗證模組
用於驗證使用者身分與角色，防止前端自稱角色
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException, status

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
if not JWT_SECRET:
    raise RuntimeError("❌ 必須設定 JWT_SECRET 環境變數（生產環境請使用強密鑰）")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# 允許的角色（包含 admin）
ALLOWED_ROLES = {"employee", "manager", "hr", "admin"}


def create_token(user_id: str, role: str, display_name: str = "", expires_in_hours: int = JWT_EXPIRATION_HOURS) -> str:
    """
    建立 JWT token
    
    Args:
        user_id: 使用者 ID
        role: 使用者角色 (employee/manager/hr/admin)
        display_name: 使用者顯示名稱
        expires_in_hours: token 過期時間（小時）
    
    Returns:
        JWT token 字符串
    """
    if role not in ALLOWED_ROLES:
        raise ValueError(f"無效的角色: {role}")
    
    payload = {
        "sub": user_id,  # subject（使用者 ID）
        "role": role,
        "display_name": display_name,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=expires_in_hours)
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Dict:
    """
    驗證 JWT token 並提取 payload
    
    Args:
        token: JWT token 字符串
    
    Returns:
        token payload (包含 sub, role, display_name, exp)
    
    Raises:
        HTTPException: token 無效或過期
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role")
        
        if not user_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 缺少必要資訊"
            )
        
        if role not in ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"無效的角色: {role}"
            )
        
        return {
            "sub": user_id,
            "role": role,
            "display_name": payload.get("display_name", ""),
            "exp": payload.get("exp")
        }
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已過期"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 無效: {str(e)}"
        )


def extract_token_from_header(authorization: Optional[str]) -> str:
    """
    從 Authorization header 提取 token
    
    格式: Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Authorization header"
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header 格式錯誤，應為 'Bearer <token>'"
        )
    
    return parts[1]
