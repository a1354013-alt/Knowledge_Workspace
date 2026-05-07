from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main

router = APIRouter()

router.add_api_route("/api/logbook/entries", legacy_main.list_logbook_entries, methods=["GET"])
router.add_api_route("/api/logbook/entries", legacy_main.create_logbook_entry, methods=["POST"])
router.add_api_route("/api/logbook/entries/{entry_id}", legacy_main.update_logbook_entry, methods=["PATCH"])
router.add_api_route(
    "/api/logbook/entries/{entry_id}/promote-to-knowledge",
    legacy_main.promote_logbook_to_knowledge,
    methods=["POST"],
)
router.add_api_route("/api/logbook/entries/{entry_id}", legacy_main.delete_logbook_entry, methods=["DELETE"])
