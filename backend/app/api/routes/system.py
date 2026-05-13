from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main
from app.models import (
    GenerateResponse,
    HealthResponse,
    ItemLinksResponse,
    LoginResponse,
    MeResponse,
    MessageResponse,
    QAResponse,
    ResolveItemsResponse,
    SavedPromptResponse,
    TemplatesMetaResponse,
)

router = APIRouter()

router.add_api_route("/health", legacy_main.healthcheck, methods=["GET"], response_model=HealthResponse)
router.add_api_route("/api/health", legacy_main.api_healthcheck, methods=["GET"], response_model=HealthResponse)
router.add_api_route("/api/login", legacy_main.login, methods=["POST"], response_model=LoginResponse)
router.add_api_route("/api/me", legacy_main.me, methods=["GET"], response_model=MeResponse)
router.add_api_route("/api/search", legacy_main.global_search, methods=["GET"], response_model=ResolveItemsResponse)
router.add_api_route("/api/item-links", legacy_main.list_item_links, methods=["GET"], response_model=ItemLinksResponse)
router.add_api_route("/api/items/resolve", legacy_main.resolve_items, methods=["POST"], response_model=ResolveItemsResponse)
router.add_api_route("/api/qa", legacy_main.qa, methods=["POST"], response_model=QAResponse)
router.add_api_route("/api/generate", legacy_main.generate, methods=["POST"], response_model=GenerateResponse)
router.add_api_route("/api/prompts", legacy_main.list_saved_prompts, methods=["GET"], response_model=list[SavedPromptResponse])
router.add_api_route("/api/prompts", legacy_main.create_saved_prompt, methods=["POST"], response_model=SavedPromptResponse)
router.add_api_route("/api/prompts/{prompt_id}", legacy_main.delete_saved_prompt, methods=["DELETE"], response_model=MessageResponse)
router.add_api_route("/api/meta/templates", legacy_main.list_templates, methods=["GET"], response_model=TemplatesMetaResponse)
