import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import legacy_main
from app.context import db
from app.core.security import create_token
from app.main import app
from app.services.report_generator import ReportGenerator

client = TestClient(app)

@pytest.fixture
def mock_autotest_data(monkeypatch):
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
        "created_at": "2024-01-01T00:00:00Z"
    }
    steps_data = [
        {
            "name": "install",
            "status": "passed",
            "exit_code": 0,
            "started_at": "2024-01-01T00:00:01Z",
            "finished_at": "2024-01-01T00:00:05Z",
            "command": "pip install",
            "output": "Success"
        }
    ]
    
    monkeypatch.setattr(db, "get_autotest_run", lambda run_id, created_by: run_data)
    monkeypatch.setattr(db, "list_autotest_steps", lambda run_id: steps_data)
    monkeypatch.setattr(legacy_main.db, "get_autotest_run", lambda run_id, created_by: run_data)
    monkeypatch.setattr(legacy_main.db, "list_autotest_steps", lambda run_id: steps_data)
    
    return run_id


@pytest.fixture
def auth_headers():
    token = create_token(user_id="owner", role="owner", display_name="Owner")
    return {"Authorization": f"Bearer {token}"}

def test_report_generator_markdown():
    run_data = {
        "project_name": "Test",
        "project_type_detected": "python",
        "summary": "Passed"
    }
    steps_data = [{"name": "test", "status": "passed"}]
    md = ReportGenerator.generate_markdown(run_data, steps_data)
    assert "# Project AutoTest Report" in md
    assert "## 1. Project Information" in md
    assert "Test" in md

def test_report_generator_html():
    md = "# Title\n- Item"
    html = ReportGenerator.convert_to_html(md)
    assert "<!DOCTYPE html>" in html
    assert "Title" in html

def test_export_api_md(mock_autotest_data, auth_headers):
    response = client.get(f"/api/autotest/{mock_autotest_data}/export?format=md", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "Project AutoTest Report" in response.text

def test_export_api_html(mock_autotest_data, auth_headers):
    response = client.get(f"/api/autotest/{mock_autotest_data}/export?format=html", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "<!DOCTYPE html>" in response.text


def test_export_api_404(monkeypatch, auth_headers):
    monkeypatch.setattr(db, "get_autotest_run", lambda run_id, created_by: None)
    monkeypatch.setattr(legacy_main.db, "get_autotest_run", lambda run_id, created_by: None)

    response = client.get("/api/autotest/nonexistent/export?format=md", headers=auth_headers)
    assert response.status_code == 404

def test_export_api_invalid_format(mock_autotest_data, auth_headers):
    response = client.get(
        f"/api/autotest/{mock_autotest_data}/export?format=pdf",
        headers=auth_headers,
    )
    assert response.status_code == 400
