# Testing

## Backend

Use Python `3.11.9` from `.python-version`. The backend is intentionally pinned to `>=3.11,<3.12`; Python 3.12/3.13 passing locally is not release evidence unless dependency constraints are updated.

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

Windows bootstrap shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_windows.ps1
```

After a Python 3.11 virtualenv is active, the repo-root helper runs the same checks:

```bash
python scripts/run_backend_checks.py
```

Full local CI-equivalent verification from the repo root:

```powershell
python scripts/verify_all.py
```

Backend tests use isolated temporary SQLite databases and upload directories. AutoTest defaults to simulated mode in tests; trusted-host tests patch the subprocess runner and explicitly enable the full gate, while Docker sandbox tests mock command construction unless `KNOWLEDGE_WORKSPACE_DOCKER_INTEGRATION=1` is set for an environment that has Docker. See `backend/.env.example` and `docs/LOCAL_TESTING.md` for the local environment contract.

For a fresh Python 3.11 backend environment:

Windows PowerShell:

```powershell
.\scripts\bootstrap_backend.ps1
.\.venv\Scripts\Activate.ps1
python scripts\run_backend_checks.py
python scripts\export_openapi.py
cd frontend
npm run generate:api-types
```

Linux/macOS:

```bash
./scripts/bootstrap_backend.sh
source .venv/bin/activate
python scripts/run_backend_checks.py
python scripts/export_openapi.py
cd frontend && npm run generate:api-types
```

If OpenAPI export says the Python runtime is unsupported, you are probably using Python 3.12/3.13. Create a Python 3.11 venv with the bootstrap scripts or run `uv python install 3.11 && uv venv --python 3.11`.

Optional reviewer shortcuts:

```powershell
python scripts/verify_repo_hygiene.py
make verify
```

AutoTest is still a local-first in-process worker in tests and runtime:

- queued/running jobs live in SQLite plus an in-process daemon thread
- execution heartbeats refresh `updated_at`
- startup recovery marks stale queued/running jobs failed after restart
- this is not equivalent to a durable queue such as RQ or Celery

Direct repo-root validation:

```powershell
python scripts/check_python_version.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
python scripts/check_index_consistency.py
```

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

Use Node `20.19.0` from `.nvmrc` to match CI and the Vite/Vitest toolchain engine range.

## Release

```powershell
python scripts/export_openapi.py
python scripts/check_api_types.py
git diff --exit-code docs/openapi.json frontend/src/api/generated/api-types.ts
python scripts/check_versions.py
python scripts/check_index_consistency.py
python scripts/package_release.py
python scripts/verify_release_package.py dist/knowledge-workspace-*.zip
```

Chroma / vector index note:

- `pip install -e ".[dev]"` installs the pinned `chromadb` runtime used by this repo.
- If Chroma is missing or cannot initialize, the app stays in degraded mode: indexing responses use `unavailable`, repair-queue reporting uses `index_unavailable`, and search falls back to deterministic non-semantic matching.
- The built-in embedding provider is still the deterministic local demo/fallback provider documented in `backend/app/vector_db.py`; placeholder production providers are not enabled in this release.

Recommended full verification flow before release:

1. `python scripts/check_python_version.py`
2. `python -m compileall backend`
3. `pytest backend/tests`
4. `python scripts/export_openapi.py`
5. `python scripts/check_api_types.py`
6. `git diff --exit-code docs/openapi.json frontend/src/api/generated/api-types.ts`
7. `python scripts/check_versions.py`
8. `python scripts/check_index_consistency.py`
9. `cd frontend && npm ci && npm audit --omit=dev --audit-level=high && npm run lint && npm run typecheck && npm run test && npm run build`
10. `python scripts/package_release.py`
11. `python scripts/verify_release_package.py dist/knowledge-workspace-*.zip`

The same end-to-end gate can also be run with `python scripts/verify_all.py`.

Contract-specific checks now include:

- backend pytest coverage for public OpenAPI route groups plus internal-only endpoint inventory
- frontend Vitest coverage that every `apiPaths` route maps to an OpenAPI path
- `export_openapi.py` and `check_api_types.py` so generated artifacts drift is caught before release
- archived/inactive index rows are expected to become `excluded` so they do not appear as pending indexing work

Frontend API usage rules:

- JSON APIs should use the shared helpers in `frontend/src/api.ts`
- blob/download flows should use `frontend/src/services/downloads.ts`
- dangerous confirm flows should use `frontend/src/services/confirm.ts` so tests can stub them consistently

Release verification rejects runtime databases, journals, secrets, caches, uploads, build outputs, and test artifacts.
It also rejects packaging artifacts such as `*.egg-info` and `*.dist-info`.
`python scripts/verify_release_package.py` resolves the versioned `dist/knowledge-workspace-*.zip`, extracts it to a temporary directory, and re-checks the extracted tree so archive contents and unzip results stay aligned.
Release verification also rejects WAL/SHM files, `ci_chroma/`, `.chroma/`, `chroma/`, `runtime/`, and `data/index/`.
`python scripts/verify_release_zip.py` extracts the archive to a temporary directory and re-checks the extracted tree so archive contents and unzip results stay aligned.
The release zip is a clean source package. `scripts/package_release.py` intentionally does not build or include `frontend/dist`; build frontend assets after extracting the package.

## Smoke

CI starts the backend with simulated AutoTest settings and then runs:

```powershell
python scripts/smoke_check.py --password "OwnerPass123!"
```

The smoke check is part of the release gate, not a substitute for backend pytest or frontend typecheck/build.

There are currently no intentionally skipped core tests. If slow integration tests are added later, they should use pytest markers and CI should still run the core suite by default.

Core pytest runs include `pytest-timeout` with a default 45-second per-test timeout using the cross-platform `thread` method so a hung test fails with a concrete test name instead of stalling CI indefinitely.
CI additionally runs `python scripts/run_backend_tests.py`, which wraps `python -m pytest -q` in a whole-process timeout and fails if pytest prints passing results but never returns to the shell.
