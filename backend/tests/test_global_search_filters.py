from __future__ import annotations


def _set_updated_at(app_module, *, table: str, id_column: str, row_id: str, updated_at: str) -> None:
    with app_module.db._connection() as conn:
        conn.execute(f"UPDATE {table} SET updated_at = ? WHERE {id_column} = ?", (updated_at, row_id))
        conn.commit()


def test_global_search_rejects_unknown_types(client, auth_headers):
    response = client.get("/api/search", headers=auth_headers, params={"types": "knowledge,unknown"})
    assert response.status_code == 400, response.text
    assert "Unsupported search type" in response.json()["message"]


def test_global_search_date_to_includes_same_day_rows(app_module, client, auth_headers):
    assert app_module.db.add_knowledge_entry(
        entry_id="search-date-1",
        title="Date filter",
        status="draft",
        problem="Date filter needle",
        root_cause="",
        solution="Solution",
        tags="alpha",
        notes="",
        created_by="owner",
    )
    _set_updated_at(
        app_module,
        table="knowledge_entries",
        id_column="entry_id",
        row_id="search-date-1",
        updated_at="2026-05-25T18:30:00+00:00",
    )

    response = client.get(
        "/api/search",
        headers=auth_headers,
        params={"q": "needle", "types": "knowledge", "date_to": "2026-05-25"},
    )
    assert response.status_code == 200, response.text
    item_ids = [item["item_id"] for item in response.json()["items"]]
    assert "knowledge:search-date-1" in item_ids


def test_global_search_mixed_type_filter_returns_only_requested_types(app_module, client, auth_headers):
    assert app_module.db.add_knowledge_entry(
        entry_id="search-knowledge-1",
        title="Knowledge target",
        status="draft",
        problem="Shared search marker",
        root_cause="",
        solution="Solution",
        tags="shared",
        notes="",
        created_by="owner",
    )
    assert app_module.db.add_saved_prompt(
        prompt_id="search-prompt-1",
        title="Prompt target",
        content="Shared search marker",
        tags="shared",
        created_by="owner",
    )
    assert app_module.db.add_photo(
        photo_id="search-photo-1",
        filename="photo.png",
        saved_filename="photo.png",
        tags="shared",
        description="Shared search marker",
        ocr_text="",
        file_size=10,
        uploaded_by="owner",
        status="reviewed",
    )

    response = client.get(
        "/api/search",
        headers=auth_headers,
        params={"q": "Shared search marker", "types": "knowledge,prompt"},
    )
    assert response.status_code == 200, response.text
    item_types = {item["item_type"] for item in response.json()["items"]}
    assert item_types == {"knowledge", "prompt"}


def test_global_search_accepts_limit_bounds(client, auth_headers):
    low = client.get("/api/search", headers=auth_headers, params={"limit": 1})
    default = client.get("/api/search", headers=auth_headers)
    high = client.get("/api/search", headers=auth_headers, params={"limit": 200})

    assert low.status_code == 200, low.text
    assert default.status_code == 200, default.text
    assert high.status_code == 200, high.text


def test_global_search_rejects_limit_out_of_bounds(client, auth_headers):
    zero = client.get("/api/search", headers=auth_headers, params={"limit": 0})
    over = client.get("/api/search", headers=auth_headers, params={"limit": 201})

    assert zero.status_code == 422, zero.text
    assert over.status_code == 422, over.text
