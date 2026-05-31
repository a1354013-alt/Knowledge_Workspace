# Local Testing

## Backend

Use Python `3.11.x`. The backend package declares `requires-python = ">=3.11,<3.12"`, so Python `3.12` and `3.13` results are not accepted as supported release evidence.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .\backend\.env.example .\backend\.env
python scripts/check_python_version.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
```

Equivalent single command from the repo root after dependencies are installed:

```powershell
python scripts/run_backend_checks.py
```

Full repo verification:

```powershell
python scripts/verify_all.py
```

`run_backend_tests.py` is the CI-style wrapper around pytest. It still runs `python -m pytest -q`, but it also enforces a whole-process timeout and fails if pytest reports passing tests without exiting cleanly.

## Frontend

```powershell
cd frontend
npm ci
npm audit --omit=dev --audit-level=high
npm run lint
npm run typecheck
npm run test:run
npm run build
```

## API contract

```powershell
python scripts/export_openapi.py --check
python scripts/generate_api_types.py --check
python scripts/check_index_consistency.py
```

When the API contract intentionally changes, regenerate both artifacts and commit them together.

## Release and smoke

```powershell
python scripts/check_version_consistency.py
python scripts/package_release.py
python scripts/verify_release.py dist/knowledge-workspace-*.zip
python scripts/smoke_check.py --password "OwnerPass123!"
```

The release zip is a source release, not a deployable bundle. It excludes `frontend/dist`, runtime DB files, caches, uploads, and temporary Chroma/AutoTest data.

## Release zip quickstart

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
cd frontend
npm ci
cd ..
Copy-Item .\backend\.env.example .\backend\.env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

bash:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
cd frontend
npm ci
cd ..
cp backend/.env.example backend/.env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
