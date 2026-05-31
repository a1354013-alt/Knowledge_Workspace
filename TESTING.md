# Testing

## Backend

Use Python `3.11.9` from `.python-version`. The backend is intentionally pinned to `>=3.11,<3.12`; Python `3.12` and `3.13` are not supported verification runtimes for this repo today.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python scripts/check_python_version.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
```

Full repo verification:

```powershell
python scripts/verify_all.py
```

Backend tests use isolated temporary SQLite databases and upload directories. AutoTest defaults to simulated execution in tests; trusted-host tests patch subprocess execution and explicitly enable the full gate, while Docker sandbox tests mock command construction unless `KNOWLEDGE_WORKSPACE_DOCKER_INTEGRATION=1` is set in an environment that has Docker.

AutoTest remains a local-first in-process worker in tests and runtime:

- queued/running jobs live in SQLite plus an in-process daemon thread
- execution heartbeats refresh `updated_at`
- startup recovery marks stale queued/running jobs failed after restart
- this is not equivalent to a durable queue such as RQ or Celery

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

Use Node `20.19.0` from `.nvmrc` to match CI.

## Contract and release checks

```powershell
python scripts/export_openapi.py --check
python scripts/generate_api_types.py --check
python scripts/check_version_consistency.py
python scripts/check_index_consistency.py
python scripts/package_release.py
python scripts/verify_release_zip.py dist/knowledge-workspace-*.zip
```

The release zip is a clean source release. It is not a prebuilt deployable bundle and intentionally does not include `frontend/dist`.

## Smoke

CI starts the backend with simulated AutoTest settings and then runs:

```powershell
python scripts/smoke_check.py --password "OwnerPass123!"
```

The smoke check is part of the release gate, not a substitute for backend pytest or frontend typecheck/build.
