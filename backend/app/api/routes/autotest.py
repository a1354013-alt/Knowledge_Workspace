from __future__ import annotations

from fastapi import APIRouter

from app.api import legacy_main

router = APIRouter()

router.add_api_route("/api/autotest/run", legacy_main.run_autotest, methods=["POST"])
router.add_api_route("/api/autotest/runs", legacy_main.list_autotest_runs, methods=["GET"])
router.add_api_route("/api/autotest/runs/{run_id}", legacy_main.get_autotest_run, methods=["GET"])
router.add_api_route("/api/autotest/{run_id}/export", legacy_main.export_autotest_report, methods=["GET"])
router.add_api_route("/api/autotest/github/analyze", legacy_main.analyze_github_repo, methods=["POST"])
