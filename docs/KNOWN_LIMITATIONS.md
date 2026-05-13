# Known Limitations

- AutoTest real mode is constrained command execution, not a hardened sandbox. It must run inside an isolated sandbox/container and requires `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1`.
- `/api/autotest/run` uses an async in-process job runner. Jobs are durable in SQLite and visible through `GET /api/autotest/runs/{run_id}`, but a process crash can still interrupt an active in-memory worker; a future queue should recover or requeue interrupted runs.
- Python dependency installation for uploaded projects is disabled in AutoTest real mode until a trusted sandbox policy is added.
- Search fallback is deterministic keyword-style matching when a real embedding backend is unavailable; it should not be described as true semantic search in that mode.
- JWT and browser storage are suitable for a local-first demo, not a public multi-tenant deployment.
- `legacy_main.py` and `legacy_database.py` still contain compatibility logic while routes and repositories are migrated incrementally.
- CI enforces frontend dependency audit with `npm audit --audit-level=moderate`, including devDependencies.
- Release zip verification rejects runtime databases, journal files, secrets, caches, uploads, build outputs, and test artifacts.
