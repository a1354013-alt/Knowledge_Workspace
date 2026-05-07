from __future__ import annotations

from fastapi.testclient import TestClient

from app.llm.providers import MockProvider, NoopProvider


class UnhealthyProvider(MockProvider):
    async def healthcheck(self) -> bool:
        return False


def test_llm_settings_primary_healthy_returns_ready(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    primary = MockProvider(model="mock-primary")
    monkeypatch.setattr(
        app_module.dashboard_service,
        "get_llm_provider",
        lambda: (
            primary,
            {
                "primary_provider": "mock",
                "primary_provider_instance": primary,
                "fallback_provider": "",
                "fallback_provider_instance": None,
                "model": "mock-primary",
                "base_url": "",
                "fallback_enabled": False,
                "primary_error_message": "",
            },
        ),
    )

    response = client.get("/api/settings/llm", headers=auth_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["primary_healthy"] is True
    assert payload["active_provider"] == "mock"
    assert payload["llm_ready_for_generation"] is True
    assert payload["error_message"] == ""


def test_llm_settings_noop_fallback_is_not_ready_for_generation(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    primary = UnhealthyProvider(model="mock-primary")
    fallback = NoopProvider()
    monkeypatch.setattr(
        app_module.dashboard_service,
        "get_llm_provider",
        lambda: (
            primary,
            {
                "primary_provider": "ollama",
                "primary_provider_instance": primary,
                "fallback_provider": fallback.name,
                "fallback_provider_instance": fallback,
                "model": "llama3.1",
                "base_url": "http://localhost:11434",
                "fallback_enabled": True,
                "primary_error_message": "",
            },
        ),
    )

    response = client.get("/api/settings/llm", headers=auth_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["primary_healthy"] is False
    assert payload["fallback_enabled"] is True
    assert payload["active_provider"] == "none"
    assert payload["llm_ready_for_generation"] is False
    assert "noop only" in payload["error_message"].lower()


def test_llm_settings_healthy_real_fallback_returns_ready(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    primary = UnhealthyProvider(model="mock-primary")
    fallback = MockProvider(model="mock-fallback")
    monkeypatch.setattr(
        app_module.dashboard_service,
        "get_llm_provider",
        lambda: (
            primary,
            {
                "primary_provider": "ollama",
                "primary_provider_instance": primary,
                "fallback_provider": fallback.name,
                "fallback_provider_instance": fallback,
                "model": "llama3.1",
                "base_url": "http://localhost:11434",
                "fallback_enabled": True,
                "primary_error_message": "",
            },
        ),
    )

    response = client.get("/api/settings/llm", headers=auth_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["primary_healthy"] is False
    assert payload["active_provider"] == "mock"
    assert payload["llm_ready_for_generation"] is True
    assert "fallback provider" in payload["error_message"].lower()
