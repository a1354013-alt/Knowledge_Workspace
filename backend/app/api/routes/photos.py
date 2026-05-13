from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.handlers import photos as photo_handlers
from app.models import ItemLinksResponse, MessageResponse, PhotoResponse, UploadPhotoResponse

router = APIRouter()

router.add_api_route("/api/photos/upload", photo_handlers.upload_photo, methods=["POST"], response_model=UploadPhotoResponse)
router.add_api_route("/api/photos", photo_handlers.list_photos, methods=["GET"], response_model=list[PhotoResponse])
router.add_api_route("/api/photos/{photo_id}/download", photo_handlers.download_photo, methods=["GET"], response_class=Response)
router.add_api_route("/api/photos/{photo_id}", photo_handlers.update_photo, methods=["PATCH"], response_model=MessageResponse)
router.add_api_route("/api/photos/{photo_id}", photo_handlers.delete_photo, methods=["DELETE"], response_model=MessageResponse)
router.add_api_route(
    "/api/photos/{photo_id}/references",
    photo_handlers.list_photo_references,
    methods=["GET"],
    response_model=ItemLinksResponse,
)
