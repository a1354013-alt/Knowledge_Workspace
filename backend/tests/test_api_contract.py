from __future__ import annotations

import subprocess
import sys
from importlib import import_module
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "docs" / "openapi.json"
GENERATED_TYPES_PATH = ROOT / "frontend" / "src" / "api" / "generated" / "api-types.ts"

PUBLIC_ENDPOINTS = {
    "auth/session": ["/api/login", "/api/me"],
    "documents": ["/api/docs", "/api/docs/upload", "/api/docs/{doc_id}", "/api/docs/{doc_id}/download"],
    "photos": ["/api/photos", "/api/photos/upload", "/api/photos/{photo_id}", "/api/photos/{photo_id}/download"],
    "knowledge": ["/api/knowledge/entries", "/api/knowledge/entries/{entry_id}"],
    "logbook": [
        "/api/logbook/entries",
        "/api/logbook/entries/{entry_id}",
        "/api/logbook/entries/{entry_id}/promote-to-knowledge",
    ],
    "search": ["/api/search", "/api/item-links"],
    "dashboard/project health": ["/api/dashboard/health"],
    "autotest": ["/api/autotest/capabilities", "/api/autotest/runs", "/api/autotest/github/analyze"],
}

INTERNAL_ONLY_ENDPOINTS = {
    "/health",
    "/api/index/status",
    "/api/index/rebuild",
    "/api/index/rebuild/{item_type}/{item_id}",
    "/api/settings/llm",
    "/api/settings/ocr",
    "/api/meta/templates",
    "/api/generate",
    "/api/qa",
    "/api/prompts",
    "/api/prompts/{prompt_id}",
}


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


def test_checked_in_openapi_matches_runtime_app_schema(client: TestClient):
    python311 = ROOT / ".venv311" / "Scripts" / "python.exe"
    python_executable = str(python311 if python311.exists() else Path(sys.executable))
    result = subprocess.run(
        [python_executable, "scripts/export_openapi.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_generated_api_types_match_openapi_contract():
    generator = import_module("scripts.generate_api_types")
    expected = generator.generate()
    actual = GENERATED_TYPES_PATH.read_text(encoding="utf-8")
    assert actual == expected


def test_public_openapi_endpoints_are_present_and_internal_endpoints_are_documented(client: TestClient):
    schema = client.get("/openapi.json").json()
    available_paths = set(schema["paths"].keys())

    for area, paths in PUBLIC_ENDPOINTS.items():
        missing = [path for path in paths if path not in available_paths]
        assert not missing, f"missing public {area} endpoint(s) from OpenAPI: {missing}"

    for path in INTERNAL_ONLY_ENDPOINTS:
        assert path in available_paths, f"internal endpoint missing from OpenAPI inventory: {path}"


def test_autotest_openapi_and_generated_types_reflect_registered_intake_only_contract(client: TestClient):
    schema = client.get("/openapi.json").json()
    autotest_run_status = schema["components"]["schemas"]["AutoTestRunResponse"]["properties"]["status"]["enum"]
    assert "registered" in autotest_run_status

    autotest_execution_mode = schema["components"]["schemas"]["AutoTestRunResponse"]["properties"]["execution_mode"]
    assert autotest_execution_mode["default"] == "simulated"

    github_analyze = schema["components"]["schemas"]["GitHubAnalyzeResponse"]["properties"]
    assert github_analyze["status"]["const"] == "registered"
    assert github_analyze["analysis_scope"]["const"] == "intake_only"

    generated_types = GENERATED_TYPES_PATH.read_text(encoding="utf-8")
    assert 'status: "registered";' in generated_types
    assert 'analysis_scope?: "intake_only";' in generated_types
