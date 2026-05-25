from fastapi import HTTPException, status

from app.api.handlers.support import Depends, ItemSummary, ResolveItemsResponse, db, get_current_user
from app.repositories.search_repository import SUPPORTED_SEARCH_ITEM_TYPES
from app.source_types import canonicalize_source_type


async def global_search(
    q: str = "",
    types: str = "",
    status_filter: str = "",
    tag: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 200,
    current_user: dict = Depends(get_current_user),
) -> ResolveItemsResponse:
    """
    Global search across workspace entities.

    Query params:
    - q: keyword substring match
    - types: comma-separated list: knowledge,logbook,document,photo,prompt,autotest_run
      Unsupported values return HTTP 400.
    - status_filter: exact status match (e.g. draft/reviewed/verified/archived/passed/failed)
    - tag: tags substring match (where applicable)
    - date_from/date_to: ISO comparisons; a date-only date_to includes the full day (e.g. 2026-04-01)
    """
    user_id = current_user["sub"]
    requested_types = [part.strip() for part in str(types or "").split(",") if part.strip()]
    invalid_types = [item_type for item_type in requested_types if item_type not in SUPPORTED_SEARCH_ITEM_TYPES]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported search type(s): {', '.join(sorted(invalid_types))}",
        )
    rows = db.search_items(
        user_id=user_id,
        keyword=q,
        item_types=requested_types,
        status=status_filter,
        tag=tag,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    items = [
        ItemSummary(
            item_id=f"{row.get('item_type')}:{row.get('item_id')}",
            item_type=str(row.get("item_type") or ""),
            title=str(row.get("title") or ""),
            status=str(row.get("status") or ""),
            created_at=str(row.get("created_at") or ""),
            updated_at=str(row.get("updated_at") or ""),
            source_type=canonicalize_source_type(str(row.get("item_type") or "knowledge"))
            if str(row.get("item_type") or "").strip()
            in {"knowledge", "logbook", "document", "photo", "prompt"}
            else "",
            source_ref=str(row.get("source_ref") or ""),
        )
        for row in rows
    ]
    return ResolveItemsResponse(items=items)
