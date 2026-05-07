from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main

router = APIRouter()

router.add_api_route("/api/knowledge/entries", legacy_main.list_knowledge_entries, methods=["GET"])
router.add_api_route("/api/knowledge/entries", legacy_main.create_knowledge_entry, methods=["POST"])
router.add_api_route("/api/knowledge/entries/{entry_id}", legacy_main.update_knowledge_entry, methods=["PATCH"])
router.add_api_route("/api/knowledge/{entry_id}/revisions", legacy_main.list_knowledge_revisions, methods=["GET"])
router.add_api_route(
    "/api/knowledge/{entry_id}/revisions/{revision_id}/diff",
    legacy_main.get_knowledge_revision_diff,
    methods=["GET"],
)
router.add_api_route(
    "/api/knowledge/{entry_id}/revisions/{revision_id}/restore",
    legacy_main.restore_knowledge_revision,
    methods=["POST"],
)
