from __future__ import annotations

import os

from .providers import FallbackProvider, LLMProvider, MockProvider, NoopProvider, OllamaProvider


def validate_env_vars() -> None:
    """
    Validate required environment variables at startup.
    Raises RuntimeError if critical configuration is missing.
    """
    errors: list[str] = []
    
    # Validate JWT_SECRET
    jwt_secret = os.getenv("JWT_SECRET", "")
    if not jwt_secret or jwt_secret == "replace-with-a-long-random-secret":
        errors.append(
            "JWT_SECRET is not set or still using default value. "
            "Please set a strong random secret (at least 32 characters)."
        )
    elif len(jwt_secret) < 32:
        errors.append(
            f"JWT_SECRET is too short ({len(jwt_secret)} chars). "
            "Please use at least 32 characters for security."
        )
    
    # Validate OLLAMA_BASE_URL format if provided
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if ollama_url and not ollama_url.startswith(("http://", "https://")):
        errors.append(
            f"OLLAMA_BASE_URL must start with http:// or https:// (got: {ollama_url})"
        )
    
    # Warn about weak default password (log only, don't fail)
    default_pwd = os.getenv("DEFAULT_OWNER_PASSWORD", os.getenv("DEFAULT_ADMIN_PASSWORD", ""))
    if default_pwd in ("ChangeMe123!", "owner12345", "admin123"):
        import logging
        logger = logging.getLogger("enterprise_ai")
        logger.warning(
            "DEFAULT_OWNER_PASSWORD is set to a weak default value. "
            "Please change it in production."
        )
    
    if errors:
        raise RuntimeError("\n".join(errors))


def get_llm_provider() -> tuple[LLMProvider, dict[str, object]]:
    """
    Returns (provider, status_dict) where status_dict is safe to expose via API.

    Defaults to Ollama with graceful fallback behavior:
    - If Ollama is down, API endpoints should continue to work in retrieval-only mode.
    """

    provider_name = (os.getenv("LLM_PROVIDER", "ollama") or "ollama").strip().lower()

    if provider_name == "mock":
        provider: LLMProvider = MockProvider()
    elif provider_name == "fallback":
        provider = FallbackProvider([OllamaProvider(), NoopProvider()])
    else:
        provider = FallbackProvider([OllamaProvider(), NoopProvider()])

    status = {
        "provider": getattr(provider, "name", "unknown"),
        "model": getattr(provider, "model", ""),
        "base_url": getattr(provider, "base_url", ""),
        "fallback_mode": isinstance(provider, FallbackProvider),
    }
    return provider, status
