"""mojibake_fixer — detect + re-encode XAML files com encoding corruption.

Two corruption modes:
  1. double_encoded: UTF-8 bytes were read as cp1252 then re-encoded UTF-8.
     Identifier: text contains patterns like `Ã[\x80-\xBF]` (UTF-8 multi-byte
     prefix interpreted as cp1252 `Ã` + UTF-8 continuation byte).
  2. non_utf8_bytes: raw bytes don't decode as UTF-8 strict (decode errors).
     Likely file written by an editor that saved cp1252/Latin-1 without BOM.

Fix:
  - double_encoded: text.encode('cp1252').decode('utf-8') reverses the chain.
  - non_utf8_bytes: content.decode('cp1252').encode('utf-8').

Both 100% deterministic. Round-trip validation: post-fix file decodes utf-8
strict with no U+FFFD.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MojibakeKind(Enum):
    CLEAN = "clean"
    DOUBLE_ENCODED_UTF8 = "double_encoded_utf8"
    NON_UTF8_BYTES = "non_utf8_bytes"
    REPLACEMENT_CHARS = "replacement_chars"     # contains U+FFFD already
    UNCERTAIN = "uncertain"                     # detect but can't safely fix


@dataclass(frozen=True)
class DetectionResult:
    kind: MojibakeKind
    affected_sequences: tuple[str, ...] = ()    # short samples
    confidence: float = 0.0                     # 0-1


# Regex patterns for double-encoded sequences (Portuguese specifically)
# Common: à (U+00E0) → bytes C3 A0 → as cp1252 → "Ã " (capital A tilde + nbsp/space)
#         ã (U+00E3) → C3 A3 → "Ã£"
#         ç (U+00E7) → C3 A7 → "Ã§"
#         é (U+00E9) → C3 A9 → "Ã©"
#         õ (U+00F5) → C3 B5 → "Ãµ"
_DOUBLE_ENCODED_PATTERN = re.compile(r"Ã[\x80-\xBF]|Â[\xA0-\xBF]")
# Detect U+FFFD replacement chars
_REPLACEMENT_PATTERN = re.compile("�")


def detect(content: bytes) -> DetectionResult:
    """Analyze bytes, classify corruption kind."""
    # Try strict UTF-8 first
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        # Non-UTF-8 bytes. Probably cp1252.
        try:
            content.decode("cp1252", errors="strict")
            return DetectionResult(MojibakeKind.NON_UTF8_BYTES, confidence=0.9)
        except UnicodeDecodeError:
            return DetectionResult(MojibakeKind.UNCERTAIN, confidence=0.0)

    # UTF-8 OK. Check for U+FFFD (already-corrupted reads)
    fffd_matches = _REPLACEMENT_PATTERN.findall(text)
    if fffd_matches:
        return DetectionResult(
            MojibakeKind.REPLACEMENT_CHARS,
            affected_sequences=tuple(set(fffd_matches[:5])),
            confidence=1.0,
        )

    # Check for double-encoded patterns
    de_matches = _DOUBLE_ENCODED_PATTERN.findall(text)
    if de_matches:
        # Threshold: at least 3 distinct sequences OR > 5 hits
        if len(de_matches) >= 5 or len(set(de_matches)) >= 3:
            samples = tuple(sorted(set(de_matches))[:5])
            return DetectionResult(
                MojibakeKind.DOUBLE_ENCODED_UTF8,
                affected_sequences=samples,
                confidence=min(1.0, len(de_matches) / 10),
            )

    return DetectionResult(MojibakeKind.CLEAN, confidence=1.0)


def fix(content: bytes, kind: MojibakeKind) -> bytes | None:
    """Apply deterministic re-encoding. Return None se non-fixable."""
    if kind == MojibakeKind.CLEAN:
        return content
    if kind == MojibakeKind.DOUBLE_ENCODED_UTF8:
        try:
            text = content.decode("utf-8")
            # Reverse: text was UTF-8 bytes read as cp1252 then re-encoded UTF-8.
            # So encode("cp1252") returns the original UTF-8 bytes.
            return text.encode("cp1252").decode("utf-8").encode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return None
    if kind == MojibakeKind.NON_UTF8_BYTES:
        try:
            return content.decode("cp1252", errors="strict").encode("utf-8")
        except UnicodeDecodeError:
            return None
    if kind == MojibakeKind.REPLACEMENT_CHARS:
        # Already corrupted reads. Cannot recover without source. Return None.
        return None
    return None


def validate_round_trip(fixed: bytes) -> bool:
    """Confirm fixed bytes decode utf-8 strict + no U+FFFD."""
    try:
        text = fixed.decode("utf-8", errors="strict")
        return "�" not in text
    except UnicodeDecodeError:
        return False


def fix_file(path: Path, *, dry_run: bool = False) -> tuple[DetectionResult, bool]:
    """Detect + fix file in-place. Return (detection, was_modified)."""
    content = path.read_bytes()
    det = detect(content)
    if det.kind == MojibakeKind.CLEAN:
        return det, False
    fixed = fix(content, det.kind)
    if fixed is None:
        return det, False
    if not validate_round_trip(fixed):
        return det, False
    if not dry_run:
        path.write_bytes(fixed)
    return det, True
