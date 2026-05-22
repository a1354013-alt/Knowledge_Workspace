# API Contract

The source of truth for backend contracts is the Pydantic schema set in `backend/app/models.py` plus each FastAPI route `response_model`.

## Export

```bash
python scripts/export_openapi.py
```

This writes `docs/openapi.json`.

## Frontend Types

```bash
cd frontend
npm run generate:api-types
```

The generated file is `frontend/src/api/generated/api-types.ts`. CI checks that generated types are current with:

```bash
python scripts/generate_api_types.py --check
git diff --exit-code docs/openapi.json frontend/src/api/generated/api-types.ts
```

## Contract Tests

Backend tests include OpenAPI checks for the main route groups and response schemas. Frontend API types are generated from `docs/openapi.json` and re-exported from `frontend/src/types/index.ts`; API helper changes must stay aligned with those generated types. The CI contract lane exports OpenAPI first, then checks generated types, then fails on any uncommitted diff in either `docs/openapi.json` or `frontend/src/api/generated/api-types.ts`.
