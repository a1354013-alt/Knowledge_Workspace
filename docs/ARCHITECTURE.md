# Architecture Pointer

The maintained architecture overview lives at the repo root in `ARCHITECTURE.md`.

Current highlights:

- backend OpenAPI is the API contract source of truth
- frontend generated types come from `docs/openapi.json`
- UI-only types are the only frontend types that should stay hand-written
- AutoTest currently uses a local-first in-process worker with heartbeat-based stale recovery, not a production-durable queue
- Docker sandbox mode (`AUTOTEST_MODE=docker_sandbox`) is implemented for containerized AutoTest execution with basic isolation
- trusted-host live execution (`AUTOTEST_MODE=real`, with legacy `AUTOTEST_MODE=local_trusted` still accepted) provides trusted local host execution without container isolation
- `backend/app/api/legacy_main.py` and `backend/app/db/legacy_database.py` are compatibility bridges; see `docs/LEGACY_DEPRECATION_PLAN.md`
