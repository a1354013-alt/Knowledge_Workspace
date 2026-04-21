from __future__ import annotations

import logging
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional runtime dependency
    PdfReader = None

from app.database import DocumentDatabase, add_to_vector_db, query_kb_vector_db, query_vector_db
from app.llm import get_llm_provider
from app.models import Source
from app.text_files import read_text_file

logger = logging.getLogger("knowledge_workspace")


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
        try:
            text, _encoding = read_text_file(file_path)
        except ValueError as exc:
            raise ValueError("Unable to decode text document.") from exc
        return [('1', text)]

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


def _fallback_sources_from_db(*, db: DocumentDatabase, question: str, user_id: str, limit: int = 5) -> list[Source]:
    keyword = str(question or "").strip()
    if not keyword:
        return []

    hits = db.search_items(user_id=user_id, keyword=keyword, limit=int(limit))
    sources: list[Source] = []

    for hit in hits:
        item_type = str(hit.get("item_type", "") or "")
        item_id = str(hit.get("item_id", "") or "")
        title = str(hit.get("title", "") or "unknown")

        snippet = ""
        try:
            if item_type == "knowledge":
                entry = db.get_knowledge_entry(item_id) or {}
                snippet = "\n".join(
                    part
                    for part in [
                        str(entry.get("title", "") or ""),
                        str(entry.get("problem", "") or ""),
                        str(entry.get("solution", "") or ""),
                        str(entry.get("tags", "") or ""),
                        str(entry.get("source_ref", "") or ""),
                    ]
                    if part.strip()
                )
            elif item_type == "logbook":
                entry = db.get_logbook_entry(item_id) or {}
                snippet = "\n".join(
                    part
                    for part in [
                        str(entry.get("title", "") or ""),
                        str(entry.get("problem", "") or ""),
                        str(entry.get("solution", "") or ""),
                        str(entry.get("tags", "") or ""),
                        str(entry.get("source_ref", "") or ""),
                    ]
                    if part.strip()
                )
            elif item_type == "document":
                doc = db.get_document(item_id) or {}
                snippet = "\n".join(
                    part
                    for part in [
                        str(doc.get("filename", "") or ""),
                        str(doc.get("category", "") or ""),
                        str(doc.get("tags", "") or ""),
                        str(doc.get("status", "") or ""),
                    ]
                    if part.strip()
                )
            elif item_type == "photo":
                photo = db.get_photo(item_id) or {}
                snippet = "\n".join(
                    part
                    for part in [
                        str(photo.get("filename", "") or ""),
                        str(photo.get("tags", "") or ""),
                        str(photo.get("description", "") or ""),
                        str(photo.get("ocr_text", "") or ""),
                    ]
                    if part.strip()
                )
            elif item_type == "prompt":
                prompt = db.get_saved_prompt(item_id) or {}
                snippet = "\n".join(
                    part
                    for part in [
                        str(prompt.get("title", "") or ""),
                        str(prompt.get("tags", "") or ""),
                        str(prompt.get("content", "") or ""),
                    ]
                    if part.strip()
                )
            elif item_type == "autotest_run":
                run = db.get_autotest_run(run_id=item_id, created_by=user_id) or {}
                snippet = "\n".join(
                    part
                    for part in [
                        str(run.get("project_name", "") or ""),
                        str(run.get("summary", "") or ""),
                        str(run.get("suggestion", "") or ""),
                    ]
                    if part.strip()
                )
        except Exception:
            snippet = ""

        snippet = (snippet or title).strip().replace("\r", "\n")
        sources.append(
            Source(
                source_type=item_type,
                title=title,
                location=None,
                snippet=snippet[:240],
            )
        )

    return sources


async def perform_qa(question: str, user_id: str, db: DocumentDatabase) -> tuple[str, list[Source]]:
    doc_results = query_vector_db(question, user_id, n_results=4)
    kb_results = query_kb_vector_db(question, user_id, n_results=4)
    results = doc_results + kb_results
    if not results:
        fallback_sources = _fallback_sources_from_db(db=db, question=question, user_id=user_id, limit=5)
        if not fallback_sources:
            return 'No relevant knowledge was found yet. Try uploading a document or adding a logbook entry.', []
        context_parts = [f"[{src.source_type}:{src.title}]\n{src.snippet}" for src in fallback_sources]

        provider, _status = get_llm_provider()
        try:
            context = "\n\n".join(context_parts)
            response = await provider.generate(
                system=SYSTEM_PROMPT,
                prompt=f"Context:\n{context}\n\nQuestion:\n{question}",
                temperature=0.2,
            )
            if response.text.strip():
                return response.text, fallback_sources
        except Exception as exc:
            logger.warning("LLM provider unavailable; falling back to retrieval-only answer: %s", exc)

        joined = "\n\n".join(context_parts[:3]).strip()
        fallback_answer = (
            "LLM provider is unavailable right now, so here are the most relevant context snippets I found:\n\n"
            f"{joined}" if joined else "LLM provider is unavailable right now, and no relevant context was found."
        )
        return fallback_answer, fallback_sources

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
