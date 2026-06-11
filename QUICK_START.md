# Quick Start

Supported toolchain:

- Python `3.11.x`
- Node.js `20` LTS

Python `3.12` and `3.13` are not supported backend runtimes for this repo today.

## 1. Create the supported Python environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

Or let the project bootstrap both backend and frontend dependencies. This is the recommended first-run path:

```powershell
.\scripts\bootstrap-dev.ps1
```

After the first successful bootstrap, use F5 or `.\scripts\start-dev.ps1` for daily development. They run preflight checks only and do not rerun `npm ci`.

## 2. Prepare backend env

```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

`backend/.env.example` uses backend-relative paths like `./documents.db` and `./uploads` because the API starts from `backend/`.

## 3. Start backend

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 4. Install and start frontend

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

`package-lock.json` is the source of truth for frontend installs; use `npm ci`, not `npm install`, during verification.

## VS Code F5

Run `.\scripts\bootstrap-dev.ps1` once, open the repo root in VS Code, select `Knowledge Workspace: Full Stack Dev`, and press F5. The compound launch runs `preflight: dev`, starts FastAPI with `.venv`, starts Vite, and opens `http://localhost:5173`.

Do not use F5 as a dependency installer. If preflight reports a missing `.venv`, `frontend\node_modules`, `backend\.env`, Node.js, npm, or Python 3.11, run `.\scripts\bootstrap-dev.ps1` manually.

Windows EPERM during `npm ci` usually means `frontend\node_modules` is locked by a Node/Vite process, an editor, antivirus, or OneDrive sync. Stop dev servers, close terminals using `node_modules`, restart VS Code if needed, and avoid OneDrive-synced dependency folders. If the dependency tree is truly broken, stop all Node/Vite processes, delete `frontend\node_modules`, then rerun bootstrap.

## 5. AutoTest mode vocabulary

- `disabled`: no uploaded commands execute
- `simulated`: default and safest mode
- `local_trusted`: host execution for trusted local projects only
- `docker_sandbox`: Docker-backed execution after Docker executable and daemon preflight

Trusted-host live execution is only for code you trust. This repo is local-first, not a public upload execution service.

## 6. Verify the app

Backend:

```powershell
python scripts/check_python_version.py
python scripts/check_text_encoding.py
python scripts/audit_python.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
```

Frontend:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run test:run
npm run build
```

Repo-wide:

```powershell
python scripts/verify_all.py
```

## 7. Release expectation

`python scripts/package_release.py` produces a source release zip. It is not a one-click deployable package and does not include prebuilt `frontend/dist`.
