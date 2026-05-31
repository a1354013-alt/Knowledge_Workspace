# Backend API

Supported backend runtime: Python `3.11.x` only. The repo currently declares `requires-python = ">=3.11,<3.12"`, so Python `3.12` and `3.13` are not supported verification or release evidence yet.

## Install

Preferred development and CI-equivalent install from the repo root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

Runtime-only fallback from `backend/`:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Use the repo-root editable install whenever you need pytest, Ruff, OpenAPI checks, or release verification.

## Start

The backend is started from `backend/`, so environment file paths must be backend-relative.

```powershell
Copy-Item .\backend\.env.example .\backend\.env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Minimum required values in `backend/.env`:

- `JWT_SECRET`
- `DEFAULT_OWNER_PASSWORD`
- `ALLOWED_ORIGINS=http://localhost:5173`

Path variables in `backend/.env.example` intentionally use:

- `DATABASE_PATH=./documents.db`
- `UPLOAD_DIR=./uploads`
- `PHOTO_DIR=./photos`
- `CHROMA_DB_PATH=./chroma_db`

This avoids accidental `backend/backend/...` nesting when the server is started from `backend/`.

## AutoTest naming

Use these terms consistently:

- `runner disabled`: `runner_mode=disabled`; no uploaded project commands run
- `simulated execution`: `execution_mode=simulated`; safe default for local dev, demos, and CI
- `live execution`: human-facing term for `execution_mode=real`; commands do run, using either the trusted host runner or Docker sandbox runner

Environment settings:

- `AUTOTEST_MODE=simulated`: default; keeps execution simulated
- `AUTOTEST_MODE=real` plus `AUTOTEST_SANDBOX_BACKEND=local_trusted`: trusted-host live execution
- `AUTOTEST_MODE=docker_sandbox`: Docker-backed live execution
- `KW_AUTOTEST_REAL_MODE=1` or `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1`: extra gate required before trusted-host live execution can run

Safety notes:

- trusted-host live execution is for a local trusted environment only
- Docker sandbox execution adds useful isolation, but it is not a production multi-tenant sandbox
- this backend remains local-first and is not a public code-execution service

## Verification

Run these from the repo root with Python 3.11 active:

```powershell
python scripts/check_python_version.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
python scripts/check_index_consistency.py
python scripts/export_openapi.py --check
python scripts/generate_api_types.py --check
python scripts/check_version_consistency.py
```

Integration smoke:

```powershell
python scripts/smoke_check.py --password "<DEFAULT_OWNER_PASSWORD>"
```

Do not treat a single green local test run as "production ready". The repo gate is the maintained verification baseline, but the deployment model is still local-first.

## Encoding note

Text uploads are decoded with `utf-8`, `utf-8-sig`, or `cp950`. The bootstrap scripts also normalize UTF-8 BOM from existing `.env` files so Windows-created env files do not load with hidden prefix bytes.
