from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.handlers import docs as doc_handlers
from app.models import DocumentResponse, ItemLinksResponse, MessageResponse, UploadDocumentResponse

router = APIRouter()

router.add_api_route(
    "/api/docs/upload", doc_handlers.upload_document, methods=["POST"], response_model=UploadDocumentResponse
)
router.add_api_route("/api/docs", doc_handlers.list_documents, methods=["GET"], response_model=list[DocumentResponse])
router.add_api_route(
    "/api/docs/{doc_id}/download", doc_handlers.download_document, methods=["GET"], response_class=Response
)
router.add_api_route(
    "/api/docs/{doc_id}/references",
    doc_handlers.list_document_references,
    methods=["GET"],
    response_model=ItemLinksResponse,
)
router.add_api_route(
    "/api/docs/{doc_id}", doc_handlers.update_document, methods=["PATCH"], response_model=MessageResponse
)
router.add_api_route(
    "/api/docs/{doc_id}", doc_handlers.delete_own_document, methods=["DELETE"], response_model=MessageResponse
)
