from app.api.handlers.support import (
    Depends,
    ItemLinksResponse,
    ItemSummary,
    ResolveItemsRequest,
    ResolveItemsResponse,
    build_links_response,
    get_current_user,
    normalize_related_item_ids,
    resolve_item_summary,
)


async def list_item_links(item_id: str, current_user: dict = Depends(get_current_user)) -> ItemLinksResponse:
    return build_links_response(item_id=str(item_id or "").strip(), user_id=current_user["sub"])


async def resolve_items(request: ResolveItemsRequest, current_user: dict = Depends(get_current_user)) -> ResolveItemsResponse:
    user_id = current_user["sub"]
    items: list[ItemSummary] = []
    for item_id in normalize_related_item_ids(request.item_ids):
        summary = resolve_item_summary(item_id=item_id, user_id=user_id)
        if summary:
            items.append(summary)
    return ResolveItemsResponse(items=items)
