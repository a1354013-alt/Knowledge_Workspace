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


def build_zip_with_member(name: str, content: str = "x") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    return buffer.getvalue()


def test_real_autotest_is_rejected_without_explicit_enable(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KW_AUTOTEST_REAL_MODE = False
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = False
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "disabled"

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_node_zip(), "application/zip")},
    )

    assert response.status_code == 403
    assert "KW_AUTOTEST_REAL_MODE=1" in response.text
    assert "local trusted" in response.text.lower()


def test_autotest_capabilities_exposes_real_mode_availability(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KW_AUTOTEST_REAL_MODE = False
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = False
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "disabled"

    response = client.get("/api/autotest/capabilities", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "simulated"
    assert payload["runner_mode"] == "disabled"
    assert payload["real_mode_requested"] is True
    assert payload["real_mode_available"] is False
    assert payload["sandbox_backend"] == "disabled"
    assert payload["sandbox_backend_ready"] is False
    assert "simulated mode is active" in payload["message"].lower()
    assert "disabled" in payload["message"].lower()


def test_real_autotest_is_blocked_without_supported_sandbox_backend(
    app_module,
    client: TestClient,
    auth_headers: dict[str, str],
):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "disabled"

    response = client.post(
        "/api/autotest/run",
        headers=auth_headers,
        files={"file": ("demo.zip", build_node_zip(), "application/zip")},
    )

    assert response.status_code == 409
    assert "AUTOTEST_SANDBOX_BACKEND=local_trusted" in response.text


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


def test_run_command_scrubs_sensitive_env_in_real_mode(app_module, monkeypatch, tmp_path: Path):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KW_AUTOTEST_REAL_MODE = True
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "local_trusted"
    monkeypatch.setenv("API_TOKEN", "secret")
    monkeypatch.setenv("deploy_key", "secret")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("NORMAL_FLAG", "keep-me")
    captured_env: dict[str, str] = {}

    def fake_run(*args, **kwargs):
        captured_env.update(kwargs["env"])
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(app_module.autotest_service.subprocess, "run", fake_run)

    app_module.autotest_service._run_command(argv=["python", "--version"], cwd=tmp_path, timeout_seconds=7)

    assert "API_TOKEN" not in captured_env
    assert "deploy_key" not in captured_env
    assert "DB_PASSWORD" not in captured_env
    assert captured_env["NORMAL_FLAG"] == "keep-me"


def test_run_command_refuses_host_execution_when_backend_not_ready(app_module, monkeypatch, tmp_path: Path):
    app_module.autotest_service.settings.AUTOTEST_MODE = "real"
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = True
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "docker"
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(app_module.autotest_service.subprocess, "run", fake_run)

    try:
        app_module.autotest_service._run_command(argv=["python", "--version"], cwd=tmp_path, timeout_seconds=7)
    except PermissionError as exc:
        assert "blocked" in str(exc).lower() or "not implemented" in str(exc).lower()
    else:
        raise AssertionError("Expected host execution to stay blocked without a supported backend.")

    assert called is False


def test_service_source_does_not_use_shell_true(app_module):
    source = inspect.getsource(app_module.autotest_service._run_command)
    assert "shell=False" in source
    assert "shell=True" not in source


def test_real_autotest_defaults_to_simulated_mode(app_module):
    app_module.autotest_service.settings.AUTOTEST_MODE = "disabled"
    app_module.autotest_service.settings.KW_AUTOTEST_REAL_MODE = False
    app_module.autotest_service.settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST = False
    app_module.autotest_service.settings.AUTOTEST_SANDBOX_BACKEND = "disabled"

    capabilities = app_module.autotest_service.get_autotest_capabilities()

    assert capabilities.mode == "simulated"
    assert capabilities.runner_mode == "disabled"
    assert capabilities.real_mode_requested is False
    assert capabilities.real_mode_available is False
    assert "No uploaded project commands will run" in capabilities.message


def test_docker_sandbox_runner_builds_constrained_command(app_module, tmp_path: Path):
    from app.services.autotest.runners import DockerSandboxRunner, RunnerCommand

    app_module.autotest_service.settings.AUTOTEST_DOCKER_IMAGE = "python:3.11-slim"
    app_module.autotest_service.settings.AUTOTEST_DOCKER_NETWORK = False
    app_module.autotest_service.settings.AUTOTEST_DOCKER_MEMORY = "512m"
    app_module.autotest_service.settings.AUTOTEST_DOCKER_CPUS = "1"
    app_module.autotest_service.settings.AUTOTEST_DOCKER_USER = ""
    workspace = tmp_path / "workspace"
    artifacts = tmp_path / "artifacts"
    workspace.mkdir()
    runner = DockerSandboxRunner()
    assert runner.name == "docker_sandbox"
    assert runner.trusted is False
    assert runner.sandboxed is True

    command = runner.build_docker_command(
        RunnerCommand(argv=["python", "--version"], cwd=workspace, timeout_seconds=5),
        workspace_dir=workspace,
        artifact_dir=artifacts,
    )

    # Verify base structure
    assert command[0] == "docker"
    assert command[1] == "run"
    assert command[2] == "--rm"
    # Verify network isolation
    assert "--network" in command
    assert "none" in command
    # Verify resource limits
    assert "--cpus" in command
    assert "1" in command
    assert "--memory" in command
    assert "512m" in command
    assert "--pids-limit" in command
    assert "256" in command
    # Verify security hardening
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt" in command
    assert "no-new-privileges" in command
    # Verify volumes and image
    assert str(workspace) in " ".join(command)
    assert "python:3.11-slim" in command
    assert "python" in command
    assert "--version" in command


def test_report_paths_are_sanitized(app_module, tmp_path: Path):
    base_dir = tmp_path / "extract"
    project_dir = base_dir / "project"
    project_dir.mkdir(parents=True)

    assert app_module.autotest_service.sanitize_path_for_report(project_dir, base_dir=base_dir) == "project"
    assert (
        app_module.autotest_service.sanitize_path_for_report(Path("C:/outside"), base_dir=base_dir)
        == "<sanitized-path>"
    )


def test_safe_extract_zip_rejects_absolute_path(app_module, tmp_path: Path):
    zip_path = tmp_path / "absolute.zip"
    zip_path.write_bytes(build_zip_with_member("/absolute.txt"))

    try:
        app_module.autotest_service.safe_extract_zip(zip_path, tmp_path / "extract")
    except ValueError as exc:
        assert "unsafe paths" in str(exc).lower()
    else:
        raise AssertionError("Expected absolute path zip member to be rejected.")


def test_safe_extract_zip_rejects_windows_drive_path(app_module, tmp_path: Path):
    zip_path = tmp_path / "drive.zip"
    zip_path.write_bytes(build_zip_with_member("C:/escape.txt"))

    try:
        app_module.autotest_service.safe_extract_zip(zip_path, tmp_path / "extract")
    except ValueError as exc:
        assert "unsafe paths" in str(exc).lower()
    else:
        raise AssertionError("Expected Windows drive path zip member to be rejected.")


def test_safe_extract_zip_rejects_unc_path(app_module, tmp_path: Path):
    zip_path = tmp_path / "unc.zip"
    zip_path.write_bytes(build_zip_with_member("//server/share.txt"))

    try:
        app_module.autotest_service.safe_extract_zip(zip_path, tmp_path / "extract")
    except ValueError as exc:
        assert "unsafe paths" in str(exc).lower()
    else:
        raise AssertionError("Expected UNC path zip member to be rejected.")


def test_safe_extract_zip_rejects_path_traversal(app_module, tmp_path: Path):
    zip_path = tmp_path / "traversal.zip"
    zip_path.write_bytes(build_zip_with_member("../escape.txt"))

    try:
        app_module.autotest_service.safe_extract_zip(zip_path, tmp_path / "extract")
    except ValueError as exc:
        assert "unsafe paths" in str(exc).lower()
    else:
        raise AssertionError("Expected path traversal zip member to be rejected.")


def test_safe_extract_zip_rejects_symlink_member(app_module, tmp_path: Path):
    zip_path = tmp_path / "symlink.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        archive.writestr(info, "target")

    try:
        app_module.autotest_service.safe_extract_zip(zip_path, tmp_path / "extract")
    except ValueError as exc:
        assert "symlink" in str(exc).lower()
    else:
        raise AssertionError("Expected symlink zip member to be rejected.")


def test_safe_extract_zip_rejects_oversized_archive(app_module, tmp_path: Path):
    app_module.autotest_service.settings.AUTOTEST_MAX_UNZIPPED_BYTES = 8
    zip_path = tmp_path / "large.zip"
    zip_path.write_bytes(build_zip_with_member("demo.txt", "0123456789"))

    try:
        app_module.autotest_service.safe_extract_zip(zip_path, tmp_path / "extract")
    except ValueError as exc:
        assert "allowed size" in str(exc).lower()
    else:
        raise AssertionError("Expected oversized archive to be rejected.")
