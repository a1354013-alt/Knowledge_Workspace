from __future__ import annotations

from app.core.security import create_token


def test_inactive_user_old_token_is_rejected(client, auth_headers, app_module):
    assert client.get("/api/me", headers=auth_headers).status_code == 200

    assert app_module.legacy_main.db.update_user("owner", is_active=0)

    response = client.get("/api/me", headers=auth_headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "User account is inactive or no longer exists."


def test_empty_sub_token_is_rejected(client):
    token = create_token(user_id="", role="owner", display_name="Owner")

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token payload."
