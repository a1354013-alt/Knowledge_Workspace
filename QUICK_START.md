# Quick Start

Recommended toolchain:

- Python `3.11.x`
- Node.js `20` LTS

## 1. Create the supported Python 3.11 environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

Required environment variables:

```env
JWT_SECRET=<minimum 32 chars>
DEFAULT_OWNER_PASSWORD=<local owner password>
ALLOWED_ORIGINS=http://localhost:5173
AUTOTEST_MODE=simulated
# Real mode additionally requires KW_AUTOTEST_REAL_MODE=1
```

Notes:

- keep `AUTOTEST_MODE=simulated` unless you intentionally want trusted local command execution
- `AUTOTEST_MODE=real` is rejected unless `KW_AUTOTEST_REAL_MODE=1`
- real mode is trusted local execution, not a hardened sandbox; do not run untrusted ZIPs there

## 2. Start backend

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 3. Install frontend

```powershell
cd frontend
npm ci
```

## 4. Start frontend

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## 5. Verify the app

- open `http://localhost:5173`
- sign in with `owner`
- upload a document and confirm index status is visible
- run AutoTest in `simulated` mode
- open the run detail and verify:
  - timeline is populated
  - Markdown/HTML export works
  - AI fix prompt copy works for failed runs

## 6. Run verification commands

Backend:

```powershell
python scripts/check_python_version.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
python scripts/export_openapi.py
python scripts/generate_api_types.py --check
python scripts/check_version_consistency.py
```

Frontend:

```powershell
cd frontend
npm ci
npm audit --omit=dev --audit-level=high
npm run lint
npm run typecheck
npm run test:run
npm run build
```

Repo-wide:

```powershell
python scripts/package_release.py dist/knowledge_workspace_release.zip
python scripts/verify_release.py dist/knowledge_workspace_release.zip
```

Runtime-only fallback:

- `backend/requirements.txt` is kept for runtime-only installs such as `cd backend && python -m pip install -r requirements.txt`
- if you need tests, lint, or CI-equivalent verification, use the repo-root `pip install -e ".[dev]"` flow above

