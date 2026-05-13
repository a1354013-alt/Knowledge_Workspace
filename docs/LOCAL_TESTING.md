# Local Testing

## Backend

Use Python 3.11.x. The backend package declares `requires-python = ">=3.11,<3.12"`, so Python 3.12/3.13 results are not accepted as release evidence.

```bash
cd backend
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python -m compileall app tests
.venv\Scripts\ruff check .
.venv\Scripts\python -m pytest
```

Equivalent single command from the repo root after dependencies are installed:

```bash
py -3.11 scripts\run_backend_checks.py
```

Required test defaults are documented in `backend/.env.example`. The test suite itself sets isolated values for `JWT_SECRET`, `DEFAULT_OWNER_PASSWORD`, `DATABASE_PATH`, `UPLOAD_DIR`, `PHOTO_DIR`, `AUTOTEST_DIR`, `CHROMA_DB_PATH`, `AUTOTEST_MODE`, and `ALLOWED_ORIGINS`.

## Frontend

```bash
cd frontend
npm ci
npm audit --omit=dev --audit-level=high
npm run test:run
npm run lint
npm run typecheck
npm run build
```

## API Contract

```bash
python scripts/export_openapi.py
cd frontend
npm run generate:api-types
```

Commit `docs/openapi.json` and `frontend/src/generated/api-types.ts` together when the API contract intentionally changes.
