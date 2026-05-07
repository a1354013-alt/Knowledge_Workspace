from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main

router = APIRouter()

router.add_api_route("/health", legacy_main.healthcheck, methods=["GET"])
router.add_api_route("/api/health", legacy_main.api_healthcheck, methods=["GET"])
router.add_api_route("/api/login", legacy_main.login, methods=["POST"])
router.add_api_route("/api/me", legacy_main.me, methods=["GET"])
router.add_api_route("/api/search", legacy_main.global_search, methods=["GET"])
router.add_api_route("/api/item-links", legacy_main.list_item_links, methods=["GET"])
router.add_api_route("/api/items/resolve", legacy_main.resolve_items, methods=["POST"])
router.add_api_route("/api/qa", legacy_main.qa, methods=["POST"])
router.add_api_route("/api/generate", legacy_main.generate, methods=["POST"])
router.add_api_route("/api/prompts", legacy_main.list_saved_prompts, methods=["GET"])
router.add_api_route("/api/prompts", legacy_main.create_saved_prompt, methods=["POST"])
router.add_api_route("/api/prompts/{prompt_id}", legacy_main.delete_saved_prompt, methods=["DELETE"])
router.add_api_route("/api/meta/templates", legacy_main.list_templates, methods=["GET"])
