from __future__ import annotations

from typing import Any


class AutoTestRepository:
    def __init__(self, database):
        self._db = database

    def create_run(self, **kwargs: Any) -> bool:
        return bool(self._db.add_autotest_run(**kwargs))

    def update_run(self, run_id: str, **updates: Any) -> bool:
        return bool(self._db.update_autotest_run(run_id, **updates))

    def get_run(self, *, run_id: str, created_by: str) -> dict[str, Any] | None:
        return self._db.get_autotest_run(run_id=run_id, created_by=created_by)

    def list_runs(self, *, created_by: str, limit: int = 50) -> list[dict[str, Any]]:
        return self._db.list_autotest_runs(limit=limit, created_by=created_by)

    def list_unfinished_runs(self) -> list[dict[str, Any]]:
        return self._db.list_unfinished_autotest_runs(statuses=("queued", "running"))

    def create_step(self, **kwargs: Any) -> bool:
        return bool(self._db.add_autotest_step(**kwargs))

    def update_step(self, step_id: str, **updates: Any) -> bool:
        return bool(self._db.update_autotest_step(step_id, **updates))

    def list_steps(self, run_id: str) -> list[dict[str, Any]]:
        return self._db.list_autotest_steps(run_id)
