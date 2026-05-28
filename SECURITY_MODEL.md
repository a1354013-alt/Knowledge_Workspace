# Security Model

Knowledge Workspace is a local-first portfolio tool. It is designed for a developer machine, CI, or an isolated demo environment, not for a public upload service.

## Trust Boundary

- The backend trusts the authenticated local owner account.
- Uploaded documents and photos are treated as untrusted content.
- AutoTest ZIP uploads are treated as untrusted code unless real mode is explicitly enabled and the runtime is isolated.
- Do not expose this app directly to the public internet without adding hardened auth, malware scanning, network isolation, and resource controls.

## AutoTest Modes

Safe simulated mode is the default. It extracts and inspects project ZIPs, creates deterministic reports, and does not execute arbitrary uploaded project code.

Real mode requires both settings:

```env
AUTOTEST_MODE=real
KW_AUTOTEST_REAL_MODE=1
```

If `AUTOTEST_MODE=real` is set without the explicit enable flag, the API rejects the run with `403`.

AutoTest real mode is constrained command execution, not a hardened sandbox. Real mode should be run only inside an isolated local environment. It uses `shell=False`, fixed command timeouts, output truncation, sanitized report paths, and environment scrubbing, but those controls are not a full sandbox. `DockerSandboxRunner` is still a placeholder, so production-style container isolation is not finished yet. Treat real mode as trusted local execution only.

Do not treat guarded execution as safe for arbitrary public ZIP uploads. Real mode is appropriate for controlled/local inputs that you trust, not for exposing uploaded code execution to unknown internet users or multi-user public services.

The current AutoTest worker is also in-process rather than a durable queue. If the backend process is interrupted, an active run can become stale/interrupted and is later marked failed during startup recovery instead of being resumed mid-flight.

If you need production-style execution, add all of the following:

- container or VM isolation
- non-root user
- read-only workspace/root filesystem
- network egress restriction
- CPU, memory, and disk quotas
- disposable per-run workspace

## AutoTest Command Policy

- Node install uses `npm ci --ignore-scripts --no-audit --no-fund`.
- Node package scripts are limited to the fixed AutoTest steps: `build`, `test`, and `lint`.
- Missing Node scripts are skipped instead of guessed.
- Python dependency installation is disabled for uploaded projects. Python real mode can compile and run tests only when tests are detected.
- Every subprocess receives a timeout and capped stdout/stderr.

## ZIP Intake

ZIP extraction rejects path traversal, absolute paths, Windows drive paths, symlinks, excessive file counts, and excessive expanded size.

## Auth And Storage Limits

JWT auth is intended for a local owner workflow. Frontend token storage uses browser storage, so XSS would be a serious risk in a public deployment. Use HTTPS, stronger session handling, CSRF review, and separate user roles before multi-user or public use.

Password hashing is currently local-first PBKDF2-HMAC-SHA256. New hashes include the algorithm and iteration metadata, and legacy two-part PBKDF2 hashes remain readable so existing users can still log in. This is acceptable for the current local-first scope, but Argon2id would be the preferred production upgrade path if the deployment model expands.

## Dependency Audit Policy

CI enforces the frontend production dependency audit gate with `npm audit --omit=dev --audit-level=high`. High or critical production dependency vulnerabilities must be fixed before release. Any accepted exception must be documented in `docs/KNOWN_LIMITATIONS.md` with package name, dependency path, risk, and follow-up plan.

## Release Hygiene

Release zip verification rejects runtime databases, journal files, secrets, caches, uploads, build outputs, and test artifacts before a package is accepted.

