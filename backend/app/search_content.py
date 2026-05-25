from __future__ import annotations

from app.source_types import canonicalize_source_type


def build_knowledge_search_text(entry: dict[str, object]) -> str:
    return _join_parts(
        entry.get("title", ""),
        f"Problem:\n{entry.get('problem', '')}",
        f"Root cause:\n{entry.get('root_cause', '')}",
        f"Solution:\n{entry.get('solution', '')}",
        f"Tags:\n{entry.get('tags', '')}",
        f"Notes:\n{entry.get('notes', '')}",
        f"Status:\n{entry.get('status', '')}",
        f"Source:\n{entry.get('source_type', '')} {entry.get('source_ref', '')}",
    )


def build_logbook_search_text(entry: dict[str, object]) -> str:
    return _join_parts(
        entry.get("title", ""),
        f"Problem:\n{entry.get('problem', '')}",
        f"Root cause:\n{entry.get('root_cause', '')}",
        f"Solution:\n{entry.get('solution', '')}",
        f"Tags:\n{entry.get('tags', '')}",
        f"Source type:\n{entry.get('source_type', '')}",
        f"Status:\n{entry.get('status', '')}",
        f"Source ref:\n{entry.get('source_ref', '')}",
    )


def build_photo_search_text(entry: dict[str, object]) -> str:
    return _join_parts(
        entry.get("filename", ""),
        f"Tags:\n{entry.get('tags', '')}",
        f"Description:\n{entry.get('description', '')}",
        f"OCR:\n{entry.get('ocr_text', '')}",
    )


def build_prompt_search_text(entry: dict[str, object]) -> str:
    return _join_parts(
        entry.get("title", ""),
        f"Tags:\n{entry.get('tags', '')}",
        f"Content:\n{entry.get('content', '')}",
    )


def build_document_search_text(*, filename: str, category: str, tags: str, status: str, content: str) -> str:
    return _join_parts(
        filename,
        f"Category:\n{category}",
        f"Tags:\n{tags}",
        f"Status:\n{status}",
        content,
    )


def item_type_to_source_type(item_type: str) -> str:
    return canonicalize_source_type(item_type)


def _join_parts(*parts: object) -> str:
    return "\n".join(str(part or "").strip() for part in parts if str(part or "").strip()).strip()
