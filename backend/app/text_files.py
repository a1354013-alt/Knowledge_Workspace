from __future__ import annotations

from pathlib import Path
from typing import Iterable

TEXT_FILE_ENCODINGS: tuple[str, ...] = ("utf-8", "utf-8-sig", "cp950")


def looks_like_text_bytes(data: bytes) -> bool:
    """Heuristic check to avoid accepting obvious binary payloads as text."""
    if not data:
        return True
    if b"\x00" in data:
        return False

    sample = data[:4096]
    length = len(sample)
    if length == 0:
        return True

    control = 0
    for byte in sample:
        if byte in (9, 10, 13):  # \t, \n, \r
            continue
        if byte < 32 or byte == 127:
            control += 1

    # If the sample is mostly control characters, it's almost certainly binary.
    return (control / length) < 0.05


def decode_text_bytes(data: bytes, *, encodings: Iterable[str] = TEXT_FILE_ENCODINGS) -> tuple[str, str]:
    for encoding in encodings:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode text document.")


def read_text_file(path: str | Path) -> tuple[str, str]:
    file_path = Path(path)
    data = file_path.read_bytes()
    if not looks_like_text_bytes(data):
        raise ValueError("File appears to be binary but has a text extension.")
    text, encoding = decode_text_bytes(data)
    return text, encoding

