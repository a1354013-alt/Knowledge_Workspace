# Local Testing

## Backend

Use Python `3.11.x`. The backend package declares `requires-python = ">=3.11,<3.12"`, so Python `3.12` and `3.13` results are not accepted as supported release evidence.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .\backend\.env.example .\backend\.env
python scripts/check_python_version.py
python scripts/check_text_encoding.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
```

Equivalent single command from the repo root after dependencies are installed:

```powershell
python scripts/run_backend_checks.py
```

Full repo verification:

```powershell
python scripts/verify_all.py
```

`run_backend_tests.py` is the CI-style wrapper around pytest. It still runs `python -m pytest -q`, but it also enforces a whole-process timeout and fails if pytest reports passing tests without exiting cleanly.

## Frontend

```powershell
cd frontend
npm ci
npm audit --omit=dev --audit-level=high
npm run lint
npm run typecheck
npm run test:run
npm run build
npx playwright install chromium
npm run test:e2e
```

Use `npm ci` instead of `npm install` for verification. `npm install` is only for intentional dependency changes that must update `package-lock.json`.

## Local dev startup

Windows first run:

```powershell
.\scripts\bootstrap-dev.ps1
```

Daily development:

```powershell
.\scripts\start-dev.ps1
```

VS Code users can run the `bootstrap: dev` task manually for first setup, then use the `Knowledge Workspace: Full Stack Dev` F5 profile. F5 runs `preflight: dev` only; it must not rerun `npm ci` on every launch.

`start-dev.ps1` waits for `http://127.0.0.1:8000/api/health` and `http://127.0.0.1:5173` before reporting the dev stack as ready. If the backend is not ready, fix that error first instead of debugging frontend `/api/login` 502 responses.

Windows EPERM troubleshooting:

- Stop Vite, Node, and frontend test watchers before running `npm ci`.
- Close terminals or editors that are actively reading `frontend\node_modules`.
- Restart VS Code if an extension host or integrated terminal keeps a native binding locked.
- Avoid keeping `node_modules` in a OneDrive-synced directory.
- If dependencies or the Vite optimize cache are corrupted, stop all Node/Vite processes, delete `frontend\node_modules`, and rerun `.\scripts\bootstrap-dev.ps1`.

If pip or another parser reports `TOMLDecodeError` at line 1 column 1, check for a UTF-8 BOM before reinstalling dependencies:

```powershell
python scripts/check_text_encoding.py
```

## API contract

```powershell
python scripts/export_openapi.py --check
python scripts/generate_api_types.py --check
python scripts/check_index_consistency.py
```

When the API contract intentionally changes, regenerate both artifacts and commit them together.

## Release and smoke

```powershell
python scripts/check_version_consistency.py
python scripts/package_release.py
python scripts/verify_release.py dist/knowledge-workspace-*.zip
python scripts/smoke_check.py --password "OwnerPass123!"
```

The release zip is a source release, not a deployable bundle. It excludes `frontend/dist`, runtime DB files, caches, uploads, and temporary Chroma/AutoTest data.

## Release zip quickstart

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
cd frontend
npm ci
cd ..
Copy-Item .\backend\.env.example .\backend\.env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

bash:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
cd frontend
npm ci
cd ..
cp backend/.env.example backend/.env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
