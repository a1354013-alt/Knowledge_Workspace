from app.api.handlers.support import (
    Depends,
    HTTPException,
    MessageResponse,
    SavedPromptCreateRequest,
    SavedPromptResponse,
    _run_deindex_side_effect,
    _run_index_side_effect,
    _side_effect_warning,
    db,
    delete_from_kb_vector_db,
    get_current_user,
    index_saved_prompt,
    item_id_from_parts,
    status,
    uuid,
)


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
            index_status="indexed",
            index_error="",
        )
        for row in db.list_saved_prompts(user_id=user_id, limit=200)
    ]


async def create_saved_prompt(request: SavedPromptCreateRequest, current_user: dict = Depends(get_current_user)) -> SavedPromptResponse:
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
            operation=lambda: index_saved_prompt(prompt),
        )
    else:
        warning = None
    return SavedPromptResponse(
        id=prompt_id,
        title=str(prompt.get("title", "")),
        content=str(prompt.get("content", "")),
        tags=str(prompt.get("tags", "")),
        created_at=str(prompt.get("created_at", "")),
        updated_at=str(prompt.get("updated_at", "")),
        index_status="failed" if warning else "indexed",
        index_error=str(warning or ""),
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
    db.delete_links(from_item_id=item_id_from_parts("prompt", prompt_id))
    db.delete_links(to_item_id=item_id_from_parts("prompt", prompt_id))
    if not db.delete_saved_prompt(prompt_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete prompt.")
    return MessageResponse(message=_side_effect_warning("Prompt deleted.", warning))