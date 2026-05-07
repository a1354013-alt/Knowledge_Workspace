from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main

router = APIRouter()

router.add_api_route("/api/dashboard/health", legacy_main.dashboard_health, methods=["GET"])
router.add_api_route("/api/settings/llm", legacy_main.llm_settings, methods=["GET"])
router.add_api_route("/api/settings/ocr", legacy_main.ocr_settings, methods=["GET"])
