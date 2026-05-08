# Project Structure

## Primary Entry Points

- `backend/app/main.py`
  - main FastAPI runtime entrypoint
  - exports compatibility handles used by tests
- `backend/app/api/app_factory.py`
  - assembles routers, middleware, and exception handlers
- `backend/app/api/legacy_main.py`
  - transition compatibility layer for routes not yet fully moved
  - still production-used, but not the desired long-term shape

## Backend Layout

```text
backend/
  main.py                       # compatibility launcher; imports app.main:app
  app/
    main.py                     # official backend runtime entrypoint
    api/
      app_factory.py            # FastAPI assembly
      routes/                   # focused router modules
      legacy_main.py            # transition compatibility layer
    services/                   # orchestration / workflows / formatting
    repositories/               # SQL-backed query logic
    db/
      schema.py                 # table/status contract
      migrations.py             # schema migration helpers
      legacy_database.py        # current SQLite persistence implementation
    llm/                        # provider wiring and health state
    kb_index.py                 # knowledge/photo/prompt vector indexing helpers
    vector_db.py                # Chroma integration
    models.py                   # Pydantic API contracts
    core/config.py              # env/config loading
  tests/
```

## Frontend Layout

```text
frontend/
  src/
    App.vue
    api.ts                      # shared Axios client and error handling
    autotest-api.ts             # focused AutoTest API helpers
    types/index.ts              # frontend-backend contract mirror
    components/                 # view panels
    utils/blob.ts               # report download helpers
  tests/
```

## Responsibility Guide

- `routes`
  - translate HTTP requests into typed service calls
  - no business orchestration
- `services`
  - own workflow order, safety boundaries, and user-facing summaries
  - keep DB writes separate from secondary indexing side effects
- `repositories`
  - own SQL details for read/write patterns that deserve isolation
- `db/schema.py`
  - source of truth for stable statuses such as AutoTest run/step states

## AutoTest Notes

- default mode is `simulated`
- `real` mode is opt-in and not a hardened sandbox
- report export is available in Markdown and HTML
- GitHub repo analyze currently registers/queues analysis metadata only
