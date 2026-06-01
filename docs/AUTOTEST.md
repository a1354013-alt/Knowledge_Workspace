# AutoTest

## Purpose

AutoTest gives the project a fast acceptance-style verification lane without pretending to be a full sandboxed CI runner. It is designed for:

- portfolio demos
- local troubleshooting
- CI-safe simulated runs
- visible pass/fail timelines that can be promoted into reusable knowledge

## Current Backend Structure

- `backend/app/api/routes/autotest.py`
  - request parsing
  - auth dependency wiring
  - response handoff
- `backend/app/services/autotest_service.py`
  - compatibility shim for older imports
- `backend/app/services/autotest/service.py`
  - stable facade used by routers and compatibility imports
- `backend/app/services/autotest/run_lifecycle.py`
  - startup recovery for stale queued/running runs
  - durable failed-state marking after worker interruption
- `backend/app/services/autotest/job_executor.py`
  - async in-process worker lifecycle
  - run status heartbeat / `updated_at` refreshes
  - project extraction, stack detection, step ordering, and failure finalization
- `backend/app/services/autotest/step_runner.py`
  - command step execution entrypoint
- `backend/app/services/autotest/report_side_effects.py`
  - Knowledge draft and Logbook draft side effects after report generation
- `backend/app/services/autotest/workspace_cleanup.py`
  - ZIP and temporary directory cleanup
- `backend/app/services/autotest/archive.py`
  - ZIP validation/extraction
- `backend/app/services/autotest/detector.py`
  - stack detection and command selection
- `backend/app/services/autotest/runner.py`
  - constrained subprocess execution with `shell=False`
- `backend/app/services/autotest/timeline.py`
  - timeline normalization and response serialization
- `backend/app/services/autotest/reports.py`
  - AI suggestion fallback and indexing side-effect guards
- `backend/app/repositories/autotest_persistence_repository.py`
  - SQLite run/step persistence mixed into the DB facade
- `backend/app/repositories/autotest_repository.py`
  - narrow service-facing repository wrapper

## Mode vocabulary

Use these terms consistently across UI, docs, and code reviews:

- `disabled`: uploaded project commands do not execute
- `simulated`: safe default for CI, demos, and shared machines
- `local_trusted`: trusted-host execution for local projects only
- `docker_sandbox`: Docker-backed execution after Docker executable and daemon preflight

Legacy aliases such as `AUTOTEST_MODE=real` and `AUTOTEST_MODE=docker` are normalized internally for compatibility, but new docs and configs should use the vocabulary above.

## Modes

### `simulated`

- default mode
- safest option for CI and demos
- does not execute real project commands
- frontend/UI should describe this as simulated execution mode
- queued/API responses explicitly report that simulated mode is active
- still creates a real run, timeline, and derived knowledge/logbook artifacts

### `local_trusted`

- must be explicitly enabled with `AUTOTEST_MODE=local_trusted`
- requires `AUTOTEST_SANDBOX_BACKEND=local_trusted`
- requires either `KW_AUTOTEST_REAL_MODE=1` or `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1`
- extracts the uploaded ZIP
- detects a Node/Python project root
- executes commands from the uploaded project
- frontend/UI should describe this as trusted local execution, not a safe sandbox
- executes commands with:
  - `shell=False`
  - fixed timeout
  - best-effort POSIX resource limits
  - sensitive environment variable scrubbing
  - zip path traversal / absolute path / drive path / UNC path / symlink rejection

### `docker_sandbox`

- enabled with `AUTOTEST_MODE=docker_sandbox`
- performs preflight checks for the `docker` executable and Docker daemon before accepting a run
- runs commands through Docker without `shell=True`
- copies source into an isolated artifact workspace before container execution
- applies command timeout, CPU and memory flags where Docker supports them
- writes stdout/stderr logs under the configured artifact directory
- disables network by default; set `AUTOTEST_DOCKER_NETWORK=true` only when tests require it
- mounts a writable `/tmp` tmpfs while keeping the rest of the container read-only

## Local Trusted Safety Boundary

Local trusted mode is not a container sandbox. Treat it as trusted-code local execution only.
It is a local trusted-workspace execution mode, not Docker isolation.

Do not accept arbitrary public ZIP uploads into local trusted mode. Guarded execution is still host execution.

If the sandbox backend is missing, disabled, or set to an unimplemented value such as `docker`, the API fails safely before any uploaded command executes on the host.

Sensitive env vars are stripped when their names contain:

- `TOKEN`
- `KEY`
- `SECRET`
- `PASSWORD`
- `DATABASE_URL`

Recommended usage:

- use simulated execution in CI
- use simulated execution on shared/dev machines
- use trusted host live execution only on isolated local environments you control
- use trusted host live execution only with trusted local projects
- use `docker_sandbox` when Docker is available and command execution should be containerized
- future hardening direction:
  - Docker or Podman sandbox
  - no-network execution
  - non-root user
  - read-only root filesystem
  - CPU / memory / file-size limits
  - durable job queue
  - persistent logs / timeline

## Timeline Contract

Returned steps:

- `Uploaded`
- `Extracted`
- `Detected stack`
- `Installed dependencies / Prepared environment`
- `Ran tests`
- `Generated report`
- `Failed reason`

Returned fields per timeline item:

- `name`
- `status`
- `started_at`
- `finished_at`
- `duration_ms`
- `message`

Allowed statuses:

- `pending`
- `running`
- `success`
- `failed`
- `skipped`

## Failure Contract

Any exception after run creation must end in a consistent terminal state:

- `run.status = failed`
- `failed_reason` persisted
- current timeline phase marked `failed`
- later phases marked `skipped` when appropriate
- in-flight steps finalized so the frontend does not look stuck
- ZIP/temp folders removed in `finally`
- non-critical side effects (draft linking/indexing) must not leave the run stuck in `running`

## Frontend Expectations

The frontend should rely on:

- `POST /api/autotest/run` returning `202 Accepted` with a queued run
- `GET /api/autotest/runs/{run_id}` polling until `run.status` is `passed` or `failed`
- `run.status`
- `failed_reason`
- `timeline[*].status`
- `timeline[*].message`
- report export endpoints for completed runs:
  - `GET /api/autotest/{run_id}/export?format=md`
  - `GET /api/autotest/{run_id}/export?format=html`
- `suggestion` / `prompt_output` for AI-fix copy affordances

It should not infer success/failure from missing fields or command text alone.

## Known Limitations

- Docker sandbox availability depends on the host Docker installation and image availability
- AutoTest jobs run in an in-process background worker, not an external durable queue
- a restart/crash is handled by stale-run recovery, but interrupted work is not resumed
- if the backend restarts or the in-process worker disappears, runs can become interrupted/stale and are later marked failed by startup recovery rather than resumed in place
- local trusted and Docker sandbox tasks fail if they exceed the configured backend command timeout
- timeline/log updates currently use polling; SSE can be added later without changing the run contract
- a process crash can interrupt an active worker, so a future queue should recover or requeue interrupted runs
- GitHub analyze is URL intake plus `registered` intake-only metadata, not a queued execution job, remote clone-and-run path, or complete repository scan
- report export is generated on demand rather than persisted as a versioned artifact

## Interview Demo Flow

1. Show the runner-disabled / simulated default and explain why it is the default.
2. Run a passing ZIP and inspect the timeline.
3. Run a failing ZIP and point out `failed_reason` plus logbook creation.
4. Promote the logbook entry and show dashboard metrics update.
5. Explain that trusted host live execution and Docker live execution exist with different safety boundaries.
