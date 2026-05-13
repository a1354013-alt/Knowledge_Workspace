from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from app.context import db, settings
from app.kb_index import index_knowledge_entry, index_logbook_entry
from app.llm import get_llm_provider
from app.models import (
    AutoTestCapabilitiesResponse,
    AutoTestExportFormat,
    AutoTestRunListItemResponse,
    AutoTestRunResponse,
    AutoTestTimelineItemResponse,
    GitHubAnalyzeRequest,
    GitHubAnalyzeResponse,
    GitHubRepoInfoResponse,
)
from app.repositories.autotest_repository import AutoTestRepository
from app.services.report_generator import ReportGenerator
from app.utils import generate_safe_filename, stream_write_file

logger = logging.getLogger("knowledge_workspace")
autotest_repository = AutoTestRepository(db)

TIMELINE_LABELS: tuple[tuple[str, str], ...] = (
    ("uploaded", "Uploaded"),
    ("extracted", "Extracted"),
    ("detected_stack", "Detected stack"),
    ("prepared_environment", "Installed dependencies / Prepared environment"),
    ("ran_tests", "Ran tests"),
    ("generated_report", "Generated report"),
    ("failed_reason", "Failed reason"),
)

TIMELINE_KEYS = {key for key, _label in TIMELINE_LABELS}

AUTOTEST_SUGGEST_SYSTEM_PROMPT = """You are a local-first engineering assistant.

Rules:
1. Do not invent outputs or versions. Use only the provided AutoTest logs.
2. Prefer actionable, reproducible steps (commands, filenames, config keys).
3. If logs are insufficient, say what extra info is needed.
"""

AUTOTEST_OUTPUT_LIMIT = 12_000


def is_real_autotest_requested() -> bool:
    return str(settings.AUTOTEST_MODE or "").strip().lower() == "real"


def is_real_autotest_enabled() -> bool:
    return bool(settings.KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST)


def current_autotest_execution_mode() -> str:
    return "real" if is_real_autotest_requested() and is_real_autotest_enabled() else "simulated"


def get_autotest_capabilities() -> AutoTestCapabilitiesResponse:
    requested = is_real_autotest_requested()
    enabled = is_real_autotest_enabled()
    available = requested and enabled
    message = (
        "Real AutoTest mode is enabled. Run only trusted projects inside a sandbox/container."
        if available
        else "Safe simulated mode is active. Real command execution requires AUTOTEST_MODE=real and KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1."
    )
    return AutoTestCapabilitiesResponse(
        mode="real" if available else "simulated",
        real_mode_requested=requested,
        real_mode_enabled=enabled,
        real_mode_available=available,
        message=message,
    )


def sanitize_path_for_report(path: Path, *, base_dir: Path) -> str:
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix() or "."
    except ValueError:
        return "<sanitized-path>"


def clamp_output(value: str, *, limit: int = AUTOTEST_OUTPUT_LIMIT) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated to {limit} characters]"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_ms(started_at: str | None, finished_at: str | None) -> int | None:
    start = _parse_iso_datetime(started_at)
    end = _parse_iso_datetime(finished_at)
    if not start or not end:
        return None
    return max(int((end - start).total_seconds() * 1000), 0)


def _normalize_timeline_status(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"passed", "done", "success"}:
        return "success"
    if normalized == "failed":
        return "failed"
    if normalized in {"skipped", "unavailable"}:
        return "skipped"
    if normalized == "running":
        return "running"
    return "pending"


def _new_timeline_item(
    key: str,
    label: str,
    *,
    status: str = "pending",
    message: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "name": label,
        "status": _normalize_timeline_status(status),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": _duration_ms(started_at, finished_at),
        "message": message,
    }


def initial_autotest_timeline(*, source_ref: str, created_at: str) -> list[dict[str, object]]:
    items = [_new_timeline_item(key, label) for key, label in TIMELINE_LABELS]
    items[0] = _new_timeline_item(
        "uploaded",
        "Uploaded",
        status="success",
        message=source_ref or None,
        started_at=created_at,
        finished_at=created_at,
    )
    return items


def save_run_timeline(run_id: str, timeline: list[dict[str, object]]) -> None:
    autotest_repository.update_run(run_id, timeline_json=json.dumps(timeline, ensure_ascii=True))


def set_timeline_item(
    timeline: list[dict[str, object]],
    key: str,
    *,
    status: str | None = None,
    message: str | None = None,
    clear_message: bool = False,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> list[dict[str, object]]:
    updated: list[dict[str, object]] = []
    for item in timeline:
        if str(item.get("key")) != key:
            updated.append(item)
            continue
        next_item = dict(item)
        if status is not None:
            next_item["status"] = _normalize_timeline_status(status)
        if clear_message:
            next_item["message"] = None
        elif message is not None:
            next_item["message"] = message
        if started_at is not None:
            next_item["started_at"] = started_at
        if finished_at is not None:
            next_item["finished_at"] = finished_at
        next_item["duration_ms"] = _duration_ms(
            str(next_item.get("started_at") or "") or None,
            str(next_item.get("finished_at") or "") or None,
        )
        updated.append(next_item)
    return updated


def finalize_autotest_timeline_failure(
    *,
    timeline: list[dict[str, object]],
    failed_phase: str,
    failed_reason: str,
) -> list[dict[str, object]]:
    output = timeline
    phase_found = False
    failed_at = utc_now_iso()
    for key, _label in TIMELINE_LABELS:
        if key == failed_phase:
            phase_found = True
            output = set_timeline_item(
                output,
                key,
                status="failed",
                finished_at=failed_at,
                message=failed_reason,
            )
            continue
        current_item = next((item for item in output if str(item.get("key")) == key), None)
        if not current_item:
            continue
        current_status = str(current_item.get("status", "") or "")
        if phase_found and current_status == "pending":
            output = set_timeline_item(output, key, status="skipped")
    output = set_timeline_item(
        output,
        "failed_reason",
        status="failed",
        started_at=failed_at,
        finished_at=failed_at,
        message=failed_reason,
    )
    return output


def serialize_autotest_step(step: dict) -> dict[str, object]:
    return {
        "step_id": step.get("step_id", ""),
        "name": step.get("name", ""),
        "command": step.get("command", ""),
        "status": step.get("status", ""),
        "started_at": step.get("started_at", ""),
        "finished_at": step.get("finished_at", ""),
        "output": step.get("output", ""),
        "success": int(step.get("success", 0)),
        "exit_code": int(step.get("exit_code", 0)),
        "stdout_summary": step.get("stdout_summary", ""),
        "stderr_summary": step.get("stderr_summary", ""),
        "error_type": step.get("error_type", ""),
        "created_at": step.get("created_at", ""),
    }


def build_autotest_timeline(run_row: dict, step_rows: list[dict]) -> list[AutoTestTimelineItemResponse]:
    timeline_json = str(run_row.get("timeline_json", "") or "").strip()
    if timeline_json:
        try:
            items = json.loads(timeline_json)
            if isinstance(items, list):
                normalized: list[AutoTestTimelineItemResponse] = []
                for raw in items:
                    if not isinstance(raw, dict):
                        continue
                    key = str(raw.get("key", "") or "")
                    label = str(raw.get("label", "") or raw.get("name", "") or "")
                    if not key or not label:
                        continue
                    normalized.append(
                        AutoTestTimelineItemResponse(
                            key=key,
                            label=label,
                            name=str(raw.get("name", "") or label),
                            status=_normalize_timeline_status(str(raw.get("status", "") or "pending")),
                            started_at=str(raw.get("started_at", "") or "") or None,
                            finished_at=str(raw.get("finished_at", "") or "") or None,
                            duration_ms=(
                                int(raw["duration_ms"])
                                if raw.get("duration_ms") is not None
                                else _duration_ms(raw.get("started_at"), raw.get("finished_at"))
                            ),
                            message=str(raw.get("message", "") or "") or None,
                        )
                    )
                if normalized:
                    return normalized
        except json.JSONDecodeError:
            logger.warning("Invalid timeline_json for AutoTest run %s", run_row.get("run_id", ""))

    run_status = str(run_row.get("status", "") or "").lower()
    created_at = str(run_row.get("created_at", "") or "") or None
    has_workdir = bool(str(run_row.get("working_directory", "") or "").strip())
    detected_stack = str(run_row.get("project_type_detected", "") or run_row.get("project_type", "") or "").strip()
    has_report = any(str(run_row.get(field, "") or "").strip() for field in ("summary", "suggestion", "prompt_output"))
    has_started_steps = any(str(step.get("status", "") or "").lower() not in {"queued", "pending", ""} for step in step_rows)
    failed_step = next((step for step in step_rows if str(step.get("status", "")).lower() == "failed"), None)
    latest_step = step_rows[-1] if step_rows else None

    ran_tests_status = "pending"
    if failed_step:
        ran_tests_status = "failed"
    elif run_status == "running" or any(str(step.get("status", "")).lower() == "running" for step in step_rows):
        ran_tests_status = "running"
    elif step_rows and all(str(step.get("status", "")).lower() in {"passed", "skipped", "unavailable"} for step in step_rows):
        ran_tests_status = "done"
    elif has_started_steps:
        ran_tests_status = "running"

    generated_report_status = "pending"
    if run_status == "running" and has_report:
        generated_report_status = "running"
    elif run_status in {"passed", "failed"} and has_report:
        generated_report_status = "done"

    extracted_status = "done" if has_workdir else ("running" if run_status == "running" else "pending")
    detected_status = "done" if detected_stack else ("running" if extracted_status in {"done", "running"} and run_status == "running" else "pending")
    failed_reason_status = "failed" if run_status == "failed" else ("skipped" if run_status == "passed" else "pending")

    failed_message = None
    if failed_step:
        failed_message = str(
            failed_step.get("stderr_summary")
            or failed_step.get("output")
            or run_row.get("failed_reason")
            or run_row.get("summary")
            or "AutoTest run failed."
        )
    elif run_status == "failed":
        failed_message = str(run_row.get("failed_reason") or run_row.get("summary") or "AutoTest run failed.")

    def build_item(
        key: str,
        label: str,
        *,
        status: str,
        started_at: str | None = None,
        finished_at: str | None = None,
        message: str | None = None,
    ) -> AutoTestTimelineItemResponse:
        return AutoTestTimelineItemResponse(
            key=key,
            label=label,
            name=label,
            status=_normalize_timeline_status(status),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=_duration_ms(started_at, finished_at),
            message=message,
        )

    items = {
        "uploaded": build_item(
            "uploaded",
            "Uploaded",
            status="success",
            started_at=created_at,
            finished_at=created_at,
            message=str(run_row.get("source_ref", "") or "") or None,
        ),
        "extracted": build_item(
            "extracted",
            "Extracted",
            status=extracted_status,
            started_at=created_at if has_workdir else None,
            finished_at=created_at if has_workdir else None,
            message=str(run_row.get("working_directory", "") or "") or None,
        ),
        "detected_stack": build_item(
            "detected_stack",
            "Detected stack",
            status=detected_status,
            started_at=created_at if detected_stack else None,
            finished_at=created_at if detected_stack else None,
            message=detected_stack or None,
        ),
        "prepared_environment": build_item(
            "prepared_environment",
            "Installed dependencies / Prepared environment",
            status="success" if step_rows else ("running" if run_status == "running" else "pending"),
            started_at=str((step_rows[0] if step_rows else {}).get("started_at", "") or "") or None,
            finished_at=str((step_rows[0] if step_rows else {}).get("finished_at", "") or "") or None,
            message=str((step_rows[0] if step_rows else {}).get("name", "") or "") or None,
        ),
        "ran_tests": build_item(
            "ran_tests",
            "Ran tests",
            status=ran_tests_status,
            started_at=str((step_rows[0] if step_rows else {}).get("started_at", "") or "") or None,
            finished_at=str((failed_step or latest_step or {}).get("finished_at") or (latest_step or {}).get("started_at") or "") or None,
            message=str((failed_step or latest_step or {}).get("name", "") or "") or None,
        ),
        "generated_report": build_item(
            "generated_report",
            "Generated report",
            status=generated_report_status,
            started_at=created_at if has_report else None,
            finished_at=created_at if has_report else None,
            message=str(run_row.get("summary", "") or "") or None,
        ),
        "failed_reason": build_item(
            "failed_reason",
            "Failed reason",
            status=failed_reason_status,
            started_at=str((failed_step or {}).get("finished_at", "") or "") or created_at if run_status == "failed" else None,
            finished_at=str((failed_step or {}).get("finished_at", "") or "") or created_at if run_status == "failed" else None,
            message=failed_message,
        ),
    }
    return [items[key] for key, _label in TIMELINE_LABELS]


def serialize_autotest_run(run_row: dict, step_rows: list[dict]) -> AutoTestRunResponse:
    return AutoTestRunResponse(
        id=run_row.get("run_id", ""),
        source_type=run_row.get("source_type", ""),
        source_ref=run_row.get("source_ref", ""),
        execution_mode=run_row.get("execution_mode", "real") or "real",
        project_type_detected=run_row.get("project_type_detected", "") or run_row.get("project_type", "") or "",
        working_directory=run_row.get("working_directory", "") or "",
        project_name=run_row.get("project_name", "") or run_row.get("source_ref", ""),
        project_type=run_row.get("project_type", ""),
        status=run_row.get("status", ""),
        summary=run_row.get("summary", ""),
        suggestion=run_row.get("suggestion", ""),
        prompt_output=run_row.get("prompt_output", ""),
        failed_reason=run_row.get("failed_reason", "") or "",
        problem_entry_id=run_row.get("problem_entry_id", "") or "",
        solution_entry_id=run_row.get("solution_entry_id", "") or "",
        created_at=run_row.get("created_at", ""),
        steps=[serialize_autotest_step(step) for step in step_rows if str(step.get("name", "")) not in TIMELINE_KEYS],
        timeline=build_autotest_timeline(run_row, step_rows),
    )


def _safe_autotest_index_entry(*, run_id: str, item_kind: str, item_id: str, entry: dict | None, indexer) -> bool:
    if not entry:
        return False
    try:
        result = indexer(entry)
    except Exception as exc:
        logger.warning(
            "AutoTest run %s saved %s %s but indexing failed: %s",
            run_id,
            item_kind,
            item_id,
            exc,
        )
        return False
    if result is False:
        logger.warning(
            "AutoTest run %s saved %s %s but indexing returned failure without an exception",
            run_id,
            item_kind,
            item_id,
        )
        return False
    return True


def validate_github_url(repo_url: str) -> bool:
    try:
        parsed = urlparse(str(repo_url or "").strip())
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return False
    if parsed.params or parsed.query or parsed.fragment:
        return False
    cleaned_path = parsed.path.strip("/")
    parts = [part for part in cleaned_path.split("/") if part]
    if len(parts) != 2:
        return False
    owner, repo = parts
    if not owner or not repo:
        return False
    if any(token in repo_url for token in (";", "\\", "..", "%00")):
        return False
    repo_name = repo.removesuffix(".git")
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    return set(owner) <= allowed_chars and set(repo_name) <= allowed_chars and bool(repo_name)


def get_repo_info(repo_url: str) -> dict[str, object]:
    if not validate_github_url(repo_url):
        raise ValueError("Invalid GitHub URL.")
    parsed = urlparse(repo_url.strip())
    owner, repo = [part for part in parsed.path.strip("/").split("/") if part]
    normalized_repo = repo.removesuffix(".git")
    normalized_url = f"https://github.com/{owner}/{normalized_repo}"
    return {
        "owner": owner,
        "repo": normalized_repo,
        "url": normalized_url,
        "default_branch": "",
        "provider": "github",
        "clone_supported": False,
    }


def safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        logger.warning("Could not delete file %s because it is locked by the OS.", path)


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    max_files = int(settings.AUTOTEST_MAX_FILES)
    max_unzipped_bytes = int(settings.AUTOTEST_MAX_UNZIPPED_BYTES)
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) > max_files:
            raise ValueError("Zip contains too many files.")
        total_bytes = 0
        for member in members:
            if member.is_dir():
                continue
            total_bytes += int(getattr(member, "file_size", 0) or 0)
            if total_bytes > max_unzipped_bytes:
                raise ValueError("Zip expands beyond allowed size.")
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("Zip contains unsafe paths.")
            if ":" in member_path.parts[0] or str(member.filename).startswith(("\\\\", "//")):
                raise ValueError("Zip contains unsafe paths.")
            is_symlink = (member.external_attr >> 16) & 0o170000 == 0o120000
            if is_symlink:
                raise ValueError("Zip contains symlinks, which are not allowed.")
        archive.extractall(dest_dir)


def _walk_dirs_for_markers(base_dir: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", "dist", "build", ".venv", "venv", ".mypy_cache"}
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


def _safe_download_filename(value: str) -> str:
    name = str(value or "").replace("\r", "").replace("\n", "").strip()
    if not name:
        return "file"
    return name.replace('"', "'")


def _run_command(*, argv: list[str], cwd: Path, timeout_seconds: int) -> tuple[int, str, str]:
    if not argv:
        raise ValueError("Missing command argv.")
    env = os.environ.copy()
    if current_autotest_execution_mode() == "real":
        sensitive_tokens = ("TOKEN", "KEY", "SECRET", "PASSWORD", "DATABASE_URL")
        for key in list(env):
            normalized = key.upper()
            if any(token in normalized for token in sensitive_tokens):
                env.pop(key, None)
    env.setdefault("CI", "true")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    preexec_fn = None
    if os.name == "posix":
        try:
            import resource

            cpu_limit = int(settings.AUTOTEST_RLIMIT_CPU_SECONDS)
            as_limit_mb = int(settings.AUTOTEST_RLIMIT_AS_MB)
            fsize_mb = int(settings.AUTOTEST_RLIMIT_FSIZE_MB)

            def _apply_limits():
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
                resource.setrlimit(resource.RLIMIT_AS, (as_limit_mb * 1024 * 1024, as_limit_mb * 1024 * 1024))
                resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_mb * 1024 * 1024, fsize_mb * 1024 * 1024))

            preexec_fn = _apply_limits
        except Exception as exc:
            logger.warning("AutoTest resource limits unavailable: %s", exc)
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=env,
        preexec_fn=preexec_fn,
    )
    return int(completed.returncode), clamp_output(completed.stdout or ""), clamp_output(completed.stderr or "")


async def suggest_fix_from_autotest(*, project_type: str, failed_step: str, command: str, output: str) -> str:
    provider, _status = get_llm_provider()
    prompt = (
        "AutoTest failure analysis.\n\n"
        f"Project type: {project_type}\n"
        f"Failed step: {failed_step}\n"
        f"Command: {command}\n\n"
        "Output (stdout+stderr):\n"
        f"{output[:6000]}\n\n"
        "Write:\n"
        "- Error summary (1-3 sentences)\n"
        "- Likely root causes (bullets)\n"
        "- Fix plan (numbered steps)\n"
        "- Verification steps (bullets)\n"
        "- Suggested tags (comma-separated)\n"
    )
    try:
        response = await provider.generate(system=AUTOTEST_SUGGEST_SYSTEM_PROMPT, prompt=prompt, temperature=0.2)
        text = (response.text or "").strip()
        if text:
            return text
    except Exception as exc:
        logger.warning("AutoTest suggestion unavailable; using fallback: %s", exc)
    return (
        "Error summary:\n"
        f"- AutoTest failed at '{failed_step}'.\n\n"
        "Fix plan:\n"
        "- Re-run the failed command locally and capture full logs.\n"
        "- Check dependency install/build/test configuration for the project type.\n"
        "- Apply a minimal fix and re-run AutoTest.\n\n"
        "Verification steps:\n"
        "- Re-run AutoTest and confirm all steps pass.\n\n"
        "Suggested tags:\n"
        "autotest,build,test,lint\n"
    )


async def run_autotest(file: UploadFile, current_user: dict) -> AutoTestRunResponse:
    user_id = current_user["sub"]
    if is_real_autotest_requested() and not is_real_autotest_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "AutoTest real mode is disabled. Set KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=1 "
                "and run inside an isolated sandbox/container before executing uploaded projects."
            ),
        )
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    if Path(file.filename).suffix.lower() != ".zip":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AutoTest only accepts .zip uploads.")

    autotest_dir = settings.AUTOTEST_DIR
    autotest_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = generate_safe_filename(file.filename)
    zip_path = autotest_dir / safe_filename
    file_size = await stream_write_file(file, zip_path)
    if file_size <= 0:
        safe_unlink(zip_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded zip is empty.")

    run_id = str(uuid.uuid4())
    created_at = utc_now_iso()
    source_ref = file.filename
    timeline = initial_autotest_timeline(source_ref=source_ref, created_at=created_at)
    execution_mode = current_autotest_execution_mode()
    project_name = Path(file.filename).stem or "uploaded-project"

    created = autotest_repository.create_run(
        run_id=run_id,
        source_type="zip_upload",
        source_ref=source_ref,
        execution_mode=execution_mode,
        project_type_detected="",
        working_directory="",
        project_name=project_name,
        project_type="zip",
        status="queued",
        summary="AutoTest queued.",
        suggestion="",
        prompt_output="",
        failed_reason="",
        timeline_json=json.dumps(timeline, ensure_ascii=True),
        created_by=user_id,
    )
    if not created:
        safe_unlink(zip_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create AutoTest run.")

    work_dir = autotest_dir / f"autotest-{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir = work_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    step_ids = {name: str(uuid.uuid4()) for name in ("install", "build", "test", "lint")}
    timeout_seconds = int(settings.AUTOTEST_TIMEOUT_SECONDS)
    commands_by_step: dict[str, str] = {}
    outputs: dict[str, str] = {}
    failed_step_name = ""
    failed_reason = ""

    for name in ("install", "build", "test", "lint"):
        autotest_repository.create_step(
            step_id=step_ids[name],
            run_id=run_id,
            name=name,
            command="",
            status="queued",
            started_at="",
            finished_at="",
            output="",
            success=0,
            exit_code=0,
            stdout_summary="",
            stderr_summary="",
            error_type="",
        )

    def refresh_run() -> tuple[dict, list[dict]]:
        run_row = autotest_repository.get_run(run_id=run_id, created_by=user_id)
        if not run_row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Autotest run missing after creation.")
        return run_row, autotest_repository.list_steps(run_id)

    def mark_unfinished_command_steps(*, current_failed_step: str = "") -> None:
        for step in autotest_repository.list_steps(run_id):
            status_value = str(step.get("status", "") or "").lower()
            if status_value in {"passed", "failed", "skipped", "unavailable"}:
                continue
            next_status = "failed" if current_failed_step and str(step.get("name", "")) == current_failed_step else "skipped"
            autotest_repository.update_step(
                str(step.get("step_id", "")),
                status=next_status,
                finished_at=utc_now_iso(),
                output=str(step.get("output", "") or ""),
                success=0 if next_status == "failed" else 1,
                exit_code=1 if next_status == "failed" else 0,
                stdout_summary=str(step.get("stdout_summary", "") or ""),
                stderr_summary=str(step.get("stderr_summary", "") or ""),
                error_type="failed_before_completion" if next_status == "failed" else "skipped_after_failure",
            )

    try:
        autotest_repository.update_run(run_id, status="running", summary="Extracting uploaded ZIP archive.")
        extract_started_at = utc_now_iso()
        timeline = set_timeline_item(timeline, "extracted", status="running", started_at=extract_started_at, message="extracting")
        save_run_timeline(run_id, timeline)
        safe_extract_zip(zip_path, extracted_dir)
        extract_finished_at = utc_now_iso()
        timeline = set_timeline_item(timeline, "extracted", status="success", finished_at=extract_finished_at, message="extracted")
        save_run_timeline(run_id, timeline)

        timeline = set_timeline_item(timeline, "detected_stack", status="running", started_at=utc_now_iso())
        save_run_timeline(run_id, timeline)
        project_type_detected, working_dir = find_project_root_on_disk(extracted_dir)
        working_dir_rel = sanitize_path_for_report(working_dir, base_dir=extracted_dir)
        project_name = working_dir.name or project_name
        autotest_repository.update_run(
            run_id,
            project_type_detected=project_type_detected,
            working_directory=working_dir_rel,
            project_name=project_name,
            project_type=project_type_detected,
            summary=f"Detected {project_type_detected or 'unknown'} project.",
        )
        timeline = set_timeline_item(
            timeline,
            "detected_stack",
            status="success",
            finished_at=utc_now_iso(),
            message=project_type_detected or "unknown",
        )
        save_run_timeline(run_id, timeline)

        commands = autotest_commands(project_type_detected)
        overall_ok = True
        fail_step_marker = (working_dir / ".autotest_fail_step")
        fail_step = fail_step_marker.read_text(encoding="utf-8").strip() if fail_step_marker.exists() else ""

        skipped_steps: list[str] = []
        ran_tests_started_at: str | None = None

        for name, argv in commands.items():
            step_id = step_ids[name]
            command = " ".join(argv)
            commands_by_step[name] = command
            autotest_repository.update_step(step_id, command=command)

            ok = True
            exit_code = 0
            error_type = ""
            output_text = ""
            stdout = ""
            stderr = ""

            if ran_tests_started_at is None:
                ran_tests_started_at = utc_now_iso()
                timeline = set_timeline_item(timeline, "ran_tests", status="running", started_at=ran_tests_started_at)
                save_run_timeline(run_id, timeline)

            if fail_step and fail_step == name:
                started_at = utc_now_iso()
                autotest_repository.update_step(step_id, status="running", started_at=started_at)
                ok = False
                exit_code = 1
                error_type = "simulated_failure"
                output_text = (
                    f"[{name}] command: {command}\n"
                    f"[{name}] project_type_detected: {project_type_detected}\n"
                    f"[{name}] execution_mode: simulated\n"
                    f"[{name}] working_directory: {working_dir_rel}\n"
                    f"[{name}] simulated: FAILED\n"
                    f"Simulated failure requested by zip marker: {fail_step}\n"
                )
            elif execution_mode == "real" and project_type_detected in {"node", "python"}:
                should_run, skip_reason = autotest_step_should_run(
                    project_type=project_type_detected,
                    working_dir=working_dir,
                    step_name=name,
                )
                if not should_run:
                    skipped_steps.append(name)
                    started_at = utc_now_iso()
                    output_text = (
                        f"[{name}] command: {command}\n"
                        f"[{name}] project_type_detected: {project_type_detected}\n"
                        f"[{name}] execution_mode: real\n"
                        f"[{name}] working_directory: {working_dir_rel}\n"
                        f"[{name}] skipped: yes\n"
                        f"Reason: {skip_reason}\n"
                    ).strip()
                    outputs[name] = output_text
                    autotest_repository.update_step(
                        step_id,
                        status="skipped",
                        started_at=started_at,
                        finished_at=started_at,
                        output=output_text,
                        success=1,
                        exit_code=0,
                        stdout_summary="",
                        stderr_summary="",
                        error_type="skipped",
                    )
                    continue

                started_at = utc_now_iso()
                autotest_repository.update_step(step_id, status="running", started_at=started_at)
                try:
                    exit_code, stdout, stderr = _run_command(argv=argv, cwd=working_dir, timeout_seconds=timeout_seconds)
                    ok = exit_code == 0
                except subprocess.TimeoutExpired:
                    ok = False
                    exit_code = 124
                    error_type = "timeout"
                    output_text = f"[{name}] command timed out after {timeout_seconds}s: {command}"
                except FileNotFoundError:
                    ok = False
                    exit_code = 127
                    error_type = "command_not_found"
                    output_text = f"[{name}] command not found: {command}"
                except Exception as exc:
                    ok = False
                    exit_code = 1
                    error_type = "exception"
                    output_text = f"[{name}] exception while running command: {exc}"
            else:
                started_at = utc_now_iso()
                autotest_repository.update_step(step_id, status="running", started_at=started_at)
                output_text = (
                    f"[{name}] command: {command}\n"
                    f"[{name}] project_type_detected: {project_type_detected}\n"
                    f"[{name}] execution_mode: simulated\n"
                    f"[{name}] working_directory: {working_dir_rel}\n"
                    f"[{name}] simulated: ok\n"
                )

            if stdout or stderr:
                output_text = (
                    f"[{name}] command: {command}\n"
                    f"[{name}] project_type_detected: {project_type_detected}\n"
                    f"[{name}] execution_mode: real\n"
                    f"[{name}] working_directory: {working_dir_rel}\n\n"
                    "STDOUT:\n"
                    f"{stdout.strip()}\n\n"
                    "STDERR:\n"
                    f"{stderr.strip()}\n"
                ).strip()

            finished_at = utc_now_iso()
            output_text = clamp_output(output_text)
            outputs[name] = output_text
            step_status = "passed" if ok else "failed"
            if error_type == "command_not_found":
                step_status = "unavailable"
            autotest_repository.update_step(
                step_id,
                status=step_status,
                finished_at=finished_at,
                output=output_text,
                success=1 if ok else 0,
                exit_code=exit_code,
                stdout_summary=(stdout or "")[-800:],
                stderr_summary=(stderr or "")[-800:],
                error_type=error_type,
            )

            if not ok:
                overall_ok = False
                failed_step_name = name
                failed_reason = output_text or f"AutoTest {name} step failed."
                timeline = set_timeline_item(
                    timeline,
                    "prepared_environment",
                    status="failed" if name == "install" else "success",
                    finished_at=finished_at,
                    message=name,
                )
                timeline = set_timeline_item(
                    timeline,
                    "ran_tests",
                    status="failed",
                    finished_at=finished_at,
                    message=name,
                )
                save_run_timeline(run_id, timeline)
                break

            if name == "install":
                timeline = set_timeline_item(
                    timeline,
                    "prepared_environment",
                    status="success",
                    finished_at=finished_at,
                    message=name,
                )
                save_run_timeline(run_id, timeline)

        if overall_ok:
            timeline = set_timeline_item(timeline, "generated_report", status="running", started_at=utc_now_iso())
            save_run_timeline(run_id, timeline)
            skipped_suffix = f"; skipped: {', '.join(skipped_steps)}" if skipped_steps else ""
            summary = f"Acceptance pipeline passed ({project_type_detected}){skipped_suffix}."
            prompt_output = (
                "AutoTest passed.\n\n"
                f"Project: {project_name}\n"
                "Steps: install, build, test, lint\n"
            )
            if skipped_steps:
                prompt_output += f"Skipped: {', '.join(skipped_steps)}\n"
            prompt_output += "Next: capture any useful learnings into a Knowledge entry."
            autotest_repository.update_run(
                run_id,
                status="passed",
                summary=summary,
                prompt_output=prompt_output,
                failed_reason="",
            )

            knowledge_id = str(uuid.uuid4())
            candidate_ok = db.add_knowledge_entry(
                entry_id=knowledge_id,
                title=f"AutoTest Passed: {project_name}",
                status="draft",
                problem=summary,
                root_cause="",
                solution=prompt_output,
                tags="autotest,acceptance",
                notes=f"source=autotest\nrun_id={run_id}",
                created_by=user_id,
                source_type="autotest-derived",
                source_ref=f"autotest_run:{run_id}",
            )
            if candidate_ok:
                autotest_repository.update_run(run_id, solution_entry_id=knowledge_id)
                db.add_link(f"autotest_run:{run_id}", f"knowledge:{knowledge_id}", link_type="produced")
                db.add_link(f"knowledge:{knowledge_id}", f"autotest_run:{run_id}", link_type="derived_from")
                entry = db.get_knowledge_entry(knowledge_id)
                if entry:
                    _safe_autotest_index_entry(
                        run_id=run_id,
                        item_kind="knowledge",
                        item_id=knowledge_id,
                        entry=entry,
                        indexer=index_knowledge_entry,
                    )
            timeline = set_timeline_item(
                timeline,
                "ran_tests",
                status="success",
                finished_at=utc_now_iso(),
                message="install/build/test/lint completed",
            )
            timeline = set_timeline_item(
                timeline,
                "generated_report",
                status="success",
                finished_at=utc_now_iso(),
                message=summary,
            )
            timeline = set_timeline_item(timeline, "failed_reason", status="skipped", clear_message=True)
            save_run_timeline(run_id, timeline)
        else:
            failed_step = failed_step_name or "unknown"
            summary = f"Acceptance pipeline failed at step '{failed_step}' ({project_type_detected})."
            failed_output = outputs.get(failed_step, "")
            timeline = set_timeline_item(timeline, "generated_report", status="running", started_at=utc_now_iso())
            save_run_timeline(run_id, timeline)
            suggestion = await suggest_fix_from_autotest(
                project_type=project_type_detected,
                failed_step=failed_step,
                command=commands_by_step.get(failed_step, ""),
                output=failed_output,
            )
            prompt_output = (
                "AutoTest failed.\n\n"
                f"Project: {project_name}\n"
                f"Failed step: {failed_step}\n\n"
                "Failure output:\n"
                f"{failed_output}\n\n"
                "Please fix the failure, then re-run AutoTest."
            )
            failed_reason = failed_output or summary
            autotest_repository.update_run(
                run_id,
                status="failed",
                summary=summary,
                prompt_output=prompt_output,
                suggestion=suggestion,
                failed_reason=failed_reason,
            )

            logbook_id = str(uuid.uuid4())
            created_problem = db.add_logbook_entry(
                entry_id=logbook_id,
                title=f"AutoTest Failed: {project_name}",
                status="draft",
                run_id=run_id,
                problem=prompt_output,
                root_cause="",
                solution=suggestion,
                tags="autotest,acceptance",
                source_type="autotest-derived",
                created_by=user_id,
                source_ref=f"autotest_run:{run_id}",
            )
            if created_problem:
                autotest_repository.update_run(run_id, problem_entry_id=logbook_id)
                db.add_link(f"autotest_run:{run_id}", f"logbook:{logbook_id}", link_type="produced")
                db.add_link(f"logbook:{logbook_id}", f"autotest_run:{run_id}", link_type="derived_from")
                entry = db.get_logbook_entry(logbook_id)
                if entry:
                    _safe_autotest_index_entry(
                        run_id=run_id,
                        item_kind="logbook",
                        item_id=logbook_id,
                        entry=entry,
                        indexer=index_logbook_entry,
                    )
            timeline = set_timeline_item(
                timeline,
                "generated_report",
                status="success",
                finished_at=utc_now_iso(),
                message=summary,
            )
            timeline = finalize_autotest_timeline_failure(
                timeline=timeline,
                failed_phase="ran_tests",
                failed_reason=failed_reason,
            )
            save_run_timeline(run_id, timeline)
    except Exception as exc:
        failed_reason = str(exc) or "AutoTest run failed unexpectedly."
        logger.exception("AutoTest run %s failed unexpectedly", run_id)
        autotest_repository.update_run(
            run_id,
            status="failed",
            summary=f"AutoTest run failed: {failed_reason}",
            prompt_output="",
            suggestion="",
            failed_reason=failed_reason,
        )
        current_phase = "generated_report" if "report" in failed_reason.lower() else "detected_stack"
        if str(next((item for item in timeline if str(item.get("key")) == "generated_report"), {}).get("status", "")) == "running":
            current_phase = "generated_report"
        elif str(next((item for item in timeline if str(item.get("key")) == "ran_tests"), {}).get("status", "")) == "running":
            current_phase = "ran_tests"
        elif str(next((item for item in timeline if str(item.get("key")) == "prepared_environment"), {}).get("status", "")) == "running":
            current_phase = "prepared_environment"
        elif str(next((item for item in timeline if str(item.get("key")) == "detected_stack"), {}).get("status", "")) == "running":
            current_phase = "detected_stack"
        elif str(next((item for item in timeline if str(item.get("key")) == "extracted"), {}).get("status", "")) == "running":
            current_phase = "extracted"
        timeline = finalize_autotest_timeline_failure(
            timeline=timeline,
            failed_phase=current_phase,
            failed_reason=failed_reason,
        )
        save_run_timeline(run_id, timeline)
        mark_unfinished_command_steps(current_failed_step=failed_step_name)
    finally:
        safe_unlink(zip_path)
        shutil.rmtree(work_dir, ignore_errors=True)

    run_row, step_rows = refresh_run()
    return serialize_autotest_run(run_row, step_rows)


def list_autotest_runs(current_user: dict) -> list[AutoTestRunListItemResponse]:
    user_id = current_user["sub"]
    return [
        AutoTestRunListItemResponse(
            id=row.get("run_id", ""),
            project_name=row.get("project_name", "") or row.get("source_ref", ""),
            status=row.get("status", ""),
            created_at=row.get("created_at", ""),
            summary=row.get("summary", ""),
        )
        for row in autotest_repository.list_runs(created_by=user_id, limit=50)
    ]


def get_autotest_run(run_id: str, current_user: dict) -> AutoTestRunResponse:
    user_id = current_user["sub"]
    run_row = autotest_repository.get_run(run_id=run_id, created_by=user_id)
    if not run_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autotest run not found.")
    step_rows = autotest_repository.list_steps(run_id)
    return serialize_autotest_run(run_row, step_rows)


def export_autotest_report(run_id: str, requested_format: str, current_user: dict) -> Response:
    export_format_value = str(requested_format or "").strip().lower()
    if export_format_value not in {"md", "html"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid export format. Use 'md' or 'html'.")
    export_format: AutoTestExportFormat = export_format_value
    run_row = autotest_repository.get_run(run_id=run_id, created_by=current_user["sub"])
    if not run_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autotest run not found.")
    step_rows = autotest_repository.list_steps(run_id)
    markdown_report = ReportGenerator.generate_markdown(run_row, step_rows)
    filename_base = _safe_download_filename(f"autotest-report-{run_id}")
    if export_format == "md":
        return PlainTextResponse(
            content=markdown_report,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.md"'},
        )
    html_report = ReportGenerator.convert_to_html(markdown_report)
    return HTMLResponse(
        content=html_report,
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.html"'},
    )


def analyze_github_repo(payload: GitHubAnalyzeRequest, current_user: dict) -> GitHubAnalyzeResponse:
    repo_url = str(payload.repo_url or "").strip()
    if not validate_github_url(repo_url):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid GitHub URL. Use https://github.com/{owner}/{repo}.")
    repo_info_data = get_repo_info(repo_url)
    run_id = str(uuid.uuid4())
    summary = "GitHub repository registered for queued analysis. Remote clone and remote test execution are not performed."
    created = autotest_repository.create_run(
        run_id=run_id,
        source_type="github_repo",
        source_ref=str(repo_info_data["url"]),
        execution_mode="simulated",
        project_type_detected="",
        working_directory="",
        project_name=str(repo_info_data["repo"]),
        project_type="github",
        status="queued",
        summary=summary,
        suggestion="",
        prompt_output="",
        failed_reason="",
        timeline_json="",
        created_by=current_user["sub"],
    )
    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create AutoTest run.")
    repo_info = GitHubRepoInfoResponse(**repo_info_data)
    return GitHubAnalyzeResponse(run_id=run_id, status="queued", repo_info=repo_info)
