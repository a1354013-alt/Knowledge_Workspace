from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api import legacy_main
from app.dependencies import get_current_user
from app.models import DashboardHealthResponse, SettingsLLMResponse, SettingsOCRResponse
from app.services import dashboard_service

router = APIRouter()


@router.get("/api/dashboard/health", response_model=DashboardHealthResponse)
async def dashboard_health(current_user: dict = Depends(get_current_user)) -> DashboardHealthResponse:
    return dashboard_service.get_dashboard_health(current_user["sub"])


@router.get("/api/settings/llm", response_model=SettingsLLMResponse)
async def llm_settings(current_user: dict = Depends(get_current_user)) -> SettingsLLMResponse:
    return await legacy_main.llm_settings(current_user=current_user)


@router.get("/api/settings/ocr", response_model=SettingsOCRResponse)
async def ocr_settings(current_user: dict = Depends(get_current_user)) -> SettingsOCRResponse:
    return await legacy_main.ocr_settings(current_user=current_user)
