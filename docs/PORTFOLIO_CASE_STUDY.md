# Portfolio Case Study: Knowledge Workspace

## Problem Background

Engineering teams accumulate troubleshooting notes, half-finished fixes, ad hoc prompts, uploaded docs, screenshots, and local test results in disconnected tools. The result is predictable:

- the same incidents are rediscovered repeatedly
- dashboards drift away from reality because metrics come from inference rather than persisted state
- “background” workflows get stuck in `queued` or `running`
- promotion flows create knowledge, but linked analytics do not reflect what actually happened

This project treats those gaps as the product problem, not just implementation details.

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
- service-oriented helper modules for form generation, report export, and indexing
- compatibility-preserving legacy logic gradually wrapped by explicit routers

### Frontend

- Vue 3 + Vite
- typed API contracts mirroring backend response models
- panels for dashboard, knowledge, logbook, docs/photos, prompts, search, settings, and AutoTest detail

## AutoTest Flow

1. user uploads a ZIP or registers a GitHub repo
2. backend creates an AutoTest run immediately
3. timeline state is initialized and persisted
4. ZIP extraction / stack detection / command execution proceed stage by stage
5. every failure path writes:
   - `run.status = failed`
   - `failed_reason`
   - stable timeline state
   - non-running terminal step states
6. successful runs create a draft knowledge item
7. failed runs create a draft logbook item

## Project Health Dashboard Design

The dashboard was explicitly redesigned around persisted truth:

- logbook promotion counts come from canonical `logbook -> knowledge` `produced` links
- document indexing counts come from persisted `index_status`
- recent activity is user-scoped and date-bounded
- LLM health separates primary provider health from fallback readiness so the UI does not overclaim

## Major Technical Challenges

### 1. Promote flow and dashboard drift

The project originally had reverse promote links in some paths. Dashboard analytics counted only `logbook -> knowledge`, which made promoted counts inconsistent.

Fix:

- promotion now always writes canonical `logbook:{id} -> knowledge:{id}` `produced`
- reverse `derived_from` is kept for traceability
- migration backfills canonical links for old reverse-only rows

### 2. AutoTest stuck states

A partially failing AutoTest flow is one of the fastest ways to make a dashboard untrustworthy.

Fix:

- run creation happens first
- exception handling forces terminal `failed`
- `failed_reason` is stored in DB
- timeline state is persisted, not inferred only at render time
- temporary ZIP/work directories are always cleaned in `finally`

### 3. Fake document indexing metrics

Counting “reviewed” documents as indexed made the dashboard look healthy without proof.

Fix:

- documents now store `index_status`, `index_error`, `indexed_at`
- upload starts with `pending`
- success writes `indexed`
- failure writes `failed` with error detail

### 4. Test isolation

Mixed test styles made it too easy to pass locally because of shared state.

Fix:

- function-scoped temp DB and app fixtures
- isolated TestClient setup per test
- precise assertions for dashboard/autotest/report paths

## Resolved Issues

- dashboard promoted count inconsistency
- AutoTest exception paths stuck in non-terminal states
- document index metrics based on guesswork
- misleading LLM readiness signal when fallback/noop was active
- oversized backend entrypoint and route sprawl

## Known Limitations

- AutoTest real mode is still process-constrained rather than sandbox-isolated
- frontend lint output still includes stylistic Vue warnings
- GitHub analyze stops at validated intake and queued run creation

## Future Work

- move more business logic from `legacy_main.py` into dedicated services
- add containerized real-mode execution
- add background queue support for larger indexing or AutoTest jobs
- add richer dashboard drill-down views by metric source

## Interview Demo Script

1. open the dashboard and explain that all metrics are user-scoped and DB-backed
2. upload a document and show `pending -> indexed/failed`
3. create a logbook entry, promote it, and show the promoted count increment
4. run AutoTest in simulated mode and inspect the timeline
5. trigger a failure case and show `failed_reason`, logbook draft creation, and dashboard impact
6. explain the safety boundary between simulated and real mode
