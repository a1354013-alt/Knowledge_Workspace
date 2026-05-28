# Security Pointer

The maintained security model lives at the repo root in `SECURITY_MODEL.md`.

Current highlights:

- AutoTest local_trusted mode is guarded host execution, not a true sandbox
- use local_trusted mode only for controlled/local trusted inputs
- Docker sandbox mode (`AUTOTEST_MODE=docker_sandbox`) provides basic local container isolation but is not a production-grade multi-tenant sandbox; do not expose AutoTest as a public upload execution service
- production-style safety requires container isolation, non-root execution, read-only workspace, egress restrictions, quotas, and disposable workspaces
- password hashing is currently PBKDF2-HMAC-SHA256 with backward-compatible legacy hash verification
