# Security Model

Knowledge Workspace is a local-first, single-owner, trusted-environment application. It is suitable for a developer workstation, private demo machine, or similarly controlled environment. It is not a hardened public SaaS deployment and should not be described as production-ready in that sense.

## Current security posture

- auth, storage, and process boundaries are scoped to a trusted local owner workflow
- uploaded documents and photos are treated as untrusted content and validated accordingly
- AutoTest ZIPs are treated as untrusted code unless live execution is deliberately enabled in a trusted environment
- the app should not be exposed directly to the public internet without additional controls

## What "not production SaaS ready" means here

The repo does not yet provide all of the controls expected for a public multi-tenant service, including:

- hardened session management and broader auth policy
- network isolation for uploaded-code execution
- malware scanning and content quarantine
- durable external job execution
- per-tenant isolation and stronger secrets handling
- deployment packaging for prebuilt frontend assets and service orchestration

The current release zip is therefore a source release for controlled environments, not a turnkey deploy artifact.

## AutoTest modes

Use these terms consistently:

- `disabled`: no uploaded project commands execute
- `simulated`: safe default for CI, demos, and shared machines
- `local_trusted`: explicit trusted-host execution for local projects only
- `docker_sandbox`: Docker-backed execution after Docker executable and daemon preflight

Trusted-host live execution requires:

```env
AUTOTEST_MODE=local_trusted
KW_AUTOTEST_REAL_MODE=1
AUTOTEST_SANDBOX_BACKEND=local_trusted
```

Docker live execution uses:

```env
AUTOTEST_MODE=docker_sandbox
AUTOTEST_DOCKER_NETWORK=false
```

Safety boundaries:

- trusted-host live execution runs uploaded project commands on the local host
- Docker live execution adds useful container isolation, but it still depends on host Docker policy and is not a full public sandbox
- the worker is still in-process, so process interruption can fail active runs

## Command policy

- Node installs use `npm ci --ignore-scripts --no-audit --no-fund`
- missing package scripts are skipped instead of guessed
- Python dependency installation for uploaded projects remains disabled
- subprocesses use fixed timeouts, output truncation, and environment scrubbing

## ZIP intake

ZIP extraction rejects path traversal, absolute paths, Windows drive paths, symlinks, excessive file counts, and excessive expanded size.

## Auth and storage limits

JWT auth and browser token storage are acceptable for the current trusted local scope, but would need stronger session handling, XSS hardening, transport guarantees, and role separation before any multi-user or public deployment.

## Release hygiene

Release verification rejects runtime databases, journal files, secrets, caches, uploads, build outputs, and test artifacts. Passing those checks means the source release is clean; it does not mean the system is ready for internet-facing production deployment.
