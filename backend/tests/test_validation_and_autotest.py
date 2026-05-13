from __future__ import annotations

import io
import time
import zipfile

from fastapi.testclient import TestClient


def build_zip(*, marker_fail_step: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("package.json", '{"name":"demo","version":"1.0.0","scripts":{"test":"echo ok","build":"echo ok","lint":"echo ok"}}')
        archive.writestr("README.md", "# Demo")
        if marker_fail_step:
            archive.writestr(".autotest_fail_step", marker_fail_step)
    return buffer.getvalue()


def wait_for_autotest_run(client: TestClient, auth_headers: dict[str, str], run_id: str, *, timeout_seconds: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    latest: dict = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/autotest/runs/{run_id}", headers=auth_headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"passed", "failed"}:
            return latest
        time.sleep(0.05)
    raise AssertionError(f"AutoTest run {run_id} did not finish in time. Latest: {latest}")


def test_invalid_template_returns_400(client: TestClient, auth_headers: dict[str, str]):
    response = client.post("/api/generate", headers=auth_headers, json={"template_type": "nope", "inputs": {}})
    assert response.status_code == 400


def test_missing_field_returns_400(client: TestClient):
    response = client.post("/api/login", json={"user_id": "owner"})
    assert response.status_code == 400


def test_autotest_db_rejects_invalid_status(app_module):
    try:
        app_module.db.add_autotest_run(
            run_id="bad-status",
            source_type="upload",
            source_ref="demo.zip",
            execution_mode="simulated",
            project_type_detected="python",
            working_directory=".",
            project_name="Bad",
            project_type="python",
            status="pending",
            summary="",
            suggestion="",
            prompt_output="",
            failed_reason="",
            timeline_json="[]",
            created_by="owner",
        )
    except ValueError as exc:
        assert "Unsupported autotest status" in str(exc)
    else:
        raise AssertionError("Expected invalid autotest status to be rejected.")


def test_autotest_run_success_creates_knowledge_draft(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    queued_payload = response.json()
    assert queued_payload["status"] in {"queued", "running", "passed"}
    payload = wait_for_autotest_run(client, auth_headers, queued_payload["id"])
    assert payload["status"] == "passed"
    assert payload["execution_mode"] == "simulated"
    assert payload["failed_reason"] == ""
    assert [item["key"] for item in payload["timeline"]] == [
        "uploaded",
        "extracted",
        "detected_stack",
        "prepared_environment",
        "ran_tests",
        "generated_report",
        "failed_reason",
    ]
    failed_reason = next(item for item in payload["timeline"] if item["key"] == "failed_reason")
    assert failed_reason["status"] == "skipped"
    assert failed_reason["message"] is None

    knowledge = client.get("/api/knowledge/entries", headers=auth_headers)
    assert knowledge.status_code == 200
    entries = knowledge.json()
    assert len(entries) == 1
    assert entries[0]["title"].startswith("AutoTest Passed")


def test_autotest_run_failure_creates_logbook_entry(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(marker_fail_step="test"), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "failed"
    assert payload["failed_reason"]
    failed_reason = next(item for item in payload["timeline"] if item["key"] == "failed_reason")
    assert failed_reason["status"] == "failed"
    assert failed_reason["message"]

    logbook = client.get("/api/logbook/entries", headers=auth_headers)
    assert logbook.status_code == 200
    entries = logbook.json()
    assert len(entries) == 1
    assert entries[0]["run_id"] == payload["id"]


def test_autotest_run_is_filtered_by_owner(app_module, client: TestClient, auth_headers: dict[str, str]):
    assert app_module.db.add_user("alice", "AlicePass123!", "Alice", "owner")

    response = client.post("/api/login", json={"user_id": "alice", "password": "AlicePass123!"})
    assert response.status_code == 200, response.text
    alice_headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    run_response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert run_response.status_code == 202, run_response.text
    run_id = run_response.json()["id"]

    owner_runs = client.get("/api/autotest/runs", headers=auth_headers)
    assert owner_runs.status_code == 200
    assert owner_runs.json()[0]["id"] == run_id

    alice_runs = client.get("/api/autotest/runs", headers=alice_headers)
    assert alice_runs.status_code == 200
    assert alice_runs.json() == []

    alice_detail = client.get(f"/api/autotest/runs/{run_id}", headers=alice_headers)
    assert alice_detail.status_code == 404


def test_autotest_run_detail_derives_timeline_for_legacy_sparse_runs(app_module, client: TestClient, auth_headers: dict[str, str]):
    run_id = "legacy-run"
    assert app_module.db.add_autotest_run(
        run_id=run_id,
        source_type="github_repo",
        source_ref="https://github.com/example/repo",
        execution_mode="simulated",
        project_type_detected="",
        working_directory="",
        project_name="Legacy Repo",
        project_type="github",
        status="queued",
        summary="",
        suggestion="",
        prompt_output="",
        failed_reason="",
        timeline_json="",
        created_by="owner",
    )

    response = client.get(f"/api/autotest/runs/{run_id}", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert [item["key"] for item in payload["timeline"]] == [
        "uploaded",
        "extracted",
        "detected_stack",
        "prepared_environment",
        "ran_tests",
        "generated_report",
        "failed_reason",
    ]
    assert all(
        set(item.keys()) == {"key", "label", "name", "status", "started_at", "finished_at", "duration_ms", "message"}
        for item in payload["timeline"]
    )


def test_autotest_zip_extract_failure_sets_failed(app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch):
    monkeypatch.setattr(app_module.autotest_service, "safe_extract_zip", lambda zip_path, dest_dir: (_ for _ in ()).throw(ValueError("zip explode failed")))
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "failed"
    assert payload["failed_reason"]


def test_autotest_stack_detection_failure_sets_failed(app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch):
    monkeypatch.setattr(app_module.autotest_service, "find_project_root_on_disk", lambda extracted_dir: (_ for _ in ()).throw(RuntimeError("stack detect failed")))
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "failed"
    assert payload["failed_reason"]


def test_autotest_test_command_failure_sets_failed(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(marker_fail_step="test"), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "failed"
    assert payload["failed_reason"]


def test_autotest_report_generation_failure_sets_failed(app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch):
    monkeypatch.setattr(app_module.autotest_service, "index_knowledge_entry", lambda entry: (_ for _ in ()).throw(RuntimeError("report generation failed")))

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "passed"
    assert payload["failed_reason"] == ""


def test_autotest_real_mode_executes_commands_when_enabled(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True
    calls: list[list[str]] = []

    def fake_run_command(*, argv, cwd, timeout_seconds):
        calls.append(list(argv))
        return 0, "ok", ""

    monkeypatch.setattr(app_module.autotest_service, "_run_command", fake_run_command)

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "passed"
    assert payload["execution_mode"] == "real"
    assert calls
    assert any(command[:2] == ["npm", "ci"] and "--ignore-scripts" in command for command in calls)


def test_autotest_simulated_mode_does_not_execute_real_commands(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "simulated"
    monkeypatch.setattr(
        app_module.autotest_service,
        "_run_command",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("real command should not run in simulated mode")),
    )

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "passed"
    assert payload["execution_mode"] == "simulated"


def test_autotest_run_returns_queued_response_before_background_execution(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    scheduled: list[dict] = []

    def capture_schedule(**kwargs):
        scheduled.append(kwargs)
        return None

    monkeypatch.setattr(app_module.autotest_service, "schedule_autotest_run_job", capture_schedule)

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )

    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["summary"] == "AutoTest queued."
    assert payload["steps"]
    assert all(step["status"] == "queued" for step in payload["steps"])
    assert scheduled
    assert scheduled[0]["run_id"] == payload["id"]


def test_set_timeline_item_can_clear_message(app_module):
    timeline = app_module.autotest_service.initial_autotest_timeline(
        source_ref="demo.zip",
        created_at="2026-05-08T00:00:00+00:00",
    )
    timeline = app_module.autotest_service.set_timeline_item(
        timeline,
        "failed_reason",
        status="failed",
        message="old failure",
    )
    timeline = app_module.autotest_service.set_timeline_item(
        timeline,
        "failed_reason",
        status="skipped",
        clear_message=True,
    )
    failed_reason = next(item for item in timeline if item["key"] == "failed_reason")
    assert failed_reason["status"] == "skipped"
    assert failed_reason["message"] is None
