import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.report_generator import ReportGenerator
import uuid

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
    
    # Mock database calls
    from app.context import db
    monkeypatch.setattr(db, "get_autotest_run", lambda run_id, created_by: run_data)
    monkeypatch.setattr(db, "list_autotest_steps", lambda run_id: steps_data)
    
    return run_id

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

def test_export_api_md(mock_autotest_data):
    # Mock current user
    headers = {"Authorization": "Bearer test-token"}
    # We need to mock get_current_user dependency
    from app.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"sub": "owner", "role": "owner"}
    
    response = client.get(f"/api/autotest/{mock_autotest_data}/export?format=md", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "Project AutoTest Report" in response.text
    
    app.dependency_overrides.clear()

def test_export_api_html(mock_autotest_data):
    from app.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"sub": "owner", "role": "owner"}
    
    response = client.get(f"/api/autotest/{mock_autotest_data}/export?format=html", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "<!DOCTYPE html>" in response.text
    
    app.dependency_overrides.clear()

def test_export_api_404(monkeypatch):
    from app.context import db
    monkeypatch.setattr(db, "get_autotest_run", lambda run_id, created_by: None)
    
    from app.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"sub": "owner", "role": "owner"}
    
    response = client.get("/api/autotest/nonexistent/export?format=md", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 404
    
    app.dependency_overrides.clear()
