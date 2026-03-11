import os
import uuid
from pathlib import Path
from typing import List, Tuple
import aiofiles
from fastapi import HTTPException, status


# ============ 檔案大小限制 ============

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ============ 檔案工具 ============

def generate_safe_filename(original_filename: str) -> str:
    """
    生成安全的檔案名稱（使用 UUID）
    
    Args:
        original_filename: 原始檔案名稱
    
    Returns:
        安全的檔案名稱（UUID + 副檔名）
    """
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4()}{ext}"


def validate_file_extension(filename: str, allowed_extensions: Tuple[str, ...] = (".pdf", ".txt", ".md")) -> bool:
    """
    驗證檔案副檔名
    
    Args:
        filename: 檔案名稱
        allowed_extensions: 允許的副檔名
    
    Returns:
        是否有效
    """
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


async def stream_write_file(file, file_path: Path, max_size: int = MAX_FILE_SIZE, chunk_size: int = 8192) -> int:
    """
    流式寫入 FastAPI UploadFile 檔案（邊讀邊寫，節省記憶體）
    
    Args:
        file: FastAPI UploadFile 物件
        file_path: 檔案路徑
        max_size: 最大檔案大小（位元組）
        chunk_size: 每次讀取的大小
    
    Returns:
        寫入的總位元組
    
    Raises:
        HTTPException: 檔案超過最大大小
    """
    total_size = 0
    try:
        async with aiofiles.open(file_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                total_size += len(chunk)
                if total_size > max_size:
                    # 檔案超過最大大小，刪除檔案
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"檔案大小超過限制 ({max_size / 1024 / 1024:.1f} MB)"
                    )
                
                await f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"檔案寫入失敗: {str(e)}"
        )
    
    return total_size


# ============ 角色相關工具 ============

# 使用者角色（包含 admin）
ALLOWED_USER_ROLES = {"employee", "manager", "hr", "admin"}

# 文件可見角色（包含 admin）
ALLOWED_DOC_ROLES = {"employee", "manager", "hr", "admin"}

# 向後相容
ALLOWED_ROLES = ALLOWED_USER_ROLES


def validate_user_roles(roles: List[str]) -> bool:
    """
    驗證使用者角色列表是否都在白名單中
    
    Args:
        roles: 角色列表
    
    Returns:
        是否有效
    """
    if not roles:
        return False
    return all(role in ALLOWED_USER_ROLES for role in roles)


def validate_doc_roles(roles: List[str]) -> bool:
    """
    驗證文件可見角色列表是否都在白名單中
    
    Args:
        roles: 角色列表
    
    Returns:
        是否有效
    """
    if not roles:
        return False
    return all(role in ALLOWED_DOC_ROLES for role in roles)


def validate_roles(roles: List[str]) -> bool:
    """向後相容：驗證使用者角色"""
    return validate_user_roles(roles)


def parse_user_roles(roles_str: str) -> List[str]:
    """
    解析使用者角色字符串（逗號分隔）
    
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
    
    if not validate_user_roles(roles):
        invalid_roles = [r for r in roles if r not in ALLOWED_USER_ROLES]
        raise ValueError(
            f"無效的使用者角色: {', '.join(invalid_roles)}。允許: {', '.join(ALLOWED_USER_ROLES)}"
        )
    
    return roles


def parse_doc_roles(roles_str: str) -> List[str]:
    """
    解析文件可見角色字符串（逗號分隔）
    
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
    
    if not validate_doc_roles(roles):
        invalid_roles = [r for r in roles if r not in ALLOWED_DOC_ROLES]
        raise ValueError(
            f"無效的文件角色: {', '.join(invalid_roles)}。允許: {', '.join(ALLOWED_DOC_ROLES)}"
        )
    
    return roles


def parse_roles(roles_str: str) -> List[str]:
    """向後相容：解析使用者角色"""
    return parse_user_roles(roles_str)


# ============ 錯誤回應格式化 ============

class ErrorResponse:
    """統一的錯誤回應格式"""
    
    @staticmethod
    def format(detail: str, status_code: int = 400):
        """格式化錯誤回應"""
        return {
            "detail": detail,
            "status_code": status_code
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
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes"):
        return True
    elif value in ("false", "0", "no"):
        return False
    return default


def get_env_int(key: str, default: int = 0) -> int:
    """
    從環境變數讀取整數
    
    Args:
        key: 環境變數名稱
        default: 預設值
    
    Returns:
        整數
    """
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_list(key: str, default: List[str] = None, separator: str = ",") -> List[str]:
    """
    從環境變數讀取列表
    
    Args:
        key: 環境變數名稱
        default: 預設值
        separator: 分隔符
    
    Returns:
        列表
    """
    if default is None:
        default = []
    
    value = os.getenv(key, "")
    if not value:
        return default
    
    return [v.strip() for v in value.split(separator) if v.strip()]
