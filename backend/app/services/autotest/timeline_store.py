from __future__ import annotations

import json
import logging

from app.context import db
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.timeline_events import initial_autotest_timeline, utc_now_iso

logger = logging.getLogger("knowledge_workspace")
autotest_repository = AutoTestRepository(db)


def save_run_timeline(run_id: str, timeline: list[dict[str, object]]) -> None:
    autotest_repository.update_run(run_id, timeline_json=json.dumps(timeline, ensure_ascii=True))


def load_run_timeline(run_row: dict) -> list[dict[str, object]]:
    raw = str(run_row.get("timeline_json", "") or "").strip()
    if raw:
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            return [item for item in decoded if isinstance(item, dict)]
        logger.warning("Invalid timeline_json for AutoTest run %s", run_row.get("run_id", ""))
    created_at = str(run_row.get("created_at", "") or "") or utc_now_iso()
    return initial_autotest_timeline(source_ref=str(run_row.get("source_ref", "") or ""), created_at=created_at)
