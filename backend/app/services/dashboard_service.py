from __future__ import annotations

from app.context import db
from app.llm import get_llm_provider
from app.llm.providers import NoopProvider
from app.models import DashboardHealthResponse, SettingsLLMResponse, SettingsOCRResponse
from app.ocr_service import get_ocr_status
from app.repositories.dashboard_repository import DashboardRepository

dashboard_repository = DashboardRepository(db)


def _build_recent_activity_payload(recent_activity_counts: dict[str, int], *, days: int) -> dict[str, int]:
    return {
        "days": days,
        "documents_added": recent_activity_counts["documents_added"],
        "knowledge_added": recent_activity_counts["knowledge_added"],
        "logbook_added": recent_activity_counts["logbook_added"],
        "autotest_runs": recent_activity_counts["autotest_runs"],
        "autotest_passed": recent_activity_counts["autotest_passed"],
        "autotest_failed": recent_activity_counts["autotest_failed"],
    }


def get_dashboard_health(user_id: str) -> DashboardHealthResponse:
    knowledge_counts = dashboard_repository.get_knowledge_counts(user_id)
    logbook_counts = dashboard_repository.get_logbook_counts(user_id)
    document_counts = dashboard_repository.get_document_index_counts(user_id)
    autotest_metrics = dashboard_repository.get_autotest_metrics(user_id)
    recent_activity_counts = dashboard_repository.get_recent_activity_rows(user_id, days=7)

    payload = {
        "knowledge": {
            "total": knowledge_counts["total"],
            "by_status": knowledge_counts["by_status"],
        },
        "logbook": {
            "total": logbook_counts["total"],
            "with_solution": logbook_counts["with_solution"],
            "promoted_to_knowledge": dashboard_repository.get_promoted_logbook_count(user_id),
            "resolution_rate": logbook_counts["resolution_rate"],
        },
        "autotest": {
            "total_runs": autotest_metrics["total_runs"],
            "passed": autotest_metrics["passed"],
            "failed": autotest_metrics["failed"],
            "pass_rate": autotest_metrics["pass_rate"],
            "recent_runs": autotest_metrics["recent_runs"],
        },
        "documents": {
            "total": document_counts["total"],
            "indexed": document_counts["indexed"],
            "pending": document_counts["pending"],
            "failed_documents": document_counts["failed_documents"],
            "archived_documents": document_counts["archived_documents"],
        },
        "recent_activity": _build_recent_activity_payload(recent_activity_counts, days=7),
    }
    return DashboardHealthResponse(**payload)


async def get_llm_settings(user_id: str) -> SettingsLLMResponse:
    _ = user_id
    _provider, status_payload = get_llm_provider()

    primary_provider = status_payload["primary_provider_instance"]
    primary_healthy = bool(await primary_provider.healthcheck())

    fallback_provider = status_payload.get("fallback_provider_instance")
    fallback_enabled = fallback_provider is not None
    fallback_is_noop = bool(
        fallback_provider
        and (
            isinstance(fallback_provider, NoopProvider)
            or str(getattr(fallback_provider, "name", "") or "").lower() == NoopProvider.name
            or str(getattr(fallback_provider, "model", "") or "").lower() == "none"
        )
    )
    fallback_healthy = bool(await fallback_provider.healthcheck()) if fallback_enabled else False
    fallback_ready_for_generation = fallback_enabled and fallback_healthy and not fallback_is_noop

    if primary_healthy:
        active_provider = str(status_payload.get("primary_provider", "") or "")
        ready_for_generation = True
        error_message = ""
    elif fallback_ready_for_generation:
        active_provider = str(status_payload.get("fallback_provider", "") or "")
        ready_for_generation = True
        error_message = str(
            status_payload.get("primary_error_message", "") or "Primary provider is unavailable; using healthy fallback provider."
        )
    elif fallback_enabled:
        active_provider = str(status_payload.get("fallback_provider", "") or "none")
        ready_for_generation = False
        if fallback_is_noop:
            error_message = str(
                status_payload.get("primary_error_message", "")
                or "Primary provider is unavailable; fallback is noop only, so generation is unavailable."
            )
        else:
            error_message = str(
                status_payload.get("primary_error_message", "")
                or "Primary provider is unavailable and fallback provider is not healthy."
            )
    else:
        active_provider = "none"
        ready_for_generation = False
        error_message = str(status_payload.get("primary_error_message", "") or "Primary provider is unavailable.")

    return SettingsLLMResponse(
        primary_provider=str(status_payload.get("primary_provider", "")),
        active_provider=active_provider or "none",
        model=str(status_payload.get("model", "")),
        base_url=str(status_payload.get("base_url", "")),
        primary_healthy=primary_healthy,
        fallback_enabled=fallback_enabled,
        llm_ready_for_generation=ready_for_generation,
        error_message=error_message,
    )


def get_ocr_settings(user_id: str) -> SettingsOCRResponse:
    _ = user_id
    status_payload = get_ocr_status()
    return SettingsOCRResponse(
        enabled=bool(status_payload.get("enabled", False)),
        available=bool(status_payload.get("available", False)),
        tesseract_cmd=str(status_payload.get("tesseract_cmd", "") or ""),
        tesseract_version=str(status_payload.get("tesseract_version", "") or ""),
        details=str(status_payload.get("details", "") or ""),
    )
