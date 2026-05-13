# Known Limitations

- AutoTest real mode is constrained command execution, not a hardened sandbox. It must run inside an isolated sandbox/container and requires `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1`.
- `/api/autotest/run` currently uses a single request execution model. Real mode jobs that exceed the frontend/backend timeout fail; long-term, this should become an async job flow with run creation, status polling or SSE logs, and report download after completion.
- Python dependency installation for uploaded projects is disabled in AutoTest real mode until a trusted sandbox policy is added.
- Search fallback is deterministic keyword-style matching when a real embedding backend is unavailable; it should not be described as true semantic search in that mode.
- JWT and browser storage are suitable for a local-first demo, not a public multi-tenant deployment.
- `legacy_main.py` and `legacy_database.py` still contain compatibility logic while routes and repositories are migrated incrementally.
- CI enforces production dependency audit with `npm audit --omit=dev --audit-level=high`.
- Release zip verification rejects runtime databases, journal files, secrets, caches, uploads, build outputs, and test artifacts.
