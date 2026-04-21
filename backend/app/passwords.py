from __future__ import annotations

import hashlib
import hmac
import secrets

PASSWORD_ITERATIONS = 120000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), PASSWORD_ITERATIONS)
    return f'{salt}${derived.hex()}'


def verify_password_hash(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split('$', 1)
    except ValueError:
        return False
    computed = hash_password(password, salt).split('$', 1)[1]
    return hmac.compare_digest(computed, expected)

