# ruff: noqa: F401,F403,F405
from app.api.handlers.support import *  # noqa: F403


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
    - status_filter: exact status match (e.g. draft/reviewed/verified/archived/passed/failed)
    - tag: tags substring match (where applicable)
    - date_from/date_to: ISO prefix comparisons (e.g. 2026-04-01)
    """
    user_id = current_user["sub"]
    requested_types = [part.strip() for part in str(types or "").split(",") if part.strip()]
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
            source_type=str(row.get("source_type") or ""),
            source_ref=str(row.get("source_ref") or ""),
        )
        for row in rows
    ]
    return ResolveItemsResponse(items=items)

