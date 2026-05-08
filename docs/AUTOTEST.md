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
  - run creation
  - timeline orchestration
  - ZIP extraction
  - stack detection
  - command execution policy
  - report generation
  - failure finalization
  - temporary directory cleanup
- `backend/app/repositories/autotest_repository.py`
  - AutoTest run CRUD
  - AutoTest step CRUD
  - status / failed_reason / timeline persistence

## Modes

### `simulated`

- default mode
- safest option for CI and demos
- does not execute real project commands
- still creates a real run, timeline, and derived knowledge/logbook artifacts

### `real`

- must be explicitly enabled with `AUTOTEST_MODE=real`
- extracts the uploaded ZIP
- detects a Node/Python project root
- executes commands from the uploaded project
- executes commands with:
  - `shell=False`
  - fixed timeout
  - best-effort POSIX resource limits
  - sensitive environment variable scrubbing

## Real Mode Safety Boundary

Real mode is not a container sandbox. Treat it as trusted-code local execution only.

Sensitive env vars are stripped when their names contain:

- `TOKEN`
- `KEY`
- `SECRET`
- `PASSWORD`
- `DATABASE_URL`

Recommended usage:

- use `simulated` in CI
- use `simulated` on shared/dev machines
- use `real` only on isolated local environments you control
- use `real` only with trusted local projects
- future hardening direction:
  - Docker sandbox
  - no-network execution
  - stricter resource limits

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

## Frontend Expectations

The frontend should rely on:

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

- no container or VM isolation
- GitHub analyze is still URL intake and queued analysis registration, not a full remote clone-and-run path
- report export is generated on demand rather than persisted as a versioned artifact

## Interview Demo Flow

1. Show AutoTest in `simulated` mode and explain why it is the default.
2. Run a passing ZIP and inspect the timeline.
3. Run a failing ZIP and point out `failed_reason` plus logbook creation.
4. Promote the logbook entry and show dashboard metrics update.
5. Explain that `real` mode exists, but only behind an explicit safety boundary.
