from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.api import legacy_main
from app.models import ItemLinksResponse, MessageResponse, PhotoResponse, UploadPhotoResponse

router = APIRouter()

router.add_api_route("/api/photos/upload", legacy_main.upload_photo, methods=["POST"], response_model=UploadPhotoResponse)
router.add_api_route("/api/photos", legacy_main.list_photos, methods=["GET"], response_model=list[PhotoResponse])
router.add_api_route("/api/photos/{photo_id}/download", legacy_main.download_photo, methods=["GET"], response_class=Response)
router.add_api_route("/api/photos/{photo_id}", legacy_main.update_photo, methods=["PATCH"], response_model=MessageResponse)
router.add_api_route("/api/photos/{photo_id}", legacy_main.delete_photo, methods=["DELETE"], response_model=MessageResponse)
router.add_api_route(
    "/api/photos/{photo_id}/references",
    legacy_main.list_photo_references,
    methods=["GET"],
    response_model=ItemLinksResponse,
)
