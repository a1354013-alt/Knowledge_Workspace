from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.api.common import (
    build_links_response,
    normalize_related_item_ids,
    resolve_item_summary,
)
from app.dependencies import get_current_user
from app.models import ItemLinksResponse, ItemSummary, ResolveItemsRequest, ResolveItemsResponse


async def list_item_links(item_id: str, current_user: dict = Depends(get_current_user)) -> ItemLinksResponse:
    normalized_item_id = str(item_id or "").strip()
    summary = resolve_item_summary(item_id=normalized_item_id, user_id=current_user["sub"])
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return build_links_response(item_id=normalized_item_id, user_id=current_user["sub"])


async def resolve_items(request: ResolveItemsRequest, current_user: dict = Depends(get_current_user)) -> ResolveItemsResponse:
    user_id = current_user["sub"]
    items: list[ItemSummary] = []
    for item_id in normalize_related_item_ids(request.item_ids):
        summary = resolve_item_summary(item_id=item_id, user_id=user_id)
        if summary:
            items.append(summary)
    return ResolveItemsResponse(items=items)
