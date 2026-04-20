"""Document management router for file uploads and CRUD operations."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.database import DocumentDatabase, delete_from_kb_vector_db, delete_from_vector_db
from app.dependencies import get_current_user
from app.models import (
    DocumentResponse,
    DocumentUpdateRequest,
    ItemLinksResponse,
    MessageResponse,
    UploadDocumentResponse,
)
from app.utils import (
    generate_safe_filename,
    stream_write_file,
    validate_file_extension,
    validate_file_magic_bytes,
)

logger = logging.getLogger("knowledge_workspace")

router = APIRouter(prefix="/api/docs", tags=["documents"])


def _safe_download_filename(filename: str) -> str:
    """Sanitize filename for download to prevent header injection."""
    import re
    sanitized = re.sub(r"[^\w\-. ]", "_", filename)
    return sanitized[:255]  # Limit length


def _guess_media_type(filename: str) -> str | None:
    """Guess media type from filename extension."""
    import mimetypes
    return mimetypes.guess_type(filename)[0]


async def sync_document_index(document: dict) -> None:
    """Synchronize document with vector index."""
    from app.kb_index import index_document
    
    try:
        doc_id = document["doc_id"]
        saved_filename = document["saved_filename"]
        upload_dir = Path("./uploads")
        file_path = upload_dir / saved_filename
        
        if not file_path.exists():
            logger.warning("Document file missing for indexing: %s", doc_id)
            return
        
        pages = []
        ext = Path(saved_filename).suffix.lower()
        
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append((str(idx + 1), text))
        elif ext in {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml"}:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            pages.append(("1", text))
        
        if pages:
            index_document(doc_id, pages)
    except Exception as e:
        logger.error("Failed to index document %s: %s", document.get("doc_id"), e)


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default=""),
    tags: str = Form(default=""),
    current_user: dict = Depends(get_current_user),
) -> UploadDocumentResponse:
    """Upload a document and create vector index.
    
    Validates file extension and magic bytes to prevent security issues.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    
    if not validate_file_extension(file.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")
    
    # Read file content for magic bytes validation
    file_content = await file.read()
    await file.seek(0)  # Reset file pointer for subsequent reading
    
    # Validate file content using magic bytes (prevents file spoofing attacks)
    validate_file_magic_bytes(file_content, file.filename)
    
    safe_filename = generate_safe_filename(file.filename)
    file_path = Path("./uploads") / safe_filename
    file_size = await stream_write_file(file, file_path)
    
    doc_id = str(uuid.uuid4())
    
    db = DocumentDatabase("./documents.db")
    if not db.add_document(
        doc_id=doc_id,
        filename=file.filename,
        saved_filename=safe_filename,
        file_size=file_size,
        uploaded_by=current_user["sub"],
        category=str(category or ""),
        tags=str(tags or ""),
        status="reviewed",
    ):
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist document.")
    
    document = db.get_document(doc_id)
    if document:
        await sync_document_index(document)
    
    logger.info("Uploaded document %s by %s", doc_id, current_user["sub"])
    
    return UploadDocumentResponse(
        id=doc_id,
        filename=file.filename,
        category=str(category or ""),
        tags=str(tags or ""),
        status="reviewed",
        uploaded_at=document["uploaded_at"],
        updated_at=document.get("updated_at") or document["uploaded_at"],
        file_size=file_size,
        uploaded_by=current_user["sub"],
        message="Document uploaded and indexed.",
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: dict = Depends(get_current_user),
) -> list[DocumentResponse]:
    """List all documents owned by the current user."""
    db = DocumentDatabase("./documents.db")
    documents = db.list_documents(user_id=current_user["sub"], include_archived=False)
    
    def serialize_document(document: dict) -> DocumentResponse:
        return DocumentResponse(
            id=document["doc_id"],
            filename=document["filename"],
            category=str(document.get("category", "") or ""),
            tags=str(document.get("tags", "") or ""),
            status=str(document.get("status", "") or "reviewed"),
            uploaded_at=str(document["uploaded_at"]),
            updated_at=str(document.get("updated_at") or document["uploaded_at"]),
            file_size=int(document.get("file_size", 0)),
            uploaded_by=document.get("uploaded_by"),
        )
    
    return [serialize_document(doc) for doc in documents]


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    inline: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Download a document file."""
    db = DocumentDatabase("./documents.db")
    document = db.get_document(doc_id)
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    
    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this document.")
    
    file_path = Path("./uploads") / document["saved_filename"]
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


@router.get("/{doc_id}/references", response_model=ItemLinksResponse)
async def list_document_references(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
) -> ItemLinksResponse:
    """Get item links/references for a document."""
    db = DocumentDatabase("./documents.db")
    document = db.get_document(doc_id)
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    
    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this document.")
    
    from app.main import build_links_response, item_id_from_parts
    
    return build_links_response(
        item_id=item_id_from_parts("document", doc_id),
        user_id=current_user["sub"],
    )


@router.patch("/{doc_id}", response_model=MessageResponse)
async def update_document(
    doc_id: str,
    request: DocumentUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    """Update document metadata."""
    db = DocumentDatabase("./documents.db")
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
    await sync_document_index(updated)
    
    return MessageResponse(message="Document updated.")


@router.delete("/{doc_id}", response_model=MessageResponse)
async def delete_own_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    """Delete a document and its associated resources."""
    db = DocumentDatabase("./documents.db")
    document = db.get_document(doc_id)
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    
    if document.get("uploaded_by") != current_user["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this document.")
    
    # Delete from vector databases
    delete_from_vector_db(doc_id)
    delete_from_kb_vector_db(doc_id)
    
    # Delete physical file
    file_path = Path("./uploads") / document["saved_filename"]
    try:
        file_path.unlink()
    except PermissionError:
        logger.warning("Could not delete file %s because it is locked by the OS.", file_path)
    
    # Delete links
    from app.main import item_id_from_parts
    item_id = item_id_from_parts("document", doc_id)
    db.delete_links(from_item_id=item_id)
    db.delete_links(to_item_id=item_id)
    
    # Delete database record
    db.delete_document(doc_id)
    
    return MessageResponse(message="Document deleted.")
