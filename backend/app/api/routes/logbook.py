from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main
from app.models import LogbookEntryResponse, MessageResponse, PromoteToKnowledgeResponse

router = APIRouter()

router.add_api_route(
    "/api/logbook/entries",
    legacy_main.list_logbook_entries,
    methods=["GET"],
    response_model=list[LogbookEntryResponse],
)
router.add_api_route("/api/logbook/entries", legacy_main.create_logbook_entry, methods=["POST"], response_model=MessageResponse)
router.add_api_route(
    "/api/logbook/entries/{entry_id}",
    legacy_main.update_logbook_entry,
    methods=["PATCH"],
    response_model=MessageResponse,
)
router.add_api_route(
    "/api/logbook/entries/{entry_id}/promote-to-knowledge",
    legacy_main.promote_logbook_to_knowledge,
    methods=["POST"],
    response_model=PromoteToKnowledgeResponse,
)
router.add_api_route(
    "/api/logbook/entries/{entry_id}",
    legacy_main.delete_logbook_entry,
    methods=["DELETE"],
    response_model=MessageResponse,
)
