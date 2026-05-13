from __future__ import annotations

import inspect
import io
import subprocess
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


def build_node_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "package.json",
            '{"name":"demo","version":"1.0.0","scripts":{"test":"echo ok","build":"echo ok","lint":"echo ok"}}',
        )
    return buffer.getvalue()


def test_real_autotest_is_rejected_without_explicit_enable(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = False

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_node_zip(), "application/zip")},
    )

    assert response.status_code == 403
    assert "KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1" in response.text


def test_autotest_capabilities_exposes_real_mode_availability(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = False

    response = client.get("/api/autotest/capabilities", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "simulated"
    assert payload["real_mode_requested"] is True
    assert payload["real_mode_available"] is False


def test_command_builder_uses_ignore_scripts_and_disables_python_install(app_module, tmp_path: Path):
    node_commands = app_module.autotest_service.autotest_commands("node")
    python_commands = app_module.autotest_service.autotest_commands("python")

    assert node_commands["install"][:2] == ["npm", "ci"]
    assert "--ignore-scripts" in node_commands["install"]
    assert python_commands["install"] == ["python", "-m", "pip", "--version"]

    should_run, reason = app_module.autotest_service.autotest_step_should_run(
        project_type="python",
        working_dir=tmp_path,
        step_name="install",
    )
    assert should_run is False
    assert "disabled" in reason


def test_run_command_uses_shell_false_timeout_and_clamps_output(app_module, monkeypatch, tmp_path: Path):
    calls: list[dict] = []

    def fake_run(*args, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="x" * 13000, stderr="")

    monkeypatch.setattr(app_module.autotest_service.subprocess, "run", fake_run)

    exit_code, stdout, stderr = app_module.autotest_service._run_command(
        argv=["python", "--version"],
        cwd=tmp_path,
        timeout_seconds=7,
    )

    assert exit_code == 0
    assert stderr == ""
    assert len(stdout) < 12500
    assert "truncated" in stdout
    assert calls[0]["shell"] is False
    assert calls[0]["timeout"] == 7


def test_service_source_does_not_use_shell_true(app_module):
    source = inspect.getsource(app_module.autotest_service._run_command)
    assert "shell=False" in source
    assert "shell=True" not in source


def test_report_paths_are_sanitized(app_module, tmp_path: Path):
    base_dir = tmp_path / "extract"
    project_dir = base_dir / "project"
    project_dir.mkdir(parents=True)

    assert app_module.autotest_service.sanitize_path_for_report(project_dir, base_dir=base_dir) == "project"
    assert app_module.autotest_service.sanitize_path_for_report(Path("C:/outside"), base_dir=base_dir) == "<sanitized-path>"
