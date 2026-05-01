import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid
import os

client = TestClient(app)

# Set environment variables for tests
os.environ["JWT_SECRET"] = "0123456789abcdef0123456789abcdef"
os.environ["DEFAULT_OWNER_PASSWORD"] = "password123"

@pytest.fixture
def auth_headers():
    from app.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"sub": "owner", "role": "owner"}
    yield {"Authorization": "Bearer test-token"}
    app.dependency_overrides.clear()

def test_validate_github_url():
    from app.api.legacy_main import validate_github_url
    assert validate_github_url("https://github.com/owner/repo") == True
    assert validate_github_url("https://github.com/owner/repo.git") == True
    assert validate_github_url("https://github.com/owner/repo/") == True
    assert validate_github_url("http://github.com/owner/repo") == False
    assert validate_github_url("https://evil.com/owner/repo") == False
    assert validate_github_url("https://github.com/owner/repo;rm -rf /") == False

def test_analyze_github_repo_invalid_url(auth_headers):
    response = client.post(
        "/api/autotest/github/analyze",
        json={"repo_url": "invalid-url"},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "Invalid GitHub URL" in response.json()["detail"]

def test_analyze_github_repo_success_trigger(auth_headers, monkeypatch):
    # Mock background task and DB
    from app.context import db
    monkeypatch.setattr(db, "add_autotest_run", lambda **kwargs: True)
    
    response = client.post(
        "/api/autotest/github/analyze",
        json={"repo_url": "https://github.com/a1354013-alt/Knowledge_Workspace"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "run_id" in response.json()
    assert response.json()["status"] == "queued"

def test_get_repo_info():
    from app.api.legacy_main import get_repo_info
    owner, repo = get_repo_info("https://github.com/owner/my-project.git")
    assert owner == "owner"
    assert repo == "my-project"
