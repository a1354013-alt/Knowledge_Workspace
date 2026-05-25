from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db import schema

LINK_TYPE_VALUES = schema.LINK_TYPE_VALUES
WORKFLOW_STATUS_VALUES = schema.WORKFLOW_STATUS_VALUES
KNOWLEDGE_STATUS_VALUES = schema.KNOWLEDGE_STATUS_VALUES
LOGBOOK_STATUS_VALUES = schema.LOGBOOK_STATUS_VALUES
DOC_STATUS_VALUES = schema.DOC_STATUS_VALUES
PHOTO_STATUS_VALUES = schema.PHOTO_STATUS_VALUES
AUTOTEST_STATUS_VALUES = schema.AUTOTEST_STATUS_VALUES
AUTOTEST_RUN_STATUS_VALUES = schema.AUTOTEST_RUN_STATUS_VALUES
AUTOTEST_STEP_STATUS_VALUES = schema.AUTOTEST_STEP_STATUS_VALUES
INDEX_STATUS_VALUES = ("pending", "indexed", "failed", "unavailable")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
