from __future__ import annotations

import importlib
import sys
from pathlib import Path


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


def test_safe_download_filename_removes_header_injection_and_path_separators():
    from app.api.common import safe_download_filename

    filename = safe_download_filename('..\r\n"..//report\\final.txt')

    assert "\r" not in filename
    assert "\n" not in filename
    assert "/" not in filename
    assert "\\" not in filename
    assert '"' not in filename
    assert filename.endswith(".txt")


def test_safe_download_filename_falls_back_for_empty_values():
    from app.api.common import safe_download_filename

    assert safe_download_filename("") == "file"
    assert safe_download_filename("\u0000\u0001\r\n") == "file"


def test_safe_download_filename_truncates_while_preserving_extension():
    from app.api.common import MAX_SAFE_DOWNLOAD_FILENAME_LENGTH, safe_download_filename

    filename = safe_download_filename(f'{"a" * 400}.tar.gz')

    assert len(filename) <= MAX_SAFE_DOWNLOAD_FILENAME_LENGTH
    assert filename.endswith(".gz")
    assert Path(filename).suffix == ".gz"
