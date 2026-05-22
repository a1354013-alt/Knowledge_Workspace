from __future__ import annotations

import sqlite3
from pathlib import Path


def test_normalize_roles_defaults_to_owner():
    from app.utils import normalize_roles

    assert normalize_roles(None) == ["owner"]
    assert normalize_roles([]) == ["owner"]


def test_owner_seed_uses_single_authority_for_new_and_migrated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")

    from app.db import DocumentDatabase

    new_db_path = tmp_path / "new.db"
    new_db = DocumentDatabase(str(new_db_path))
    owner = new_db.get_user("owner")
    assert owner is not None
    assert owner["role"] == "owner"

    legacy_db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(legacy_db_path)
    conn.execute(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

    migrated_db = DocumentDatabase(str(Path(legacy_db_path)))
    migrated_owner = migrated_db.get_user("owner")
    assert migrated_owner is not None
    assert migrated_owner["role"] == "owner"
