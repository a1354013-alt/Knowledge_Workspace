"""
FastAPI Dependency 模組
統一 Token 驗證、用戶認證、Admin 權限檢查
避免在各 endpoint 重複寫 authorization 解析邏輯
"""

import logging
from typing import Dict, Optional
from fastapi import Header, HTTPException, status
from auth import extract_token_from_header, verify_token

logger = logging.getLogger("enterprise-ai-assistant")


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """
    Dependency：驗證 token 並提取當前使用者資訊
    
    使用方式：
        @app.get("/api/docs")
        async def list_documents(current_user: Dict = Depends(get_current_user)):
            user_id = current_user["sub"]
            role = current_user["role"]
            ...
    
    Returns:
        {
            "sub": user_id,
            "role": role,
            "display_name": display_name,
            "exp": expiration_time
        }
    
    Raises:
        HTTPException: 401 Unauthorized（缺少 token 或 token 無效）
    """
    try:
        if not authorization:
            logger.warning("缺少 Authorization header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        
        return token_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token 驗證異常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 驗證失敗"
        )


async def get_current_admin(current_user: Dict = None) -> Dict:
    """
    Dependency：驗證當前使用者是否為 admin
    
    使用方式：
        @app.get("/api/admin/docs")
        async def admin_list_documents(current_admin: Dict = Depends(get_current_admin)):
            # 此時已確認 current_admin["role"] == "admin"
            ...
    
    Args:
        current_user: 由 get_current_user 注入
    
    Returns:
        current_user（已驗證為 admin）
    
    Raises:
        HTTPException: 403 Forbidden（非 admin）
    """
    # 注意：FastAPI 會自動調用 get_current_user 作為前置 Dependency
    # 所以這裡的 current_user 已經是驗證過的
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少認證資訊"
        )
    
    if current_user.get("role") != "admin":
        logger.warning(f"非 admin 用戶嘗試存取 admin 資源: user_id={current_user.get('sub')}, role={current_user.get('role')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有 admin 可以存取此資源"
        )
    
    return current_user
