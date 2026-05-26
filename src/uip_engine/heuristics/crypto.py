"""Heuristics para activity renames deprecated (CRY-* + IOCR-4).

CRY-5: HashText/HashFile (legacy) → KeyedHashText/KeyedHashFile.
UiPath.Cryptography.Activities marca HashText/HashFile como deprecated
desde v1.4.0+. Rename é puramente cosmético no schema atual (args
idênticos); valida intent de "key required" via nome.
"""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


_RE_HASH_LEGACY = re.compile(r'<([A-Za-z_][\w]*):(HashText|HashFile)\b')
_RE_CJK_OCR = re.compile(r'<([A-Za-z_][\w]*):CjkOCR\b')

_HASH_RENAME_MAP = {
    "HashText": "KeyedHashText",
    "HashFile": "KeyedHashFile",
}


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def detect_cry5_hash_legacy(rule, fc, pc):
    """CRY-5: emite finding por uso de HashText/HashFile (deprecated).

    1 finding por match (multi-occorrência no XAML). fix_mechanical scope
    via rename_element (open+close+property elements).

    Idempotente: skip XAML não-presente. Word boundary impede match em
    HashTextExtended ou nomes derivados.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []
    content = fc.active_content or ""
    findings: list[Finding] = []
    seen = set()  # dedup por (prefix, local) — 1 finding por par
    for m in _RE_HASH_LEGACY.finditer(content):
        prefix = m.group(1)
        local = m.group(2)
        key = (prefix, local)
        if key in seen:
            continue
        seen.add(key)
        new_local = _HASH_RENAME_MAP.get(local)
        if not new_local:
            continue
        line = _line_for(content, m.start())
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=line,
            message=(
                f"{rule.title}: <{prefix}:{local}> deprecated em "
                f"UiPath.Cryptography v1.4.0+. Usar <{prefix}:{new_local}>."
            ),
            fix_mechanical={
                "type": "rename_element",
                "prefix": prefix,
                "old_local": local,
                "new_local": new_local,
            },
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_iocr4_cjk_ocr(rule, fc, pc):
    """IOCR-4: emite finding por uso de `<*:CjkOCR>` (deprecated jan/2025).

    Schema confirma args IDÊNTICOS entre CjkOCR e ExtendedLanguagesOCR —
    rename é seguro. Mesmo pkg (UiPath.OCR.Activities), sem mudança de
    dependência.

    1 finding por (prefix, local). fix_mechanical scope via rename_element.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []
    content = fc.active_content or ""
    findings: list[Finding] = []
    seen = set()
    for m in _RE_CJK_OCR.finditer(content):
        prefix = m.group(1)
        if prefix in seen:
            continue
        seen.add(prefix)
        line = _line_for(content, m.start())
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=line,
            message=(
                f"{rule.title}: <{prefix}:CjkOCR> deprecated jan/2025. "
                f"Usar <{prefix}:ExtendedLanguagesOCR> (args idênticos)."
            ),
            fix_mechanical={
                "type": "rename_element",
                "prefix": prefix,
                "old_local": "CjkOCR",
                "new_local": "ExtendedLanguagesOCR",
            },
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
