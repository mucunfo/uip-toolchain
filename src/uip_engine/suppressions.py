"""Inline suppression parsing (rule-disable / rtk-disable)."""
from __future__ import annotations

import re
from dataclasses import dataclass


FILE_SCOPE = "file"
INLINE_SCOPE = "inline"
INLINE_PROXIMITY = 5  # lines after the comment that are covered


_RE_DISABLE = re.compile(
    r"<!--\s*(?:rule-disable|rtk-disable)\s*:\s*([^>]+?)\s*-->",
    re.IGNORECASE,
)
_RE_DISABLE_FILE = re.compile(
    r"<!--\s*(?:rule-disable-file|rtk-disable-file)\s*:\s*([^>]+?)\s*-->",
    re.IGNORECASE,
)


@dataclass
class Suppression:
    rule_id: str
    line: int
    scope: str  # FILE_SCOPE or INLINE_SCOPE


def parse_suppressions(content: str) -> list[Suppression]:
    """Parse rule-disable / rtk-disable comments. Returns list of Suppression."""
    suppressions: list[Suppression] = []
    # Track which positions are file-scope (more specific) so we don't double-count
    file_scope_spans: list[tuple[int, int]] = []
    for m in _RE_DISABLE_FILE.finditer(content):
        file_scope_spans.append((m.start(), m.end()))
        line = content[: m.start()].count("\n") + 1
        for rid in _split_ids(m.group(1)):
            suppressions.append(Suppression(rid, line, FILE_SCOPE))
    for m in _RE_DISABLE.finditer(content):
        # Skip if this span is the file-scope match
        if any(start <= m.start() < end for start, end in file_scope_spans):
            continue
        line = content[: m.start()].count("\n") + 1
        for rid in _split_ids(m.group(1)):
            suppressions.append(Suppression(rid, line, INLINE_SCOPE))
    return suppressions


def _split_ids(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def is_suppressed_at(
    suppressions: list[Suppression], rule_id: str, line: int
) -> bool:
    """Check if `rule_id` is suppressed at `line` given parsed suppressions."""
    for s in suppressions:
        if s.rule_id != rule_id:
            continue
        if s.scope == FILE_SCOPE:
            return True
        if s.scope == INLINE_SCOPE:
            if s.line <= line <= s.line + INLINE_PROXIMITY:
                return True
    return False
