from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.services.report_generator import ReportGenerator


@pytest.fixture
def mock_autotest_data(app_module, monkeypatch):
    run_id = str(uuid.uuid4())
    run_data = {
        "run_id": run_id,
        "project_name": "Test Project",
        "source_ref": "test.zip",
        "project_type_detected": "python",
        "execution_mode": "simulated",
        "working_directory": ".",
        "status": "passed",
        "summary": "All tests passed.",
        "suggestion": "Keep up the good work!",
        "prompt_output": "Fix failing tests...",
        "failed_reason": "",
        "timeline_json": "[]",
        "created_at": "2024-01-01T00:00:00+00:00",
    }
    steps_data = [
        {
            "step_id": "step-install",
            "name": "install",
            "status": "passed",
            "exit_code": 0,
            "started_at": "2024-01-01T00:00:01+00:00",
            "finished_at": "2024-01-01T00:00:05+00:00",
            "command": "pip install",
            "output": "Success",
            "success": 1,
            "stdout_summary": "",
            "stderr_summary": "",
            "error_type": "",
            "created_at": "2024-01-01T00:00:01+00:00",
        }
    ]

    monkeypatch.setattr(app_module.db, "get_autotest_run", lambda run_id, created_by: run_data)
    monkeypatch.setattr(app_module.db, "list_autotest_steps", lambda run_id: steps_data)
    monkeypatch.setattr(app_module, "db", app_module.db)
    return run_id


def test_report_generator_markdown():
    run_data = {
        "project_name": "Test",
        "project_type_detected": "python",
        "summary": "Passed",
    }
    steps_data = [{"name": "test", "status": "passed"}]
    markdown = ReportGenerator.generate_markdown(run_data, steps_data)
    assert "# Project AutoTest Report" in markdown
    assert "## 1. Project Information" in markdown
    assert "Test" in markdown


def test_report_generator_html():
    markdown = "# Title\n- Item"
    html = ReportGenerator.convert_to_html(markdown)
    assert "<!DOCTYPE html>" in html
    assert "Title" in html


def test_export_api_md(client: TestClient, auth_headers: dict[str, str], mock_autotest_data: str):
    response = client.get(f"/api/autotest/{mock_autotest_data}/export?format=md", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "Project AutoTest Report" in response.text


def test_export_api_html(client: TestClient, auth_headers: dict[str, str], mock_autotest_data: str):
    response = client.get(f"/api/autotest/{mock_autotest_data}/export?format=html", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "<!DOCTYPE html>" in response.text


def test_export_api_404(app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch):
    monkeypatch.setattr(app_module.db, "get_autotest_run", lambda run_id, created_by: None)
    response = client.get("/api/autotest/nonexistent/export?format=md", headers=auth_headers)
    assert response.status_code == 404


def test_export_api_invalid_format(client: TestClient, auth_headers: dict[str, str], mock_autotest_data: str):
    response = client.get(f"/api/autotest/{mock_autotest_data}/export?format=pdf", headers=auth_headers)
    assert response.status_code == 400
