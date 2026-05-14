from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from app.context import db
from app.repositories.autotest_repository import AutoTestRepository
from app.services.autotest.reports import _safe_autotest_index_entry

logger = logging.getLogger("knowledge_workspace")
autotest_repository = AutoTestRepository(db)


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
    autotest_repository.update_run(run_id, solution_entry_id=knowledge_id)
    db.add_link(f"autotest_run:{run_id}", f"knowledge:{knowledge_id}", link_type="produced")
    db.add_link(f"knowledge:{knowledge_id}", f"autotest_run:{run_id}", link_type="derived_from")
    _safe_autotest_index_entry(
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
    autotest_repository.update_run(run_id, problem_entry_id=logbook_id, status="failed")
    db.add_link(f"autotest_run:{run_id}", f"logbook:{logbook_id}", link_type="produced")
    db.add_link(f"logbook:{logbook_id}", f"autotest_run:{run_id}", link_type="derived_from")
    _safe_autotest_index_entry(
        run_id=run_id,
        item_kind="logbook",
        item_id=logbook_id,
        entry=db.get_logbook_entry(logbook_id),
        indexer=indexer,
    )
    return logbook_id
