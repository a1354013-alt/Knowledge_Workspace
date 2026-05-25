from app.api.handlers.support import (
    UPLOAD_DIR,
    Depends,
    DocumentResponse,
    DocumentUpdateRequest,
    File,
    FileResponse,
    Form,
    HTTPException,
    ItemLinksResponse,
    MessageResponse,
    Path,
    UploadDocumentResponse,
    UploadFile,
    _guess_media_type,
    _run_deindex_side_effect,
    _safe_download_filename,
    _side_effect_warning,
    build_links_response,
    classify_index_failure,
    db,
    delete_from_vector_db,
    generate_safe_filename,
    get_current_user,
    item_id_from_parts,
    logger,
    safe_unlink,
    serialize_document,
    status,
    stream_write_file,
    sync_document_index,
    uuid,
    validate_file_extension,
    validate_file_magic_bytes,
)


async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(""),
    tags: str = Form(""),
    current_user: dict = Depends(get_current_user),
) -> UploadDocumentResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    if not validate_file_extension(file.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")

    # Validate content using a small prefix sample (avoid reading large uploads into RAM).
    # - binary signatures: first bytes are sufficient
    # - text/markdown: validate using a bounded sample prefix
    prefix_limit = 64 * 1024 if Path(file.filename).suffix.lower() in (".txt", ".md") else 32
    file_prefix = await file.read(prefix_limit)
    await file.seek(0)
    validate_file_magic_bytes(file_prefix, file.filename)

    safe_filename = generate_safe_filename(file.filename)
    file_path = UPLOAD_DIR / safe_filename
    file_size = await stream_write_file(file, file_path)

    doc_id = str(uuid.uuid4())
    if not db.add_document(
        doc_id=doc_id,
        filename=file.filename,
        saved_filename=safe_filename,
        file_size=file_size,
        uploaded_by=current_user["sub"],
        category=str(category or ""),
        tags=str(tags or ""),
        status="reviewed",
        index_status="pending",
        index_error="",
        indexed_at="",
    ):
        safe_unlink(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist document.")

    document = db.get_document(doc_id)
    message = "Document uploaded and indexed."
    if document:
        try:
            await sync_document_index(document)
        except Exception as exc:
            index_status, detail = classify_index_failure(exc)
            db.update_document(doc_id, index_status=index_status, index_error=detail, indexed_at="")
            logger.warning("Document indexing failed for %s: %s", doc_id, exc)
            message = f"Document uploaded, but indexing failed: {exc}"
        document = db.get_document(doc_id) or document
    logger.info("Uploaded document %s by %s", doc_id, current_user["sub"])
    return UploadDocumentResponse(
        **serialize_document(document).model_dump(),
        message=message,
    )


async def list_documents(current_user: dict = Depends(get_current_user)) -> list[DocumentResponse]:
    return [
        serialize_document(document)
        for document in db.list_documents(user_id=current_user["sub"], include_archived=False)
    ]


async def download_document(doc_id: str, inline: int = 0, current_user: dict = Depends(get_current_user)):
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this document.")
    file_path = UPLOAD_DIR / document["saved_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file missing on disk.")

    disposition = "inline" if int(inline) == 1 else "attachment"
    safe_name = _safe_download_filename(str(document.get("filename") or "document"))
    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type=_guess_media_type(safe_name),
        headers={"Content-Disposition": f'{disposition}; filename="{safe_name}"'},
    )


async def list_document_references(doc_id: str, current_user: dict = Depends(get_current_user)) -> ItemLinksResponse:
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this document.")
    return build_links_response(item_id=item_id_from_parts("document", doc_id), user_id=current_user["sub"])


async def update_document(
    doc_id: str, request: DocumentUpdateRequest, current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    original = db.get_document(doc_id)
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if original.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit this document.")

    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No document fields provided.")

    if not db.update_document(doc_id, **updates):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update document.")

    updated = db.get_document(doc_id) or original
    warning = None
    try:
        await sync_document_index(updated)
    except Exception as exc:
        index_status, detail = classify_index_failure(exc)
        db.update_document(doc_id, index_status=index_status, index_error=detail, indexed_at="")
        warning = f"Document indexing failed: {exc}"
    return MessageResponse(message=_side_effect_warning("Document updated.", warning))


async def delete_own_document(doc_id: str, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this document.")

    warning = _run_deindex_side_effect(
        label="Document",
        item_id=doc_id,
        operation=lambda: delete_from_vector_db(doc_id),
    )
    safe_unlink(UPLOAD_DIR / document["saved_filename"])
    db.delete_links(from_item_id=item_id_from_parts("document", doc_id))
    db.delete_links(to_item_id=item_id_from_parts("document", doc_id))
    db.delete_document(doc_id)
    return MessageResponse(message=_side_effect_warning("Document deleted.", warning))
