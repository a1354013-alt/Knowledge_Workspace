from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.context import settings


@dataclass(frozen=True)
class RunnerCommand:
    argv: list[str]
    cwd: Path
    timeout_seconds: int
    artifact_dir: Path | None = None


@dataclass(frozen=True)
class RunnerResult:
    exit_code: int
    stdout: str
    stderr: str


class AutoTestRunner(Protocol):
    name: str
    trusted: bool
    sandboxed: bool

    def run(self, command: RunnerCommand) -> RunnerResult: ...


class SimulatedRunner:
    name = "simulated"
    trusted = False
    sandboxed = False

    def run(self, command: RunnerCommand) -> RunnerResult:
        _ = command
        return RunnerResult(exit_code=0, stdout="simulated", stderr="")


class LocalTrustedRunner:
    name = "local-trusted"
    trusted = True
    sandboxed = False

    def run(self, command: RunnerCommand) -> RunnerResult:
        raise NotImplementedError("LocalTrustedRunner uses the existing subprocess execution path.")


class DockerSandboxRunner:
    name = "docker_sandbox"
    trusted = False
    sandboxed = True

    def _artifact_dir(self, command: RunnerCommand) -> Path:
        base = (command.artifact_dir or settings.AUTOTEST_ARTIFACT_DIR).resolve()
        base.mkdir(parents=True, exist_ok=True)
        return (base / f"docker-{uuid.uuid4().hex}").resolve()

    def build_docker_command(self, command: RunnerCommand, *, workspace_dir: Path, artifact_dir: Path) -> list[str]:
        if not command.argv:
            raise ValueError("Missing command argv.")
        workspace_dir = workspace_dir.resolve()
        artifact_dir = artifact_dir.resolve()
        if not workspace_dir.exists() or not workspace_dir.is_dir():
            raise ValueError("Docker sandbox workspace does not exist.")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        network = "bridge" if bool(settings.AUTOTEST_DOCKER_NETWORK) else "none"
        
        # Build base docker command with security hardening
        cmd = [
            "docker",
            "run",
            "--rm",
            # Network isolation
            "--network",
            network,
            # Resource limits
            "--cpus",
            str(settings.AUTOTEST_DOCKER_CPUS),
            "--memory",
            str(settings.AUTOTEST_DOCKER_MEMORY),
            "--pids-limit",
            "256",
            # Security hardening
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt",
            "no-new-privileges",
            # Volume mounts (workspace and artifacts as the only writable paths)
            "-v",
            f"{workspace_dir}:/workspace:rw",
            "-v",
            f"{artifact_dir}:/artifacts:rw",
            "-w",
            "/workspace",
        ]
        
        # Optional non-root user if configured
        if bool(settings.AUTOTEST_DOCKER_USER):
            cmd.extend(["--user", settings.AUTOTEST_DOCKER_USER])
        
        # Image and command
        cmd.append(str(settings.AUTOTEST_DOCKER_IMAGE))
        cmd.extend(command.argv)
        
        return cmd

    def run(self, command: RunnerCommand) -> RunnerResult:
        source_dir = command.cwd.resolve()
        artifact_dir = self._artifact_dir(command)
        workspace_dir = artifact_dir / "workspace"
        try:
            shutil.copytree(source_dir, workspace_dir, symlinks=False)
            docker_argv = self.build_docker_command(command, workspace_dir=workspace_dir, artifact_dir=artifact_dir)
            completed = subprocess.run(
                docker_argv,
                cwd=str(artifact_dir),
                shell=False,
                capture_output=True,
                text=True,
                timeout=command.timeout_seconds,
            )
            (artifact_dir / "stdout.log").write_text(completed.stdout or "", encoding="utf-8")
            (artifact_dir / "stderr.log").write_text(completed.stderr or "", encoding="utf-8")
            return RunnerResult(
                exit_code=int(completed.returncode),
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
            (artifact_dir / "stdout.log").write_text(stdout, encoding="utf-8")
            (artifact_dir / "stderr.log").write_text(stderr or "Docker sandbox command timed out.", encoding="utf-8")
            return RunnerResult(exit_code=124, stdout=stdout, stderr=stderr or "Docker sandbox command timed out.")
