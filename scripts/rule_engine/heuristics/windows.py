"""Heuristics for Windows-target rules (W-*)."""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


_RE_LINQ_ON_ARG = re.compile(
    r'\b(in_\w+|io_\w+)\.(Contains|Any|Where|Select|First|Single|All)\('
)
_RE_SENDMAIL_OPEN = re.compile(r'<ui:SendMail\s[^>]*>')

_RE_ISNULLOREMPTY = re.compile(
    r'(?<![A-Za-z_:])((?:[a-zA-Z_]\w*\.)*[a-zA-Z_]\w*)\.IsNullOrEmpty\b'
)
_RE_TOINT32 = re.compile(
    r'(?<![A-Za-z_:])((?:[a-zA-Z_]\w*\.)*[a-zA-Z_]\w*)\.ToInt32\b'
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _params(rule):
    return rule.detect.get("params", {}) or {}


def _last_segment(chain: str) -> str:
    return chain.rsplit(".", 1)[-1]


def detect_w2_linq_no_guard(rule, fc, pc):
    content = fc.active_content
    findings = []
    for m in _RE_LINQ_ON_ARG.finditer(content):
        arg, method = m.group(1), m.group(2)
        start = max(0, m.start() - 200)
        prefix = content[start:m.start()]
        guarded = (
            f"{arg} Is Nothing" in prefix
            or f"If({arg} Is Nothing" in prefix
            or f"If({arg} IsNot Nothing" in prefix
        )
        if guarded:
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {arg}.{method}(...) sem guard",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w13_sendmail(rule, fc, pc):
    content = fc.active_content
    findings = []
    for m in _RE_SENDMAIL_OPEN.finditer(content):
        if 'UseISConnection="False"' in m.group(0):
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w16_isnullorempty(rule, fc, pc):
    """W-16: `<expr>.IsNullOrEmpty` em VB Windows — usar `String.IsNullOrEmpty(<expr>)`.

    Skip já-correto via params.static_class_names + params.last_segment_skip.
    """
    p = _params(rule)
    static_names = {s.lower() for s in (p.get("static_class_names") or ())}
    skip_last = {s.lower() for s in (p.get("last_segment_skip") or ())}

    content = fc.active_content
    findings = []
    for m in _RE_ISNULLOREMPTY.finditer(content):
        chain = m.group(1)
        if chain.lower() in static_names:
            continue
        if _last_segment(chain).lower() in skip_last:
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {chain}.IsNullOrEmpty",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w17_toint32(rule, fc, pc):
    """W-17: `<expr>.ToInt32` em VB Windows — usar `Convert.ToInt32(<expr>)`."""
    p = _params(rule)
    static_names = {s.lower() for s in (p.get("static_class_names") or ())}
    skip_last = {s.lower() for s in (p.get("last_segment_skip") or ())}

    content = fc.active_content
    findings = []
    for m in _RE_TOINT32.finditer(content):
        chain = m.group(1)
        if chain.lower() in static_names:
            continue
        if _last_segment(chain).lower() in skip_last:
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {chain}.ToInt32",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
