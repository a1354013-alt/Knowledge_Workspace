from __future__ import annotations

import asyncio
import importlib
from pathlib import Path


async def _perform(question: str, *, user_id: str, db):
    core = importlib.import_module("app.services.core")
    return await core.perform_qa(question, user_id, db)


def test_qa_vector_results_are_mapped_to_canonical_source_types_runtime(app_module, monkeypatch):
    core = importlib.import_module("app.services.core")

    class Response:
        text = "answer"

    class Provider:
        async def generate(self, **kwargs):
            return Response()

    monkeypatch.setattr(core, "get_llm_provider", lambda: (Provider(), {}))
    monkeypatch.setattr(core, "query_vector_db", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        core,
        "query_kb_vector_db",
        lambda *args, **kwargs: [
            ("prompt:prompt-1", "Prompt content", {"item_type": "saved_prompt", "title": "Prompt title"})
        ],
    )

    answer, sources = asyncio.run(_perform("prompt", user_id="owner", db=app_module.db))
    assert answer == "answer"
    assert sources[0].source_type == "prompt"


def test_qa_fallback_search_uses_persisted_fulltext_for_all_supported_types(app_module, monkeypatch):
    core = importlib.import_module("app.services.core")
    indexing_service = importlib.import_module("app.services.indexing_service")

    uploads_dir = Path(app_module.legacy_main.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "guide.txt").write_text("Document fallback needle", encoding="utf-8")

    assert app_module.db.add_document(
        doc_id="doc-fallback",
        filename="guide.txt",
        saved_filename="guide.txt",
        file_size=24,
        uploaded_by="owner",
        category="notes",
        tags="fallback",
        status="reviewed",
    )
    indexing_service.sync_document_index(app_module.db.get_document("doc-fallback"))

    assert app_module.db.add_knowledge_entry(
        entry_id="knowledge-fallback",
        title="Knowledge title",
        status="draft",
        problem="Knowledge fallback needle",
        root_cause="",
        solution="Knowledge solution",
        tags="fallback",
        notes="",
        created_by="owner",
    )
    indexing_service.sync_knowledge_entry_index(app_module.db.get_knowledge_entry("knowledge-fallback"))

    assert app_module.db.add_logbook_entry(
        entry_id="logbook-fallback",
        title="Logbook title",
        status="draft",
        run_id="",
        problem="Logbook fallback needle",
        root_cause="",
        solution="Logbook solution",
        tags="fallback",
        source_type="manual",
        created_by="owner",
    )
    indexing_service.sync_logbook_entry_index(app_module.db.get_logbook_entry("logbook-fallback"))

    assert app_module.db.add_saved_prompt(
        prompt_id="prompt-fallback",
        title="Prompt title",
        content="Prompt fallback needle",
        tags="fallback",
        created_by="owner",
    )
    indexing_service.sync_prompt_index(app_module.db.get_saved_prompt("prompt-fallback"))

    assert app_module.db.add_photo(
        photo_id="photo-fallback",
        filename="photo.png",
        saved_filename="photo.png",
        tags="fallback",
        description="Photo fallback needle",
        ocr_text="OCR fallback needle",
        file_size=10,
        uploaded_by="owner",
        status="reviewed",
    )
    indexing_service.sync_photo_index(app_module.db.get_photo("photo-fallback"))

    monkeypatch.setattr(core, "query_vector_db", lambda *args, **kwargs: [])
    monkeypatch.setattr(core, "query_kb_vector_db", lambda *args, **kwargs: [])

    class Response:
        text = "fallback answer"

    class Provider:
        async def generate(self, **kwargs):
            return Response()

    monkeypatch.setattr(core, "get_llm_provider", lambda: (Provider(), {}))

    for query, expected_source_type in (
        ("Document fallback needle", "document"),
        ("Knowledge fallback needle", "knowledge"),
        ("Logbook fallback needle", "logbook"),
        ("Prompt fallback needle", "prompt"),
        ("Photo fallback needle", "photo"),
    ):
        answer, sources = asyncio.run(_perform(query, user_id="owner", db=app_module.db))
        assert answer == "fallback answer"
        assert any(source.source_type == expected_source_type for source in sources), (query, sources)
