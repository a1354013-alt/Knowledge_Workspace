from __future__ import annotations

from app.context import db
from app.models import DashboardHealthResponse
from app.repositories.dashboard_repository import DashboardRepository

dashboard_repository = DashboardRepository(db)


def get_dashboard_health(user_id: str) -> DashboardHealthResponse:
    payload = {
        "knowledge": dashboard_repository.fetch_knowledge_metrics(user_id),
        "logbook": dashboard_repository.fetch_logbook_metrics(user_id),
        "autotest": dashboard_repository.fetch_autotest_metrics(user_id),
        "documents": dashboard_repository.fetch_document_metrics(user_id),
        "recent_activity": dashboard_repository.fetch_recent_activity(user_id, days=7),
    }
    return DashboardHealthResponse(**payload)
