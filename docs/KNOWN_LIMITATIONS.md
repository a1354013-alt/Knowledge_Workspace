# Known Limitations

- AutoTest real mode is constrained command execution, not a hardened sandbox. It must run inside an isolated sandbox/container and requires `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1`.
- Python dependency installation for uploaded projects is disabled in AutoTest real mode until a trusted sandbox policy is added.
- Search fallback is deterministic keyword-style matching when a real embedding backend is unavailable; it should not be described as true semantic search in that mode.
- JWT and browser storage are suitable for a local-first demo, not a public multi-tenant deployment.
- `legacy_main.py` and `legacy_database.py` still contain compatibility logic while routes and repositories are migrated incrementally.
- Current `npm audit` reports no vulnerabilities. If future moderate transitive issues remain after safe upgrades, document package name, production-path status, risk, and follow-up here.
