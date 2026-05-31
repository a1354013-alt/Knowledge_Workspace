# Operations

## Supported runtime

- Backend support is currently Python `3.11.x` only.
- Python `3.12` and `3.13` are not supported for backend verification, packaging, or release evidence.
- Frontend verification should use Node `20 LTS`.

## Backend startup contract

Start the API from `backend/` and keep env paths backend-relative:

```powershell
Copy-Item .\backend\.env.example .\backend\.env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Use these path forms in `backend/.env`:

- `DATABASE_PATH=./documents.db`
- `UPLOAD_DIR=./uploads`
- `PHOTO_DIR=./photos`
- `CHROMA_DB_PATH=./chroma_db`

This prevents accidental `backend/backend/...` path expansion.

## AutoTest terminology

Use these terms consistently across ops docs, UI copy, and reviews:

- `runner disabled`: `runner_mode=disabled`, no uploaded commands execute
- `simulated execution`: `execution_mode=simulated`, safe default for CI and shared machines
- `live execution`: human-facing umbrella term for `execution_mode=real`

Live execution can mean either:

- trusted-host live execution: `AUTOTEST_MODE=real` with `AUTOTEST_SANDBOX_BACKEND=local_trusted`
- Docker live execution: `AUTOTEST_MODE=docker_sandbox`

The backend is local-first. Neither live path should be described as public SaaS-ready code execution.

## Verification commands

Repo-root backend verification:

```powershell
python scripts/check_python_version.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
python scripts/check_index_consistency.py
python scripts/export_openapi.py --check
python scripts/generate_api_types.py --check
python scripts/check_version_consistency.py
```

## Source release vs deployable release

`scripts/package_release.py` creates a source release, not a one-click deployable release.

Source release characteristics:

- ships repository source plus release documentation
- excludes `frontend/dist`, `node_modules`, runtime databases, caches, uploads, and temporary AutoTest/Chroma workdirs
- requires the receiver to create a Python 3.11 environment, install dependencies, run `npm ci`, and build frontend assets after extraction

Do not describe the zip as a prebuilt bundle, deploy artifact, or turnkey production package.

## Release packaging

```powershell
python scripts/verify_repo_hygiene.py
python scripts/package_release.py --output dist
python scripts/verify_release_zip.py dist/knowledge-workspace-<version>.zip
```

## Index repair

- `python scripts/check_index_consistency.py` reports search/vector drift plus queued repair items
- `python scripts/check_index_consistency.py --repair` replays queued `index` and `deindex` work

## UTF-8 BOM policy

- committed Markdown, env files, and scripts should be UTF-8 without BOM unless a tool explicitly requires otherwise
- `scripts/bootstrap-dev.ps1` and `scripts/bootstrap-dev.sh` normalize BOM on existing `.env` files before reuse
- text upload decoding still accepts `utf-8-sig` for user content, but repo-maintained files should not rely on BOM
