# Deprecation Plan

## Legacy API Bridge

`backend/app/api/legacy_main.py` remains in the repo only as a compatibility bridge.

Current purpose:

- keep older monkeypatch-heavy tests working during the router/service split
- preserve import compatibility for code that still reaches legacy names

It is not the primary architecture entrypoint. The supported runtime path is:

- `backend/app/main.py`
- `backend/app/api/app_factory.py`
- `backend/app/api/routes/*`
- `backend/app/services/*`
- `backend/app/repositories/*`

Removal conditions:

1. all tests patch concrete route, service, or repository modules directly
2. runtime code no longer imports `app.api.legacy_main` for behavior
3. release notes explicitly mark the bridge deprecated before removal

## Legacy Database Facade

`backend/app/db/legacy_database.py` is still the schema/bootstrap compatibility facade.

Current purpose:

- initialize SQLite schema and migrations
- compose repository mixins into the public `DocumentDatabase` facade
- preserve older import paths during the repository split

It should not grow new business logic. New behavior belongs in:

- `backend/app/db/schema.py`
- `backend/app/db/migrations.py`
- `backend/app/repositories/*`
- `backend/app/services/*`
