import uuid

from fastapi import Depends, HTTPException, status

from app.api.common import classify_index_failure, item_id_from_parts, side_effect_warning
from app.api.runtime import db, logger
from app.database import delete_from_kb_vector_db
from app.dependencies import get_current_user
from app.models import MessageResponse, SavedPromptCreateRequest, SavedPromptResponse
from app.services.indexing_service import sync_prompt_index


def _side_effect_warning(message: str, warning: str | None) -> str:
    return side_effect_warning(message, warning)


def _run_index_side_effect(*, label: str, item_id: str, operation, on_error):
    try:
        operation()
    except Exception as exc:
        index_status, detail = classify_index_failure(exc)
        on_error(index_status, detail)
        logger.warning("%s indexing failed for %s: %s", label, item_id, exc)
        return f"{label} indexing failed: {exc}"
    return None


def _run_deindex_side_effect(*, label: str, item_id: str, operation):
    try:
        operation()
    except Exception as exc:
        logger.warning("%s de-indexing failed for %s: %s", label, item_id, exc)
        return f"{label} de-index failed: {exc}"
    return None


async def list_saved_prompts(current_user: dict = Depends(get_current_user)) -> list[SavedPromptResponse]:
    user_id = current_user["sub"]
    return [
        SavedPromptResponse(
            id=row.get("prompt_id", ""),
            title=row.get("title", ""),
            content=row.get("content", ""),
            tags=row.get("tags", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
            index_status=row.get("index_status", "pending") or "pending",
            index_error=row.get("index_error", "") or "",
        )
        for row in db.list_saved_prompts(user_id=user_id, limit=200)
    ]


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
            db.resolve_index_repair(item_id=item_id_from_parts("prompt", prompt_id), action="index")
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
        index_status=str(prompt.get("index_status", "pending") or "pending"),
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
        db.resolve_index_repair(item_id=item_id_from_parts("prompt", prompt_id), action="deindex")
    db.delete_search_content(item_id_from_parts("prompt", prompt_id))
    db.delete_links(from_item_id=item_id_from_parts("prompt", prompt_id))
    db.delete_links(to_item_id=item_id_from_parts("prompt", prompt_id))
    if not db.delete_saved_prompt(prompt_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete prompt.")
    return MessageResponse(message=_side_effect_warning("Prompt deleted.", warning))
