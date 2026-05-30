# Backend API

Prereqs: Python 3.11.x (matches `requires-python = ">=3.11,<3.12"` and CI).

## Start

Supported development and test install from the repo root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

Runtime-only fallback from `backend/`:

```powershell
cd backend
python -m pip install -r requirements.txt
```

`requirements.txt` now includes runtime imports such as `httpx`, but it is not the supported test/lint install path.
If you need pytest, Ruff, or CI-equivalent verification, use `pip install -e ".[dev]"` from the repo root.

```powershell
cd backend
# copy .env.example .env
# Set at least: JWT_SECRET (min 32 chars) and DEFAULT_OWNER_PASSWORD
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Main endpoints

- `GET /health` (legacy)
- `GET /api/health` (CI + clients)
- `POST /api/login`
- `GET /api/me`
- `POST /api/docs/upload`
- `GET /api/docs`
- `PATCH /api/docs/{doc_id}`
- `DELETE /api/docs/{doc_id}`
- `GET /api/docs/{doc_id}/download`
- `POST /api/photos/upload`
- `GET /api/photos`
- `PATCH /api/photos/{photo_id}`
- `DELETE /api/photos/{photo_id}`
- `GET /api/photos/{photo_id}/download`
- `POST /api/qa`
- `POST /api/generate`
- `GET /api/knowledge/entries`
- `POST /api/knowledge/entries`
- `PATCH /api/knowledge/entries/{entry_id}`
- `GET /api/logbook/entries`
- `POST /api/logbook/entries`
- `PATCH /api/logbook/entries/{entry_id}`
- `POST /api/logbook/entries/{entry_id}/promote-to-knowledge`
- `POST /api/autotest/run`
- `GET /api/autotest/runs`
- `GET /api/autotest/runs/{run_id}`
- `GET /api/item-links?item_id=...`
- `POST /api/items/resolve`

## Contract rules

- Login, QA, generate, and knowledge/logbook create/update use JSON bodies
- File upload uses multipart form data
- Auth is handled only through bearer token dependency injection

## Search reality

- Ollama embedding provider is now available as an optional real semantic embedding provider via `EMBEDDING_PROVIDER=ollama`
- If Ollama is unavailable and fallback is enabled, the system falls back to demo hash embeddings or full-text search
- the fallback vector path uses Chroma plus a deterministic lightweight hash embedding
- demo hash embeddings keep demos, tests, and clean environments reproducible without external model dependencies
- demo hash embeddings are not a production-grade semantic model
- `/api/index/status` reports the current embedding mode

## Tests

```powershell
python scripts/check_python_version.py
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
```

Integration smoke (starts a real backend process; used by CI):

```powershell
python scripts/smoke_check.py --password "<DEFAULT_OWNER_PASSWORD>"
```

## Key env vars

Minimum required:
- `JWT_SECRET` (min 32 chars)
- `DEFAULT_OWNER_PASSWORD` (seeds initial `owner` when DB is empty)

Optional (common):
- `ALLOWED_ORIGINS` (comma-separated)
- `MAX_FILE_SIZE` (bytes; default: 52428800 = 50MB)
- `AUTOTEST_MODE` (`simulated` by default; `real` or legacy `local_trusted` for trusted host execution, `docker_sandbox` for container execution)
- `KW_AUTOTEST_REAL_MODE` / `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST` (set either to `1` before trusted host execution can run)
- `AUTOTEST_SANDBOX_BACKEND` (`local_trusted` required before trusted host execution can run; `docker` is reserved but not implemented)
- `AUTOTEST_TIMEOUT_SECONDS`
- `AUTOTEST_MAX_FILES`
- `AUTOTEST_MAX_UNZIPPED_BYTES`
- `AUTOTEST_RLIMIT_CPU_SECONDS`
- `AUTOTEST_RLIMIT_AS_MB`
- `AUTOTEST_RLIMIT_FSIZE_MB`
- `OCR_ENABLED` (`true/false/1/0`)
- `OCR_TESSERACT_CMD` (optional absolute path to the `tesseract` binary)
- `LLM_PROVIDER` (`ollama`, `mock`, `fallback`)
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`

AutoTest mode notes:

- `AUTOTEST_MODE=real` (or legacy `AUTOTEST_MODE=local_trusted`) without an explicit enable flag and `AUTOTEST_SANDBOX_BACKEND=local_trusted` is rejected
- trusted host execution is not a hardened sandbox
- it executes commands from uploaded projects on the trusted local workspace host
- Docker sandbox mode (`AUTOTEST_MODE=docker_sandbox`) is implemented as an optional containerized AutoTest runner
- Docker sandbox provides basic local container isolation with timeout/resource/network controls, but should not be described as a production-grade multi-tenant sandbox
- use trusted host execution only with trusted local code
- use docker_sandbox mode only on systems with Docker or Podman available

Text uploads:
- `.txt` / `.md` are decoded with `utf-8`, `utf-8-sig`, or `cp950` (upload validation and indexing use the same rules).

OCR notes:
- `available=true` requires the Python deps **and** a runnable system Tesseract binary.
