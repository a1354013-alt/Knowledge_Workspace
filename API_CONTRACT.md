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

The generated file is `frontend/src/generated/api-types.ts`. CI checks that generated types are current with:

```bash
python scripts/generate_api_types.py --check
```

## Contract Tests

Backend tests include OpenAPI checks for the main route groups and response schemas. Frontend API helpers still use the stable hand-maintained types while generated types are introduced incrementally.
