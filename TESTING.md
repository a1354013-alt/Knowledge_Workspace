# Testing

## Backend

Use Python 3.11.x. The backend is intentionally pinned to `>=3.11,<3.12`; Python 3.12/3.13 passing locally is not release evidence unless dependency constraints are updated.

```bash
python scripts/check_python_version.py
cd backend
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\ruff check .
.venv\Scripts\python -m compileall app
.venv\Scripts\python -m pytest -q
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
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m compileall app
python -m pytest -q
```

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

Use Node 20.19+ LTS to match CI and the Vite/Vitest toolchain engine range.

## Release

```bash
python scripts/export_openapi.py
python scripts/generate_api_types.py --check
python scripts/check_version_consistency.py
python scripts/package_release.py /tmp/kw_release.zip
python scripts/verify_release_zip.py /tmp/kw_release.zip
```

Release verification rejects runtime databases, journals, secrets, caches, uploads, build outputs, and test artifacts.
The release zip is a clean source package and intentionally does not include `frontend/dist`; build frontend assets after extracting the package.

## Smoke

CI starts the backend with simulated AutoTest settings and then runs:

```bash
python scripts/smoke_check.py --password "OwnerPass123!"
```

The smoke check is part of the release gate, not a substitute for backend pytest or frontend typecheck/build.

There are currently no intentionally skipped core tests. If slow integration tests are added later, they should use pytest markers and CI should still run the core suite by default.
