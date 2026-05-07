from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main

router = APIRouter()

router.add_api_route("/api/photos/upload", legacy_main.upload_photo, methods=["POST"])
router.add_api_route("/api/photos", legacy_main.list_photos, methods=["GET"])
router.add_api_route("/api/photos/{photo_id}/download", legacy_main.download_photo, methods=["GET"])
router.add_api_route("/api/photos/{photo_id}", legacy_main.update_photo, methods=["PATCH"])
router.add_api_route("/api/photos/{photo_id}", legacy_main.delete_photo, methods=["DELETE"])
router.add_api_route("/api/photos/{photo_id}/references", legacy_main.list_photo_references, methods=["GET"])
