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
    assert "Invalid GitHub URL" in response.json()["message"]


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
        "status": "registered",
        "execution_mode": "simulated",
        "analysis_scope": "intake_only",
        "remote_clone_performed": False,
        "report_ready": False,
        "message": "GitHub repository registered for intake-only analysis metadata. It is not queued for execution; remote clone, remote test execution, and full repository scan are not performed.",
        "repo_info": {
            "owner": "a1354013-alt",
            "repo": "Knowledge_Workspace",
            "url": "https://github.com/a1354013-alt/Knowledge_Workspace",
            "default_branch": "",
            "provider": "github",
            "clone_supported": False,
            "analysis_scope": "intake_only",
        },
    }


def test_analyze_github_repo_run_detail_uses_honest_summary(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/autotest/github/analyze",
        json={"repo_url": "https://github.com/a1354013-alt/Knowledge_Workspace"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text

    detail = client.get(f"/api/autotest/runs/{response.json()['run_id']}", headers=auth_headers)
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "registered"
    assert payload["execution_mode"] == "simulated"
    assert "intake-only analysis metadata" in payload["summary"].lower()
    assert "not queued for execution" in payload["summary"].lower()
    assert "clone" in payload["summary"].lower()
    assert "full repository scan" in response.json()["message"].lower()


def test_get_repo_info():
    from app.services.autotest_service import get_repo_info

    assert get_repo_info("https://github.com/owner/my-project.git") == {
        "owner": "owner",
        "repo": "my-project",
        "url": "https://github.com/owner/my-project",
        "default_branch": "",
        "provider": "github",
        "clone_supported": False,
        "analysis_scope": "intake_only",
    }
