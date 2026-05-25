from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.errors import api_error
from app.dependencies import get_current_user
from app.models import IndexRebuildResponse, IndexStatusResponse
from app.services import indexing_service

router = APIRouter()


@router.get("/api/index/status", response_model=IndexStatusResponse)
async def get_index_status(current_user: dict = Depends(get_current_user)) -> IndexStatusResponse:
    return indexing_service.get_index_status(current_user)


@router.post("/api/index/rebuild", response_model=IndexRebuildResponse)
async def rebuild_all_indexes(current_user: dict = Depends(get_current_user)) -> IndexRebuildResponse:
    return indexing_service.rebuild_all_indexes(current_user)


@router.post("/api/index/rebuild/{item_type}/{item_id}", response_model=IndexRebuildResponse)
async def rebuild_single_index(
    item_type: str, item_id: str, current_user: dict = Depends(get_current_user)
) -> IndexRebuildResponse:
    normalized_type = str(item_type or "").strip().lower()
    if normalized_type not in {"document", "knowledge", "logbook", "photo", "prompt"}:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_index_item_type",
            message="Unsupported index item type.",
            details={"item_type": normalized_type},
        )
    try:
        return indexing_service.rebuild_single_item(current_user, normalized_type, item_id)
    except LookupError as exc:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="index_item_not_found",
            message=str(exc),
        ) from exc
