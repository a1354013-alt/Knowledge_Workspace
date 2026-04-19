from __future__ import annotations

import logging
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional runtime dependency
    PdfReader = None

from app.database import add_to_vector_db, query_kb_vector_db, query_vector_db
from app.llm import get_llm_provider
from app.models import Source


logger = logging.getLogger("enterprise_ai")


def split_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def load_document_text(file_path: str, filename: str) -> list[tuple[str, str]]:
    extension = Path(filename).suffix.lower()
    if extension == '.pdf':
        if PdfReader is None:
            raise RuntimeError('pypdf is not installed.')
        reader = PdfReader(file_path)
        pages: list[tuple[str, str]] = []
        for index, page in enumerate(reader.pages):
            pages.append((str(index + 1), page.extract_text() or ''))
        return pages

    if extension in {'.txt', '.md'}:
        for encoding in ('utf-8', 'utf-8-sig', 'cp950'):
            try:
                text = Path(file_path).read_text(encoding=encoding)
                return [('1', text)]
            except UnicodeDecodeError:
                continue
        raise ValueError('Unable to decode text document.')

    raise ValueError(f'Unsupported file type: {extension}')


def process_file(
    doc_id: str,
    file_path: str,
    filename: str,
    owner_user_id: str,
    status: str = "reviewed",
    is_active: int = 1,
) -> str:
    documents = load_document_text(file_path, filename)
    texts: list[str] = []
    metadatas: list[dict[str, object]] = []

    for page_or_section, content in documents:
        for chunk in split_text(content):
            texts.append(chunk)
            metadatas.append(
                {
                    'doc_id': doc_id,
                    'filename': filename,
                    'page_or_section': page_or_section,
                    'is_active': is_active,
                    'status': status,
                    'owner_user_id': owner_user_id,
                }
            )

    if not texts:
        raise ValueError('No readable content found in document.')

    if not add_to_vector_db(doc_id, texts, metadatas):
        logger.warning('Vector indexing skipped for %s.', doc_id)
    return doc_id


SYSTEM_PROMPT = """You are a local-first engineering assistant.

Rules:
1. Answer only from the provided context.
2. If the context is insufficient, say so clearly.
3. Prefer actionable, reproducible steps (commands, config, filenames).
4. Do not invent facts, versions, or outputs.
"""


async def perform_qa(question: str, user_id: str) -> tuple[str, list[Source]]:
    doc_results = query_vector_db(question, user_id, n_results=4)
    kb_results = query_kb_vector_db(question, user_id, n_results=4)
    results = doc_results + kb_results
    if not results:
        return 'No relevant knowledge was found yet. Try uploading a document or adding a logbook entry.', []

    sources: list[Source] = []
    context_parts: list[str] = []
    for _, chunk_text, metadata in results:
        if "filename" in metadata:
            title = metadata.get("filename", "unknown")
            location = str(metadata.get("page_or_section", ""))
            source_type = "document"
        else:
            title = metadata.get("title", "unknown")
            location = metadata.get("location") or ""
            source_type = metadata.get("item_type", "knowledge")

        sources.append(
            Source(
                source_type=str(source_type),
                title=str(title),
                location=str(location) if location else None,
                snippet=chunk_text[:240],
            )
        )
        context_parts.append(f"[{source_type}:{title} {location}]\n{chunk_text}")

    provider, _status = get_llm_provider()
    try:
        context = "\n\n".join(context_parts)
        response = await provider.generate(
            system=SYSTEM_PROMPT,
            prompt=f"Context:\n{context}\n\nQuestion:\n{question}",
            temperature=0.2,
        )
        if response.text.strip():
            return response.text, sources
    except Exception as exc:
        logger.warning("LLM provider unavailable; falling back to retrieval-only answer: %s", exc)

    joined = "\n\n".join(context_parts[:3]).strip()
    fallback_answer = (
        "LLM provider is unavailable right now, so here are the most relevant context snippets I found:\n\n"
        f"{joined}" if joined else "LLM provider is unavailable right now, and no relevant context was found."
    )
    return fallback_answer, sources


FORM_TEMPLATES = {
    "bug_report": {
        "fields": ["title", "environment", "expected", "actual", "repro_steps", "logs", "impact"],
        "template": (
            "# Bug Report: {title}\n\n"
            "## Environment\n{environment}\n\n"
            "## Expected\n{expected}\n\n"
            "## Actual\n{actual}\n\n"
            "## Repro steps\n{repro_steps}\n\n"
            "## Logs / Screenshots\n{logs}\n\n"
            "## Impact\n{impact}\n"
        ),
    },
    "troubleshooting_note": {
        "fields": ["symptom", "root_cause", "fix", "verification", "prevention", "refs"],
        "template": (
            "# Troubleshooting Note\n\n"
            "## Symptom\n{symptom}\n\n"
            "## Root cause\n{root_cause}\n\n"
            "## Fix (steps)\n{fix}\n\n"
            "## Verification\n{verification}\n\n"
            "## Prevention / follow-ups\n{prevention}\n\n"
            "## References\n{refs}\n"
        ),
    },
    "pr_description": {
        "fields": ["summary", "why", "what_changed", "testing", "risk", "rollback"],
        "template": (
            "# PR Summary\n{summary}\n\n"
            "## Why\n{why}\n\n"
            "## What changed\n{what_changed}\n\n"
            "## Testing\n{testing}\n\n"
            "## Risk\n{risk}\n\n"
            "## Rollback plan\n{rollback}\n"
        ),
    },
    "postmortem": {
        "fields": ["incident", "timeline", "root_cause", "impact", "detection", "resolution", "action_items"],
        "template": (
            "# Postmortem\n\n"
            "## Incident\n{incident}\n\n"
            "## Timeline\n{timeline}\n\n"
            "## Root cause\n{root_cause}\n\n"
            "## Impact\n{impact}\n\n"
            "## Detection\n{detection}\n\n"
            "## Resolution\n{resolution}\n\n"
            "## Action items\n{action_items}\n"
        ),
    },
}


async def generate_form(template_type: str, inputs: dict[str, str], user_id: str) -> str:
    _ = user_id
    template = FORM_TEMPLATES.get(template_type)
    if not template:
        raise ValueError(f'Unsupported template type: {template_type}')
    try:
        return template['template'].format(**inputs)
    except KeyError as exc:
        raise ValueError(f'Missing template field: {exc.args[0]}') from exc
