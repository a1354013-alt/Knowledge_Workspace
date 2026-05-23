from __future__ import annotations

import importlib
import sys


def _reload_security_modules(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
    monkeypatch.setenv("JWT_ALGORITHM", "HS512")
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]
    config = importlib.import_module("app.core.config")
    config.reload_settings()
    security = importlib.import_module("app.core.security")
    return config, security


def test_jwt_helper_uses_settings_algorithm_for_encode_and_decode(monkeypatch):
    _config, security = _reload_security_modules(monkeypatch)

    token = security.JWTHelper.create_access_token(user_id="owner", role="owner", display_name="Owner")
    header = security.jwt.get_unverified_header(token)
    assert header["alg"] == "HS512"

    payload = security.JWTHelper.verify_token(token, token_type="access")
    assert payload["sub"] == "owner"
    assert payload["role"] == "owner"


def test_password_hash_verifies_legacy_and_versioned_formats():
    from app.passwords import PASSWORD_ITERATIONS, PBKDF2_SCHEME, hash_password, verify_password_hash

    versioned_hash = hash_password("OwnerPass123!", salt="abc123")
    assert versioned_hash.startswith(f"{PBKDF2_SCHEME}${PASSWORD_ITERATIONS}$abc123$")
    assert verify_password_hash("OwnerPass123!", versioned_hash) is True
    assert verify_password_hash("wrong-password", versioned_hash) is False

    legacy_hash = "abc123$" + hash_password("OwnerPass123!", salt="abc123").rsplit("$", 1)[-1]
    assert verify_password_hash("OwnerPass123!", legacy_hash) is True
    assert verify_password_hash("wrong-password", legacy_hash) is False


def test_password_hash_rejects_invalid_formats():
    from app.passwords import verify_password_hash

    assert verify_password_hash("OwnerPass123!", "") is False
    assert verify_password_hash("OwnerPass123!", "pbkdf2_sha256$bad$abc$def") is False
