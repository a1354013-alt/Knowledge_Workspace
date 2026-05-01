import markdown
from datetime import datetime
from typing import Any, Dict, List
import os

class ReportGenerator:
    @staticmethod
    def generate_markdown(run_data: Dict[str, Any], steps_data: List[Dict[str, Any]]) -> str:
        project_name = run_data.get("project_name", "Unknown Project")
        repo_name = run_data.get("source_ref", "N/A")
        scan_time = run_data.get("created_at", "N/A")
        report_time = datetime.now().isoformat()
        
        # 1. Project Information
        md = f"# Project AutoTest Report\n\n"
        md += f"## 1. Project Information\n\n"
        md += f"- **Project Name**: {project_name}\n"
        md += f"- **Repo Name**: {repo_name}\n"
        md += f"- **Scan Time**: {scan_time}\n"
        md += f"- **Report Generated Time**: {report_time}\n\n"
        
        # 2. Detected Tech Stack
        project_type = run_data.get("project_type_detected") or run_data.get("project_type", "Unknown")
        md += f"## 2. Detected Tech Stack\n\n"
        md += f"- **Language/Framework**: {project_type.capitalize()}\n"
        md += f"- **Execution Mode**: {run_data.get('execution_mode', 'N/A')}\n"
        md += f"- **Working Directory**: {run_data.get('working_directory', 'N/A')}\n\n"
        
        # 3. Execution Results
        md += f"## 3. Execution Results\n\n"
        md += "| Step | Status | Exit Code | Duration |\n"
        md += "|------|--------|-----------|----------|\n"
        
        failed_steps = []
        for step in steps_data:
            name = step.get("name", "N/A")
            status = step.get("status", "N/A")
            exit_code = step.get("exit_code", "N/A")
            
            # Duration calculation
            started = step.get("started_at")
            finished = step.get("finished_at")
            duration = "N/A"
            if started and finished:
                try:
                    start_dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(finished.replace('Z', '+00:00'))
                    duration = f"{(end_dt - start_dt).total_seconds():.2f}s"
                except Exception:
                    pass
            
            md += f"| {name} | {status} | {exit_code} | {duration} |\n"
            
            if status == "failed":
                failed_steps.append(step)
        md += "\n"
        
        # 4. Failed Steps Summary
        if failed_steps:
            md += f"## 4. Failed Steps Summary\n\n"
            for step in failed_steps:
                error_msg = step.get("stderr_summary") or step.get("output", "No error message")
                error_type = step.get("error_type", "unknown")
                md += f"### Step: {step.get('name')}\n"
                md += f"- **Status**: Failed\n"
                md += f"- **Category**: {error_type}\n"
                md += f"- **Error Message**:\n```\n{error_msg}\n```\n\n"
        
        # 5. Error Summary
        md += f"## 5. Error Summary\n\n"
        summary = run_data.get("summary", "No summary available")
        md += f"**Summary**: {summary}\n\n"
        
        # 6. AI Suggestions
        md += f"## 6. AI Suggestions\n\n"
        suggestion = run_data.get("suggestion")
        if suggestion:
            md += f"### Fix Suggestion\n{suggestion}\n\n"
        else:
            md += "No specific AI suggestions available.\n\n"
            
        # 7. Codex / Copilot Prompt
        md += f"## 7. Codex / Copilot Prompt\n\n"
        prompt_output = run_data.get("prompt_output")
        if prompt_output:
            md += "```\n" + prompt_output + "\n```\n"
        else:
            # Fallback prompt generation
            fallback_prompt = f"Fix failing {project_type} project build."
            if failed_steps:
                fallback_prompt = f"Fix failing {failed_steps[0].get('name')} step in {project_type} project."
            md += "```\n" + fallback_prompt + "\n```\n"
            
        return md

    @staticmethod
    def convert_to_html(markdown_content: str) -> str:
        html_body = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AutoTest Report</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1, h2, h3 {{ color: #1a202c; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
                th, td {{ border: 1px solid #e2e8f0; padding: 8px; text-align: left; }}
                th {{ background-color: #f7fafc; }}
                pre {{ background-color: #f7fafc; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; border: 1px solid #e2e8f0; }}
                code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.9em; }}
                .badge {{ padding: 2px 8px; border-radius: 999px; font-size: 0.8em; font-weight: bold; }}
            </style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """
        return full_html

    @staticmethod
    def convert_to_pdf(html_content: str, output_path: str):
        # Using weasyprint if available, otherwise fallback or error
        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(output_path)
            return True
        except ImportError:
            # If weasyprint is not available, we might need to install it or use another tool
            # For this sandbox, we'll try to use manus-md-to-pdf utility if we can save to file
            return False
