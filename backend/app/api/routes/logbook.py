from __future__ import annotations

from fastapi import APIRouter

from app.api.handlers import logbook as logbook_handlers
from app.models import LogbookEntryPageResponse, MessageResponse, PromoteToKnowledgeResponse

router = APIRouter()

router.add_api_route(
    "/api/logbook/entries",
    logbook_handlers.list_logbook_entries,
    methods=["GET"],
    response_model=LogbookEntryPageResponse,
)
router.add_api_route(
    "/api/logbook/entries", logbook_handlers.create_logbook_entry, methods=["POST"], response_model=MessageResponse
)
router.add_api_route(
    "/api/logbook/entries/{entry_id}",
    logbook_handlers.update_logbook_entry,
    methods=["PATCH"],
    response_model=MessageResponse,
)
router.add_api_route(
    "/api/logbook/entries/{entry_id}/promote-to-knowledge",
    logbook_handlers.promote_logbook_to_knowledge,
    methods=["POST"],
    response_model=PromoteToKnowledgeResponse,
)
router.add_api_route(
    "/api/logbook/entries/{entry_id}",
    logbook_handlers.delete_logbook_entry,
    methods=["DELETE"],
    response_model=MessageResponse,
)
