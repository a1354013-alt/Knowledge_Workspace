import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status

from app.api.common import item_id_from_parts, run_deindex_side_effect, run_index_side_effect, side_effect_warning
from app.api.runtime import db
from app.database import delete_from_kb_vector_db
from app.dependencies import get_current_user
from app.models import MessageResponse, SavedPromptCreateRequest, SavedPromptPageResponse, SavedPromptResponse
from app.repositories.repository_utils import normalize_index_status
from app.services.indexing_service import sync_prompt_index


def _side_effect_warning(message: str, warning: str | None) -> str:
    return side_effect_warning(message, warning)


_run_index_side_effect = run_index_side_effect
_run_deindex_side_effect = run_deindex_side_effect


def serialize_saved_prompt(row: dict) -> SavedPromptResponse:
    return SavedPromptResponse(
        id=row.get("prompt_id", ""),
        title=row.get("title", ""),
        content=row.get("content", ""),
        tags=row.get("tags", ""),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
        index_status=normalize_index_status(row.get("index_status"), is_active=row.get("is_active", 1)),
        index_error=row.get("index_error", "") or "",
    )


async def list_saved_prompts(
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: dict = Depends(get_current_user),
) -> SavedPromptPageResponse:
    user_id = current_user["sub"]
    rows = db.list_saved_prompts(user_id=user_id, limit=limit, offset=offset)
    total = db.count_saved_prompts(user_id=user_id)
    return SavedPromptPageResponse(
        items=[serialize_saved_prompt(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(rows) < total,
    )


async def create_saved_prompt(
    request: SavedPromptCreateRequest, current_user: dict = Depends(get_current_user)
) -> SavedPromptResponse:
    user_id = current_user["sub"]
    prompt_id = str(uuid.uuid4())
    ok = db.add_saved_prompt(
        prompt_id=prompt_id,
        title=request.title,
        content=request.content,
        tags=request.tags,
        created_by=user_id,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create prompt.")
    prompt = db.get_saved_prompt(prompt_id) or {}
    if prompt:
        warning = _run_index_side_effect(
            label="Prompt",
            item_id=prompt_id,
            operation=lambda: sync_prompt_index(prompt),
            on_error=lambda index_status, detail: db.update_saved_prompt_index(
                prompt_id, index_status=index_status, index_error=detail, indexed_at=""
            ),
        )
        if warning:
            db.queue_index_repair(
                item_id=item_id_from_parts("prompt", prompt_id),
                item_type="prompt",
                action="index",
                owner_user_id=str(user_id),
                last_error=warning,
            )
        else:
            db.resolve_index_repair(
                item_id=item_id_from_parts("prompt", prompt_id),
                action="index",
                owner_user_id=str(user_id),
            )
    else:
        warning = None
    prompt = db.get_saved_prompt(prompt_id) or prompt
    return SavedPromptResponse(
        id=prompt_id,
        title=str(prompt.get("title", "")),
        content=str(prompt.get("content", "")),
        tags=str(prompt.get("tags", "")),
        created_at=str(prompt.get("created_at", "")),
        updated_at=str(prompt.get("updated_at", "")),
        index_status=normalize_index_status(prompt.get("index_status"), is_active=prompt.get("is_active", 1)),
        index_error=str(prompt.get("index_error", "") or warning or ""),
    )


async def delete_saved_prompt(prompt_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    user_id = current_user["sub"]
    prompt = db.get_saved_prompt(prompt_id)
    if not prompt or int(prompt.get("is_active", 1)) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found.")
    if prompt.get("created_by") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this prompt.")
    warning = _run_deindex_side_effect(
        label="Prompt",
        item_id=prompt_id,
        operation=lambda: delete_from_kb_vector_db(f"prompt:{prompt_id}"),
    )
    if warning:
        db.queue_index_repair(
            item_id=item_id_from_parts("prompt", prompt_id),
            item_type="prompt",
            action="deindex",
            owner_user_id=str(user_id),
            last_error=warning,
        )
    else:
        db.resolve_index_repair(
            item_id=item_id_from_parts("prompt", prompt_id),
            action="deindex",
            owner_user_id=str(user_id),
        )
    db.delete_search_content(item_id_from_parts("prompt", prompt_id))
    db.delete_links(from_item_id=item_id_from_parts("prompt", prompt_id))
    db.delete_links(to_item_id=item_id_from_parts("prompt", prompt_id))
    if not db.delete_saved_prompt(prompt_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete prompt.")
    return MessageResponse(message=_side_effect_warning("Prompt deleted.", warning))
