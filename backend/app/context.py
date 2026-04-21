from __future__ import annotations

import logging

from dotenv import load_dotenv

from app.core.config import get_settings
from app.database import DocumentDatabase

load_dotenv()
settings = get_settings()

APP_VERSION = settings.APP_VERSION

logger = logging.getLogger("knowledge_workspace")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

UPLOAD_DIR = settings.UPLOAD_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

db = DocumentDatabase(str(settings.DATABASE_PATH))

allowed_origins = settings.ALLOWED_ORIGINS
allow_credentials = "*" not in allowed_origins

