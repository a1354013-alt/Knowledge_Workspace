from __future__ import annotations

import subprocess
import sys


# Temporary, explicit allowlist for the current Python 3.11 dependency set.
# These are not ignored wholesale: each advisory remains visible here until the
# owning package can be upgraded and fully revalidated against FastAPI, Chroma,
# PDF extraction, OCR, and the existing API contract tests.
PIP_AUDIT_IGNORES = {
    "fastapi": ("PYSEC-2024-38",),
    "h11": ("GHSA-vqfr-h8mv-ghfj",),
    "markdown": ("PYSEC-2026-89",),
    "pillow": (
        "PYSEC-2026-165",
        "GHSA-3f63-hfp8-52jq",
        "GHSA-44wm-f244-xhp3",
        "GHSA-r73j-pqj5-w3x7",
    ),
    "pypdf": (
        "GHSA-7hfw-26vp-jp8m",
        "GHSA-vr63-x8vc-m265",
        "GHSA-jfx9-29x2-rv3j",
        "GHSA-m449-cwjh-6pw7",
        "GHSA-4xc4-762w-m6cg",
        "GHSA-4f6g-68pf-7vhv",
        "GHSA-2q4j-m29v-hq73",
        "GHSA-9mvc-8737-8j8h",
        "GHSA-996q-pr4m-cvgq",
        "GHSA-wgvp-vg3v-2xq3",
        "GHSA-2rw7-x74f-jg35",
        "GHSA-x7hp-r3qg-r3cj",
        "GHSA-f2v5-7jq9-h8cg",
        "GHSA-9m86-7pmv-2852",
        "GHSA-hqmh-ppp3-xvm7",
        "GHSA-qpxp-75px-xjcp",
        "GHSA-87mj-5ggw-8qc3",
        "GHSA-3crg-w4f6-42mx",
        "GHSA-jj6c-8h6c-hppx",
        "GHSA-4pxv-j86v-mhcw",
        "GHSA-7gw9-cf7v-778f",
        "GHSA-x284-j5p8-9c5p",
    ),
    "pytest": ("GHSA-6w46-j5rx-g56g",),
    "python-dotenv": ("GHSA-mf9w-mj56-hr94",),
    "python-multipart": (
        "GHSA-2jv5-9r88-3w3p",
        "GHSA-59g5-xgcq-4qw3",
        "GHSA-wp53-j4wj-2cfg",
        "GHSA-mj87-hwqh-73pj",
        "GHSA-pp6c-gr5w-3c5g",
    ),
    "requests": (
        "GHSA-9wx4-h78v-vm56",
        "GHSA-9hjg-9r4m-mvj7",
        "GHSA-gc5v-m9x4-r6x2",
    ),
    "setuptools": (
        "PYSEC-2022-43012",
        "PYSEC-2025-49",
        "GHSA-cx63-2mw6-8hw5",
    ),
    "starlette": (
        "PYSEC-2026-161",
        "GHSA-f96h-pmfr-66vw",
        "GHSA-2c2j-9gv5-cj73",
    ),
}


def main() -> int:
    command = [sys.executable, "-m", "pip_audit", "--skip-editable"]
    for advisory_ids in PIP_AUDIT_IGNORES.values():
        for advisory_id in advisory_ids:
            command.extend(["--ignore-vuln", advisory_id])

    print("+ " + " ".join(command))
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        print(
            "Python dependency audit failed. Review the advisory above, upgrade the dependency, "
            "or add a narrowly scoped allowlist entry with a comment in scripts/audit_python.py.",
            file=sys.stderr,
        )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
