# Release Checklist

1. Confirm runtime versions:
   - Python 3.11
   - `.python-version` is `3.11`
   - `python scripts/check_python_version.py`
   - Node 20.19+ LTS
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
3. Frontend verification:
   - `cd frontend`
   - `npm ci`
   - `npm audit --omit=dev --audit-level=high`
   - `npm run lint`
   - `npm run typecheck`
   - `npm run test:run`
   - `npm run build`
4. Release package:
   - `python scripts/package_release.py --output dist`
   - `python scripts/verify_release.py dist/knowledge_workspace_release.zip`
   - `scripts/package_release.py` stages a source release and does not build or ship `frontend/dist` by default
   - release zip is a clean source package; it does not include `frontend/dist`
   - release verification rejects `node_modules`, `dist`, `.env`, runtime databases/journals, caches, uploads, AutoTest workdirs, and test artifacts
