"""Encoding detection for XAML files (BOM-aware)."""
from __future__ import annotations

from pathlib import Path


def detect_and_decode(path: Path | str) -> str:
    """
    Read file with encoding auto-detection. Order:
    1. Detect by BOM.
    2. Try utf-8-sig (handles BOM gracefully).
    3. Try utf-8.
    4. Try utf-16 (LE/BE auto via BOM).

    Raises FileNotFoundError if file doesn't exist.
    Raises UnicodeDecodeError if no encoding works.
    """
    p = Path(path)
    raw = p.read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le")
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be")

    for enc in ("utf-8-sig", "utf-8", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "utf-8", raw, 0, len(raw),
        f"Cannot decode {p} with utf-8/utf-8-sig/utf-16"
    )
