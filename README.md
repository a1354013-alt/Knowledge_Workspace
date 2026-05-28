# Knowledge Workspace

Knowledge Workspace is a local-first engineering workspace that combines three product surfaces in one project:

- `Knowledge Workspace`: curated knowledge entries, logbook troubleshooting notes, saved prompts, and related-item links
- `AutoTest`: guarded ZIP / GitHub intake for quick acceptance-style test runs with structured timelines
- `Project Health Dashboard`: real aggregate metrics for knowledge quality, logbook promotion, AutoTest reliability, and document indexing state

## Product Positioning

This repo is intentionally a local-first, single-owner workspace. It is not a public multi-tenant SaaS product, and its auth/session/storage model should be evaluated in that scope.

This repo is built as a portfolio-grade full-stack system rather than a demo CRUD app. The goal is to show:

- consistent data contracts across backend, frontend, and dashboard metrics
- observable background-style workflows with reliable failure states
- testable safety boundaries for file handling and command execution
- clean, auditable architecture with incremental router/service separation

## Core Flow

```mermaid
graph TD
  UI["Vue Frontend"] --> API["FastAPI API"]
  API --> SQLITE["SQLite Metadata"]
  API --> FS["Uploads / Photos / AutoTest Workdirs"]
  API --> CHROMA["Chroma + Deterministic Lightweight Embeddings"]
  API --> LLM["Primary LLM + Fallback Status"]

  DOC["Document Upload"] --> IDX["Index Status: pending/indexed/failed"]
  IDX --> DASH["Project Health Dashboard"]

  LOG["Logbook Entry"] --> PROMOTE["Promote to Knowledge"]
  PROMOTE --> LINK["Canonical link: logbook -> knowledge"]
  LINK --> DASH

  ZIP["AutoTest ZIP"] --> RUN["AutoTest Run"]
  RUN --> TIME["Structured Timeline"]
  RUN --> NOTE["Failure Logbook or Success Knowledge Draft"]
```

## Feature Summary

### Knowledge + Logbook

- knowledge lifecycle: `draft -> reviewed -> verified -> archived`
- logbook troubleshooting capture with source refs and related item links
- promote flow now writes the canonical `logbook:{id} -> knowledge:{id}` `produced` link
- legacy reverse `knowledge -> logbook` `derived_from` links stay readable in the query/UI compatibility layer, but new promote writes only the canonical direction

### AutoTest

- upload `.zip` projects or register GitHub repos for intake-only analysis registration
- disabled command execution by default for demos, CI, and safe reproducibility
- local trusted mode is opt-in behind `AUTOTEST_MODE=local_trusted` plus `KW_AUTOTEST_REAL_MODE=1`
- Docker sandbox mode is available with `AUTOTEST_MODE=docker_sandbox` and uses fixed timeouts, `shell=False`, output limits, path sanitization, artifact logs, network-off-by-default, and Docker CPU/memory flags
- backend is now split into:
  - `api/routes/autotest.py`: thin HTTP layer
  - `services/autotest_service.py`: compatibility shim for older imports
  - `services/autotest/service.py`: stable facade used by routers
  - `services/autotest/run_lifecycle.py`: run state transitions and startup recovery
  - `services/autotest/job_executor.py`: background worker flow
  - `services/autotest/report_side_effects.py`: knowledge/logbook draft side effects
  - `services/autotest/workspace_cleanup.py`: temporary workspace cleanup
  - `repositories/autotest_repository.py`: run/step persistence
- run detail includes a timeline with:
  - `Uploaded`
  - `Extracted`
  - `Detected stack`
  - `Installed dependencies / Prepared environment`
  - `Ran tests`
  - `Generated report`
  - `Failed reason`
- any exception after run creation is forced into `failed`, with `failed_reason` persisted

### Project Health Dashboard

- knowledge counts by status
- logbook resolution rate and promoted-to-knowledge count
- AutoTest totals, pass rate, and recent runs
- backend is now split into:
  - `api/routes/dashboard.py`: thin HTTP layer
  - `services/dashboard_service.py`: response composition
  - `repositories/dashboard_repository.py`: SQL-backed metric queries
- document counts based on real DB index state:
  - `pending`
  - `indexed`
  - `failed`
  - `archived`

## Search Reality Check

- the built-in search/indexing path uses Chroma with the deterministic lightweight hash embedding in `backend/app/vector_db.py`
- the active default embedding path is explicitly labeled as a `demo/fallback` provider
- this is intentionally optimized for local demos, tests, and no-external-dependency environments
- it is not a production-grade semantic understanding model and should not be described as full AI semantic search
- production-grade semantic retrieval would require a real embedding provider such as Ollama embeddings, `sentence-transformers`, or an OpenAI-compatible embedding API
- that provider integration is a roadmap item in the current codebase, not a completed runtime switch

## Ollama, OpenAI, And OpenAPI

Ollama is optional. If Ollama is not running, the application still starts and the core workspace, knowledge, logbook, docs, and photos features remain available. LLM generation and QA degrade to retrieval-only, unavailable, or no-op fallback behavior depending on the endpoint path.

OpenAI-compatible providers are not enabled as production runtime providers in this release, and no OpenAI API key is required to start or use the project. OpenAPI is the local API contract in `docs/openapi.json`; it is used for tests and frontend type generation, not as an external AI service.

Ollama 為選用服務。未啟動 Ollama 時，系統仍可正常啟動與使用主要 knowledge workspace、logbook、docs/photos 功能，但 AI 生成回答會降級為 retrieval-only / unavailable / no-op fallback。OpenAI-compatible provider 在本版本尚未作為正式 runtime provider 啟用，也不需要 OpenAI API Key 才能啟動專案。OpenAPI 是本專案的 API 契約與前端型別產生依據，不是外部 AI 服務。

## Entry Points And Architecture

Primary runtime entrypoints:

- `backend/app/main.py`
- `backend/app/api/app_factory.py`

Transition compatibility layer:

- `backend/app/api/legacy_main.py`
  - compatibility shim for older imports and tests
  - stable handlers now live under `backend/app/api/handlers/*` by domain
- `backend/app/db/legacy_database.py`
  - database facade and schema bootstrap
  - focused repository mixins now live under `backend/app/repositories/*`

Responsibility split:

- `api/routes/*`: HTTP layer and dependency wiring
- `services/*`: workflow orchestration, safety checks, formatting, and side effects
- `repositories/*`: focused persistence queries/updates
- `api/handlers/support.py`: compatibility-only exports for older imports; handlers should import concrete dependencies directly
- `db/schema.py` + `db/migrations.py`: database contract and schema evolution
- `docs/openapi.json`: API contract source of truth
- `frontend/src/api/generated/api-types.ts`: generated frontend types from OpenAPI
- `frontend/src/types/index.ts`: re-export layer plus UI-only client types
- `frontend/src/services/downloads.ts`: shared blob/download helper layer
- `frontend/src/services/confirm.ts`: shared confirm flow for dangerous actions

## AutoTest Safety Boundary

AutoTest is intentionally constrained, but it is not a sandbox.

- default mode is `AUTOTEST_MODE=disabled`
- local trusted mode must be explicitly enabled with both `AUTOTEST_MODE=local_trusted` and `KW_AUTOTEST_REAL_MODE=1`
- if `AUTOTEST_MODE=local_trusted` is set without that enable flag, the API rejects the run
- local trusted mode executes commands from uploaded projects on the local trusted workspace host
- Docker sandbox mode is enabled with `AUTOTEST_MODE=docker_sandbox`
- Docker sandbox mode uses Docker command execution with timeout, CPU/memory limits, artifact logs, and network disabled by default
- Node installs use `npm ci --ignore-scripts --no-audit --no-fund`
- Python dependency installation for uploaded projects is disabled until a stronger trusted sandbox policy is added
- subprocess execution uses `shell=False`
- command timeout is fixed via `AUTOTEST_TIMEOUT_SECONDS`
- `/api/autotest/run` creates an in-process background job; a backend process crash can interrupt an active run until a durable external queue is added
- the worker refreshes `updated_at` heartbeats during execution, and startup recovery marks stale queued/running AutoTest runs failed after `AUTOTEST_STALE_RUN_MINUTES` (default 30) with a `worker_interrupted: server_restarted` failure reason
- real mode strips env vars containing:
  - `TOKEN`
  - `KEY`
  - `SECRET`
  - `PASSWORD`
  - `DATABASE_URL`
- ZIP intake rejects unsafe paths, symlinks, overlarge expansion, and excessive file counts

Recommended usage:

- use `disabled` mode in CI, demos, and shared machines
- use `local_trusted` mode only on a local or isolated environment you control
- use `local_trusted` mode only with trusted local projects
- use `docker_sandbox` when Docker is available and you want containerized execution
- enable Docker network only with `AUTOTEST_DOCKER_NETWORK=true` when tests require it
- recommended future hardening direction:
  - Docker or Podman sandboxing
  - disposable workspace per run
  - no-network execution
  - non-root user
  - read-only workspace/root filesystem
  - CPU / memory / disk / file-size limits
  - durable job queue
  - persistent logs / timeline

## First Startup

### Prerequisites

- Python `3.11.x` is required; Python `3.12` / `3.13` are not supported until dependency constraints are updated.
- Node.js `20` LTS with npm `10` or newer is the supported frontend runtime and matches CI.
- The bootstrap scripts create `.venv311`, install backend dev dependencies, run `npm ci` in `frontend/`, and create `.env` / `backend/.env` if missing.
- Existing `.env` files are never overwritten.

### Windows

```powershell
.\scripts\bootstrap-dev.ps1
.\scripts\start-dev.ps1
```

### macOS/Linux

```bash
bash scripts/bootstrap-dev.sh
bash scripts/start-dev.sh
```

Default development URLs:

- Backend API: `http://127.0.0.1:8000`
- API Docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:5173`

### Environment Files

Bootstrap writes safe local defaults only when files are missing:

- `.env` for repo-root defaults and documentation
- `backend/.env` for the backend server started from `backend/`

AutoTest real mode stays off in both files:

```env
AUTOTEST_MODE=disabled
KW_AUTOTEST_REAL_MODE=0
```

### AutoTest Runner Modes

AutoTest local trusted mode is disabled by default because it executes commands from uploaded projects on the local host. Use it only for trusted local projects; do not run untrusted ZIP uploads.

To enable local trusted mode:

```env
AUTOTEST_MODE=local_trusted
KW_AUTOTEST_REAL_MODE=1
```

To enable Docker sandbox mode:

```env
AUTOTEST_MODE=docker_sandbox
AUTOTEST_DOCKER_IMAGE=python:3.11-slim
AUTOTEST_DOCKER_NETWORK=false
AUTOTEST_DOCKER_MEMORY=2g
AUTOTEST_DOCKER_CPUS=2
```

## Embedding And Search Modes

Document upload writes full-text search content before vector indexing. If ChromaDB or an embedding provider is unavailable, upload can still succeed and the API reports a degraded semantic index instead of a fatal upload failure.

```env
EMBEDDING_PROVIDER=demo_hash
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_TIMEOUT_SECONDS=5
EMBEDDING_FALLBACK_ENABLED=true
```

Set `EMBEDDING_PROVIDER=ollama` to use Ollama embeddings. If Ollama is not running and fallback is enabled, the backend falls back to deterministic demo hash embeddings. `GET /api/index/status` reports `full_text_only`, `demo_hash_embedding`, `real_semantic_embedding`, or `vector_degraded`.

## Test And Verification

Windows:

```powershell
.\scripts\verify-all.ps1
```

macOS/Linux:

```bash
bash scripts/verify-all.sh
```

The verification scripts reuse the existing CI-equivalent Python gate (`scripts/verify_all.py`) and stop on the first failing stage.

### Backend Checks

```powershell
.\.venv311\Scripts\python.exe scripts\check_python_version.py
.\.venv311\Scripts\python.exe scripts\safe_compile.py -q .
.\.venv311\Scripts\python.exe -m ruff check backend scripts
.\.venv311\Scripts\python.exe scripts\run_backend_tests.py
.\.venv311\Scripts\python.exe scripts\check_index_consistency.py
.\.venv311\Scripts\python.exe scripts\export_openapi.py
.\.venv311\Scripts\python.exe scripts\generate_api_types.py --check
.\.venv311\Scripts\python.exe scripts\check_version_consistency.py
```

Python 3.11.x is the supported backend test runtime. Python 3.12/3.13 are not officially supported until dependency constraints are updated. Run `python scripts/check_python_version.py` before backend checks; see [docs/LOCAL_BACKEND_VERIFY.md](docs/LOCAL_BACKEND_VERIFY.md) and `docs/LOCAL_TESTING.md` for the reproducible local flow. CI additionally uses `python scripts/run_backend_tests.py` so backend pytest must both pass and return to the shell.

### Frontend Checks

```bash
cd frontend
npm ci
npm audit --omit=dev --audit-level=high
npm run lint
npm run typecheck
npm run test:run
npm run build
```

Use Node 20.19+ or newer for frontend lint/test/build to match the Vite/Vitest toolchain and CI.

## CI

CI lives in [.github/workflows/ci.yml](.github/workflows/ci.yml) and currently runs:

1. backend dependency install on Python `3.11`
2. `python scripts/check_python_version.py`
3. `python scripts/safe_compile.py -q .`
4. `python -m ruff check backend scripts`
5. `python scripts/run_backend_tests.py`
6. `python scripts/export_openapi.py --check`
7. `python scripts/generate_api_types.py --check`
8. Git checkouts also run `git diff --exit-code -- docs/openapi.json frontend/src/api/generated/api-types.ts`; source zip environments skip this Git-only check
9. `python scripts/check_version_consistency.py`
10. `python scripts/check_index_consistency.py`
11. frontend `npm ci`
12. frontend `npm audit --omit=dev --audit-level=high`
13. frontend `npm run lint`
14. frontend `npm run typecheck`
15. frontend `npm run test:run`
16. frontend `npm run build`
17. `python scripts/package_release.py`
18. `python scripts/verify_release.py dist/knowledge-workspace-*.zip`
19. backend startup plus `python scripts/smoke_check.py --password "OwnerPass123!"`

`python scripts/verify_all.py` is the repo-root local equivalent for the full CI gate, including frontend, `python scripts/check_index_consistency.py`, release zip verification, and smoke.

The release zip is a clean source package. `scripts/package_release.py` writes `dist/knowledge-workspace-<version>.zip` by default, does not build frontend assets unless `--build-frontend` is passed, and still does not ship `frontend/dist` in the final archive even when that staging build flag is used. The archive deliberately excludes `frontend/dist`, `node_modules`, runtime DB/journal files, caches, uploads, and temporary AutoTest/Chroma data; users build frontend assets after extraction with `cd frontend && npm ci && npm run build`.

### Release Zip Quickstart

The release zip is a source package, not a prebuilt app bundle. It does not include `frontend/dist`.

After extracting the zip:

Windows PowerShell:

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

Separate PowerShell frontend terminal:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
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
cp .env.example .env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Separate bash frontend terminal:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Smoke check after both servers are running:

```powershell
python scripts/smoke_check.py --password "OwnerPass123!"
```

## Knowledge Restore And Index Repair

- restoring a knowledge revision updates the SQLite row, refreshes `source_ref`-driven links, and immediately re-runs indexing
- restore is not allowed to pretend success if re-indexing raises or returns a degraded `False`/falsy result
- restore indexing failure persists `index_status`, stores `index_error`, and queues repair work so UI state and search state cannot silently drift apart
- `python scripts/check_index_consistency.py --repair` replays queued index/deindex work after the underlying issue is fixed

## Dashboard Metric Contract

`GET /api/dashboard/health`

Key guarantees:

- `logbook.promoted_to_knowledge` is counted from canonical `logbook -> knowledge` links
- promoted logbooks remain countable even after the source logbook is archived
- `documents.indexed`, `documents.pending`, and `documents.failed_documents` come from persisted document index state, not UI inference
- archived or inactive items are marked `excluded` for indexing and do not count as pending indexing work
- metrics are scoped to the current authenticated user

Metric sources:

- `knowledge.*`: `knowledge_entries`
- `logbook.*`: `logbook_entries` + canonical `item_links`
- `autotest.*`: `autotest_runs`
- `documents.*`: `documents.index_status`
- `recent_activity.*`: last-7-day slices from the same user-scoped tables

## AutoTest Modes

`POST /api/autotest/run` creates an asynchronous job and returns `202 Accepted` with the queued run. The queued response summary explicitly states whether the backend is in `simulated` or `real` mode. The frontend polls `GET /api/autotest/runs/{run_id}` for timeline/log updates and downloads reports only after the run reaches `passed` or `failed`.

### `simulated`

- safest default
- no real dependency install or user project command execution
- stable for CI and screenshots

### `real`

- extracts the ZIP
- detects Node/Python project roots
- requires `KW_AUTOTEST_REAL_MODE=1`
- runs a fixed command plan from the uploaded project with constrained subprocess settings
- does not run Python dependency installation for uploaded projects
- should only be used on trusted code in an isolated environment

## AutoTest Report Export

- backend endpoints:
  - `GET /api/autotest/{run_id}/export?format=md`
  - `GET /api/autotest/{run_id}/export?format=html`
- frontend run detail exposes:
  - `Download Markdown Report`
  - `Download HTML Report`
  - `Copy AI Fix Prompt`
- HTML export escapes run output and adds a basic CSP meta policy

## Index Repair API

- `GET /api/index/status`: summary of `pending/indexed/failed/unavailable` state plus provider mode
- `POST /api/index/rebuild`: rebuild all indexable content for the current owner
- `POST /api/index/rebuild/{item_type}/{item_id}`: rebuild one item
- `python scripts/check_index_consistency.py`: detect DB/vector/full-text drift and report repair-queue items
- `python scripts/check_index_consistency.py --repair`: replay queued index/deindex repairs and re-check consistency

## AutoTest Timeline Statuses

Each timeline step returns:

- `name`
- `status`
- `started_at`
- `finished_at`
- `duration_ms`
- `message`

Status meanings:

- `pending`: not started yet
- `running`: actively in progress
- `success`: completed successfully
- `failed`: terminal failure at this phase
- `skipped`: intentionally not run because an earlier failure or a safe skip rule applied

## Known Limitations

- `legacy_main.py` is a compatibility shim for older imports and monkeypatch-based tests; it now forwards only the compatibility names that still need to reach concrete handlers
- `api/handlers/support.py` is a compatibility export layer, not the preferred place for new handler dependencies
- AutoTest real mode is constrained local trusted-workspace subprocess execution, not a hardened sandbox
- AutoTest uses an in-process background worker, not a durable external queue; backend process crashes can interrupt active jobs
- GitHub analyze is currently an intake-only flow: validated URL intake plus `registered` local-analysis metadata, not a remote clone-and-run executor, full repository scan, or real execution queue entry
- built-in vector search uses deterministic lightweight hash embeddings for demos/tests; it is not a production semantic retrieval model
- Chroma emits third-party deprecation warnings in tests
- frontend verification should be run with Node `20` to match CI
- `legacy_main.py` and `legacy_database.py` remain compatibility bridges during the refactor; see [docs/DEPRECATION.md](docs/DEPRECATION.md) for removal conditions

## Portfolio Case Study

See [SECURITY_MODEL.md](SECURITY_MODEL.md), [API_CONTRACT.md](API_CONTRACT.md), [TESTING.md](TESTING.md), [docs/LOCAL_BACKEND_VERIFY.md](docs/LOCAL_BACKEND_VERIFY.md), and [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the security, contract, verification, and release rules.

See [docs/AUTOTEST.md](docs/AUTOTEST.md) for the AutoTest architecture, modes, timeline contract, and safety boundary.

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for the reproducible Windows PowerShell setup, Python 3.11 / Node 20 workflow, API contract refresh commands, and release packaging steps.

See [docs/PORTFOLIO_CASE_STUDY.md](docs/PORTFOLIO_CASE_STUDY.md) for:

- problem framing
- architecture choices
- major bug fixes
- dashboard contract design
- interview demo script


