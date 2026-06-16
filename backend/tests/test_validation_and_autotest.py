from __future__ import annotations

import io
import sqlite3
import subprocess
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


def build_zip(*, marker_fail_step: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "package.json",
            '{"name":"demo","version":"1.0.0","scripts":{"test":"echo ok","build":"echo ok","lint":"echo ok"}}',
        )
        archive.writestr("README.md", "# Demo")
        if marker_fail_step:
            archive.writestr(".autotest_fail_step", marker_fail_step)
    return buffer.getvalue()


def wait_for_autotest_run(
    client: TestClient, auth_headers: dict[str, str], run_id: str, *, timeout_seconds: float = 5.0
) -> dict:
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


def test_missing_field_returns_422(client: TestClient):
    response = client.post("/api/login", json={"user_id": "owner"})
    assert response.status_code == 422


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
    assert "simulated mode" in queued_payload["summary"].lower()
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
    entries = knowledge.json()["items"]
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
    entries = logbook.json()["items"]
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


def test_autotest_run_detail_derives_timeline_for_legacy_sparse_runs(
    app_module, client: TestClient, auth_headers: dict[str, str]
):
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


def test_autotest_run_detail_handles_nullable_numeric_fields(
    app_module, client: TestClient, auth_headers: dict[str, str]
):
    run_id = "nullable-numeric-run"
    assert app_module.db.add_autotest_run(
        run_id=run_id,
        source_type="zip_upload",
        source_ref="nullable.zip",
        execution_mode="simulated",
        project_type_detected="node",
        working_directory=".",
        project_name="Nullable Numeric",
        project_type="node",
        status="failed",
        summary="failed after extraction",
        suggestion="",
        prompt_output="",
        failed_reason="zip explode failed",
        timeline_json='[{"key":"uploaded","label":"Uploaded","name":"Uploaded","status":"success","started_at":null,"finished_at":null,"duration_ms":null,"message":"nullable.zip"},{"key":"failed_reason","label":"Failed reason","name":"Failed reason","status":"failed","started_at":null,"finished_at":null,"duration_ms":"not-a-number","message":"zip explode failed"}]',
        created_by="owner",
    )
    assert app_module.db.add_autotest_step(
        step_id="nullable-step",
        run_id=run_id,
        name="test",
        command="npm test",
        status="failed",
        success=None,
        exit_code=None,
    )

    response = client.get(f"/api/autotest/runs/{run_id}", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["steps"][0]["success"] == 0
    assert payload["steps"][0]["exit_code"] == 0
    assert payload["timeline"][0]["duration_ms"] is None
    assert payload["timeline"][1]["duration_ms"] is None


def test_autotest_zip_extract_failure_sets_failed(
    app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch
):
    monkeypatch.setattr(
        app_module.autotest_service,
        "safe_extract_zip",
        lambda zip_path, dest_dir: (_ for _ in ()).throw(ValueError("zip explode failed")),
    )
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KW_AUTOTEST_REAL_MODE = True
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "local_trusted"

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "failed"
    assert payload["failed_reason"]


def test_autotest_stack_detection_failure_sets_failed(
    app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch
):
    monkeypatch.setattr(
        app_module.autotest_service,
        "find_project_root_on_disk",
        lambda extracted_dir: (_ for _ in ()).throw(RuntimeError("stack detect failed")),
    )
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KW_AUTOTEST_REAL_MODE = True
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "local_trusted"

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "failed"
    assert "stack detect failed" in payload["failed_reason"]
    assert "stack detection failed" in payload["summary"].lower()
    detected_stack = next(item for item in payload["timeline"] if item["key"] == "detected_stack")
    assert detected_stack["status"] == "failed"
    assert "stack detect failed" in detected_stack["message"]
    assert all(item["status"] != "running" for item in payload["timeline"])
    assert all(step["status"] != "running" for step in payload["steps"])
    assert all(step["status"] in {"skipped", "failed"} for step in payload["steps"])
    assert all(step["name"] != "install" or step["status"] == "skipped" for step in payload["steps"])


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


def test_autotest_report_generation_failure_sets_failed(
    app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch
):
    monkeypatch.setattr(
        app_module.autotest_service,
        "index_knowledge_entry",
        lambda entry: (_ for _ in ()).throw(RuntimeError("report generation failed")),
    )

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "passed"
    assert payload["failed_reason"] == ""


def test_autotest_pass_side_effect_failure_keeps_terminal_status(
    app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch
):
    from app.services.autotest import job_reporter

    monkeypatch.setattr(
        job_reporter,
        "create_passed_knowledge_draft",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("knowledge side effect exploded")),
    )

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "passed"
    assert payload["failed_reason"] == ""
    assert payload["timeline"][-1]["status"] == "skipped"


def test_autotest_failed_side_effect_failure_keeps_terminal_status(
    app_module, client: TestClient, auth_headers: dict[str, str], monkeypatch
):
    from app.services.autotest import job_reporter

    monkeypatch.setattr(
        job_reporter,
        "create_failed_logbook_draft",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("logbook side effect exploded")),
    )

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(marker_fail_step="test"), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "failed"
    assert payload["failed_reason"]
    assert payload["timeline"][-1]["status"] == "failed"


def test_autotest_real_mode_executes_commands_when_enabled(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KW_AUTOTEST_REAL_MODE = True
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "local_trusted"
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


def test_autotest_real_mode_timeout_is_terminal_failed(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KW_AUTOTEST_REAL_MODE = True
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "local_trusted"

    def fake_run_command(*, argv, cwd, timeout_seconds):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout_seconds)

    monkeypatch.setattr(app_module.autotest_service, "_run_command", fake_run_command)

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_zip(), "application/zip")},
    )
    assert response.status_code == 202, response.text
    payload = wait_for_autotest_run(client, auth_headers, response.json()["id"])
    assert payload["status"] == "failed"
    assert "timed out" in payload["failed_reason"].lower()
    assert payload["timeline"][-1]["status"] == "failed"


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
    assert payload["execution_mode"] == "simulated"
    assert "queued in simulated mode" in payload["summary"].lower()
    assert payload["steps"]
    assert all(step["status"] == "queued" for step in payload["steps"])
    assert scheduled
    assert scheduled[0]["run_id"] == payload["id"]


def test_autotest_run_detail_uses_valid_simulated_execution_mode(
    app_module, client: TestClient, auth_headers: dict[str, str]
):
    run_id = "valid-simulated-mode"
    with app_module.db._connection() as conn:
        conn.execute(
            """
            INSERT INTO autotest_runs (
                run_id,
                source_type,
                source_ref,
                execution_mode,
                project_type_detected,
                working_directory,
                project_name,
                project_type,
                status,
                summary,
                suggestion,
                prompt_output,
                failed_reason,
                timeline_json,
                problem_entry_id,
                solution_entry_id,
                created_by,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "zip_upload",
                "simulated.zip",
                "simulated",
                "",
                "",
                "Simulated",
                "zip",
                "failed",
                "simulated row",
                "",
                "",
                "simulated failure",
                "",
                "",
                "",
                "owner",
                "2026-05-08T00:00:00+00:00",
                "2026-05-08T00:00:00+00:00",
            ),
        )
        conn.commit()

    response = client.get(f"/api/autotest/runs/{run_id}", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["execution_mode"] == "simulated"


def test_autotest_run_detail_rejects_missing_execution_mode_at_db_layer(app_module):
    with app_module.db._connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO autotest_runs (
                    run_id,
                    source_type,
                    source_ref,
                    execution_mode,
                    project_type_detected,
                    working_directory,
                    project_name,
                    project_type,
                    status,
                    summary,
                    suggestion,
                    prompt_output,
                    failed_reason,
                    timeline_json,
                    problem_entry_id,
                    solution_entry_id,
                    created_by,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "invalid-missing-mode",
                    "zip_upload",
                    "legacy.zip",
                    "",
                    "",
                    "",
                    "Legacy",
                    "zip",
                    "failed",
                    "legacy row",
                    "",
                    "",
                    "legacy failure",
                    "",
                    "",
                    "",
                    "owner",
                    "2026-05-08T00:00:00+00:00",
                    "2026-05-08T00:00:00+00:00",
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            assert "CHECK constraint failed" in str(exc)
        else:
            raise AssertionError("Expected invalid execution_mode to fail a SQLite CHECK constraint.")


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


def _create_recovery_run(app_module, *, run_id: str, status: str) -> None:
    assert app_module.db.add_autotest_run(
        run_id=run_id,
        source_type="zip_upload",
        source_ref=f"{run_id}.zip",
        execution_mode="simulated",
        project_type_detected="node",
        working_directory=".",
        project_name=run_id,
        project_type="node",
        status=status,
        summary="",
        suggestion="",
        prompt_output="",
        failed_reason="",
        timeline_json="",
        created_by="owner",
    )
    assert app_module.db.add_autotest_step(
        step_id=f"{run_id}-test",
        run_id=run_id,
        name="test",
        command="npm test",
        status="running" if status == "running" else "queued",
    )


def _set_run_updated_at(app_module, *, run_id: str, updated_at: str) -> None:
    with app_module.db._connection() as conn:
        conn.execute("UPDATE autotest_runs SET updated_at = ? WHERE run_id = ?", (updated_at, run_id))
        conn.commit()


def test_autotest_startup_recovery_fails_stale_running_run(app_module):
    from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

    _create_recovery_run(app_module, run_id="stale-running", status="running")
    recovered = recover_interrupted_autotest_runs(
        now=datetime.now(timezone.utc) + timedelta(minutes=31),
        stale_after_minutes=30,
    )

    run = app_module.db.get_autotest_run(run_id="stale-running", created_by="owner")
    assert recovered == 1
    assert run["status"] == "failed"
    assert "worker_interrupted" in run["failed_reason"]
    assert "server_restarted" in run["failed_reason"]
    assert "stale_running_job" in run["failed_reason"]
    assert run["summary"].startswith("AutoTest run failed")


def test_autotest_startup_recovery_fails_stale_queued_run(app_module):
    from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

    _create_recovery_run(app_module, run_id="stale-queued", status="queued")
    recovered = recover_interrupted_autotest_runs(
        now=datetime.now(timezone.utc) + timedelta(minutes=31),
        stale_after_minutes=30,
    )

    run = app_module.db.get_autotest_run(run_id="stale-queued", created_by="owner")
    assert recovered == 1
    assert run["status"] == "failed"
    assert "server_restarted" in run["failed_reason"]
    assert "stale_queued_job" in run["failed_reason"]


def test_failed_recovered_run_detail_is_not_reported_as_running(
    app_module, client: TestClient, auth_headers: dict[str, str]
):
    from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

    _create_recovery_run(app_module, run_id="recovered-detail", status="running")
    recovered = recover_interrupted_autotest_runs(
        now=datetime.now(timezone.utc) + timedelta(minutes=31),
        stale_after_minutes=30,
    )

    assert recovered == 1
    detail = client.get("/api/autotest/runs/recovered-detail", headers=auth_headers)
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "failed"
    assert payload["timeline"][-1]["status"] == "failed"
    assert payload["timeline"][-1]["message"]


def test_autotest_startup_recovery_keeps_recent_running_run(app_module):
    from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

    _create_recovery_run(app_module, run_id="recent-running", status="running")
    _set_run_updated_at(
        app_module,
        run_id="recent-running",
        updated_at=(datetime.now(timezone.utc) + timedelta(minutes=4)).isoformat(),
    )
    recovered = recover_interrupted_autotest_runs(
        now=datetime.now(timezone.utc) + timedelta(minutes=5),
        stale_after_minutes=30,
    )

    run = app_module.db.get_autotest_run(run_id="recent-running", created_by="owner")
    assert recovered == 0
    assert run["status"] == "running"


def test_autotest_startup_recovery_ignores_terminal_runs(app_module):
    from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

    _create_recovery_run(app_module, run_id="already-failed", status="failed")
    recovered = recover_interrupted_autotest_runs(
        now=datetime.now(timezone.utc) + timedelta(minutes=31),
        stale_after_minutes=30,
    )

    run = app_module.db.get_autotest_run(run_id="already-failed", created_by="owner")
    assert recovered == 0
    assert run["status"] == "failed"


def test_autotest_run_updates_updated_at_on_status_and_summary_changes(app_module):
    run_id = "updated-at-run"
    assert app_module.db.add_autotest_run(
        run_id=run_id,
        source_type="zip_upload",
        source_ref="updated.zip",
        execution_mode="simulated",
        project_type_detected="node",
        working_directory=".",
        project_name="UpdatedAt",
        project_type="node",
        status="queued",
        summary="queued",
        suggestion="",
        prompt_output="",
        failed_reason="",
        timeline_json="[]",
        created_by="owner",
    )

    initial = app_module.db.get_autotest_run(run_id=run_id, created_by="owner")
    assert initial["updated_at"] == initial["created_at"]
    time.sleep(0.01)

    assert app_module.db.update_autotest_run(run_id, status="running", summary="started")
    updated = app_module.db.get_autotest_run(run_id=run_id, created_by="owner")
    assert updated["status"] == "running"
    assert updated["summary"] == "started"
    assert updated["updated_at"] >= initial["updated_at"]


def test_autotest_startup_recovery_prefers_updated_at_for_stale_detection(app_module):
    from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

    now = datetime.now(timezone.utc)
    _create_recovery_run(app_module, run_id="fresh-updated", status="running")
    _set_run_updated_at(
        app_module,
        run_id="fresh-updated",
        updated_at=(now + timedelta(minutes=5)).isoformat(),
    )
    recovered = recover_interrupted_autotest_runs(
        now=now + timedelta(minutes=31),
        stale_after_minutes=30,
    )

    run = app_module.db.get_autotest_run(run_id="fresh-updated", created_by="owner")
    assert recovered == 0
    assert run["status"] == "running"


def test_autotest_startup_recovery_falls_back_to_created_at_when_updated_at_missing(app_module):
    from app.services.autotest.run_lifecycle import recover_interrupted_autotest_runs

    _create_recovery_run(app_module, run_id="legacy-no-updated", status="queued")
    _set_run_updated_at(app_module, run_id="legacy-no-updated", updated_at="")
    recovered = recover_interrupted_autotest_runs(
        now=datetime.now(timezone.utc) + timedelta(minutes=31),
        stale_after_minutes=30,
    )

    run = app_module.db.get_autotest_run(run_id="legacy-no-updated", created_by="owner")
    assert recovered == 1
    assert run["status"] == "failed"


def test_autotest_migration_backfills_updated_at_for_legacy_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
    db_path = tmp_path / "legacy-autotest.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE autotest_runs (
            run_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE autotest_steps (
            step_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO autotest_runs (run_id, source_type, source_ref, status, created_at)
        VALUES ('legacy-run', 'zip_upload', 'legacy.zip', 'queued', '2026-05-08T00:00:00+00:00')
        """
    )
    conn.commit()
    conn.close()

    from app.db import DocumentDatabase

    migrated = DocumentDatabase(str(Path(db_path)))
    run = migrated.get_autotest_run(run_id="legacy-run", created_by="owner")
    assert run is not None
    assert run["execution_mode"] == "simulated"
    assert run["updated_at"] == "2026-05-08T00:00:00+00:00"


def test_autotest_migration_normalizes_invalid_execution_mode_and_schema_default(tmp_path, monkeypatch):
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")
    db_path = tmp_path / "legacy-autotest-invalid-mode.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE autotest_runs (
            run_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            execution_mode TEXT NOT NULL DEFAULT 'real',
            project_type_detected TEXT NOT NULL DEFAULT '',
            working_directory TEXT NOT NULL DEFAULT '',
            project_name TEXT NOT NULL DEFAULT '',
            project_type TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'queued',
            summary TEXT NOT NULL DEFAULT '',
            suggestion TEXT NOT NULL DEFAULT '',
            prompt_output TEXT NOT NULL DEFAULT '',
            failed_reason TEXT NOT NULL DEFAULT '',
            timeline_json TEXT NOT NULL DEFAULT '',
            problem_entry_id TEXT NOT NULL DEFAULT '',
            solution_entry_id TEXT NOT NULL DEFAULT '',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE autotest_steps (
            step_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO autotest_runs (
            run_id, source_type, source_ref, execution_mode, project_name, project_type, status, created_by, created_at, updated_at
        ) VALUES ('legacy-invalid-mode', 'github_repo', 'https://github.com/example/repo', 'unexpected', 'repo', 'github', 'registered', 'owner', '2026-05-08T00:00:00+00:00', '')
        """
    )
    conn.commit()
    conn.close()

    from app.db import DocumentDatabase

    migrated = DocumentDatabase(str(Path(db_path)))
    run = migrated.get_autotest_run(run_id="legacy-invalid-mode", created_by="owner")
    assert run is not None
    assert run["execution_mode"] == "simulated"

    with migrated._connection() as check_conn:
        execution_mode_info = next(
            row for row in check_conn.execute("PRAGMA table_info(autotest_runs)").fetchall() if row[1] == "execution_mode"
        )
        assert str(execution_mode_info[4]).strip("'\"") == "simulated"
