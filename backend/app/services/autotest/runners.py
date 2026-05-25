from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class RunnerCommand:
    argv: list[str]
    cwd: Path
    timeout_seconds: int


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
    name = "docker-sandbox"
    trusted = False
    sandboxed = True

    def run(self, command: RunnerCommand) -> RunnerResult:
        raise NotImplementedError("DockerSandboxRunner is a placeholder until real container isolation is implemented.")
