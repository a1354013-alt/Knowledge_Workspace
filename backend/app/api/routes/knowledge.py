from __future__ import annotations

from fastapi import APIRouter

from app.api.handlers import knowledge as knowledge_handlers
from app.models import (
    KnowledgeEntryPageResponse,
    KnowledgeRevisionDiffResponse,
    KnowledgeRevisionResponse,
    MessageResponse,
)

router = APIRouter()

router.add_api_route(
    "/api/knowledge/entries",
    knowledge_handlers.list_knowledge_entries,
    methods=["GET"],
    response_model=KnowledgeEntryPageResponse,
)
router.add_api_route(
    "/api/knowledge/entries",
    knowledge_handlers.create_knowledge_entry,
    methods=["POST"],
    response_model=MessageResponse,
)
router.add_api_route(
    "/api/knowledge/entries/{entry_id}",
    knowledge_handlers.update_knowledge_entry,
    methods=["PATCH"],
    response_model=MessageResponse,
)
router.add_api_route(
    "/api/knowledge/{entry_id}/revisions",
    knowledge_handlers.list_knowledge_revisions,
    methods=["GET"],
    response_model=list[KnowledgeRevisionResponse],
)
router.add_api_route(
    "/api/knowledge/{entry_id}/revisions/{revision_id}/diff",
    knowledge_handlers.get_knowledge_revision_diff,
    methods=["GET"],
    response_model=KnowledgeRevisionDiffResponse,
)
router.add_api_route(
    "/api/knowledge/{entry_id}/revisions/{revision_id}/restore",
    knowledge_handlers.restore_knowledge_revision,
    methods=["POST"],
    response_model=MessageResponse,
)
