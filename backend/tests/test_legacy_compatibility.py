from __future__ import annotations

import importlib


def test_legacy_main_monkeypatch_still_reaches_concrete_handlers(app_module, monkeypatch):
    docs_handlers = importlib.import_module("app.api.handlers.docs")

    original = docs_handlers.delete_from_vector_db
    try:
        replacement = lambda _doc_id: False
        monkeypatch.setattr(app_module.legacy_main, "delete_from_vector_db", replacement)
        assert docs_handlers.delete_from_vector_db is replacement
    finally:
        docs_handlers.delete_from_vector_db = original
