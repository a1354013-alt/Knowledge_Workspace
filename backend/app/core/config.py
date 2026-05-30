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
    IMAGE_MAX_PIXELS: int = 40_000_000

    # Vector DB
    CHROMA_DB_PATH: Path = Field(default=Path("chroma_db"))
    EMBEDDING_PROVIDER: str = "demo_hash"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_TIMEOUT_SECONDS: float = 5.0
    EMBEDDING_FALLBACK_ENABLED: bool = True

    # AutoTest working area
    AUTOTEST_DIR: Path = Field(default=Path("autotest_uploads"))
    AUTOTEST_MODE: str = "simulated"
    KW_AUTOTEST_REAL_MODE: bool = False
    KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST: bool = False
    AUTOTEST_SANDBOX_BACKEND: str = "disabled"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    # AutoTest Settings
    AUTOTEST_MAX_FILES: int = 5000
    AUTOTEST_MAX_UNZIPPED_BYTES: int = 250 * 1024 * 1024  # 250MB
    AUTOTEST_TIMEOUT_SECONDS: int = 300
    AUTOTEST_RLIMIT_CPU_SECONDS: int = 310
    AUTOTEST_RLIMIT_AS_MB: int = 2048
    AUTOTEST_RLIMIT_FSIZE_MB: int = 200
    AUTOTEST_STALE_RUN_MINUTES: int = 30
    AUTOTEST_DOCKER_IMAGE: str = "python:3.11-slim"
    AUTOTEST_DOCKER_NETWORK: bool = False
    AUTOTEST_DOCKER_MEMORY: str = "2g"
    AUTOTEST_DOCKER_CPUS: str = "2"
    AUTOTEST_DOCKER_USER: str = ""
    AUTOTEST_ARTIFACT_DIR: Path = Field(default=Path("autotest_artifacts"))

    # OCR Settings
    OCR_ENABLED: bool = True

    # LLM Settings
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"

    @classmethod
    def load_from_env(cls) -> "Settings":
        """Load settings from environment variables with validation."""
        backend_dir = Path(__file__).resolve().parents[2]

        def parse_bool(raw: str, *, default: bool) -> bool:
            value = (raw or "").strip().lower()
            if value in {"1", "true", "yes", "y", "on"}:
                return True
            if value in {"0", "false", "no", "n", "off"}:
                return False
            return bool(default)

        def resolve_path(raw: str, *, default: Path) -> Path:
            value = (raw or "").strip()
            if value == ":memory:":
                return Path(value)
            path = default if not value else Path(value)
            if not path.is_absolute():
                path = backend_dir / path
            return path

        # Read version file
        try:
            repo_root = Path(__file__).resolve().parents[3]
            version_path = repo_root / "VERSION"
            app_version = version_path.read_text(encoding="utf-8").strip() or "0.0.0"
        except OSError:
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
            DATABASE_PATH=(
                Path(":memory:")
                if os.getenv("PYTEST_CURRENT_TEST")
                else resolve_path(os.getenv("DATABASE_PATH", ""), default=Path("documents.db"))
            ),
            UPLOAD_DIR=resolve_path(os.getenv("UPLOAD_DIR", ""), default=Path("uploads")),
            MAX_FILE_SIZE=int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024))),
            PHOTO_DIR=resolve_path(os.getenv("PHOTO_DIR", ""), default=Path("photos")),
            IMAGE_MAX_PIXELS=int(os.getenv("IMAGE_MAX_PIXELS", "40000000")),
            CHROMA_DB_PATH=resolve_path(os.getenv("CHROMA_DB_PATH", ""), default=Path("chroma_db")),
            EMBEDDING_PROVIDER=(
                os.getenv("EMBEDDING_PROVIDER")
                or os.getenv("KW_EMBEDDING_PROVIDER")
                or "demo_hash"
            ).strip().lower(),
            EMBEDDING_MODEL=(
                os.getenv("EMBEDDING_MODEL")
                or os.getenv("OLLAMA_EMBEDDING_MODEL")
                or "nomic-embed-text"
            ).strip(),
            EMBEDDING_BASE_URL=(
                os.getenv("EMBEDDING_BASE_URL")
                or os.getenv("OLLAMA_EMBEDDING_BASE_URL")
                or os.getenv("OLLAMA_BASE_URL")
                or "http://localhost:11434"
            ).strip().rstrip("/"),
            EMBEDDING_TIMEOUT_SECONDS=float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "5")),
            EMBEDDING_FALLBACK_ENABLED=parse_bool(os.getenv("EMBEDDING_FALLBACK_ENABLED", "true"), default=True),
            AUTOTEST_DIR=resolve_path(os.getenv("AUTOTEST_DIR", ""), default=Path("autotest_uploads")),
            AUTOTEST_MODE=os.getenv("AUTOTEST_MODE", "simulated").strip().lower() or "simulated",
            KW_AUTOTEST_REAL_MODE=parse_bool(
                os.getenv("KW_AUTOTEST_REAL_MODE", "0"),
                default=False,
            ),
            KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=parse_bool(
                os.getenv("KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST", "0"),
                default=False,
            ),
            AUTOTEST_SANDBOX_BACKEND=(
                os.getenv("AUTOTEST_SANDBOX_BACKEND", "disabled") or "disabled"
            ).strip().lower(),
            ALLOWED_ORIGINS=allowed_origins,
            AUTOTEST_MAX_FILES=int(os.getenv("AUTOTEST_MAX_FILES", "5000")),
            AUTOTEST_MAX_UNZIPPED_BYTES=int(os.getenv("AUTOTEST_MAX_UNZIPPED_BYTES", str(250 * 1024 * 1024))),
            AUTOTEST_TIMEOUT_SECONDS=int(
                os.getenv("AUTOTEST_TIMEOUT_SECONDS") or os.getenv("AUTOTEST_STEP_TIMEOUT_SECONDS") or "300"
            ),
            AUTOTEST_RLIMIT_CPU_SECONDS=int(os.getenv("AUTOTEST_RLIMIT_CPU_SECONDS", "310")),
            AUTOTEST_RLIMIT_AS_MB=int(os.getenv("AUTOTEST_RLIMIT_AS_MB", "2048")),
            AUTOTEST_RLIMIT_FSIZE_MB=int(os.getenv("AUTOTEST_RLIMIT_FSIZE_MB", "200")),
            AUTOTEST_STALE_RUN_MINUTES=int(os.getenv("AUTOTEST_STALE_RUN_MINUTES", "30")),
            AUTOTEST_DOCKER_IMAGE=os.getenv("AUTOTEST_DOCKER_IMAGE", "python:3.11-slim").strip() or "python:3.11-slim",
            AUTOTEST_DOCKER_NETWORK=parse_bool(os.getenv("AUTOTEST_DOCKER_NETWORK", "false"), default=False),
            AUTOTEST_DOCKER_MEMORY=os.getenv("AUTOTEST_DOCKER_MEMORY", "2g").strip() or "2g",
            AUTOTEST_DOCKER_CPUS=os.getenv("AUTOTEST_DOCKER_CPUS", "2").strip() or "2",
            AUTOTEST_DOCKER_USER=(os.getenv("AUTOTEST_DOCKER_USER", "") or "").strip(),
            AUTOTEST_ARTIFACT_DIR=resolve_path(os.getenv("AUTOTEST_ARTIFACT_DIR", ""), default=Path("autotest_artifacts")),
            OCR_ENABLED=parse_bool(os.getenv("OCR_ENABLED", "true"), default=True),
            LLM_PROVIDER=(os.getenv("LLM_PROVIDER", "ollama") or "ollama").strip().lower(),
            OLLAMA_BASE_URL=(
                os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434"
            ).strip(),
            OLLAMA_MODEL=(os.getenv("OLLAMA_MODEL", "llama3.1") or "llama3.1").strip(),
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
