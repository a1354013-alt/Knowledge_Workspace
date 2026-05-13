# Testing

## Backend

Use Python 3.11.x. The backend is intentionally pinned to `>=3.11,<3.12`; Python 3.13 passing locally is not release evidence.

```bash
cd backend
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m compileall app tests
.venv\Scripts\ruff check .
.venv\Scripts\python -m pytest
```

After a Python 3.11 virtualenv is active, the repo-root helper runs the same checks:

```bash
python scripts/run_backend_checks.py
```

Backend tests use isolated temporary SQLite databases and upload directories. AutoTest defaults to simulated mode in tests; real-mode tests patch the subprocess runner and explicitly enable the real-mode gate. See `backend/.env.example` and `docs/LOCAL_TESTING.md` for the local environment contract.

Legacy fallback:

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest
python -m compileall -q app tests
```

## Frontend

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test:run
npm run build
npm audit --audit-level=moderate
```

Use Node 20.19+ LTS to match CI and the Vite/Vitest toolchain engine range.

## Release

```bash
python scripts/check_version_consistency.py
python scripts/package_release.py --output dist
python scripts/verify_release_zip.py dist/knowledge_workspace_release.zip
```

Release verification rejects runtime databases, journals, secrets, caches, uploads, build outputs, and test artifacts.

There are currently no intentionally skipped core tests. If slow integration tests are added later, they should use pytest markers and CI should still run the core suite by default.
