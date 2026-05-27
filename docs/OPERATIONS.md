# Operations

## Index Repair

- `python scripts/check_index_consistency.py` reports search/vector drift plus queued repair items
- `python scripts/check_index_consistency.py --repair` replays queued `index` and `deindex` work
- knowledge restore follows the same indexing contract as create/update:
  - restore writes the selected revision back to SQLite
  - restore synchronizes `source_ref` and `derived_from` links
  - restore immediately re-indexes the restored entry
  - restore records `index_status` / `index_error` and queues repair if re-indexing raises or returns a degraded `False`/falsy result

## Contract Verification

- `python scripts/export_openapi.py` refreshes `docs/openapi.json`
- `python scripts/check_api_types.py` verifies `frontend/src/api/generated/api-types.ts`
- `python scripts/check_versions.py` verifies version parity across `VERSION`, Python packages, frontend package metadata, and OpenAPI

## Release Packaging

- `python scripts/package_release.py` writes `dist/knowledge-workspace-<version>.zip`
- `python scripts/verify_release_package.py dist/knowledge-workspace-*.zip` verifies the packaged archive and the extracted tree
- the release package intentionally excludes runtime DB files, journals, caches, uploads, `node_modules`, `frontend/dist`, and temporary AutoTest/Chroma workdirs
