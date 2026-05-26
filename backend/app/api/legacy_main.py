# ruff: noqa: F401,I001
from __future__ import annotations

import sys
from types import ModuleType

from app.api.handlers import (
    docs,
    items,
    knowledge,
    logbook,
    photos,
    prompts,
    qa as qa_handlers,
    search,
    support,
    system,
    templates,
)
from app.api.handlers.docs import (
    delete_own_document,
    download_document,
    list_document_references,
    list_documents,
    update_document,
    upload_document,
)
from app.api.handlers.items import list_item_links, resolve_items
from app.api.handlers.knowledge import (
    create_knowledge_entry,
    get_knowledge_revision_diff,
    list_knowledge_entries,
    list_knowledge_revisions,
    restore_knowledge_revision,
    update_knowledge_entry,
)
from app.api.handlers.logbook import (
    create_logbook_entry,
    delete_logbook_entry,
    list_logbook_entries,
    promote_logbook_to_knowledge,
    update_logbook_entry,
)
from app.api.handlers.photos import (
    delete_photo,
    download_photo,
    list_photo_references,
    list_photos,
    update_photo,
    upload_photo,
)
from app.api.handlers.prompts import create_saved_prompt, delete_saved_prompt, list_saved_prompts
from app.api.handlers.qa import generate, qa
from app.api.handlers.search import global_search
from app.api.runtime import (
    APP_VERSION,
    PHOTO_DIR,
    UPLOAD_DIR,
    create_token,
    db,
    lifespan,
    limiter,
)
from app.database import delete_from_kb_vector_db, delete_from_vector_db
from app.kb_index import index_knowledge_entry, index_logbook_entry, index_photo, index_saved_prompt
from fastapi.exceptions import RequestValidationError
from app.ocr_service import extract_text_from_image
from app.services.core import perform_qa, process_file
from app.api.handlers.system import (
    api_healthcheck,
    handle_validation_error,
    handle_value_error,
    healthcheck,
    login,
    me,
)
from app.api.handlers.templates import list_templates

_PATCH_TARGETS = (support, search, system, docs, knowledge, logbook, photos, items, qa_handlers, prompts, templates)


class _LegacyMainModule(ModuleType):
    """Compatibility bridge for tests and older imports.

    Older tests monkeypatch names on `app.api.legacy_main` and expect those
    patches to reach split handler modules. This module is deprecated as a
    primary entrypoint. Keep it only until:
    1. tests patch concrete route/service modules directly,
    2. runtime imports use `app.api.app_factory` plus routers/services, and
    3. release notes have announced the compatibility bridge removal.
    """

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for module in _PATCH_TARGETS:
            if hasattr(module, name):
                setattr(module, name, value)


sys.modules[__name__].__class__ = _LegacyMainModule
