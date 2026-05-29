"""Heuristics for Windows-target rules (W-*)."""
from __future__ import annotations

import re

from uip_engine._types import Finding


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


def _w2_mechanical_available(arg: str, method: str) -> bool:
    """Mirror de `fixers.apply_guard_linq_arg_ref::_default_for`.
    True quando fixer tem default sensato pra wrap. False = type-dependent,
    fixer skipa (e detector deve emitir fix_mechanical=None).

    Sync OBRIGATÓRIO com fixer — divergência = detector mente sobre o que
    engine pode fixar.
    """
    if method in ("Contains", "Any", "All"):
        return True  # Boolean return, default False sempre safe
    bare = re.sub(r'^(in|io)_', '', arg)
    if bare.startswith('DTab'):
        return False  # DataTable.Select chain — guard parcial mascara erro
    if method == 'AsEnumerable':
        return False
    if bare.startswith('Arr') and method in ('Select', 'Where'):
        return True  # idempotente self-wrap
    return False  # Dict/Lst/etc type-dependent


def detect_w2_linq_no_guard(rule, fc, pc):
    content = fc.active_content
    findings = []
    rule_mech = (rule.fix or {}).get("mechanical")
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
        # Per-finding mech: só se fixer realmente cobre esse caso.
        mech_for_this = rule_mech if _w2_mechanical_available(arg, method) else None
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {arg}.{method}(...) sem guard",
            fix_mechanical=mech_for_this,
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
        # Multi-part chain (obj.Field.IsNullOrEmpty): fixer regex só cobre bare
        # identifier — emitir mech aqui mente sobre auto-fix (silent no-op).
        # Mirror W-12/W-2: route multi-part p/ manual (contextual).
        mech_for_this = None if "." in chain else (rule.fix or {}).get("mechanical")
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {chain}.IsNullOrEmpty",
            fix_mechanical=mech_for_this,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


_RE_W12_ARRAYROW = re.compile(r'ArrayRow="\[\{(?!New\s)[^"}]+\}\]"')
_RE_W12_EMPTY = re.compile(r'>\[\{\}\]<|"\[\{\}\]"')


def detect_w12_array_literal(rule, fc, pc):
    """W-12: array literal sem type explícito.

    Distingue:
      - `ArrayRow="[{a,b}]"` em AddDataRow — wrap mecânico Object().
      - `[{}]` vazio (`>[{}]<` ou `"[{}]"`) — manual (precisa context p/ type).

    Emite fix_mechanical APENAS pro caso ArrayRow.
    """
    content = fc.active_content
    findings: list[Finding] = []
    mech = (rule.fix or {}).get("mechanical")
    for m in _RE_W12_ARRAYROW.finditer(content):
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: ArrayRow sem tipo — auto-wrap Object()",
            fix_mechanical=mech,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    for m in _RE_W12_EMPTY.finditer(content):
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: array vazio sem tipo — manual (context-dependent)",
            fix_mechanical=None,  # context-dependent
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


_RE_OCRENGINE_EMPTY = re.compile(
    r'<uix:NApplicationCard\.OCREngine>\s*'
    r'<ActivityFunc\b[^>]*>\s*'
    r'(?:<ActivityFunc\.Argument>\s*<DelegateInArgument\b[^>]*/?>\s*</ActivityFunc\.Argument>\s*)*'
    r'</ActivityFunc>\s*'
    r'</uix:NApplicationCard\.OCREngine>',
    re.DOTALL,
)


def detect_ocr1_empty_engine(rule, fc, pc):
    """OCR-1: NApplicationCard.OCREngine com ActivityFunc body vazio.

    Detecta apenas placeholders Migrator-injetados (sem activity OCR concreto
    dentro). Workflows com engine explícito preservados.
    """
    content = fc.active_content
    findings = []
    for m in _RE_OCRENGINE_EMPTY.finditer(content):
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=(
                f"{rule.title}: OCREngine sem activity concreto — "
                "Studio analyzer falha 'OCR Engine must be set'"
            ),
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
        # Multi-part chain (obj.Field.ToInt32): fixer regex só cobre bare
        # identifier — emitir mech aqui mente sobre auto-fix (silent no-op).
        # Mirror W-12/W-2: route multi-part p/ manual (contextual).
        mech_for_this = None if "." in chain else (rule.fix or {}).get("mechanical")
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {chain}.ToInt32",
            fix_mechanical=mech_for_this,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# UI-7: Simulate InteractionMode → DelayBefore/After devem ser 0
#
# Detecta activities UIA com `InteractionMode="Simulate"` que tenham
# `DelayBefore` ou `DelayAfter` definidos com valor != 0. Simulate é
# background-capable; delays só fazem sentido em HardwareEvents.

_RE_UIA_ACTIVITY = re.compile(
    r'<(uix?|uia):([A-Za-z][\w]*)\b([^>]*?)/?>', re.DOTALL
)
_RE_ATTR_KV = re.compile(r'\b([A-Za-z_][\w]*)\s*=\s*"([^"]*)"')


def _is_zero_delay(value: str) -> bool:
    """True se valor é '0', '[0]', '0.0', '[0.0]' (Double zero)."""
    if value is None:
        return True
    v = value.strip()
    if not v:
        return True
    # Strip outer [...] bind expression
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1].strip()
    # Numeric zero literal
    try:
        return float(v) == 0.0
    except ValueError:
        return False


def _is_numeric_delay(value: str) -> bool:
    """True se valor é literal numérico reducível (`500`, `[500]`, `0.0`).

    False p/ binding expression VB não-reducível (`[in_Config(...)]`),
    `{x:Null}`, ou qualquer coisa que float() não consegue avaliar. Nesses
    casos force-"0" determinístico apagaria valor config-bound — deve ser
    contextual (humano decide).
    """
    if value is None:
        return False
    v = value.strip()
    if not v:
        return False
    # Strip outer [...] bind expression (mirror _is_zero_delay)
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1].strip()
    try:
        float(v)
        return True
    except ValueError:
        return False


def detect_ui7_simulate_delays(rule, fc, pc):
    """UI-7: activities UIA com InteractionMode=Simulate + DelayBefore/After != 0.

    Emite 1 finding por (activity, attr) violador. fix_mechanical scope-strict
    via apply_force_attribute_in_activity_with_guard.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []
    content = fc.active_content or ""
    findings = []
    for m in _RE_UIA_ACTIVITY.finditer(content):
        prefix = m.group(1)
        local = m.group(2)
        body = m.group(3) or ""
        attrs = {am.group(1): am.group(2) for am in _RE_ATTR_KV.finditer(body)}
        mode = (attrs.get("InteractionMode") or "").strip()
        if mode != "Simulate":
            continue
        line = _line_for(content, m.start())
        for delay_attr in ("DelayBefore", "DelayAfter"):
            if delay_attr not in attrs:
                continue
            if _is_zero_delay(attrs[delay_attr]):
                continue
            # Só force-"0" determinístico p/ literal numérico não-zero.
            # Binding expression não-reducível (`[in_Config(...)]`) ou
            # `{x:Null}` => contextual (fix_mechanical=None): force-"0"
            # apagaria valor config-bound (data loss). Humano decide.
            if _is_numeric_delay(attrs[delay_attr]):
                fix_mech = {
                    "type": "force_attribute_in_activity_with_guard",
                    "prefix": prefix,
                    "activity_local": local,
                    "guard_attr": "InteractionMode",
                    "guard_value": "Simulate",
                    "attr_name": delay_attr,
                    "target_value": "0",
                    "tag_line": line,
                }
            else:
                fix_mech = None
            findings.append(Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=line,
                message=(
                    f"{rule.title}: <{prefix}:{local}> "
                    f'InteractionMode="Simulate" mas '
                    f'{delay_attr}="{attrs[delay_attr]}" (esperado 0)'
                ),
                fix_mechanical=fix_mech,
                fix_prose=(rule.fix or {}).get("prose"),
            ))
    return findings
