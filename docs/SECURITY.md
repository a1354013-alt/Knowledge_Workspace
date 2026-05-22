# Security Pointer

The maintained security model lives at the repo root in `SECURITY_MODEL.md`.

Current highlights:

- AutoTest real mode is guarded host execution, not a true sandbox
- use real mode only for controlled/local trusted inputs
- production-style safety requires container isolation, non-root execution, read-only workspace, egress restrictions, quotas, and disposable workspaces
- password hashing is currently PBKDF2-HMAC-SHA256 with backward-compatible legacy hash verification
