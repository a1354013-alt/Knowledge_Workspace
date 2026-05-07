# Portfolio Case Study: Knowledge Workspace

## Problem Background

Engineering teams accumulate troubleshooting notes, half-finished fixes, prompts, uploaded documents, screenshots, and local test results across disconnected tools. The predictable result is:

- the same incidents get rediscovered
- dashboards drift away from reality because they rely on inference instead of persisted state
- workflow-style features get stuck in `queued` or `running`
- promotion flows create knowledge, but linked analytics do not reflect what really happened

This project treats those gaps as the product problem, not just an implementation detail.

## System Goals

- make knowledge capture and troubleshooting traceable
- expose truthful dashboard metrics from the database contract
- keep AutoTest observable and failure-safe
- default to safe local behavior, with real execution only when explicitly enabled
- keep the codebase understandable for reviewers and future maintainers

## Architecture Design

### Backend

- FastAPI application with router-based app factory
- SQLite for authoritative metadata
- Chroma for vector retrieval
- service/repository split for AutoTest and Dashboard
- compatibility-preserving legacy logic gradually replaced by thin routers

Key backend split after hardening:

- `api/routes/*`: thin transport layer
- `services/autotest_service.py`: workflow orchestration
- `repositories/autotest_repository.py`: AutoTest persistence
- `services/dashboard_service.py`: dashboard composition
- `repositories/dashboard_repository.py`: dashboard SQL queries

### Frontend

- Vue 3 + Vite
- typed API contracts mirroring backend response models
- panels for dashboard, knowledge, logbook, docs/photos, prompts, search, settings, and AutoTest detail

## AutoTest Flow

1. user uploads a ZIP or registers a GitHub repo
2. backend creates an AutoTest run immediately
3. timeline state is initialized and persisted
4. ZIP extraction, stack detection, and command execution proceed stage by stage
5. every failure path writes `run.status = failed`, `failed_reason`, and a stable timeline state
6. successful runs create a draft knowledge item
7. failed runs create a draft logbook item

The key hardening improvement is that this workflow no longer depends on `legacy_main.py` for the main orchestration path; it is driven by `autotest_service.py` and persisted through `autotest_repository.py`.

## Project Health Dashboard Design

The dashboard was redesigned around persisted truth:

- logbook promotion counts come from canonical `logbook -> knowledge` `produced` links
- document indexing counts come from persisted `index_status`
- recent activity is user-scoped and date-bounded
- LLM health separates primary provider health from fallback readiness so the UI does not overclaim

## Major Technical Challenges

### 1. Promote flow and dashboard drift

The project originally had reverse promote links in some paths. Dashboard analytics counted only `logbook -> knowledge`, which made promoted counts inconsistent.

Fix:

- promotion now always writes canonical `logbook:{id} -> knowledge:{id}` `produced`
- reverse `derived_from` remains for traceability
- compatibility migration keeps old reverse-only data readable
- dashboard counts canonical promotion links without double-counting reverse links

### 2. AutoTest stuck states

A partially failing AutoTest flow quickly makes a dashboard untrustworthy.

Fix:

- run creation happens first
- exception handling forces a terminal `failed`
- `failed_reason` is stored in the DB
- timeline state is persisted instead of inferred only at render time
- temporary ZIP and work directories are always cleaned in `finally`

### 3. Fake document indexing metrics

Counting documents by workflow status instead of index status made the dashboard look healthier than it was.

Fix:

- documents now store `index_status`, `index_error`, and `indexed_at`
- upload starts with `pending`
- success writes `indexed`
- failure writes `failed` with error detail

### 4. Test isolation

Mixed test styles made it too easy to pass locally because of shared state.

Fix:

- function-scoped temp DB and app fixtures
- isolated `TestClient` setup per test
- precise assertions for dashboard, AutoTest, release packaging, and report flows

## What I Improved In The Hardening Phase

- fixed CI-facing Ruff issues instead of suppressing them
- improved test isolation so backend tests do not leak DB or filesystem state
- corrected LLM health so primary-unhealthy plus noop fallback no longer reports generation-ready
- converged AutoTest and Dashboard logic onto the router -> service -> repository path instead of leaving duplicate legacy branches
- completed release package documentation integrity so `docs/AUTOTEST.md` and `docs/PORTFOLIO_CASE_STUDY.md` ship inside the release zip

## Resolved Issues

- dashboard promoted count inconsistency
- AutoTest exception paths stuck in non-terminal states
- document index metrics based on guesswork
- misleading LLM readiness signal when fallback was noop-only
- release zip missing referenced documentation
- oversized backend entrypoint and route sprawl on the AutoTest and Dashboard paths

## Known Limitations

- `legacy_main.py` still owns part of the document, knowledge, logbook, photo, prompt, and system surface
- AutoTest real mode is process-constrained rather than sandbox-isolated
- GitHub analyze is a validated URL intake plus queued flow, not a full remote clone-and-run executor
- Chroma still emits third-party deprecation warnings in tests

## Future Work

- continue moving remaining document/photo/logbook orchestration out of `legacy_main.py`
- add containerized real-mode execution
- add background queue support for larger indexing or AutoTest jobs
- add richer dashboard drill-down views by metric source

## Interview Demo Script

1. Open the dashboard and explain that the metrics are user-scoped and DB-backed.
2. Upload a document and show `pending -> indexed/failed`.
3. Create a logbook entry, promote it, and show the promoted count increment.
4. Run AutoTest in simulated mode and inspect the timeline.
5. Trigger a failure case and show `failed_reason`, logbook draft creation, and dashboard impact.
6. Open the architecture notes and show the router -> service -> repository split.
7. Explain the safety boundary between simulated and real mode.
