# Architecture Pointer

The maintained architecture overview lives at the repo root in `ARCHITECTURE.md`.

Current highlights:

- backend OpenAPI is the API contract source of truth
- frontend generated types come from `docs/openapi.json`
- UI-only types are the only frontend types that should stay hand-written
- AutoTest currently uses a local-first in-process worker with heartbeat-based stale recovery, not a production-durable queue
- `DockerSandboxRunner` is intentionally still a placeholder; current real mode is trusted local host execution rather than finished container isolation
- `backend/app/api/legacy_main.py` and `backend/app/db/legacy_database.py` are compatibility bridges; see `docs/DEPRECATION.md`
