# Quick Start

Recommended toolchain:

- Python `3.11`
- Node.js `20` LTS

## 1. Install backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Required environment variables:

```env
JWT_SECRET=<minimum 32 chars>
DEFAULT_OWNER_PASSWORD=<local owner password>
ALLOWED_ORIGINS=http://localhost:5173
AUTOTEST_MODE=simulated
# Real mode additionally requires KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1
```

Notes:

- keep `AUTOTEST_MODE=simulated` unless you intentionally want trusted local command execution
- `AUTOTEST_MODE=real` is rejected unless `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1`
- real mode is not a hardened sandbox; use a container/sandbox

## 2. Start backend

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 3. Install frontend

```bash
cd frontend
npm ci
```

## 4. Start frontend

```bash
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

```bash
cd backend
python -m compileall -q app
python -m ruff check .
python -m pytest
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test:run
npm run build
npm audit
```

Repo-wide:

```bash
python scripts/check_version_consistency.py
python scripts/package_release.py --output dist
python scripts/verify_release_zip.py dist/knowledge_workspace_release.zip
```
