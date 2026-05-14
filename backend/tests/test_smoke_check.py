from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SMOKE_CHECK_PATH = ROOT_DIR / "scripts" / "smoke_check.py"


def load_smoke_check_module():
    spec = importlib.util.spec_from_file_location("smoke_check", SMOKE_CHECK_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load scripts/smoke_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_autotest_smoke_check_polls_until_passed(monkeypatch):
    smoke_check = load_smoke_check_module()
    poll_calls: list[tuple[str, str, str | None]] = []

    monkeypatch.setattr(
        smoke_check,
        "call_multipart",
        lambda **kwargs: (
            202,
            json.dumps(
                {
                    "id": "run-123",
                    "status": "queued",
                    "execution_mode": "simulated",
                    "project_type_detected": "node",
                    "working_directory": ".",
                }
            ),
        ),
    )

    responses = iter(
        [
            (200, json.dumps({"id": "run-123", "status": "queued"})),
            (200, json.dumps({"id": "run-123", "status": "passed"})),
        ]
    )

    def fake_call(method: str, url: str, payload=None, token: str | None = None):
        poll_calls.append((method, url, token))
        return next(responses)

    monkeypatch.setattr(smoke_check, "call", fake_call)
    monkeypatch.setattr(smoke_check.time, "sleep", lambda _: None)

    result = smoke_check.run_autotest_smoke_check(
        base_url="http://localhost:8000",
        token="token-1",
        smoke_id="abc123",
    )

    assert result == 0
    assert poll_calls == [
        ("GET", "http://localhost:8000/api/autotest/runs/run-123", "token-1"),
        ("GET", "http://localhost:8000/api/autotest/runs/run-123", "token-1"),
    ]


def test_run_autotest_smoke_check_returns_failure_details_for_failed_run(monkeypatch, capsys):
    smoke_check = load_smoke_check_module()
    monkeypatch.setattr(
        smoke_check,
        "call_multipart",
        lambda **kwargs: (
            202,
            json.dumps(
                {
                    "id": "run-456",
                    "status": "queued",
                    "execution_mode": "simulated",
                    "project_type_detected": "node",
                    "working_directory": ".",
                }
            ),
        ),
    )
    monkeypatch.setattr(
        smoke_check,
        "call",
        lambda method, url, payload=None, token=None: (
            200,
            json.dumps(
                {
                    "id": "run-456",
                    "status": "failed",
                    "summary": "Acceptance pipeline failed.",
                    "failed_reason": "lint exploded",
                    "suggestion": "Fix lint.",
                    "timeline": [{"key": "failed_reason", "message": "lint exploded"}],
                }
            ),
        ),
    )
    monkeypatch.setattr(smoke_check.time, "sleep", lambda _: None)

    result = smoke_check.run_autotest_smoke_check(
        base_url="http://localhost:8000",
        token="token-2",
        smoke_id="def456",
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "failed_reason: lint exploded" in captured.out
    assert '"failed_reason"' in captured.out


def test_poll_autotest_run_times_out_when_run_never_finishes(monkeypatch, capsys):
    smoke_check = load_smoke_check_module()
    monotonic_values = iter([0.0, 0.0, 1.0, 2.0, 61.0])

    monkeypatch.setattr(
        smoke_check,
        "call",
        lambda method, url, payload=None, token=None: (200, json.dumps({"id": "run-timeout", "status": "running"})),
    )
    monkeypatch.setattr(smoke_check.time, "sleep", lambda _: None)
    monkeypatch.setattr(smoke_check.time, "monotonic", lambda: next(monotonic_values))

    result = smoke_check.poll_autotest_run(
        base_url="http://localhost:8000",
        token="token-3",
        run_id="run-timeout",
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "FAIL autotest polling timed out" in captured.out
    assert '"status": "running"' in captured.out


def test_run_autotest_smoke_check_rejects_legacy_200_contract(monkeypatch, capsys):
    smoke_check = load_smoke_check_module()
    monkeypatch.setattr(
        smoke_check,
        "call_multipart",
        lambda **kwargs: (
            200,
            json.dumps(
                {
                    "id": "run-legacy",
                    "status": "passed",
                    "execution_mode": "simulated",
                    "project_type_detected": "node",
                    "working_directory": ".",
                }
            ),
        ),
    )

    result = smoke_check.run_autotest_smoke_check(
        base_url="http://localhost:8000",
        token="token-4",
        smoke_id="ghi789",
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "FAIL expected AutoTest 202 Accepted" in captured.out


def test_run_autotest_smoke_check_requires_run_id(monkeypatch, capsys):
    smoke_check = load_smoke_check_module()
    monkeypatch.setattr(
        smoke_check,
        "call_multipart",
        lambda **kwargs: (
            202,
            json.dumps(
                {
                    "status": "queued",
                    "execution_mode": "simulated",
                    "project_type_detected": "node",
                    "working_directory": ".",
                }
            ),
        ),
    )

    result = smoke_check.run_autotest_smoke_check(
        base_url="http://localhost:8000",
        token="token-5",
        smoke_id="jkl012",
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "FAIL autotest response missing run id" in captured.out


def test_main_returns_zero_after_autotest_passes(monkeypatch):
    smoke_check = load_smoke_check_module()
    smoke_marker = "SMOKE_marker1234"

    logbook_entry = {"id": "log-1", "title": f"Smoke logbook {smoke_marker}"}
    qa_payload = {
        "answer": "ok",
        "sources": [{"title": f"Smoke logbook {smoke_marker}", "snippet": "ok", "source_type": "knowledge"}],
    }

    def fake_call(method: str, url: str, payload=None, token: str | None = None):
        if url.endswith("/api/login"):
            return 200, json.dumps({"access_token": "token-main"})
        if url.endswith("/api/me"):
            return 200, json.dumps({"user_id": "owner"})
        if url.endswith("/api/docs"):
            return 200, json.dumps([])
        if url.endswith("/api/photos"):
            return 200, json.dumps([])
        if url.endswith("/api/prompts"):
            return 200, json.dumps([])
        if url.endswith("/api/logbook/entries") and method == "POST":
            return 200, json.dumps({"id": "log-1"})
        if url.endswith("/api/logbook/entries") and method == "GET":
            return 200, json.dumps([logbook_entry])
        if url.endswith("/promote-to-knowledge"):
            return 200, json.dumps({"knowledge_entry_id": "knowledge-1"})
        if url.endswith("/api/qa"):
            return 200, json.dumps(qa_payload)
        raise AssertionError(f"Unexpected call: {method} {url}")

    monkeypatch.setattr(smoke_check, "call", fake_call)
    monkeypatch.setattr(
        smoke_check,
        "run_autotest_smoke_check",
        lambda *, base_url, token, smoke_id: 0,
    )
    monkeypatch.setattr(smoke_check.uuid, "uuid4", lambda: type("U", (), {"hex": "marker12345"})())
    monkeypatch.setattr(smoke_check.time, "sleep", lambda _: None)

    result = smoke_check.main(["--password", "OwnerPass123!"])

    assert result == 0
