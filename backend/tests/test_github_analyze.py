from __future__ import annotations

from fastapi.testclient import TestClient


def test_validate_github_url():
    from app.services.autotest_service import validate_github_url

    assert validate_github_url("https://github.com/owner/repo")
    assert validate_github_url("https://github.com/owner/repo.git")
    assert validate_github_url("https://github.com/owner/repo/")
    assert not validate_github_url("http://github.com/owner/repo")
    assert not validate_github_url("https://evil.com/owner/repo")
    assert not validate_github_url("https://github.com/owner/repo;rm -rf /")
    assert not validate_github_url("https://github.com/owner")


def test_analyze_github_repo_invalid_url(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/autotest/github/analyze",
        json={"repo_url": "invalid-url"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Invalid GitHub URL" in response.json()["detail"]


def test_analyze_github_repo_success_trigger(app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch):
    monkeypatch.setattr(app_module.db, "add_autotest_run", lambda **kwargs: True)

    response = client.post(
        "/api/autotest/github/analyze",
        json={"repo_url": "https://github.com/a1354013-alt/Knowledge_Workspace"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {
        "run_id": response.json()["run_id"],
        "status": "queued",
        "repo_info": {
            "owner": "a1354013-alt",
            "repo": "Knowledge_Workspace",
            "url": "https://github.com/a1354013-alt/Knowledge_Workspace",
            "default_branch": "",
            "provider": "github",
            "clone_supported": False,
        },
    }


def test_get_repo_info():
    from app.services.autotest_service import get_repo_info

    assert get_repo_info("https://github.com/owner/my-project.git") == {
        "owner": "owner",
        "repo": "my-project",
        "url": "https://github.com/owner/my-project",
        "default_branch": "",
        "provider": "github",
        "clone_supported": False,
    }
