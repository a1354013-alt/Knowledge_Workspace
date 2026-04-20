from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, status

from app.models import ROLE_VALUES


MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_FILE_EXTENSIONS = (".pdf", ".txt", ".md")
ALLOWED_ROLES = set(ROLE_VALUES)

# Magic bytes signatures for common file types (file signature / "magic numbers")
MAGIC_BYTES_SIGNATURES = {
    # PDF files start with %PDF-
    ".pdf": b"%PDF-",
    # PNG files start with \x89PNG\r\n\x1a\n
    ".png": b"\x89PNG\r\n\x1a\n",
    # JPEG files start with \xff\xd8\xff
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    # GIF files start with GIF87a or GIF89a
    ".gif": b"GIF87a",
    ".webp": b"RIFF",  # WebP uses RIFF container, we'll check more specifically below
    # Text files - no specific magic bytes, but we can check for common encodings
    ".txt": None,  # No magic bytes for plain text
    ".md": None,   # No magic bytes for markdown
}


def generate_safe_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4()}{ext}"


def validate_file_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_FILE_EXTENSIONS


def validate_file_magic_bytes(file_content: bytes, filename: str) -> bool:
    """
    Validate file content using magic bytes (file signature) to prevent malicious file uploads.
    
    This function checks the actual binary content of a file against known file type signatures,
    rather than relying solely on file extensions which can be easily spoofed.
    
    Args:
        file_content: The raw bytes content of the uploaded file.
        filename: The original filename (used to determine expected extension).
    
    Returns:
        True if the file content matches the expected type based on extension.
    
    Raises:
        HTTPException: If the file content does not match the expected type.
    """
    ext = Path(filename).suffix.lower()
    
    # Check if extension is allowed
    if ext not in ALLOWED_FILE_EXTENSIONS and ext not in MAGIC_BYTES_SIGNATURES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not allowed.",
        )
    
    # For text/markdown files, we just check they're valid UTF-8
    if ext in (".txt", ".md"):
        try:
            file_content.decode("utf-8")
            return True
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File appears to be binary but has a text extension. Possible file spoofing detected.",
            ) from None
    
    # For other file types, check magic bytes
    expected_signature = MAGIC_BYTES_SIGNATURES.get(ext)
    if expected_signature is None:
        # No signature defined for this extension, allow it through
        return True
    
    # Check if file content starts with the expected magic bytes
    if not file_content.startswith(expected_signature):
        # Special handling for JPEG (sometimes has different headers)
        if ext in (".jpg", ".jpeg") and file_content.startswith(b"\xff\xd8"):
            return True
        # Special handling for WebP (RIFF container with WEBP marker)
        if ext == ".webp":
            if file_content.startswith(b"RIFF") and len(file_content) >= 12 and file_content[8:12] == b"WEBP":
                return True
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content does not match the expected format for '{ext}'. Possible file spoofing detected.",
        )
    
    return True


def normalize_roles(roles: str | Iterable[str] | None, *, default: list[str] | None = None) -> list[str]:
    if default is None:
        default = ["user"]

    if roles is None:
        normalized = list(default)
    elif isinstance(roles, str):
        normalized = [part.strip() for part in roles.split(",") if part.strip()]
    else:
        normalized = [str(part).strip() for part in roles if str(part).strip()]

    if not normalized:
        normalized = list(default)

    invalid = [role for role in normalized if role not in ALLOWED_ROLES]
    if invalid:
        raise ValueError(f"Unsupported roles: {', '.join(invalid)}")

    deduplicated: list[str] = []
    for role in normalized:
        if role not in deduplicated:
            deduplicated.append(role)
    return deduplicated


async def stream_write_file(file, file_path: Path, max_size: int = MAX_FILE_SIZE, chunk_size: int = 8192) -> int:
    total_size = 0
    try:
        with open(file_path, 'wb') as output_file:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > max_size:
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {max_size // (1024 * 1024)} MB limit.",
                    )
                output_file.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store uploaded file: {exc}",
        ) from exc

    return total_size


def get_env_list(key: str, default: list[str] | None = None) -> list[str]:
    if default is None:
        default = []
    value = os.getenv(key, '').strip()
    if not value:
        return list(default)
    return [item.strip() for item in value.split(',') if item.strip()]
