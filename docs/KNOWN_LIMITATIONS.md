# Known Limitations

- AutoTest real mode is constrained local trusted-workspace command execution, not a hardened sandbox. It requires `KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1` and should not be used for untrusted projects.
- `DockerSandboxRunner` is still a placeholder, so real mode must not be described as container-isolated or exposed as a public upload execution service.
- `/api/autotest/run` uses an async in-process job runner. Jobs are durable in SQLite and visible through `GET /api/autotest/runs/{run_id}`, but a process crash can still interrupt an active in-memory worker; a future queue should recover or requeue interrupted runs.
- Python dependency installation for uploaded projects is disabled in AutoTest real mode until a trusted sandbox policy is added.
- The Vite build still emits a large-chunk warning for the PrimeVue core bundle. Manual vendor chunking is already in place; the next improvement step is route/component lazy loading instead of hiding the warning with a larger limit.
- Built-in vector search uses a deterministic lightweight hash embedding for local demos, tests, and no-external-dependency environments. It should not be described as true semantic understanding or production-grade AI search.
- When vector indexing is unavailable, search falls back further to deterministic keyword-style matching.
- Production-grade semantic retrieval would require integrating a real embedding provider such as Ollama embeddings, `sentence-transformers`, or an OpenAI-compatible embedding API; that is a roadmap item, not a finished runtime switch.
- JWT and browser storage are suitable for a local-first demo, not a public multi-tenant deployment.
- `legacy_main.py` and `legacy_database.py` are now compatibility/facade modules, but some handler modules still use shared support imports while deeper service extraction continues.
- AutoTest async jobs are persisted as run rows, but execution is still in-process and not a durable external queue.
- CI enforces frontend production dependency audit with `npm audit --omit=dev --audit-level=high`.
- Release zip verification rejects runtime databases, journal files, secrets, caches, uploads, build outputs, and test artifacts.
- Production-grade AutoTest needs Docker or Podman isolation, no network, a non-root user, a read-only root filesystem, CPU / memory / file-size limits, a durable job queue, and persistent logs / timeline storage.
