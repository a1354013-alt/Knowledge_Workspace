PYTHON ?= python
NPM ?= npm

.PHONY: backend-verify frontend-verify release-verify verify repo-hygiene audit-python

repo-hygiene:
	$(PYTHON) scripts/verify_repo_hygiene.py

backend-verify: repo-hygiene
	$(PYTHON) scripts/check_python_version.py
	$(PYTHON) scripts/audit_python.py
	$(PYTHON) scripts/safe_compileall.py -q .
	$(PYTHON) -m ruff check backend scripts
	$(PYTHON) scripts/run_backend_tests.py

audit-python:
	$(PYTHON) scripts/audit_python.py

frontend-verify: repo-hygiene
	cd frontend && $(NPM) ci
	cd frontend && $(NPM) run lint
	cd frontend && $(NPM) run typecheck
	cd frontend && $(NPM) run test:run
	cd frontend && $(NPM) run build

release-verify: repo-hygiene
	$(PYTHON) scripts/export_openapi.py
	$(PYTHON) scripts/generate_api_types.py --check
	git diff --exit-code docs/openapi.json frontend/src/api/generated/api-types.ts
	$(PYTHON) scripts/check_version_consistency.py
	$(PYTHON) scripts/package_release.py knowledge_workspace_release.zip
	$(PYTHON) scripts/verify_release_zip.py knowledge_workspace_release.zip

verify:
	$(PYTHON) scripts/verify_all.py
