from __future__ import annotations


def test_embedding_settings_parse_provider_and_fallback(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://localhost:11434/")
    monkeypatch.setenv("EMBEDDING_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("EMBEDDING_FALLBACK_ENABLED", "0")

    settings = Settings.load_from_env()

    assert settings.EMBEDDING_PROVIDER == "ollama"
    assert settings.EMBEDDING_MODEL == "nomic-embed-text"
    assert settings.EMBEDDING_BASE_URL == "http://localhost:11434"
    assert settings.EMBEDDING_TIMEOUT_SECONDS == 2.5
    assert settings.EMBEDDING_FALLBACK_ENABLED is False


def test_ollama_embedding_provider_uses_mocked_api(monkeypatch):
    from app.vector_db import OllamaEmbeddingProvider

    calls: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"embedding": [0.1, 0.2, 0.3]}

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr("app.vector_db.requests.post", fake_post)

    provider = OllamaEmbeddingProvider(
        model="nomic-embed-text",
        base_url="http://ollama.test",
        timeout_seconds=1,
    )
    embedding = provider.embedding_function().embed_query("hello")

    assert embedding == [0.1, 0.2, 0.3]
    assert calls[0]["url"] == "http://ollama.test/api/embeddings"
    assert calls[0]["json"] == {"model": "nomic-embed-text", "prompt": "hello"}
    assert calls[0]["timeout"] == 1


def test_ollama_unavailable_falls_back_to_demo_hash(app_module, monkeypatch):
    import importlib

    _ = app_module
    vector_db = importlib.import_module("app.vector_db")
    vector_db.get_settings().EMBEDDING_PROVIDER = "ollama"
    vector_db.get_settings().EMBEDDING_FALLBACK_ENABLED = True
    vector_db.get_settings().EMBEDDING_BASE_URL = "http://ollama.test"

    class FakeResponse:
        def raise_for_status(self) -> None:
            raise RuntimeError("offline")

    monkeypatch.setattr(vector_db.requests, "get", lambda *args, **kwargs: FakeResponse())

    descriptor = vector_db.get_embedding_provider_descriptor()

    assert descriptor.kind == "demo-fallback"
    assert descriptor.demo_mode is True
    assert descriptor.semantic_search_ready is False
    assert "falling back" in descriptor.message.lower()


def test_index_status_reports_index_mode(client, auth_headers):
    response = client.get("/api/index/status", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"]["index_mode"] in {
        "full_text_only",
        "demo_hash_embedding",
        "real_semantic_embedding",
        "vector_degraded",
    }
