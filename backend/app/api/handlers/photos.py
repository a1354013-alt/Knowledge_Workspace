from app.api.handlers.support import (
    PHOTO_DIR,
    Depends,
    File,
    FileResponse,
    Form,
    HTTPException,
    ItemLinksResponse,
    MessageResponse,
    Path,
    PhotoResponse,
    PhotoUpdateRequest,
    UploadFile,
    UploadPhotoResponse,
    _guess_media_type,
    _run_deindex_side_effect,
    _run_index_side_effect,
    _safe_download_filename,
    _side_effect_warning,
    build_links_response,
    db,
    delete_from_kb_vector_db,
    extract_text_from_image,
    generate_safe_filename,
    get_current_user,
    item_id_from_parts,
    safe_unlink,
    status,
    stream_write_file,
    uuid,
)
from app.core.config import get_settings
from app.services.indexing_service import sync_photo_index

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:  # pragma: no cover - optional runtime dependency
    Image = None
    UnidentifiedImageError = ValueError


def validate_image_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def sniff_image_type(header: bytes) -> str | None:
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "gif"
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "webp"
    return None


async def upload_photo(
    file: UploadFile = File(...),
    tags: str = Form(""),
    description: str = Form(""),
    current_user: dict = Depends(get_current_user),
) -> UploadPhotoResponse:
    user_id = current_user["sub"]
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    if not validate_image_extension(file.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type.")
    if file.content_type and not str(file.content_type).lower().startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image content type.")

    # Validate image using magic bytes (more robust than extension check alone),
    # using only a small header prefix to avoid loading large uploads into RAM.
    header = await file.read(32)
    await file.seek(0)
    if sniff_image_type(header) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file does not look like an image."
        )

    safe_filename = generate_safe_filename(file.filename)
    file_path = PHOTO_DIR / safe_filename
    file_size = await stream_write_file(file, file_path)
    _validate_image_file(file_path)

    # Extract text from image using OCR
    ocr_text = extract_text_from_image(file_path)

    photo_id = str(uuid.uuid4())
    if not db.add_photo(
        photo_id=photo_id,
        filename=file.filename,
        saved_filename=safe_filename,
        tags=str(tags or ""),
        description=str(description or ""),
        ocr_text=ocr_text,
        file_size=file_size,
        uploaded_by=user_id,
        status="reviewed",
    ):
        safe_unlink(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist photo.")

    photo = db.get_photo(photo_id)
    if photo:
        warning = _run_index_side_effect(
            label="Photo",
            item_id=photo_id,
            operation=lambda: sync_photo_index(photo),
            on_error=lambda index_status, detail: db.update_photo(
                photo_id, index_status=index_status, index_error=detail, indexed_at=""
            ),
        )
    else:
        warning = None

    photo_row = db.get_photo(photo_id) or {}
    return UploadPhotoResponse(
        id=photo_id,
        filename=str(photo_row.get("filename", "")),
        tags=str(photo_row.get("tags", "")),
        description=str(photo_row.get("description", "")),
        ocr_text=str(photo_row.get("ocr_text", "")),
        status=str(photo_row.get("status", "reviewed") or "reviewed"),
        uploaded_by=str(photo_row.get("uploaded_by") or ""),
        file_size=int(photo_row.get("file_size", 0)),
        created_at=str(photo_row.get("created_at", "")),
        updated_at=str(photo_row.get("updated_at", "")),
        message=_side_effect_warning("Photo uploaded.", warning),
    )


async def list_photos(current_user: dict = Depends(get_current_user)) -> list[PhotoResponse]:
    user_id = current_user["sub"]
    return [
        PhotoResponse(
            id=row["photo_id"],
            filename=row.get("filename", ""),
            tags=row.get("tags", ""),
            description=row.get("description", ""),
            ocr_text=row.get("ocr_text", ""),
            status=row.get("status", "reviewed") or "reviewed",
            uploaded_by=row.get("uploaded_by"),
            file_size=int(row.get("file_size", 0)),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
        for row in db.list_photos(limit=200, user_id=user_id, include_archived=False)
    ]


async def download_photo(photo_id: str, inline: int = 1, current_user: dict = Depends(get_current_user)):
    photo = db.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if photo.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this photo.")
    file_path = PHOTO_DIR / photo["saved_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo file missing on disk.")

    disposition = "inline" if int(inline) == 1 else "attachment"
    safe_name = _safe_download_filename(str(photo.get("filename") or "photo"))
    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type=_guess_media_type(safe_name),
        headers={"Content-Disposition": f'{disposition}; filename="{safe_name}"'},
    )


async def update_photo(
    photo_id: str, request: PhotoUpdateRequest, current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    original = db.get_photo(photo_id)
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if original.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit this photo.")

    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No photo fields provided.")
    if not db.update_photo(photo_id, **updates):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update photo.")

    updated = db.get_photo(photo_id) or original
    warning = _run_index_side_effect(
        label="Photo",
        item_id=photo_id,
        operation=lambda: sync_photo_index(updated),
        on_error=lambda index_status, detail: db.update_photo(
            photo_id, index_status=index_status, index_error=detail, indexed_at=""
        ),
    )
    return MessageResponse(message=_side_effect_warning("Photo updated.", warning))


async def delete_photo(photo_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    photo = db.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if photo.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this photo.")
    warning = _run_deindex_side_effect(
        label="Photo",
        item_id=photo_id,
        operation=lambda: delete_from_kb_vector_db(item_id_from_parts("photo", photo_id)),
    )
    safe_unlink(PHOTO_DIR / photo["saved_filename"])
    db.delete_links(from_item_id=item_id_from_parts("photo", photo_id))
    db.delete_links(to_item_id=item_id_from_parts("photo", photo_id))
    db.delete_photo(photo_id)
    return MessageResponse(message=_side_effect_warning("Photo deleted.", warning))


async def list_photo_references(photo_id: str, current_user: dict = Depends(get_current_user)) -> ItemLinksResponse:
    photo = db.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if photo.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this photo.")
    return build_links_response(item_id=item_id_from_parts("photo", photo_id), user_id=current_user["sub"])


def _validate_image_file(file_path: Path) -> None:
    if Image is None:
        return
    settings = get_settings()
    try:
        with Image.open(file_path) as image:
            image.verify()
        with Image.open(file_path) as image:
            width, height = image.size
            pixel_count = int(width) * int(height)
            if width <= 0 or height <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image dimensions are invalid.")
            if pixel_count > int(settings.IMAGE_MAX_PIXELS):
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image exceeds the {settings.IMAGE_MAX_PIXELS} pixel limit.",
                )
            image.load()
    except HTTPException:
        safe_unlink(file_path)
        raise
    except (UnidentifiedImageError, OSError) as exc:
        safe_unlink(file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse image: {exc}") from exc
