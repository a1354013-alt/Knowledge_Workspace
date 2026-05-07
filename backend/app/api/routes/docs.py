from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main

router = APIRouter()

router.add_api_route("/api/docs/upload", legacy_main.upload_document, methods=["POST"])
router.add_api_route("/api/docs", legacy_main.list_documents, methods=["GET"])
router.add_api_route("/api/docs/{doc_id}/download", legacy_main.download_document, methods=["GET"])
router.add_api_route("/api/docs/{doc_id}/references", legacy_main.list_document_references, methods=["GET"])
router.add_api_route("/api/docs/{doc_id}", legacy_main.update_document, methods=["PATCH"])
router.add_api_route("/api/docs/{doc_id}", legacy_main.delete_own_document, methods=["DELETE"])
