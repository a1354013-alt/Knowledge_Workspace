"""
工具函數模組
提取可重用的業務邏輯，保持 main.py 和 services.py 簡潔
"""

import os
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import HTTPException, status

# ============ 檔案相關工具 ============

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def generate_safe_filename(original_filename: str) -> str:
    """
    生成安全的檔名（使用 UUID）
    
    Args:
        original_filename: 原始檔名
    
    Returns:
        安全的檔名（UUID + 副檔名）
    
    Raises:
        ValueError: 副檔名不允許
    """
    ext = Path(original_filename).suffix.lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"不允許的副檔名: {ext}。允許: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    safe_filename = f"{uuid.uuid4()}{ext}"
    return safe_filename


async def stream_write_file(file, file_path: Path, max_size: int = MAX_FILE_SIZE) -> int:
    """
    流式寫入檔案，邊讀邊寫，計算大小
    
    Args:
        file: FastAPI UploadFile 物件
        file_path: 目標檔案路徑
        max_size: 最大檔案大小（bytes）
    
    Returns:
        檔案大小（bytes）
    
    Raises:
        HTTPException: 檔案過大或寫入失敗
    """
    file_size = 0
    chunk_size = 8192  # 8KB chunks
    
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                file_size += len(chunk)
                if file_size > max_size:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"檔案過大（最大 {max_size / 1024 / 1024:.0f}MB）"
                    )
                
                f.write(chunk)
        
        return file_size
    
    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"檔案寫入失敗: {str(e)}"
        )


# ============ 角色相關工具 ============

ALLOWED_ROLES = {"employee", "manager", "hr"}


def validate_roles(roles: List[str]) -> bool:
    """
    驗證角色列表是否都在白名單中
    
    Args:
        roles: 角色列表
    
    Returns:
        是否有效
    """
    if not roles:
        return False
    return all(role in ALLOWED_ROLES for role in roles)


def parse_roles(roles_str: str) -> List[str]:
    """
    解析角色字符串（逗號分隔）
    
    Args:
        roles_str: 角色字符串（例如 "employee,manager"）
    
    Returns:
        角色列表
    
    Raises:
        ValueError: 無效的角色
    """
    if not roles_str or not roles_str.strip():
        return ["employee"]
    
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    
    if not validate_roles(roles):
        invalid_roles = [r for r in roles if r not in ALLOWED_ROLES]
        raise ValueError(
            f"無效的角色: {', '.join(invalid_roles)}。允許: {', '.join(ALLOWED_ROLES)}"
        )
    
    return roles


# ============ 錯誤回應格式化 ============

class ErrorResponse:
    """統一的錯誤回應格式"""
    
    @staticmethod
    def bad_request(detail: str) -> Dict:
        """400 Bad Request"""
        return {
            "status": "error",
            "code": 400,
            "detail": detail
        }
    
    @staticmethod
    def unauthorized(detail: str) -> Dict:
        """401 Unauthorized"""
        return {
            "status": "error",
            "code": 401,
            "detail": detail
        }
    
    @staticmethod
    def forbidden(detail: str) -> Dict:
        """403 Forbidden"""
        return {
            "status": "error",
            "code": 403,
            "detail": detail
        }
    
    @staticmethod
    def not_found(detail: str) -> Dict:
        """404 Not Found"""
        return {
            "status": "error",
            "code": 404,
            "detail": detail
        }
    
    @staticmethod
    def internal_error(detail: str) -> Dict:
        """500 Internal Server Error"""
        return {
            "status": "error",
            "code": 500,
            "detail": detail
        }


# ============ 環境變數工具 ============

def get_env_bool(key: str, default: bool = False) -> bool:
    """
    從環境變數讀取布林值
    
    Args:
        key: 環境變數名稱
        default: 預設值
    
    Returns:
        布林值
    """
    value = os.getenv(key, "").strip().lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    return default


def get_env_int(key: str, default: int = 0) -> int:
    """
    從環境變數讀取整數
    
    Args:
        key: 環境變數名稱
        default: 預設值
    
    Returns:
        整數值
    """
    try:
        return int(os.getenv(key, str(default)).strip())
    except (ValueError, TypeError):
        return default


def get_env_list(key: str, default: Optional[List[str]] = None) -> List[str]:
    """
    從環境變數讀取列表（逗號分隔）
    
    Args:
        key: 環境變數名稱
        default: 預設值
    
    Returns:
        字符串列表
    """
    if default is None:
        default = []
    
    value = os.getenv(key, "").strip()
    if not value:
        return default
    
    return [item.strip() for item in value.split(",") if item.strip()]
