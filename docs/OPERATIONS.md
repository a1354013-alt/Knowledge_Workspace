# Operations

## Index Repair

- `python scripts/check_index_consistency.py` reports search/vector drift plus queued repair items
- `python scripts/check_index_consistency.py --repair` replays queued `index` and `deindex` work
- knowledge restore follows the same indexing contract as create/update:
  - restore writes the selected revision back to SQLite
  - restore synchronizes `source_ref`-driven links
  - restore immediately re-indexes the restored entry
  - restore records `index_status` / `index_error` and queues repair if re-indexing raises or returns a degraded `False`/falsy result

## Contract Verification

- `python scripts/export_openapi.py` refreshes `docs/openapi.json`
- `python scripts/generate_api_types.py --check` verifies `frontend/src/api/generated/api-types.ts`
- `python scripts/check_version_consistency.py` verifies version parity across `VERSION`, Python packages, frontend package metadata, and OpenAPI

## Release Packaging

- `python scripts/package_release.py` writes `dist/knowledge-workspace-<version>.zip`
- `python scripts/package_release.py --build-frontend` runs `npm ci` and `npm run build` inside the temporary staging tree for verification, then removes the build output before the source zip is created
- `python scripts/verify_release.py dist/knowledge-workspace-*.zip` verifies the packaged archive and the extracted tree
- the release package intentionally excludes runtime DB files, journals, caches, uploads, `node_modules`, `frontend/dist`, and temporary AutoTest/Chroma workdirs
- the release artifact is therefore a clean source package; frontend assets are built after extraction, not bundled into the shipped zip

## Release Zip Quickstart

The shipped zip is a source package and does not include `frontend/dist`.

Windows PowerShell after extraction:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
cd frontend
npm ci
cd ..
copy .env.example .env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

bash after extraction:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
cd frontend
npm ci
cd ..
cp .env.example .env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
