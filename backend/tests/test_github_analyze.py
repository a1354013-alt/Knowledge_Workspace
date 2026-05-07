import os

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_token
from app.main import app

client = TestClient(app)

# Set environment variables for tests
os.environ.setdefault("JWT_SECRET", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")

@pytest.fixture
def auth_headers():
    token = create_token(user_id="owner", role="owner", display_name="Owner")
    yield {"Authorization": f"Bearer {token}"}

def test_validate_github_url():
    from app.api.legacy_main import validate_github_url

    assert validate_github_url("https://github.com/owner/repo")
    assert validate_github_url("https://github.com/owner/repo.git")
    assert validate_github_url("https://github.com/owner/repo/")
    assert not validate_github_url("http://github.com/owner/repo")
    assert not validate_github_url("https://evil.com/owner/repo")
    assert not validate_github_url("https://github.com/owner/repo;rm -rf /")
    assert not validate_github_url("https://github.com/owner")

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
    payload = response.json()
    assert "run_id" in payload
    assert payload["status"] == "queued"
    assert payload["repo_info"] == {
        "owner": "a1354013-alt",
        "repo": "Knowledge_Workspace",
        "url": "https://github.com/a1354013-alt/Knowledge_Workspace",
        "default_branch": "",
        "provider": "github",
        "clone_supported": False,
    }

def test_get_repo_info():
    from app.api.legacy_main import get_repo_info

    repo_info = get_repo_info("https://github.com/owner/my-project.git")
    assert repo_info == {
        "owner": "owner",
        "repo": "my-project",
        "url": "https://github.com/owner/my-project",
        "default_branch": "",
        "provider": "github",
        "clone_supported": False,
    }
