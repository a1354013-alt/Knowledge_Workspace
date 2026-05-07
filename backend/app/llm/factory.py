from __future__ import annotations

import os

from app.core.config import get_settings

from .providers import FallbackProvider, LLMProvider, MockProvider, NoopProvider, OllamaProvider


def validate_env_vars() -> None:
    """
    Validate required environment variables at startup.
    Raises RuntimeError if critical configuration is missing.
    """
    # Core settings validation (JWT_SECRET, paths, etc.)
    try:
        settings = get_settings()
    except Exception as exc:  # pragma: no cover - startup guard
        raise RuntimeError(str(exc)) from exc

    errors: list[str] = []

    # Validate OLLAMA_BASE_URL format if provided
    ollama_url = (settings.OLLAMA_BASE_URL or "").strip()
    if ollama_url and not ollama_url.startswith(("http://", "https://")):
        errors.append(f"OLLAMA_BASE_URL must start with http:// or https:// (got: {ollama_url})")

    # Warn about weak default password (log only, don't fail)
    default_pwd = os.getenv("DEFAULT_OWNER_PASSWORD", "")
    if default_pwd in ("ChangeMe123!", "owner12345", "admin123"):
        import logging

        logger = logging.getLogger("knowledge_workspace")
        logger.warning("DEFAULT_OWNER_PASSWORD is set to a weak value. Please change it in production.")

    if errors:
        raise RuntimeError("\n".join(errors))


def get_llm_provider() -> tuple[LLMProvider, dict[str, object]]:
    """
    Returns (provider, status_dict) where status_dict is safe to expose via API.

    Defaults to Ollama with graceful fallback behavior:
    - If Ollama is down, API endpoints should continue to work in retrieval-only mode.
    """

    settings = get_settings()
    provider_name = (settings.LLM_PROVIDER or "ollama").strip().lower()

    primary_provider: LLMProvider
    fallback_provider: LLMProvider | None = None

    if provider_name == "mock":
        primary_provider = MockProvider()
        provider = primary_provider
    elif provider_name == "fallback":
        primary_provider = OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
        fallback_provider = NoopProvider()
        provider = FallbackProvider([primary_provider, fallback_provider])
    else:
        primary_provider = OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
        fallback_provider = NoopProvider()
        provider = FallbackProvider([primary_provider, fallback_provider])

    status = {
        "primary_provider": getattr(primary_provider, "name", "unknown"),
        "primary_provider_instance": primary_provider,
        "fallback_provider": getattr(fallback_provider, "name", "") if fallback_provider else "",
        "model": getattr(primary_provider, "model", getattr(provider, "model", "")),
        "base_url": getattr(primary_provider, "base_url", ""),
        "fallback_enabled": fallback_provider is not None,
        "primary_error_message": "",
    }
    return provider, status
