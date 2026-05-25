from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from app.context import db
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.reports import _safe_autotest_index_entry

logger = logging.getLogger("knowledge_workspace")
autotest_repository = AutoTestRepository(db)


def _safe_update_run_link(*, run_id: str, field: str, value: str) -> None:
    try:
        autotest_repository.update_run(run_id, **{field: value})
    except Exception as exc:
        logger.warning("AutoTest run %s could not persist %s=%s: %s", run_id, field, value, exc)


def _safe_add_link(*, from_item_id: str, to_item_id: str, link_type: str) -> None:
    try:
        db.add_link(from_item_id, to_item_id, link_type=link_type)
    except Exception as exc:
        logger.warning(
            "AutoTest link side effect failed (%s -> %s, type=%s): %s",
            from_item_id,
            to_item_id,
            link_type,
            exc,
        )


def _safe_index_entry(
    *, run_id: str, item_kind: str, item_id: str, entry: dict | None, indexer: Callable[[dict], object]
) -> None:
    _safe_autotest_index_entry(
        run_id=run_id,
        item_kind=item_kind,
        item_id=item_id,
        entry=entry,
        indexer=indexer,
    )


def create_passed_knowledge_draft(
    *,
    run_id: str,
    user_id: str,
    project_name: str,
    summary: str,
    prompt_output: str,
    indexer: Callable[[dict], object],
) -> str:
    knowledge_id = str(uuid.uuid4())
    candidate_ok = db.add_knowledge_entry(
        entry_id=knowledge_id,
        title=f"AutoTest Passed: {project_name}",
        status="draft",
        problem=summary,
        root_cause="",
        solution=prompt_output,
        tags="autotest,acceptance",
        notes=f"source=autotest\nrun_id={run_id}",
        created_by=user_id,
        source_type="autotest-derived",
        source_ref=f"autotest_run:{run_id}",
    )
    if not candidate_ok:
        return ""
    _safe_update_run_link(run_id=run_id, field="solution_entry_id", value=knowledge_id)
    _safe_add_link(from_item_id=f"autotest_run:{run_id}", to_item_id=f"knowledge:{knowledge_id}", link_type="produced")
    _safe_add_link(
        from_item_id=f"knowledge:{knowledge_id}", to_item_id=f"autotest_run:{run_id}", link_type="derived_from"
    )
    _safe_index_entry(
        run_id=run_id,
        item_kind="knowledge",
        item_id=knowledge_id,
        entry=db.get_knowledge_entry(knowledge_id),
        indexer=indexer,
    )
    return knowledge_id


def create_failed_logbook_draft(
    *,
    run_id: str,
    user_id: str,
    project_name: str,
    prompt_output: str,
    suggestion: str,
    indexer: Callable[[dict], object],
) -> str:
    logbook_id = str(uuid.uuid4())
    created_problem = db.add_logbook_entry(
        entry_id=logbook_id,
        title=f"AutoTest Failed: {project_name}",
        status="draft",
        run_id=run_id,
        problem=prompt_output,
        root_cause="",
        solution=suggestion,
        tags="autotest,acceptance",
        source_type="autotest-derived",
        created_by=user_id,
        source_ref=f"autotest_run:{run_id}",
    )
    if not created_problem:
        return ""
    _safe_update_run_link(run_id=run_id, field="problem_entry_id", value=logbook_id)
    _safe_add_link(from_item_id=f"autotest_run:{run_id}", to_item_id=f"logbook:{logbook_id}", link_type="produced")
    _safe_add_link(from_item_id=f"logbook:{logbook_id}", to_item_id=f"autotest_run:{run_id}", link_type="derived_from")
    _safe_index_entry(
        run_id=run_id,
        item_kind="logbook",
        item_id=logbook_id,
        entry=db.get_logbook_entry(logbook_id),
        indexer=indexer,
    )
    return logbook_id
