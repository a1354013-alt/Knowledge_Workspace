from __future__ import annotations

from fastapi.testclient import TestClient


def test_openapi_main_routes_have_response_schemas(client: TestClient):
    schema = client.get("/openapi.json").json()
    required = [
        ("get", "/api/health"),
        ("post", "/api/login"),
        ("get", "/api/docs"),
        ("get", "/api/knowledge/entries"),
        ("get", "/api/logbook/entries"),
        ("get", "/api/photos"),
        ("get", "/api/dashboard/health"),
        ("get", "/api/autotest/capabilities"),
        ("get", "/api/autotest/runs"),
        ("post", "/api/autotest/github/analyze"),
    ]

    for method, path in required:
        operation = schema["paths"][path][method]
        response = operation["responses"]["200"]
        assert "schema" in response["content"]["application/json"], f"missing schema for {method.upper()} {path}"
