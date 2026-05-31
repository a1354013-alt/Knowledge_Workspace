# Known Limitations

- AutoTest trusted-host live execution (`AUTOTEST_MODE=real`, with legacy `AUTOTEST_MODE=local_trusted` still accepted) is constrained local trusted-workspace command execution, not a hardened sandbox. It requires `AUTOTEST_SANDBOX_BACKEND=local_trusted` plus an explicit enable flag and should not be used for untrusted projects.
- Docker sandbox mode (`AUTOTEST_MODE=docker_sandbox`) is implemented as an optional containerized AutoTest runner with basic local isolation, but should not be exposed as a public multi-tenant execution service.
- `/api/autotest/run` uses an async in-process job runner. Jobs are durable in SQLite and visible through `GET /api/autotest/runs/{run_id}`, but a process crash can still interrupt an active in-memory worker; a future queue should recover or requeue interrupted runs.
- interrupted or stale runs are marked failed during startup recovery; they are not resumed from the middle of execution because the worker is in-process rather than a durable queue.
- GitHub analyze is intake-only registration metadata. It creates a `registered` AutoTest run for visibility, but it is not queued for clone/test execution and no background worker will pick it up.
- Python dependency installation for uploaded projects is disabled in AutoTest live execution until a stronger trusted sandbox policy is added.
- The Vite build still emits a large-chunk warning for the PrimeVue core bundle. Manual vendor chunking is already in place; the next improvement step is route/component lazy loading instead of hiding the warning with a larger limit.
- Ollama embedding provider is now available as an optional real semantic embedding provider via `EMBEDDING_PROVIDER=ollama`.
- If Ollama is unavailable and fallback is enabled, the system falls back to demo hash embeddings or full-text search.
- Demo hash embeddings are a deterministic lightweight embedding for local demos, tests, and no-external-dependency environments. They should not be described as true semantic understanding or production-grade AI search.
- If Chroma is unavailable, repair-queue reporting uses `index_unavailable` and search falls back to deterministic matching; this is degraded mode, not a data-repair failure.
- When vector indexing is unavailable, search falls back further to deterministic keyword-style matching.
- JWT and browser storage are suitable for a local-first demo, not a public multi-tenant deployment.
- `legacy_main.py` and `legacy_database.py` are now compatibility/facade modules, but some handler modules still use shared support imports while deeper service extraction continues. See `docs/LEGACY_DEPRECATION_PLAN.md`.
- AutoTest async jobs are persisted as run rows, but execution is still in-process and not a durable external queue.
- CI enforces frontend production dependency audit with `npm audit --omit=dev --audit-level=high`.
- Release zip verification rejects runtime databases, journal files, secrets, caches, uploads, build outputs, and test artifacts. The resulting artifact is still a source release, not a deployable package.
- Production-grade AutoTest needs Docker or Podman isolation, no network, a non-root user, a read-only root filesystem, CPU / memory / file-size limits, a durable job queue, and persistent logs / timeline storage.
