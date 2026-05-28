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
python scripts/safe_compile.py -q .
python -m ruff check backend scripts
python scripts/run_backend_tests.py
python scripts/export_openapi.py
python scripts/generate_api_types.py --check
python scripts/check_version_consistency.py
python scripts/check_index_consistency.py
```

For the full CI-equivalent gate from the repo root, including frontend, release packaging, and smoke:

```powershell
python scripts/verify_all.py
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
- backend pytest suite via `scripts/run_backend_tests.py`
- whole-process exit verification so pytest cannot print `passed` and still hang on background resources
- OpenAPI export, with automatic delegation to the repo `.venv311` when repo-root `python` is newer than 3.11
- OpenAPI -> TypeScript contract sync check
- version consistency check
- index consistency check
