"""Database facade.

The implementation lives in `legacy_database.py` while we progressively extract
schema/migrations/repositories into dedicated modules.
"""

from __future__ import annotations

from app.db.legacy_database import (  # noqa: F401
    AUTOTEST_RUN_STATUS_VALUES,
    AUTOTEST_STATUS_VALUES,
    AUTOTEST_STEP_STATUS_VALUES,
    DOC_STATUS_VALUES,
    KNOWLEDGE_STATUS_VALUES,
    LINK_TYPE_VALUES,
    LOGBOOK_STATUS_VALUES,
    PHOTO_STATUS_VALUES,
    WORKFLOW_STATUS_VALUES,
    DocumentDatabase,
    utc_now_iso,
)

__all__ = [
    "DocumentDatabase",
    "LINK_TYPE_VALUES",
    "WORKFLOW_STATUS_VALUES",
    "KNOWLEDGE_STATUS_VALUES",
    "LOGBOOK_STATUS_VALUES",
    "DOC_STATUS_VALUES",
    "PHOTO_STATUS_VALUES",
    "AUTOTEST_RUN_STATUS_VALUES",
    "AUTOTEST_STEP_STATUS_VALUES",
    "AUTOTEST_STATUS_VALUES",
    "utc_now_iso",
]
