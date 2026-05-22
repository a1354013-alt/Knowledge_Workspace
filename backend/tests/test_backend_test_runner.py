from __future__ import annotations

import subprocess


def test_run_backend_tests_returns_pytest_exit_code(monkeypatch):
    from scripts import run_backend_tests

    popen_calls: list[dict[str, object]] = []

    class FakeProcess:
        def __init__(self) -> None:
            self.pid = 4321
            self.returncode = 3

        def poll(self):
            return self.returncode

        def communicate(self, timeout=None):
            return ("stdout line\n", "stderr line\n")

    def fake_popen(command, **kwargs):
        popen_calls.append({"command": command, **kwargs})
        return FakeProcess()

    monkeypatch.setattr(run_backend_tests.subprocess, "Popen", fake_popen)

    assert run_backend_tests.main() == 3
    assert popen_calls
    assert popen_calls[0]["command"][:3] == [run_backend_tests.sys.executable, "-m", "pytest"]


def test_run_backend_tests_timeout_returns_124_and_terminates(monkeypatch):
    from scripts import run_backend_tests

    terminate_calls: list[int] = []

    class FakeProcess:
        def __init__(self) -> None:
            self.pid = 9876
            self.returncode = None

        def poll(self):
            return None

        def communicate(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired(cmd=["pytest"], timeout=timeout)
            self.returncode = -9
            return ("late stdout\n", "late stderr\n")

    monkeypatch.setattr(run_backend_tests.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr(
        run_backend_tests,
        "_terminate_process_tree",
        lambda process: terminate_calls.append(process.pid),
    )
    monkeypatch.setenv("KNOWLEDGE_WORKSPACE_PYTEST_TIMEOUT", "1")

    assert run_backend_tests.main() == 124
    assert terminate_calls == [9876]
