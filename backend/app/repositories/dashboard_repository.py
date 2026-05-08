from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.schema import WORKFLOW_STATUS_VALUES


class DashboardRepository:
    def __init__(self, database):
        self._db = database

    def get_document_index_counts(self, user_id: str) -> dict[str, int]:
        with self._db._connection() as conn:  # noqa: SLF001 - repository owns DB query details
            total = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE uploaded_by = ? AND is_active = 1",
                (user_id,),
            ).fetchone()[0]
            indexed = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE uploaded_by = ? AND is_active = 1 AND index_status = 'indexed'",
                (user_id,),
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE uploaded_by = ? AND is_active = 1 AND index_status = 'pending'",
                (user_id,),
            ).fetchone()[0]
            failed_documents = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE uploaded_by = ? AND is_active = 1 AND index_status = 'failed'",
                (user_id,),
            ).fetchone()[0]
            archived_documents = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE uploaded_by = ? AND status = 'archived'",
                (user_id,),
            ).fetchone()[0]
        return {
            "total": total,
            "indexed": indexed,
            "pending": pending,
            "failed_documents": failed_documents,
            "archived_documents": archived_documents,
        }

    def get_knowledge_counts(self, user_id: str) -> dict[str, Any]:
        with self._db._connection() as conn:  # noqa: SLF001
            total = conn.execute(
                "SELECT COUNT(*) FROM knowledge_entries WHERE created_by = ? AND is_active = 1",
                (user_id,),
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM knowledge_entries WHERE created_by = ? AND is_active = 1 GROUP BY status",
                (user_id,),
            ).fetchall()
        by_status = {row[0]: row[1] for row in rows}
        for status in WORKFLOW_STATUS_VALUES:
            by_status.setdefault(status, 0)
        return {"total": total, "by_status": by_status}

    def get_logbook_counts(self, user_id: str) -> dict[str, int | float]:
        with self._db._connection() as conn:  # noqa: SLF001
            total = conn.execute(
                "SELECT COUNT(*) FROM logbook_entries WHERE created_by = ? AND is_active = 1",
                (user_id,),
            ).fetchone()[0]
            with_solution = conn.execute(
                "SELECT COUNT(*) FROM logbook_entries WHERE created_by = ? AND is_active = 1 AND solution != ''",
                (user_id,),
            ).fetchone()[0]
        resolution_rate = (with_solution / total * 100) if total > 0 else 0.0
        return {
            "total": total,
            "with_solution": with_solution,
            "resolution_rate": round(resolution_rate, 2),
        }

    def get_promoted_logbook_count(self, user_id: str) -> int:
        with self._db._connection() as conn:  # noqa: SLF001
            return conn.execute(
                """
                SELECT COUNT(DISTINCT le.entry_id)
                FROM logbook_entries AS le
                WHERE le.created_by = ?
                  AND EXISTS (
                      SELECT 1
                      FROM item_links AS il
                      INNER JOIN knowledge_entries AS ke
                          ON il.to_item_id = 'knowledge:' || ke.entry_id
                      WHERE il.from_item_id = 'logbook:' || le.entry_id
                        AND il.to_item_id LIKE 'knowledge:%'
                        AND ke.created_by = ?
                        AND ke.is_active = 1
                  )
                """,
                (user_id, user_id),
            ).fetchone()[0]

    def get_autotest_metrics(self, user_id: str) -> dict[str, Any]:
        with self._db._connection() as conn:  # noqa: SLF001
            total_runs = conn.execute(
                "SELECT COUNT(*) FROM autotest_runs WHERE created_by = ?",
                (user_id,),
            ).fetchone()[0]
            passed = conn.execute(
                "SELECT COUNT(*) FROM autotest_runs WHERE created_by = ? AND status = 'passed'",
                (user_id,),
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) FROM autotest_runs WHERE created_by = ? AND status = 'failed'",
                (user_id,),
            ).fetchone()[0]
            recent_runs_rows = conn.execute(
                """
                SELECT run_id as id, project_name, status, created_at, summary
                FROM autotest_runs
                WHERE created_by = ?
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user_id,),
            ).fetchall()
        pass_rate = (passed / total_runs * 100) if total_runs > 0 else 0.0
        return {
            "total_runs": total_runs,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 2),
            "recent_runs": [dict(row) for row in recent_runs_rows],
        }

    def get_recent_activity_rows(self, user_id: str, *, days: int = 7) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=days)).isoformat()
        with self._db._connection() as conn:  # noqa: SLF001
            documents_added = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE uploaded_by = ? AND uploaded_at >= ?",
                (user_id, since),
            ).fetchone()[0]
            knowledge_added = conn.execute(
                "SELECT COUNT(*) FROM knowledge_entries WHERE created_by = ? AND created_at >= ?",
                (user_id, since),
            ).fetchone()[0]
            logbook_added = conn.execute(
                "SELECT COUNT(*) FROM logbook_entries WHERE created_by = ? AND created_at >= ?",
                (user_id, since),
            ).fetchone()[0]
            autotest_runs = conn.execute(
                "SELECT COUNT(*) FROM autotest_runs WHERE created_by = ? AND created_at >= ?",
                (user_id, since),
            ).fetchone()[0]
            autotest_passed = conn.execute(
                "SELECT COUNT(*) FROM autotest_runs WHERE created_by = ? AND status = 'passed' AND created_at >= ?",
                (user_id, since),
            ).fetchone()[0]
            autotest_failed = conn.execute(
                "SELECT COUNT(*) FROM autotest_runs WHERE created_by = ? AND status = 'failed' AND created_at >= ?",
                (user_id, since),
            ).fetchone()[0]
        return {
            "documents_added": documents_added,
            "knowledge_added": knowledge_added,
            "logbook_added": logbook_added,
            "autotest_runs": autotest_runs,
            "autotest_passed": autotest_passed,
            "autotest_failed": autotest_failed,
        }
