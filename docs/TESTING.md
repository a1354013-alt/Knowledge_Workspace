# Testing Pointer

The maintained verification guide lives at the repo root in `TESTING.md`.

Current highlights:

- use Python 3.11 for backend verification
- regenerate/check OpenAPI plus generated frontend types during contract validation
- run `python scripts/check_version_consistency.py` before release packaging
- AutoTest tests cover stale recovery and terminal failure persistence for the current in-process worker model
