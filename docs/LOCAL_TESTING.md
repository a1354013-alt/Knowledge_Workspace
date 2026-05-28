# Local Testing

## Backend

Use Python 3.11.x. The backend package declares `requires-python = ">=3.11,<3.12"`, so Python 3.12/3.13 results are not accepted as release evidence unless dependency constraints are updated.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
copy .env.example .env
python scripts/check_python_version.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
```

Equivalent single command from the repo root after dependencies are installed:

```bash
py -3.11 scripts\run_backend_checks.py
```

Full CI-equivalent verification, including frontend, release zip, and smoke:

```powershell
python scripts/verify_all.py
```

`run_backend_tests.py` is the CI-style wrapper: it still executes `python -m pytest -q`, but it also enforces a whole-process timeout and fails if pytest reports passing tests without exiting cleanly.

Required test defaults are documented in `backend/.env.example`. The test suite itself sets isolated values for `JWT_SECRET`, `DEFAULT_OWNER_PASSWORD`, `DATABASE_PATH`, `UPLOAD_DIR`, `PHOTO_DIR`, `AUTOTEST_DIR`, `CHROMA_DB_PATH`, `AUTOTEST_MODE`, and `ALLOWED_ORIGINS`.

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

## API Contract

```powershell
python scripts/export_openapi.py
python scripts/generate_api_types.py --check
git diff --exit-code docs/openapi.json frontend/src/api/generated/api-types.ts
python scripts/check_index_consistency.py
```

When the API contract intentionally changes, run `python scripts/generate_api_types.py` and commit `docs/openapi.json` with `frontend/src/api/generated/api-types.ts`.

## Release And Smoke

```powershell
python scripts/check_version_consistency.py
python scripts/package_release.py
python scripts/verify_release.py dist/knowledge-workspace-*.zip
python scripts/smoke_check.py --password "OwnerPass123!"
```

The smoke check expects a local backend already running on `127.0.0.1:8000`, matching the CI startup step.
The release zip is a clean source package. `scripts/package_release.py` does not build or include `frontend/dist`, and the archive excludes `node_modules`, runtime DB/journal files, caches, uploads, and temporary Chroma/AutoTest data; run the frontend build after extraction.
`python scripts/verify_all.py` automates the same startup/wait/smoke sequence locally with simulated AutoTest settings.

## Release Zip Quickstart

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
cd frontend
npm ci
cd ..
copy .env.example .env
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
cp .env.example .env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
