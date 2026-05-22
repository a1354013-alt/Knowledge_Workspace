# Local Backend Verification

Knowledge Workspace backend verification is supported only on Python `3.11.x`.
If you run backend checks on Python `3.12` or `3.13`, treat the failure as a version guard, not as a broken dependency set.

## Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
python scripts/check_python_version.py
python scripts/safe_compileall.py -q .
python -m ruff check backend scripts
python -m pytest backend/tests
python scripts/export_openapi.py
python scripts/generate_api_types.py --check
python scripts/check_version_consistency.py
```

## Dependency Notes

- `chromadb` is part of the supported backend dependency set for the local-first vector index path.
- If `chromadb` is unavailable or disabled, indexing must report a degraded/unavailable state instead of pretending indexing succeeded.
- `markdown`, `slowapi`, `httpx`, `pytest`, and `ruff` are required for the supported verification flow.
- FastAPI test coverage uses `fastapi.testclient`, which depends on the pinned backend/runtime stack plus `httpx`.

## What The Verification Covers

- Python runtime guard
- import/compile sanity
- Ruff lint on `backend` and `scripts`
- backend pytest suite
- OpenAPI export
- OpenAPI -> TypeScript contract sync check
- version consistency check
