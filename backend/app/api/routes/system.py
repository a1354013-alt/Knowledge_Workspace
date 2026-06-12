from __future__ import annotations

from fastapi import APIRouter

from app.api.handlers import items, prompts, qa, search, system, templates
from app.models import (
    GenerateResponse,
    HealthResponse,
    ItemLinksResponse,
    LoginResponse,
    MeResponse,
    MessageResponse,
    QAResponse,
    ResolveItemsResponse,
    SavedPromptPageResponse,
    SavedPromptResponse,
    TemplatesMetaResponse,
)

router = APIRouter()

router.add_api_route("/health", system.healthcheck, methods=["GET"], response_model=HealthResponse)
router.add_api_route("/api/health", system.api_healthcheck, methods=["GET"], response_model=HealthResponse)
router.add_api_route("/api/login", system.login, methods=["POST"], response_model=LoginResponse)
router.add_api_route("/api/me", system.me, methods=["GET"], response_model=MeResponse)
router.add_api_route("/api/search", search.global_search, methods=["GET"], response_model=ResolveItemsResponse)
router.add_api_route("/api/item-links", items.list_item_links, methods=["GET"], response_model=ItemLinksResponse)
router.add_api_route("/api/items/resolve", items.resolve_items, methods=["POST"], response_model=ResolveItemsResponse)
router.add_api_route("/api/qa", qa.qa, methods=["POST"], response_model=QAResponse)
router.add_api_route("/api/generate", qa.generate, methods=["POST"], response_model=GenerateResponse)
router.add_api_route(
    "/api/prompts", prompts.list_saved_prompts, methods=["GET"], response_model=SavedPromptPageResponse
)
router.add_api_route("/api/prompts", prompts.create_saved_prompt, methods=["POST"], response_model=SavedPromptResponse)
router.add_api_route(
    "/api/prompts/{prompt_id}", prompts.delete_saved_prompt, methods=["DELETE"], response_model=MessageResponse
)
router.add_api_route(
    "/api/meta/templates", templates.list_templates, methods=["GET"], response_model=TemplatesMetaResponse
)
