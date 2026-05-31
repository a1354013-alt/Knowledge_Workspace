# Refactoring Plan

## Goal

Reduce a few oversized files that still carry mixed responsibilities, high test surface area, or too many import directions. This is a sequencing plan, not a promise that all splits happen in one release.

## Priority targets

### `frontend/src/components/DocsPhotosPanel.vue`

Current pressure:

- mixes document list, photo list, upload actions, filters, and modal/detail behavior in one panel
- large UI state surface makes tests and future feature changes harder to localize

Planned split:

- extract document table/list behavior into a document-focused child component
- extract photo gallery/upload behavior into a photo-focused child component
- move shared upload/download actions into a composable or service adapter
- keep `DocsPhotosPanel.vue` as the orchestration shell and layout entrypoint

Exit criteria:

- panel stays responsible mainly for tab-level orchestration
- document and photo interactions have narrower tests with smaller mocks

### `backend/app/services/indexing_service.py`

Current pressure:

- combines queueing, repair behavior, document reindexing, deindexing, logging, and storage lookups
- large procedural flow makes error-state auditing harder

Planned split:

- extract repair queue helpers
- extract content loading and decoding helpers
- extract item-type-specific indexing adapters
- keep one orchestration facade for callers that need a stable entrypoint

Exit criteria:

- indexing orchestration remains readable at top level
- repair logic and content-loading logic can be tested independently

### `backend/app/models.py`

Current pressure:

- broad collection of API contracts, enums, and response models in one file
- large import surface increases accidental coupling

Planned split:

- group models by domain such as auth, knowledge/logbook, docs/photos, dashboard, and autotest
- add a stable package re-export layer if import churn would otherwise be too disruptive
- keep shared literals and common response wrappers in a dedicated small module

Exit criteria:

- route files import only the domain models they use
- OpenAPI generation remains stable after modularization

## Secondary targets

- continue shrinking `legacy_main.py` compatibility reach
- continue reducing shared-barrel usage from `api/handlers/support.py`
- keep `autotest_service.py` as a thin shim only until imports are migrated

## Guardrails

- no behavior-only refactor should weaken existing assertions or bypass current tests
- preserve OpenAPI and generated API type stability when models move
- prefer adding compatibility re-exports first, then migrating imports, then removing bridges in a later pass
