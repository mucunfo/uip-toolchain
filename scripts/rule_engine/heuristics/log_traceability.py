"""N-16: LLM-assisted semantic traceability of LogMessage content.

Detects LogMessages whose Message string lacks debugging value in
production: generic literals, missing variable refs, indistinguishable
from other logs.

Calls Claude Code CLI via subprocess (cached per-message hash). Fail-open
on LLM unavailability — never blocks pipeline.
"""
from __future__ import annotations

import re
from pathlib import Path

from .._types import Finding
from ..llm_validator import validate_messages

_RE_LOGMSG_MESSAGE = re.compile(
    r'<ui:LogMessage\b[^>]*\bMessage="([^"]*)"',
    re.DOTALL,
)


def _line_for(content: str, pos: int) -> int:
    return content.count("\n", 0, pos) + 1


def detect_n16_log_semantic_traceability(rule, fc, pc):
    """N-16: LogMessage Message must provide semantic traceability.

    Batches all messages in file → single LLM call per file (cached).
    Findings emitted only for messages judged 'fail' by LLM.
    """
    content = fc.active_content
    if "<ui:LogMessage" not in content:
        return []

    matches = list(_RE_LOGMSG_MESSAGE.finditer(content))
    if not matches:
        return []

    # Decode XML entities for readable LLM eval
    def _unescape(s: str) -> str:
        return (s.replace("&quot;", '"')
                 .replace("&amp;", "&")
                 .replace("&lt;", "<")
                 .replace("&gt;", ">"))

    msgs_decoded = [_unescape(m.group(1)) for m in matches]

    project_root = Path(pc.root) if pc is not None else None
    if project_root is None:
        return []

    verdicts = validate_messages(msgs_decoded, project_root)

    findings: list[Finding] = []
    for m, raw_msg in zip(matches, msgs_decoded):
        v = verdicts.get(raw_msg, {})
        if v.get("verdict") != "fail":
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: '{raw_msg[:80]}' — {v.get('reason','')[:120]}",
            fix_mechanical=None,  # No mechanical fix — manual rewrite required.
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
