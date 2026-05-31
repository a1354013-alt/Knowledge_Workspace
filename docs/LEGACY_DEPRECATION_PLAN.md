# Legacy Deprecation Plan

## Purpose

This repo still carries a small set of compatibility modules so refactors can land incrementally without breaking older imports, monkeypatch-heavy tests, or release packaging. They are tolerated as temporary bridges, not as places for new feature work.

## Legacy modules still retained

### `backend/app/api/legacy_main.py`

Retain because:

- some older tests and imports still patch legacy entrypoints directly
- a few route-adjacent helpers still reach compatibility exports during the router/service split

Preferred replacements:

- `backend/app/main.py`
- `backend/app/api/app_factory.py`
- `backend/app/api/routes/*`
- `backend/app/api/handlers/*`
- `backend/app/services/*`

Removal conditions:

1. all tests patch concrete route, handler, or service modules instead
2. runtime code no longer imports `app.api.legacy_main`
3. compatibility exports are removed from packaging and release notes call out the deletion

### `backend/app/db/legacy_database.py`

Retain because:

- it still composes repository mixins into the public DB facade
- schema bootstrap and migration flow have not been fully disentangled from the compatibility surface

Preferred replacements:

- `backend/app/db/schema.py`
- `backend/app/db/migrations.py`
- `backend/app/repositories/*`

Removal conditions:

1. the public database facade is reconstructed without the legacy module
2. repositories no longer depend on `legacy_database.py` as a composition root
3. tests and runtime imports use the new composition path only

### `backend/app/api/handlers/support.py`

Retain because:

- it still bridges a few older handler imports
- some tests still depend on shared patch targets exposed there

Preferred replacements:

- direct imports from `app.api.common`
- direct imports from `app.context`
- direct imports from `app.dependencies`
- direct imports from `app.models`
- direct imports from `app.kb_index`

Removal conditions:

1. existing handlers import concrete dependencies directly
2. legacy patch targets are removed or rewritten
3. no new handlers depend on the support barrel

### `backend/app/services/autotest_service.py`

Retain because:

- it preserves older import paths while the maintained implementation now lives in `backend/app/services/autotest/service.py`

Preferred replacement:

- `backend/app/services/autotest/service.py`

Removal conditions:

1. all runtime and test imports target the package implementation directly
2. release notes and docs stop referencing the shim as a primary service module

## No-new-dependency rule

New code must not add fresh imports to:

- `backend/app/api/legacy_main.py`
- `backend/app/db/legacy_database.py`
- `backend/app/api/handlers/support.py`
- `backend/app/services/autotest_service.py`

If a new feature cannot be implemented without touching one of those files, treat that as a refactoring prompt and add the dependency to the maintained concrete module instead.

## Review checklist

When reviewing changes around legacy modules:

- reject new business logic added only to a legacy bridge
- prefer moving behavior into routes, handlers, services, repositories, or db schema modules
- require a comment in the PR or commit message when a legacy module must stay touched for compatibility
