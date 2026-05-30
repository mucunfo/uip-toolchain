"""N-16: semantic traceability of LogMessage content (100% determinístico).

Detects LogMessages whose Message string lacks debugging value in
production: generic literals, missing variable refs, indistinguishable
from other logs.

OFFLINE: delega para `llm_validator.validate_messages`, que desde 2026-05-30 é
uma HEURÍSTICA PURA em Python — NÃO chama `claude -p` nem qualquer LLM/rede/
subprocess. `uip` é 100% script offline. Opt-out via env `UIP_TOOLCHAIN_NO_LLM=1`.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .._types import Finding
from ..llm_validator import validate_messages


def _llm_disabled() -> bool:
    """N-16 opt-out: skip LLM validator se ambiente sem claude CLI ou usuario
    optou por bypass. Default OFF (fica ON quando claude CLI presente).

    Triggers:
      - env `UIP_TOOLCHAIN_NO_LLM=1` (explicit opt-out)
    """
    if os.environ.get("UIP_TOOLCHAIN_NO_LLM", "").strip() in ("1", "true", "yes"):
        return True
    return False

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
    if _llm_disabled():
        return []

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
