from __future__ import annotations

import json
import os
from pathlib import Path


def _walk_dirs_for_markers(base_dir: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    skip_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "dist",
        "build",
        ".venv",
        "venv",
        ".mypy_cache",
    }
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [directory for directory in dirs if directory not in skip_dirs and not directory.startswith(".")]
        files_set = {name.lower() for name in files}
        root_path = Path(root)
        if "package.json" in files_set:
            candidates.append(("node", root_path))
        if "pyproject.toml" in files_set or "requirements.txt" in files_set:
            candidates.append(("python", root_path))
    return candidates


def find_project_root_on_disk(extracted_root: Path) -> tuple[str, Path]:
    candidates = _walk_dirs_for_markers(extracted_root)
    if not candidates:
        return "unknown", extracted_root
    scored: list[tuple[int, int, str, Path]] = []
    for project_type, path in candidates:
        try:
            depth = len(path.relative_to(extracted_root).parts)
        except ValueError:
            depth = 9999
        tie_breaker = 0 if project_type == "node" else 1
        scored.append((depth, tie_breaker, project_type, path))
    scored.sort(key=lambda row: (row[0], row[1]))
    best = scored[0]
    return best[2], best[3]


def autotest_commands(project_type: str) -> dict[str, list[str]]:
    if project_type == "node":
        return {
            "install": ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
            "build": ["npm", "run", "build"],
            "test": ["npm", "test"],
            "lint": ["npm", "run", "lint"],
        }
    if project_type == "python":
        return {
            "install": ["python", "-m", "pip", "--version"],
            "build": ["python", "-m", "compileall", "."],
            "test": ["pytest"],
            "lint": ["python", "-m", "compileall", "."],
        }
    return {
        "install": ["echo", "install (simulated)"],
        "build": ["echo", "build (simulated)"],
        "test": ["echo", "test (simulated)"],
        "lint": ["echo", "lint (simulated)"],
    }


def _read_package_json_scripts(working_dir: Path) -> dict[str, str]:
    package_json = working_dir / "package.json"
    if not package_json.exists():
        return {}
    try:
        parsed = json.loads(package_json.read_text(encoding="utf-8"))
    except Exception:
        return {}
    scripts = parsed.get("scripts") if isinstance(parsed, dict) else None
    if not isinstance(scripts, dict):
        return {}
    return {key: value for key, value in scripts.items() if isinstance(key, str) and isinstance(value, str)}


def autotest_step_should_run(*, project_type: str, working_dir: Path, step_name: str) -> tuple[bool, str]:
    name = str(step_name or "").strip().lower()
    project_type_normalized = str(project_type or "").strip().lower()
    if project_type_normalized == "node" and name in {"build", "test", "lint"}:
        scripts = _read_package_json_scripts(working_dir)
        if name not in scripts:
            return False, f"Missing npm script '{name}' in package.json; step skipped."
        return True, ""
    if project_type_normalized == "python" and name == "test":
        has_tests_dir = (working_dir / "tests").is_dir()
        has_pytest_ini = (working_dir / "pytest.ini").exists()
        if not has_tests_dir and not has_pytest_ini:
            return False, "No 'tests/' directory or pytest.ini found; step skipped."
        return True, ""
    if project_type_normalized == "python" and name == "install":
        return False, "Python dependency installation is disabled unless trusted sandbox support is added."
    return True, ""
