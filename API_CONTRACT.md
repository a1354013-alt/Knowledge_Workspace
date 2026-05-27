# API Contract

The source of truth for backend contracts is the Pydantic schema set in `backend/app/models.py` plus each FastAPI route `response_model`.

## Export

```bash
python scripts/export_openapi.py
python scripts/check_api_types.py
```

The export command writes `docs/openapi.json`. It auto-delegates to the repo `.venv311` when the current repo-root `python` is newer than the supported Python 3.11 runtime.

## Frontend Types

```bash
cd frontend
npm run generate:api-types
```

The generated file is `frontend/src/api/generated/api-types.ts`. CI checks that generated types are current with:

```bash
python scripts/check_api_types.py
git diff --exit-code docs/openapi.json frontend/src/api/generated/api-types.ts
```

Canonical QA `Source.source_type` values are `knowledge`, `logbook`, `prompt`, `document`, and `photo`. Internal vector/index metadata names such as `knowledge_entry`, `logbook_entry`, and `saved_prompt` must be normalized before crossing the API boundary.

Frontend usage rules:

- JSON APIs should use `frontend/src/api.ts`
- blob/download flows should use `frontend/src/services/downloads.ts`
- request/response payload types should come from `frontend/src/api/generated/api-types.ts` via `frontend/src/types/index.ts`

## Contract Tests

Backend tests include OpenAPI checks for the main route groups, internal-only endpoint inventory, and response schemas. Frontend tests verify that every route in `frontend/src/api/endpoints.ts` maps to an OpenAPI path. Frontend API types are generated from `docs/openapi.json` and re-exported from `frontend/src/types/index.ts`; API helper changes must stay aligned with those generated types. The CI contract lane checks OpenAPI first, then checks generated types, then fails on any uncommitted diff in either `docs/openapi.json` or `frontend/src/api/generated/api-types.ts`.
