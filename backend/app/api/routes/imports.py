from __future__ import annotations

from fastapi import APIRouter

from app.api.handlers import imports as import_handlers
from app.models import BulkImportResult

router = APIRouter()

router.add_api_route(
    "/api/import/knowledge",
    import_handlers.import_knowledge_entries,
    methods=["POST"],
    response_model=BulkImportResult,
)
router.add_api_route(
    "/api/import/logbook",
    import_handlers.import_logbook_entries,
    methods=["POST"],
    response_model=BulkImportResult,
)
router.add_api_route(
    "/api/import/prompts",
    import_handlers.import_prompts,
    methods=["POST"],
    response_model=BulkImportResult,
)
