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

## 5. AutoTest mode vocabulary

- `simulated execution`: default and safest mode
- `runner disabled`: no uploaded commands execute
- `live execution`: real command execution through trusted host or Docker

Trusted-host live execution is only for code you trust. This repo is local-first, not a public upload execution service.

## 6. Verify the app

Backend:

```powershell
python scripts/check_python_version.py
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
