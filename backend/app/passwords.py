from __future__ import annotations

import hashlib
import hmac
import secrets

PASSWORD_ITERATIONS = 120000
PBKDF2_SCHEME = "pbkdf2_sha256"


def _derive_pbkdf2_sha256(password: str, salt: str, iterations: int) -> str:
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return derived.hex()


def hash_password(password: str, salt: str | None = None, *, iterations: int = PASSWORD_ITERATIONS) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    derived = _derive_pbkdf2_sha256(password, resolved_salt, iterations)
    return f"{PBKDF2_SCHEME}${iterations}${resolved_salt}${derived}"


def verify_password_hash(password: str, stored_hash: str) -> bool:
    parts = str(stored_hash or "").split("$")
    if len(parts) == 2:
        salt, expected = parts
        computed = _derive_pbkdf2_sha256(password, salt, PASSWORD_ITERATIONS)
        return hmac.compare_digest(computed, expected)
    if len(parts) == 4 and parts[0] == PBKDF2_SCHEME:
        _scheme, raw_iterations, salt, expected = parts
        try:
            iterations = int(raw_iterations)
        except ValueError:
            return False
        computed = _derive_pbkdf2_sha256(password, salt, iterations)
        return hmac.compare_digest(computed, expected)
    return False
