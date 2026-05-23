from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
DEFAULT_RELEASE_ZIP = ROOT / "knowledge_workspace_release.zip"
BACKEND_READY_URL = "http://127.0.0.1:8000/api/health"
BACKEND_READY_TIMEOUT_SECONDS = 60


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            check=False,
            capture_output=True,
            text=True,
        )
        return

    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)


def wait_for_backend() -> None:
    import urllib.request

    deadline = time.monotonic() + BACKEND_READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(BACKEND_READY_URL, timeout=5) as response:
                if response.status == 200:
                    print("Backend is ready")
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Backend did not become ready in time for smoke_check.")


def run_smoke_check() -> None:
    runtime_paths = [
        ROOT / "ci_documents.db",
        ROOT / "ci_uploads",
        ROOT / "ci_photos",
        ROOT / "ci_chroma",
        ROOT / "ci_autotest",
    ]
    for path in runtime_paths:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "JWT_SECRET": "ci-secret-ci-secret-ci-secret-ci-secret-1234",
            "DEFAULT_OWNER_PASSWORD": "OwnerPass123!",
            "DATABASE_PATH": str(ROOT / "ci_documents.db"),
            "UPLOAD_DIR": str(ROOT / "ci_uploads"),
            "PHOTO_DIR": str(ROOT / "ci_photos"),
            "CHROMA_DB_PATH": str(ROOT / "ci_chroma"),
            "AUTOTEST_DIR": str(ROOT / "ci_autotest"),
            "AUTOTEST_MODE": "simulated",
        }
    )

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    preexec_fn = os.setsid if os.name != "nt" else None
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creationflags,
        preexec_fn=preexec_fn,
    )

    try:
        wait_for_backend()
        run([sys.executable, "scripts/smoke_check.py", "--password", "OwnerPass123!"], env=env)
    finally:
        _terminate_process_tree(backend)
        output = ""
        if backend.stdout is not None:
            with suppress(Exception):
                output = backend.stdout.read()
        if output.strip():
            print("----- smoke backend log tail -----")
            print("\n".join(output.strip().splitlines()[-80:]))


def main() -> int:
    run([sys.executable, "scripts/check_python_version.py"])
    run([sys.executable, "scripts/safe_compileall.py", "-q", "."])
    run([sys.executable, "-m", "ruff", "check", "backend", "scripts"])
    run([sys.executable, "scripts/run_backend_tests.py"])
    run([sys.executable, "scripts/export_openapi.py"])
    run([sys.executable, "scripts/generate_api_types.py", "--check"])
    run(["git", "diff", "--exit-code", "docs/openapi.json", "frontend/src/api/generated/api-types.ts"])
    run([sys.executable, "scripts/check_version_consistency.py"])

    npm = npm_command()
    run([npm, "ci"], cwd=FRONTEND_DIR)
    run([npm, "audit", "--omit=dev", "--audit-level=high"], cwd=FRONTEND_DIR)
    run([npm, "run", "lint"], cwd=FRONTEND_DIR)
    run([npm, "run", "typecheck"], cwd=FRONTEND_DIR)
    run([npm, "run", "test:run"], cwd=FRONTEND_DIR)
    run([npm, "run", "build"], cwd=FRONTEND_DIR)

    run([sys.executable, "scripts/package_release.py", str(DEFAULT_RELEASE_ZIP)])
    run([sys.executable, "scripts/verify_release_zip.py", str(DEFAULT_RELEASE_ZIP)])
    run_smoke_check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
