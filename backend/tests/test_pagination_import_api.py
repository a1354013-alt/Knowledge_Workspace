from __future__ import annotations


def test_list_endpoints_return_paginated_metadata(client, auth_headers, app_module):
    db = app_module.db
    for index in range(3):
        db.add_knowledge_entry(
            entry_id=f"k-{index}",
            title=f"Knowledge {index}",
            status="draft",
            problem=f"Problem {index}",
            root_cause="",
            solution="Fix it",
            tags="",
            notes="",
            created_by="owner",
        )
        db.add_logbook_entry(
            entry_id=f"l-{index}",
            title=f"Logbook {index}",
            status="draft",
            run_id="",
            problem=f"Problem {index}",
            root_cause="",
            solution="Fix it",
            tags="",
            source_type="manual",
            created_by="owner",
        )
        db.add_saved_prompt(
            prompt_id=f"p-{index}",
            title=f"Prompt {index}",
            content="Prompt body",
            tags="",
            created_by="owner",
        )
        db.add_photo(
            photo_id=f"photo-{index}",
            filename=f"photo-{index}.png",
            saved_filename=f"photo-{index}.png",
            tags="",
            description="",
            ocr_text="",
            file_size=1,
            uploaded_by="owner",
        )

    for path in ("/api/knowledge/entries", "/api/logbook/entries", "/api/prompts", "/api/photos"):
        first = client.get(path, headers=auth_headers, params={"limit": 2, "offset": 0})
        assert first.status_code == 200, first.text
        first_payload = first.json()
        assert len(first_payload["items"]) == 2
        assert first_payload["total"] == 3
        assert first_payload["limit"] == 2
        assert first_payload["offset"] == 0
        assert first_payload["has_more"] is True

        second = client.get(path, headers=auth_headers, params={"limit": 2, "offset": 2})
        assert second.status_code == 200, second.text
        second_payload = second.json()
        assert len(second_payload["items"]) == 1
        assert second_payload["total"] == 3
        assert second_payload["has_more"] is False


def test_bulk_import_dry_run_does_not_persist(client, auth_headers, app_module):
    response = client.post(
        "/api/import/prompts",
        headers=auth_headers,
        json={
            "dry_run": True,
            "rows": [
                {
                    "row_number": 2,
                    "values": {
                        "title": "Dry run prompt",
                        "content": "This should not be inserted.",
                        "tags": "import",
                    },
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["dry_run"] is True
    assert payload["success_rows"] == 1
    assert app_module.db.count_saved_prompts(user_id="owner") == 0


def test_bulk_import_rejects_duplicate_rows_without_partial_persist(client, auth_headers, app_module):
    request = {
        "dry_run": False,
        "rows": [
            {
                "row_number": 2,
                "values": {
                    "title": "Duplicate prompt",
                    "content": "Same body",
                    "tags": "import",
                },
            },
            {
                "row_number": 3,
                "values": {
                    "title": "Duplicate prompt",
                    "content": "Same body",
                    "tags": "import",
                },
            },
        ],
    }

    response = client.post("/api/import/prompts", headers=auth_headers, json=request)

    assert response.status_code == 422, response.text
    assert app_module.db.count_saved_prompts(user_id="owner") == 0
    payload_text = str(response.json())
    assert "Duplicate import row" in payload_text
    assert "row" in payload_text
    assert "3" in payload_text
