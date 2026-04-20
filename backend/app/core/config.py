"""Core configuration and settings for the application."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    # App Info
    APP_VERSION: str = "0.0.0"
    APP_NAME: str = "Knowledge Workspace API"
    
    # JWT Settings
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_PATH: Path = Field(default=Path("documents.db"))
    
    # Upload Settings
    UPLOAD_DIR: Path = Field(default=Path("uploads"))
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB default

    # Photo uploads
    PHOTO_DIR: Path = Field(default=Path("photos"))

    # Vector DB
    CHROMA_DB_PATH: Path = Field(default=Path("chroma_db"))

    # AutoTest working area
    AUTOTEST_DIR: Path = Field(default=Path("autotest_uploads"))
    AUTOTEST_MODE: str = "real"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]
    
    # AutoTest Settings
    AUTOTEST_MAX_FILES: int = 5000
    AUTOTEST_MAX_UNZIPPED_BYTES: int = 250 * 1024 * 1024  # 250MB
    AUTOTEST_TIMEOUT_SECONDS: int = 300
    AUTOTEST_RLIMIT_CPU_SECONDS: int = 310
    AUTOTEST_RLIMIT_AS_MB: int = 2048
    AUTOTEST_RLIMIT_FSIZE_MB: int = 200
    
    # OCR Settings
    OCR_ENABLED: bool = True
    
    # LLM Settings
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "llama3.1"
    
    @classmethod
    def load_from_env(cls) -> "Settings":
        """Load settings from environment variables with validation."""
        backend_dir = Path(__file__).resolve().parents[2]

        def resolve_path(raw: str, *, default: Path) -> Path:
            value = (raw or "").strip()
            path = default if not value else Path(value)
            if not path.is_absolute():
                path = backend_dir / path
            return path

        # Read version file
        try:
            repo_root = Path(__file__).resolve().parents[3]
            version_path = repo_root / "VERSION"
            app_version = version_path.read_text(encoding="utf-8").strip() or "0.0.0"
        except Exception:
            app_version = "0.0.0"
        
        # Get allowed origins
        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
        allowed_origins = [orig.strip() for orig in allowed_origins_str.split(",") if orig.strip()]
        if not allowed_origins:
            allowed_origins = ["http://localhost:5173"]
        
        settings = cls(
            APP_VERSION=app_version,
            JWT_SECRET=os.getenv("JWT_SECRET", "").strip(),
            JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256"),
            ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
            REFRESH_TOKEN_EXPIRE_DAYS=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
            DATABASE_PATH=resolve_path(os.getenv("DATABASE_PATH", ""), default=Path("documents.db")),
            UPLOAD_DIR=resolve_path(os.getenv("UPLOAD_DIR", ""), default=Path("uploads")),
            MAX_FILE_SIZE=int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024))),
            PHOTO_DIR=resolve_path(os.getenv("PHOTO_DIR", ""), default=Path("photos")),
            CHROMA_DB_PATH=resolve_path(os.getenv("CHROMA_DB_PATH", ""), default=Path("chroma_db")),
            AUTOTEST_DIR=resolve_path(os.getenv("AUTOTEST_DIR", ""), default=Path("autotest_uploads")),
            AUTOTEST_MODE=os.getenv("AUTOTEST_MODE", "real").strip().lower() or "real",
            ALLOWED_ORIGINS=allowed_origins,
            AUTOTEST_MAX_FILES=int(os.getenv("AUTOTEST_MAX_FILES", "5000")),
            AUTOTEST_MAX_UNZIPPED_BYTES=int(os.getenv("AUTOTEST_MAX_UNZIPPED_BYTES", str(250 * 1024 * 1024))),
            AUTOTEST_TIMEOUT_SECONDS=int(
                os.getenv("AUTOTEST_TIMEOUT_SECONDS")
                or os.getenv("AUTOTEST_STEP_TIMEOUT_SECONDS")
                or "300"
            ),
            AUTOTEST_RLIMIT_CPU_SECONDS=int(os.getenv("AUTOTEST_RLIMIT_CPU_SECONDS", "310")),
            AUTOTEST_RLIMIT_AS_MB=int(os.getenv("AUTOTEST_RLIMIT_AS_MB", "2048")),
            AUTOTEST_RLIMIT_FSIZE_MB=int(os.getenv("AUTOTEST_RLIMIT_FSIZE_MB", "200")),
            OCR_ENABLED=os.getenv("OCR_ENABLED", "true").lower() == "true",
            LLM_PROVIDER=os.getenv("LLM_PROVIDER", "ollama"),
            LLM_MODEL=os.getenv("LLM_MODEL", "llama3.1"),
        )
        
        # Validate critical settings
        errors = []
        if not settings.JWT_SECRET or settings.JWT_SECRET.startswith("replace-with-a-long-random-secret"):
            errors.append("JWT_SECRET must be set to a secure value (min 32 characters)")
        elif len(settings.JWT_SECRET) < 32:
            errors.append("JWT_SECRET must be at least 32 characters long")
        
        if errors:
            raise ValueError("; ".join(errors))
        
        return settings


# Global settings instance (lazy loaded)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.load_from_env()
    return _settings


def reload_settings() -> Settings:
    """Force reload settings from environment (useful for testing)."""
    global _settings
    _settings = Settings.load_from_env()
    return _settings
