from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings


class LLMProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    raw: dict[str, Any] | None = None


class LLMProvider:
    name: str

    async def healthcheck(self) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    async def generate(self, *, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:  # pragma: no cover - interface
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_s = float(timeout_s)

    async def healthcheck(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def generate(self, *, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": float(temperature)},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc

        content = (data.get("message", {}) or {}).get("content", "")
        if not isinstance(content, str):
            content = str(content)
        return LLMResponse(text=content, provider=self.name, model=self.model, raw=data if isinstance(data, dict) else None)


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, *, model: str = "mock") -> None:
        self.model = model

    async def healthcheck(self) -> bool:
        return True

    async def generate(self, *, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:
        _ = system, temperature
        text = f"[mock] {prompt[:2000]}"
        return LLMResponse(text=text, provider=self.name, model=self.model, raw=None)


class NoopProvider(LLMProvider):
    """
    Graceful fallback provider that never fails but returns empty output.
    """

    name = "none"

    def __init__(self) -> None:
        self.model = "none"

    async def healthcheck(self) -> bool:
        return True

    async def generate(self, *, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:
        _ = prompt, system, temperature
        return LLMResponse(text="", provider=self.name, model=self.model, raw=None)


class FallbackProvider(LLMProvider):
    name = "fallback"

    def __init__(self, providers: list[LLMProvider]) -> None:
        self.providers = [provider for provider in providers if provider is not None]
        self.model = ",".join(getattr(provider, "model", provider.name) for provider in self.providers) or "none"

    async def healthcheck(self) -> bool:
        for provider in self.providers:
            if await provider.healthcheck():
                return True
        return False

    async def generate(self, *, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                return await provider.generate(prompt=prompt, system=system, temperature=temperature)
            except Exception as exc:
                last_error = exc
                continue
        raise LLMProviderError(f"All LLM providers failed. Last error: {last_error}")
