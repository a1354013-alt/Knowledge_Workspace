"""
Compatibility shim for older imports.

The authoritative security implementation lives in `app.core.security`.
New code should import from `app.core.security` directly.
This facade is retained for legacy imports only and should receive no new
dependencies.
"""

from __future__ import annotations

from app.core.security import create_token, extract_token_from_header, verify_token

__all__ = ["create_token", "extract_token_from_header", "verify_token"]
