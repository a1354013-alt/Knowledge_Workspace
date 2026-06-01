from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import Response

from app.api.runtime import limiter
from app.dependencies import get_current_user
from app.models import (
    AutoTestCapabilitiesResponse,
    AutoTestRunListItemResponse,
    AutoTestRunResponse,
    GitHubAnalyzeRequest,
    GitHubAnalyzeResponse,
)
from app.services.autotest import service as autotest_service

router = APIRouter()


@router.get("/api/autotest/capabilities", response_model=AutoTestCapabilitiesResponse)
async def get_autotest_capabilities(current_user: dict = Depends(get_current_user)) -> AutoTestCapabilitiesResponse:
    _ = current_user
    return autotest_service.get_autotest_capabilities()


@router.post("/api/autotest/run", response_model=AutoTestRunResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def run_autotest(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> AutoTestRunResponse:
    _ = request
    return await autotest_service.run_autotest(file=file, current_user=current_user)


@router.get("/api/autotest/runs", response_model=list[AutoTestRunListItemResponse])
async def list_autotest_runs(current_user: dict = Depends(get_current_user)) -> list[AutoTestRunListItemResponse]:
    return autotest_service.list_autotest_runs(current_user=current_user)


@router.get("/api/autotest/runs/{run_id}", response_model=AutoTestRunResponse)
async def get_autotest_run(run_id: str, current_user: dict = Depends(get_current_user)) -> AutoTestRunResponse:
    return autotest_service.get_autotest_run(run_id=run_id, current_user=current_user)


@router.get("/api/autotest/{run_id}/export", response_model=None)
async def export_autotest_report(run_id: str, format: str, current_user: dict = Depends(get_current_user)) -> Response:
    return autotest_service.export_autotest_report(run_id=run_id, requested_format=format, current_user=current_user)


@router.post("/api/autotest/github/analyze", response_model=GitHubAnalyzeResponse)
async def analyze_github_repo(
    payload: GitHubAnalyzeRequest,
    current_user: dict = Depends(get_current_user),
) -> GitHubAnalyzeResponse:
    return autotest_service.analyze_github_repo(payload=payload, current_user=current_user)
