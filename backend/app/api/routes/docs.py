from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.api import legacy_main
from app.models import DocumentResponse, ItemLinksResponse, MessageResponse, UploadDocumentResponse

router = APIRouter()

router.add_api_route("/api/docs/upload", legacy_main.upload_document, methods=["POST"], response_model=UploadDocumentResponse)
router.add_api_route("/api/docs", legacy_main.list_documents, methods=["GET"], response_model=list[DocumentResponse])
router.add_api_route("/api/docs/{doc_id}/download", legacy_main.download_document, methods=["GET"], response_class=Response)
router.add_api_route(
    "/api/docs/{doc_id}/references",
    legacy_main.list_document_references,
    methods=["GET"],
    response_model=ItemLinksResponse,
)
router.add_api_route("/api/docs/{doc_id}", legacy_main.update_document, methods=["PATCH"], response_model=MessageResponse)
router.add_api_route("/api/docs/{doc_id}", legacy_main.delete_own_document, methods=["DELETE"], response_model=MessageResponse)
