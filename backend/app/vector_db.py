from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.config import get_settings

try:
    import chromadb
except ImportError:  # pragma: no cover - optional runtime dependency
    chromadb = None


logger = logging.getLogger("knowledge_workspace")

_EMBEDDING_FUNCTION = None
_COLLECTION = None
_KB_COLLECTION = None


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
    descriptor = EmbeddingProviderDescriptor(
        name="ollama",
        kind="ollama",
        demo_mode=False,
        semantic_search_ready=False,
        available=False,
        message="Ollama embedding provider is not implemented yet in this runtime.",
        details=("Placeholder interface only.",),
    )

    def embedding_function(self):
        raise NotImplementedError("Ollama embedding provider is a placeholder.")


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


def vector_db_unavailable_reason() -> str:
    if chromadb is None:
        return "Vector index unavailable: chromadb is not installed."
    return "Vector index unavailable: chromadb could not be initialized."


def get_embedding_provider_descriptor() -> EmbeddingProviderDescriptor:
    if chromadb is None:
        descriptor = _EMBEDDING_PROVIDER.descriptor
        return EmbeddingProviderDescriptor(
            name=descriptor.name,
            kind=descriptor.kind,
            demo_mode=descriptor.demo_mode,
            semantic_search_ready=False,
            available=False,
            message="Vector index unavailable: chromadb is not installed. Demo/fallback provider metadata is still available.",
            details=descriptor.details,
        )
    return _EMBEDDING_PROVIDER.descriptor


def get_embedding_function():
    global _EMBEDDING_FUNCTION
    if _EMBEDDING_FUNCTION is not None:
        return _EMBEDDING_FUNCTION
    _EMBEDDING_FUNCTION = _EMBEDDING_PROVIDER.embedding_function()
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
        collection.add(ids=ids, documents=chunks, metadatas=metadata_list)
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
        collection.add(ids=ids, documents=chunks, metadatas=metadata_list)
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
