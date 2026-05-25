from __future__ import annotations

import logging

from app.llm import get_llm_provider

logger = logging.getLogger("knowledge_workspace")
AUTOTEST_SUGGEST_SYSTEM_PROMPT = """You are a local-first engineering assistant.

Rules:
1. Do not invent outputs or versions. Use only the provided AutoTest logs.
2. Prefer actionable, reproducible steps (commands, filenames, config keys).
3. If logs are insufficient, say what extra info is needed.
"""


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


def _safe_download_filename(value: str) -> str:
    name = str(value or "").replace("\r", "").replace("\n", "").strip()
    if not name:
        return "file"
    return name.replace('"', "'")


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
