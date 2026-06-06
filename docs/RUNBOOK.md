# Development Runbook

## Supported toolchain

- Backend: Python `3.11.x` only
- Frontend: Node `20 LTS`

Do not treat Python `3.12` or `3.13` results as supported validation for this repo until dependency constraints and CI are updated.

## Windows PowerShell setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
cd frontend
npm ci
cd ..
Copy-Item .\backend\.env.example .\backend\.env
```

## Start services

Backend:

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Use backend-relative paths in `backend/.env` such as `./documents.db` and `./uploads`; this avoids the old `backend/backend/...` mistake.

## Backend verification

Run from the repo root after activating Python 3.11:

```powershell
python scripts/check_python_version.py
python scripts/check_text_encoding.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
pytest
python scripts/run_backend_tests.py
python scripts/check_index_consistency.py
python scripts/export_openapi.py
python scripts/generate_api_types.py --check
python scripts/generate_api_types.py
python scripts/check_version_consistency.py
```

## AutoTest terminology and safety

Use these labels consistently:

- `runner disabled`: no uploaded commands execute
- `simulated execution`: safe default, same practical posture as disabled runner
- `live execution`: real command execution on either the trusted host or Docker runner

Trusted-host live execution:

```env
AUTOTEST_MODE=real
KW_AUTOTEST_REAL_MODE=1
AUTOTEST_SANDBOX_BACKEND=local_trusted
```

Docker live execution:

```env
AUTOTEST_MODE=docker_sandbox
AUTOTEST_DOCKER_IMAGE=python:3.11-slim
AUTOTEST_DOCKER_NETWORK=false
```

This remains a local-first trusted-environment system, not a production SaaS runner.
Use trusted-host live execution only inside a trusted local workspace, and remember it is not a public sandbox.

## Frontend verification

Run from `frontend/` with Node 20 LTS:

```powershell
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test:run
npm run build
npx playwright install chromium
npm run test:e2e
```

Use `python scripts/check_text_encoding.py` before dependency installation when a TOML or requirements parser fails at the first byte. The check rejects UTF-8 BOM and invalid UTF-8 in committed text files, including `.txt`, `requirements.txt`, and TOML files.

## Release packaging

Build and verify the source release from the repo root:

```powershell
python scripts/package_release.py
python scripts/verify_release.py dist/knowledge-workspace-<version>.zip
```

The generated zip is a source release. It is not a deployable bundle and does not include `frontend/dist`.
