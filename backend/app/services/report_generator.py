from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

import markdown


def _safe_text(value: Any) -> str:
    return escape(str(value or ""), quote=False)


def _safe_inline(value: Any, fallback: str = "N/A") -> str:
    text = str(value or "").strip()
    return _safe_text(text or fallback)


def _safe_code_block(value: Any, fallback: str = "No details available.") -> str:
    text = str(value or "").strip()
    return _safe_text(text or fallback)


def _duration_text(step: dict[str, Any]) -> str:
    started = step.get("started_at")
    finished = step.get("finished_at")
    if not started or not finished:
        return "N/A"
    try:
        start_dt = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(str(finished).replace("Z", "+00:00"))
    except ValueError:
        return "N/A"
    return f"{(end_dt - start_dt).total_seconds():.2f}s"


class ReportGenerator:
    @staticmethod
    def generate_markdown(run_data: dict[str, Any], steps_data: list[dict[str, Any]]) -> str:
        project_name = _safe_inline(run_data.get("project_name"), "Unknown Project")
        repo_name = _safe_inline(run_data.get("source_ref"))
        scan_time = _safe_inline(run_data.get("created_at"))
        report_time = _safe_inline(datetime.now().isoformat())
        project_type = _safe_inline(run_data.get("project_type_detected") or run_data.get("project_type"), "Unknown")
        execution_mode = _safe_inline(run_data.get("execution_mode"))
        working_directory = _safe_inline(run_data.get("working_directory"))

        lines = [
            "# Project AutoTest Report",
            "",
            "## 1. Project Information",
            "",
            f"- **Project Name**: {project_name}",
            f"- **Repo Name**: {repo_name}",
            f"- **Scan Time**: {scan_time}",
            f"- **Report Generated Time**: {report_time}",
            "",
            "## 2. Detected Tech Stack",
            "",
            f"- **Language/Framework**: {project_type}",
            f"- **Execution Mode**: {execution_mode}",
            f"- **Working Directory**: {working_directory}",
            "",
            "## 3. Execution Results",
            "",
            "| Step | Status | Exit Code | Duration |",
            "|------|--------|-----------|----------|",
        ]

        failed_steps: list[dict[str, Any]] = []
        for step in steps_data:
            name = _safe_inline(step.get("name"))
            status = _safe_inline(step.get("status"))
            exit_code = _safe_inline(step.get("exit_code"))
            lines.append(f"| {name} | {status} | {exit_code} | {_duration_text(step)} |")
            if str(step.get("status", "")).lower() == "failed":
                failed_steps.append(step)
        lines.append("")

        if failed_steps:
            lines.extend(["## 4. Failed Steps Summary", ""])
            for step in failed_steps:
                lines.extend(
                    [
                        f"### Step: {_safe_inline(step.get('name'))}",
                        "- **Status**: Failed",
                        f"- **Category**: {_safe_inline(step.get('error_type'), 'unknown')}",
                        "- **Error Message**:",
                        "```text",
                        _safe_code_block(step.get("stderr_summary") or step.get("output"), "No error message"),
                        "```",
                        "",
                    ]
                )

        summary = _safe_inline(run_data.get("summary"), "No summary available")
        lines.extend(["## 5. Error Summary", "", f"**Summary**: {summary}", "", "## 6. AI Suggestions", ""])

        suggestion = str(run_data.get("suggestion") or "").strip()
        if suggestion:
            lines.extend(["### Fix Suggestion", _safe_text(suggestion), ""])
        else:
            lines.extend(["No specific AI suggestions available.", ""])

        prompt_output = str(run_data.get("prompt_output") or "").strip()
        if prompt_output:
            prompt_text = _safe_code_block(prompt_output)
        else:
            fallback_prompt = f"Fix failing {project_type.lower()} project build."
            if failed_steps:
                failed_step_name = _safe_inline(failed_steps[0].get("name"), "unknown")
                fallback_prompt = f"Fix failing {failed_step_name} step in {project_type.lower()} project."
            prompt_text = _safe_code_block(fallback_prompt)
        lines.extend(["## 7. Codex / Copilot Prompt", "", "```text", prompt_text, "```", ""])

        return "\n".join(lines)

    @staticmethod
    def convert_to_html(markdown_content: str) -> str:
        html_body = markdown.markdown(markdown_content, extensions=["tables", "fenced_code"], output_format="html5")
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoTest Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; color: #1f2933; max-width: 880px; margin: 0 auto; padding: 24px; background: #f8fafc; }}
    main {{ background: #fff; border: 1px solid #d9e2ec; border-radius: 16px; padding: 24px; }}
    h1, h2, h3 {{ color: #102a43; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background-color: #f0f4f8; }}
    pre {{ background-color: #f0f4f8; padding: 1rem; border-radius: 0.75rem; overflow-x: auto; border: 1px solid #d9e2ec; white-space: pre-wrap; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.92em; }}
  </style>
</head>
<body>
  <main>
    {html_body}
  </main>
</body>
</html>
"""
