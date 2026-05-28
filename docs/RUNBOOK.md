# Development Runbook

## Supported Toolchain

- Backend: Python `3.11.x` only
- Frontend: Node `20 LTS` with `npm ci`

Do not treat Python `3.12` / `3.13` or Node `22` results as supported validation for this repo unless dependency constraints and CI are updated.

## Windows PowerShell Setup

Create and activate a Python 3.11 virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
```

Install backend development dependencies from the repo root:

```powershell
pip install -e ".[dev]"
```

Install frontend dependencies with Node 20 LTS:

```powershell
cd frontend
npm ci
cd ..
```

## Backend Verification

Run the backend verification commands from the repo root after the Python 3.11 venv is active:

```powershell
python scripts/safe_compile.py
python scripts/check_version_consistency.py
python scripts/check_index_consistency.py
pytest
```

## Frontend Verification

Run the frontend checks from `frontend/` with Node 20 LTS:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
cd ..
```

## API Contract Refresh

Refresh the backend OpenAPI schema and frontend generated API types from the repo root:

```powershell
python scripts/export_openapi.py
python scripts/generate_api_types.py
python scripts/generate_api_types.py --check
```

## Release Packaging

Build and verify the release zip from the repo root:

```powershell
python scripts/package_release.py
python scripts/verify_release.py dist/knowledge-workspace-5.0.0.zip
```

If you want the exact generated filename without hard-coding the version, inspect `dist/` after packaging and pass that path to `verify_release.py`.

## AutoTest Safety Reminder

`AUTOTEST_MODE=disabled` is the safe default.

AutoTest local_trusted mode is only for a trusted local workspace that you control:

- requires `AUTOTEST_MODE=local_trusted`
- requires `KW_AUTOTEST_REAL_MODE=1`
- is not a public sandbox
- is not container isolation
- must not be exposed as arbitrary public code execution

`AUTOTEST_MODE=docker_sandbox` uses Docker for containerized execution with basic local isolation but is not a production-grade multi-tenant sandbox.

