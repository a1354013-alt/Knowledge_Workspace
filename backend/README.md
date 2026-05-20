# Backend API

Prereqs: Python 3.11.x (matches `requires-python = ">=3.11,<3.12"` and CI).

## Start

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
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

- the current built-in vector path uses Chroma plus a deterministic lightweight hash embedding
- that keeps demos, tests, and clean environments reproducible without external model dependencies
- it is not a production-grade semantic model
- adding Ollama embeddings, `sentence-transformers`, or an OpenAI-compatible embedding provider would be the next step for real semantic retrieval

## Tests

```bash
cd backend
python -m pytest
```

Integration smoke (starts a real backend process; used by CI):

```bash
cd ..
python scripts/smoke_check.py --password "<DEFAULT_OWNER_PASSWORD>"
```

## Key env vars

Minimum required:
- `JWT_SECRET` (min 32 chars)
- `DEFAULT_OWNER_PASSWORD` (seeds initial `owner` when DB is empty)

Optional (common):
- `ALLOWED_ORIGINS` (comma-separated)
- `MAX_FILE_SIZE` (bytes; default: 52428800 = 50MB)
- `AUTOTEST_MODE` (`simulated` by default; `real` only for trusted local projects)
- `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST` (`1` required before `AUTOTEST_MODE=real` can execute)
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

AutoTest real mode note:

- `AUTOTEST_MODE=real` without `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1` is rejected
- real mode is not a hardened sandbox
- it executes commands from uploaded projects
- use it only with trusted local code inside a sandbox/container

Text uploads:
- `.txt` / `.md` are decoded with `utf-8`, `utf-8-sig`, or `cp950` (upload validation and indexing use the same rules).

OCR notes:
- `available=true` requires the Python deps **and** a runnable system Tesseract binary.
