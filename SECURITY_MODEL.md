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
KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1
```

If `AUTOTEST_MODE=real` is set without the explicit enable flag, the API rejects the run with `403`.

AutoTest real mode is constrained command execution, not a hardened sandbox. Real mode should be run only inside an isolated local environment. It uses `shell=False`, fixed command timeouts, output truncation, sanitized report paths, and environment scrubbing, but those controls are not a full sandbox.

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

## Dependency Audit Policy

CI enforces frontend dependency audit with `npm audit --audit-level=moderate`, including devDependencies used by the build and test toolchain. Moderate or higher vulnerabilities must be fixed before release. Any accepted exception must be documented in `docs/KNOWN_LIMITATIONS.md` with package name, dependency path, risk, and follow-up plan.

## Release Hygiene

Release zip verification rejects runtime databases, journal files, secrets, caches, uploads, build outputs, and test artifacts before a package is accepted.
