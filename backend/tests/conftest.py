from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
os.environ.setdefault("DEFAULT_OWNER_PASSWORD", "password123")
os.environ.setdefault("DATABASE_PATH", str(BACKEND_DIR / ".pytest-test.db"))
os.environ.setdefault("UPLOAD_DIR", str(BACKEND_DIR / ".pytest-uploads"))
os.environ.setdefault("AUTOTEST_DIR", str(BACKEND_DIR / ".pytest-autotest"))
os.environ.setdefault("CHROMA_DB_PATH", str(BACKEND_DIR / ".pytest-chroma"))
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
