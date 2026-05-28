# Delivery Checklist

## Pre-delivery cleanup

- remove `backend/.env`
- remove local DB files from `backend/`
- remove local Chroma data
- remove uploaded test files
- remove `frontend/node_modules/`
- remove `frontend/dist/`
- remove ad-hoc tar/zip backups that are not release artifacts

## Architecture sanity check

- official backend entrypoint is `backend/app/main.py`
- app assembly is `backend/app/api/app_factory.py`
- `backend/app/api/legacy_main.py` is treated as a transition compatibility layer, not the target architecture
- route/service/repository/schema responsibilities remain aligned with current code

## Product checks

- document upload/update/delete works even when indexing fails, and warnings are visible instead of 500 errors
- photo upload/update/delete works without pretending indexing is transactional
- knowledge/logbook create/update/promote flows survive indexing failures and still persist DB state
- saved prompt creation reports indexing failure honestly
- dashboard shows only real metrics
- AutoTest run detail shows:
  - timeline
  - Markdown report download
  - HTML report download
  - AI fix prompt copy when available
- AutoTest real mode availability is visible in UI and docs, and the API rejects real mode unless `KW_AUTOTEST_REAL_MODE=1`
- GitHub repo analyze language says register/queue, not clone-and-run

## Verification commands

Backend:

- `cd backend`
- `python -m compileall -q app`
- `ruff check .`
- `python -m pytest`

Frontend:

- `cd frontend`
- `npm ci`
- `npm run lint`
- `npm run typecheck`
- `npm run test:run`
- `npm run build`
- `npm audit`

Repo-wide:

- `python scripts/check_version_consistency.py`
- `python scripts/package_release.py --output dist`
- `python scripts/verify_release_zip.py dist/knowledge_workspace_release.zip`

## Packaging rule

Deliver only:

- `backend/`
- `frontend/`
- root documentation and startup scripts
- `docs/`
- `scripts/`

