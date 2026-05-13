# Release Checklist

1. Confirm runtime versions:
   - Python 3.11
   - Node 20.19+ LTS
2. Backend verification:
   - `cd backend`
   - `python -m pip install -r requirements.txt`
   - `python -m pytest`
   - `python -m compileall -q app tests`
3. Frontend verification:
   - `cd frontend`
   - `npm ci`
   - `npm run lint`
   - `npm run typecheck`
   - `npm run test:run`
   - `npm run build`
   - `npm audit --audit-level=moderate`
4. Contract verification:
   - `python scripts/export_openapi.py`
   - `cd frontend && npm run generate:api-types`
5. Release package:
   - `python scripts/check_version_consistency.py`
   - `python scripts/package_release.py --output dist`
   - `python scripts/verify_release_zip.py dist/knowledge_workspace_release.zip`
   - release verification rejects runtime databases, journals, secrets, caches, uploads, build outputs, and test artifacts
