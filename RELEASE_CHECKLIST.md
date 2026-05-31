# Release Checklist

1. Confirm supported runtimes.
   - Python `3.11.x` only
   - `.python-version` is `3.11.9`
   - Node `20.19.0` from `.nvmrc`
   - Do not use Python `3.12` or `3.13` as release evidence
2. Run backend verification from the repo root.
   - `python scripts/check_python_version.py`
   - `python scripts/check_text_encoding.py`
   - `python scripts/safe_compile.py -q .`
   - `python -m ruff check backend scripts`
   - `python scripts/run_backend_tests.py`
   - `python scripts/check_index_consistency.py`
   - `python scripts/export_openapi.py --check`
   - `python scripts/generate_api_types.py --check`
   - `python scripts/check_version_consistency.py`
3. Run frontend verification.
   - `cd frontend`
   - `npm ci`
   - `npm audit --omit=dev --audit-level=high`
   - `npm run lint`
   - `npm run typecheck`
   - `npm run test:run`
   - `npm run build`
4. Build and verify the release package.
   - `python scripts/verify_repo_hygiene.py`
   - `python scripts/package_release.py --output dist`
   - `python scripts/verify_release_zip.py dist/knowledge-workspace-<version>.zip`
5. Describe the artifact accurately.
   - it is a source release zip
   - it is not a deployable bundle
   - it does not include `frontend/dist`
   - extracted users still need Python 3.11, dependency installation, `npm ci`, and a frontend build
6. Check env documentation accuracy.
   - `backend/.env.example` remains the startup template
   - path values are backend-relative such as `./documents.db`
   - AutoTest wording uses `runner disabled`, `simulated execution`, and `live execution`
7. Check security positioning accuracy.
   - do not describe the repo as public-production-ready or SaaS-ready
   - keep local-first / trusted-environment wording intact
