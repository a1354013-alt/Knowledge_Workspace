# Release Checklist

1. Confirm runtime versions:
   - Python 3.11
   - `.python-version` is `3.11.9`
   - `python scripts/check_python_version.py`
   - `.nvmrc` is `20.19.0`
2. Backend verification:
   - use Python 3.11.x (`py -3.11 -m venv .venv`)
   - `.\\.venv\\Scripts\\Activate.ps1`
   - `python -m pip install -U pip`
   - `pip install -e ".[dev]"`
   - `python scripts/check_python_version.py`
   - `python scripts/safe_compile.py -q .`
   - `python -m ruff check backend scripts`
   - `python scripts/run_backend_tests.py`
   - `python scripts/export_openapi.py`
   - `python scripts/generate_api_types.py --check`
   - `git diff --exit-code docs/openapi.json frontend/src/api/generated/api-types.ts`
   - `python scripts/check_version_consistency.py`
   - `python scripts/check_index_consistency.py`
   - OpenAPI/export checks must run under Python 3.11; use the repo virtualenv if your system `python` is newer
3. Frontend verification:
   - `cd frontend`
   - `npm ci`
   - `npm audit --omit=dev --audit-level=high`
   - `npm run lint`
   - `npm run typecheck`
   - `npm run test:run`
   - `npm run build`
   - JSON APIs must go through `frontend/src/api.ts`
   - blob/download flows must go through `frontend/src/services/downloads.ts`
   - dangerous confirms must go through `frontend/src/services/confirm.ts`
4. Release package:
   - `python scripts/verify_repo_hygiene.py`
   - `python scripts/package_release.py --output dist`
   - `python scripts/verify_release_zip.py dist/knowledge-workspace-<version>.zip`
   - `scripts/package_release.py` stages a source release and does not build or ship `frontend/dist` by default
   - default output is `dist/knowledge-workspace-<version>.zip`
   - release zip is a clean source package; it does not include `frontend/dist`
   - release verification rejects `node_modules`, `dist`, `.env`, runtime databases/journals/WAL/SHM files, `ci_chroma/`, `.chroma/`, `chroma/`, `runtime/`, `data/index/`, caches, uploads, AutoTest workdirs, and test artifacts
5. Release zip quickstart reminder:
   - extracted users must create a Python 3.11 environment, install backend dev dependencies, run `cd frontend && npm ci`, copy `.env.example` to `.env`, then start backend and frontend separately
   - Windows PowerShell startup:
     - `cd backend`
     - `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
     - separate terminal: `cd frontend` then `npm run dev -- --host 127.0.0.1 --port 5173`
   - bash startup:
     - `cd backend`
     - `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
     - separate terminal: `cd frontend` then `npm run dev -- --host 127.0.0.1 --port 5173`
