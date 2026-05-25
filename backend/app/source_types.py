from __future__ import annotations

from typing import Final, Literal

CanonicalSourceType = Literal["knowledge", "logbook", "prompt", "document", "photo"]

CANONICAL_SOURCE_TYPES: Final[tuple[str, ...]] = ("knowledge", "logbook", "prompt", "document", "photo")

_SOURCE_TYPE_ALIASES: Final[dict[str, str]] = {
    "knowledge": "knowledge",
    "knowledge_entry": "knowledge",
    "logbook": "logbook",
    "logbook_entry": "logbook",
    "prompt": "prompt",
    "saved_prompt": "prompt",
    "document": "document",
    "doc": "document",
    "photo": "photo",
}


def canonicalize_source_type(value: str, *, default: CanonicalSourceType = "knowledge") -> CanonicalSourceType:
    normalized = str(value or "").strip().lower()
    return _SOURCE_TYPE_ALIASES.get(normalized, default)  # type: ignore[return-value]


def is_supported_canonical_source_type(value: str) -> bool:
    return str(value or "").strip().lower() in CANONICAL_SOURCE_TYPES
