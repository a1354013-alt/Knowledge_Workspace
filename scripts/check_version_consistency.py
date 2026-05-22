from __future__ import annotations

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_text_version(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _read_package_json_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data.get("version", "")).strip()


def _read_pyproject_version(path: Path) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return str(data.get("project", {}).get("version", "")).strip()


def _read_openapi_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data.get("info", {}).get("version", "")).strip()


def read_versions() -> dict[str, str]:
    sources: dict[str, str] = {
        "VERSION": _read_text_version(ROOT / "VERSION"),
        "frontend/package.json": _read_package_json_version(ROOT / "frontend" / "package.json"),
        "backend/pyproject.toml": _read_pyproject_version(ROOT / "backend" / "pyproject.toml"),
        "pyproject.toml": _read_pyproject_version(ROOT / "pyproject.toml"),
    }
    openapi_path = ROOT / "docs" / "openapi.json"
    if openapi_path.exists():
        sources["docs/openapi.json"] = _read_openapi_version(openapi_path)
    return sources


def main() -> int:
    versions = read_versions()
    expected = versions.get("VERSION", "")
    errors: list[str] = []

    if not expected:
        errors.append("VERSION is empty.")

    for path, version in versions.items():
        if not version:
            errors.append(f"{path} version is empty.")
            continue
        if version != expected:
            errors.append(f"{path} version '{version}' != VERSION '{expected}'")

    if errors:
        print("Version consistency check FAILED:")
        for err in errors:
            print(f"- {err}")
        return 1

    print(f"Version consistency check OK: {expected}")
    for path in versions:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
