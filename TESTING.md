# Testing

## Backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest
python -m compileall -q app tests
```

Backend tests use isolated temporary SQLite databases and upload directories. AutoTest defaults to simulated mode in tests; real-mode tests patch the subprocess runner and explicitly enable the real-mode gate.

## Frontend

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test:run
npm run build
npm audit --omit=dev --audit-level=high
```

Use Node 20 LTS to match CI.

## Release

```bash
python scripts/check_version_consistency.py
python scripts/package_release.py --output dist
python scripts/verify_release_zip.py dist/knowledge_workspace_release.zip
```

Release verification rejects runtime databases, journals, secrets, caches, uploads, build outputs, and test artifacts.

There are currently no intentionally skipped core tests. If slow integration tests are added later, they should use pytest markers and CI should still run the core suite by default.
