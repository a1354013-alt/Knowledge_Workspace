from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import requests

from app.core.config import get_settings

try:
    import chromadb
except ImportError:  # pragma: no cover - optional runtime dependency
    chromadb = None


logger = logging.getLogger("knowledge_workspace")

_EMBEDDING_FUNCTION = None
_COLLECTION = None
_KB_COLLECTION = None
_EMBEDDING_PROVIDER_KEY: tuple[str, str, str, float, bool] | None = None


@dataclass(frozen=True)
class EmbeddingProviderDescriptor:
    name: str
    kind: str
    demo_mode: bool
    semantic_search_ready: bool
    available: bool
    message: str
    details: tuple[str, ...] = ()


class BaseEmbeddingProvider:
    descriptor: EmbeddingProviderDescriptor

    def embedding_function(self):
        raise NotImplementedError


class DemoHashEmbeddingProvider(BaseEmbeddingProvider):
    descriptor = EmbeddingProviderDescriptor(
        name="demo-hash",
        kind="demo-fallback",
        demo_mode=True,
        semantic_search_ready=False,
        available=True,
        message="Deterministic demo/fallback embeddings are active. This is not production semantic search.",
        details=(
            "Designed for local demos, CI, and no-external-dependency environments.",
            "Use Ollama, sentence-transformers, or an OpenAI-compatible embedding API for semantic retrieval.",
        ),
    )

    def embedding_function(self):
        class SimpleHashEmbeddingFunction:
            """
            Lightweight, deterministic embedding function.

            This is intentionally a demo/fallback provider, not a real semantic model.
            """

            def __init__(self, *, dimension: int = 384) -> None:
                self.dimension = int(dimension)

            def name(self) -> str:
                return "knowledge-workspace-demo-hash"

            def is_legacy(self) -> bool:
                return False

            def default_space(self) -> str:
                return "cosine"

            def __call__(self, input: list[str]) -> list[list[float]]:
                vectors: list[list[float]] = []
                for text in input:
                    raw = text.encode("utf-8", errors="ignore")
                    seed = int(np.frombuffer(raw[:4].ljust(4, b"\0"), dtype=np.uint32)[0])
                    rng = np.random.default_rng(seed=seed)
                    vec = rng.standard_normal(self.dimension).astype(np.float32)
                    vec = vec / (np.linalg.norm(vec) + 1e-9)
                    vectors.append(vec.tolist())
                return vectors

            def embed_documents(self, input: list[str]) -> list[list[float]]:
                return self(input)

            def embed_query(self, input: str) -> list[float]:
                return self([input])[0]

        return SimpleHashEmbeddingFunction()


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, *, model: str, base_url: str, timeout_seconds: float) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.descriptor = EmbeddingProviderDescriptor(
            name="ollama",
            kind="ollama",
            demo_mode=False,
            semantic_search_ready=True,
            available=True,
            message=f"Ollama semantic embeddings are active with model '{self.model}'.",
            details=(f"base_url={self.base_url}", f"timeout_seconds={self.timeout_seconds:g}"),
        )

    def embedding_function(self):
        provider = self

        class OllamaEmbeddingFunction:
            def name(self) -> str:
                return f"knowledge-workspace-ollama-{provider.model}"

            def is_legacy(self) -> bool:
                return False

            def default_space(self) -> str:
                return "cosine"

            def _embed_one(self, text: str) -> list[float]:
                response = requests.post(
                    f"{provider.base_url}/api/embeddings",
                    json={"model": provider.model, "prompt": text},
                    timeout=provider.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                embedding = payload.get("embedding")
                if not isinstance(embedding, list) or not embedding:
                    raise RuntimeError("Ollama embedding response did not include an embedding vector.")
                return [float(value) for value in embedding]

            def __call__(self, input: list[str]) -> list[list[float]]:
                return [self._embed_one(text) for text in input]

            def embed_documents(self, input: list[str]) -> list[list[float]]:
                return self(input)

            def embed_query(self, input: str) -> list[float]:
                return self([input])[0]

        return OllamaEmbeddingFunction()


class SentenceTransformersEmbeddingProvider(BaseEmbeddingProvider):
    descriptor = EmbeddingProviderDescriptor(
        name="sentence-transformers",
        kind="sentence-transformers",
        demo_mode=False,
        semantic_search_ready=False,
        available=False,
        message="sentence-transformers embedding provider is not implemented yet in this runtime.",
        details=("Placeholder interface only.",),
    )

    def embedding_function(self):
        raise NotImplementedError("sentence-transformers embedding provider is a placeholder.")


class OpenAICompatibleEmbeddingProvider(BaseEmbeddingProvider):
    descriptor = EmbeddingProviderDescriptor(
        name="openai-compatible",
        kind="openai-compatible",
        demo_mode=False,
        semantic_search_ready=False,
        available=False,
        message="OpenAI-compatible embedding provider is not implemented yet in this runtime.",
        details=("Placeholder interface only.",),
    )

    def embedding_function(self):
        raise NotImplementedError("OpenAI-compatible embedding provider is a placeholder.")


_EMBEDDING_PROVIDER: BaseEmbeddingProvider = DemoHashEmbeddingProvider()


def _settings_provider_key() -> tuple[str, str, str, float, bool]:
    settings = get_settings()
    return (
        str(settings.EMBEDDING_PROVIDER or "demo_hash").strip().lower(),
        str(settings.EMBEDDING_MODEL or "nomic-embed-text").strip(),
        str(settings.EMBEDDING_BASE_URL or "http://localhost:11434").strip().rstrip("/"),
        float(settings.EMBEDDING_TIMEOUT_SECONDS),
        bool(settings.EMBEDDING_FALLBACK_ENABLED),
    )


def _fallback_descriptor(*, configured: str, reason: str) -> EmbeddingProviderDescriptor:
    demo = DemoHashEmbeddingProvider().descriptor
    return EmbeddingProviderDescriptor(
        name=configured,
        kind=demo.kind,
        demo_mode=demo.demo_mode,
        semantic_search_ready=False,
        available=demo.available,
        message=f"{reason} Falling back to deterministic demo hash embeddings.",
        details=demo.details,
    )


def _probe_ollama(base_url: str, timeout_seconds: float) -> tuple[bool, str]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout_seconds)
        response.raise_for_status()
        return True, ""
    except Exception as exc:
        return False, f"Ollama embedding provider is unavailable: {exc}"


def _build_embedding_provider() -> BaseEmbeddingProvider:
    provider_type, model, base_url, timeout_seconds, fallback_enabled = _settings_provider_key()
    normalized = provider_type.replace("-", "_")
    if normalized in {"demo_hash", "demo", "hash", "demo_fallback"}:
        return DemoHashEmbeddingProvider()
    if normalized == "ollama":
        available, reason = _probe_ollama(base_url, timeout_seconds)
        if available:
            return OllamaEmbeddingProvider(model=model, base_url=base_url, timeout_seconds=timeout_seconds)
        if fallback_enabled:
            class FallbackDemoHashEmbeddingProvider(DemoHashEmbeddingProvider):
                descriptor = _fallback_descriptor(configured="ollama", reason=reason)

            return FallbackDemoHashEmbeddingProvider()
        class UnavailableOllamaEmbeddingProvider(OllamaEmbeddingProvider):
            def __init__(self) -> None:
                self.descriptor = EmbeddingProviderDescriptor(
                    name="ollama",
                    kind="ollama",
                    demo_mode=False,
                    semantic_search_ready=False,
                    available=False,
                    message=reason,
                    details=(f"base_url={base_url}", f"model={model}"),
                )

            def embedding_function(self):
                raise RuntimeError(reason)

        return UnavailableOllamaEmbeddingProvider()
    if fallback_enabled:
        class UnknownFallbackProvider(DemoHashEmbeddingProvider):
            descriptor = _fallback_descriptor(
                configured=provider_type,
                reason=f"Unknown embedding provider '{provider_type}'.",
            )

        return UnknownFallbackProvider()
    return DemoHashEmbeddingProvider()


def _ensure_embedding_provider() -> BaseEmbeddingProvider:
    global _EMBEDDING_PROVIDER, _EMBEDDING_PROVIDER_KEY, _EMBEDDING_FUNCTION, _COLLECTION, _KB_COLLECTION
    key = _settings_provider_key()
    if key != _EMBEDDING_PROVIDER_KEY:
        _EMBEDDING_PROVIDER = _build_embedding_provider()
        _EMBEDDING_PROVIDER_KEY = key
        _EMBEDDING_FUNCTION = None
        _COLLECTION = None
        _KB_COLLECTION = None
    return _EMBEDDING_PROVIDER


def vector_db_unavailable_reason() -> str:
    if chromadb is None:
        return "Vector index unavailable: chromadb is not installed."
    return "Vector index unavailable: chromadb could not be initialized."


def get_embedding_provider_descriptor() -> EmbeddingProviderDescriptor:
    provider = _ensure_embedding_provider()
    if chromadb is None:
        descriptor = provider.descriptor
        return EmbeddingProviderDescriptor(
            name=descriptor.name,
            kind=descriptor.kind,
            demo_mode=descriptor.demo_mode,
            semantic_search_ready=False,
            available=False,
            message="Vector index unavailable: chromadb is not installed. Demo/fallback provider metadata is still available.",
            details=descriptor.details,
        )
    return provider.descriptor


def get_embedding_function():
    global _EMBEDDING_FUNCTION
    if _EMBEDDING_FUNCTION is not None:
        return _EMBEDDING_FUNCTION
    _EMBEDDING_FUNCTION = _ensure_embedding_provider().embedding_function()
    return _EMBEDDING_FUNCTION


def _get_client():
    settings = get_settings()
    if chromadb is None:
        return None
    try:
        return chromadb.PersistentClient(path=str(settings.CHROMA_DB_PATH))
    except Exception as exc:
        logger.warning("Failed to init chromadb client: %s", exc)
        return None


def get_collection():
    global _COLLECTION
    if _COLLECTION is not None:
        return _COLLECTION
    client = _get_client()
    if client is None:
        return None
    _COLLECTION = client.get_or_create_collection(
        name="documents",
        embedding_function=get_embedding_function(),
    )
    return _COLLECTION


def get_kb_collection():
    global _KB_COLLECTION
    if _KB_COLLECTION is not None:
        return _KB_COLLECTION
    client = _get_client()
    if client is None:
        return None
    _KB_COLLECTION = client.get_or_create_collection(
        name="knowledge_base",
        embedding_function=get_embedding_function(),
    )
    return _KB_COLLECTION


def add_to_vector_db(doc_id: str, chunks: list[str], metadata_list: list[dict[str, Any]]) -> bool:
    if chromadb is None:
        logger.warning("%s Document %s was not indexed.", vector_db_unavailable_reason(), doc_id)
        return False
    collection = get_collection()
    if collection is None:
        logger.warning("%s Document %s was not indexed.", vector_db_unavailable_reason(), doc_id)
        return False
    try:
        ids = [f"{doc_id}_{index}" for index in range(len(chunks))]
        collection.upsert(ids=ids, documents=chunks, metadatas=metadata_list)
        return True
    except Exception as exc:
        logger.error("Failed to add document %s to vector DB: %s", doc_id, exc)
        return False


def query_vector_db(question: str, user_id: str, n_results: int = 5) -> list[tuple[str, str, dict[str, Any]]]:
    if chromadb is None:
        logger.warning("chromadb not installed; QA search is disabled.")
        return []
    collection = get_collection()
    if collection is None:
        return []
    try:
        where_filter: dict[str, Any] = {"$and": [{"is_active": 1}, {"owner_user_id": user_id}]}
        results = collection.query(query_texts=[question], n_results=n_results, where=where_filter)
        output: list[tuple[str, str, dict[str, Any]]] = []
        for index, document in enumerate(results.get("documents", [[]])[0]):
            metadata = results.get("metadatas", [[]])[0][index]
            output.append((metadata.get("doc_id", ""), document, metadata))
        return output
    except Exception as exc:
        logger.error("Failed to query vector DB: %s", exc)
        return []


def add_to_kb_vector_db(item_id: str, chunks: list[str], metadata_list: list[dict[str, Any]]) -> bool:
    if chromadb is None:
        logger.warning("%s Knowledge item %s was not indexed.", vector_db_unavailable_reason(), item_id)
        return False
    collection = get_kb_collection()
    if collection is None:
        logger.warning("%s Knowledge item %s was not indexed.", vector_db_unavailable_reason(), item_id)
        return False
    try:
        ids = [f"{item_id}_{index}" for index in range(len(chunks))]
        collection.upsert(ids=ids, documents=chunks, metadatas=metadata_list)
        return True
    except Exception as exc:
        logger.error("Failed to add KB item %s to vector DB: %s", item_id, exc)
        return False


def query_kb_vector_db(question: str, user_id: str, n_results: int = 5) -> list[tuple[str, str, dict[str, Any]]]:
    if chromadb is None:
        logger.warning("chromadb not installed; KB search is disabled.")
        return []
    collection = get_kb_collection()
    if collection is None:
        return []
    try:
        where_filter: dict[str, Any] = {"$and": [{"is_active": 1}, {"owner_user_id": user_id}]}
        results = collection.query(query_texts=[question], n_results=n_results, where=where_filter)
        output: list[tuple[str, str, dict[str, Any]]] = []
        for index, document in enumerate(results.get("documents", [[]])[0]):
            metadata = results.get("metadatas", [[]])[0][index]
            output.append((metadata.get("item_id", ""), document, metadata))
        return output
    except Exception as exc:
        logger.error("Failed to query KB vector DB: %s", exc)
        return []


def delete_from_vector_db(doc_id: str) -> bool:
    if chromadb is None:
        logger.warning("%s Document %s was not de-indexed.", vector_db_unavailable_reason(), doc_id)
        return False
    collection = get_collection()
    if collection is None:
        logger.warning("%s Document %s was not de-indexed.", vector_db_unavailable_reason(), doc_id)
        return False
    try:
        collection.delete(where={"doc_id": doc_id})
        return True
    except Exception as exc:
        logger.error("Failed to delete document %s from vector DB: %s", doc_id, exc)
        return False


def delete_from_kb_vector_db(item_id: str) -> bool:
    if chromadb is None:
        logger.warning("%s Knowledge item %s was not de-indexed.", vector_db_unavailable_reason(), item_id)
        return False
    collection = get_kb_collection()
    if collection is None:
        logger.warning("%s Knowledge item %s was not de-indexed.", vector_db_unavailable_reason(), item_id)
        return False
    try:
        collection.delete(where={"item_id": item_id})
        return True
    except Exception as exc:
        logger.error("Failed to delete KB item %s from vector DB: %s", item_id, exc)
        return False


def count_vector_records_for_document(doc_id: str) -> int | None:
    if chromadb is None:
        return None
    collection = get_collection()
    if collection is None:
        return None
    try:
        result = collection.get(where={"doc_id": doc_id}, include=[])
        return len(result.get("ids", []))
    except Exception as exc:
        logger.error("Failed to count vector records for document %s: %s", doc_id, exc)
        return None


def count_vector_records_for_item(item_id: str) -> int | None:
    if chromadb is None:
        return None
    collection = get_kb_collection()
    if collection is None:
        return None
    try:
        result = collection.get(where={"item_id": item_id}, include=[])
        return len(result.get("ids", []))
    except Exception as exc:
        logger.error("Failed to count vector records for item %s: %s", item_id, exc)
        return None
