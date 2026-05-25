from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and optionally repair DB/vector/search index consistency.")
    parser.add_argument("--user-id", default="", help="Limit checks to a specific owner user id.")
    parser.add_argument("--repair", action="store_true", help="Attempt queued repairs after reporting mismatches.")
    args = parser.parse_args()

    os.environ.setdefault("JWT_SECRET", "local-index-consistency-secret-123456")
    os.environ.setdefault("DEFAULT_OWNER_PASSWORD", "OwnerPass123!")

    from app.services import indexing_service

    report = indexing_service.get_index_consistency_report(owner_user_id=args.user_id or None)
    if report:
        print(json.dumps({"status": "inconsistent", "issues": report}, indent=2))
    else:
        print(json.dumps({"status": "ok", "issues": []}, indent=2))

    if args.repair:
        repaired = indexing_service.repair_index_consistency(owner_user_id=args.user_id or None)
        print(json.dumps({"repaired": repaired}, indent=2))
        report = indexing_service.get_index_consistency_report(owner_user_id=args.user_id or None)

    return 1 if report else 0


if __name__ == "__main__":
    raise SystemExit(main())
