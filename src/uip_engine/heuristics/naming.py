"""Heuristics for naming rules (S-4 acronyms, S-6 x:Class, S-9 PT-BR).

All lists/thresholds vinem de rules.yaml params. Sem hardcoded.
"""
from __future__ import annotations

import re

from uip_engine._types import Finding


_NAME_ATTR = re.compile(r'<x:Property[^>]*Name="([^"]+)"|<Variable[^>]*Name="([^"]+)"')

_RE_XCLASS = re.compile(r'<Activity\b[^>]*\sx:Class="([^"]+)"')


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _params(rule):
    return rule.detect.get("params", {}) or {}


def detect_s4_acronyms(rule, fc, pc):
    acronyms = tuple(_params(rule).get("acronyms") or ())
    if not acronyms:
        return []
    content = fc.active_content
    findings = []
    seen = set()
    for m in _NAME_ATTR.finditer(content):
        is_arg = m.group(1) is not None
        name = m.group(1) or m.group(2) or ""
        if not name or name in seen:
            continue
        seen.add(name)
        for acro in acronyms:
            if len(acro) < 2:
                continue
            mismatch = re.search(rf'(?<![A-Z]){acro[0]}{acro[1:].lower()}(?=[A-Z]|\b)', name)
            if mismatch:
                new_name = name[:mismatch.start()] + acro + name[mismatch.end():]
                if is_arg:
                    fix_mech = {
                        "type": "rename_argument",
                        "from": name,
                        "to": new_name,
                        "target_workflow": fc.path.name,
                    }
                else:
                    fix_mech = {
                        "type": "rename_attribute",
                        "from": name,
                        "to": new_name,
                    }
                findings.append(Finding(
                    rule_id=rule.id, severity=rule.severity, category=rule.category,
                    file=str(fc.path), line=_line_for(content, m.start()),
                    message=f"{rule.title}: '{name}' usa '{mismatch.group(0)}' (esperado '{acro}') → renomear para '{new_name}'",
                    fix_mechanical=fix_mech,
                    fix_prose=(rule.fix or {}).get("prose"),
                ))
                break
    return findings


def detect_s6_xclass_filename(rule, fc, pc):
    content = fc.content
    m = _RE_XCLASS.search(content[:3000])
    if not m:
        return []
    expected = fc.path.stem
    actual = m.group(1)
    if actual == expected:
        return []
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=_line_for(content, m.start()),
        message=f"{rule.title}: x:Class='{actual}' diverge filename '{expected}'",
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )]


def detect_s9_pt_br(rule, fc, pc):
    p = _params(rule)
    forbidden = tuple(p.get("forbidden") or ())
    exceptions = tuple(p.get("exceptions") or ())
    if not forbidden:
        return []
    content = fc.active_content
    findings = []
    seen = set()
    for m in _NAME_ATTR.finditer(content):
        name = m.group(1) or m.group(2) or ""
        if not name or name in seen:
            continue
        seen.add(name)
        if any(exc in name for exc in exceptions):
            continue
        for word in forbidden:
            if re.search(rf'(?<![A-Za-z]){word}(?=[A-Z]|\b|\d|_)', name):
                findings.append(Finding(
                    rule_id=rule.id, severity=rule.severity, category=rule.category,
                    file=str(fc.path), line=_line_for(content, m.start()),
                    message=f"{rule.title}: '{name}' contém palavra EN '{word}'",
                    fix_mechanical=(rule.fix or {}).get("mechanical"),
                    fix_prose=(rule.fix or {}).get("prose"),
                ))
                break
    return findings


_VAR_NAME_RE = re.compile(r'<Variable[^>]*Name="([^"]+)"')
_PROP_NAME_RE = re.compile(r'<x:Property[^>]*Name="([^"]+)"')


def _strip_arg_prefix(name: str) -> str:
    """Strip in_/out_/io_ + tipo opcional (St, In, Bl, Dt, etc.) for verb extraction.

    Variável: vStBuscarDossie -> BuscarDossie
    Argumento: in_StBuscarDossie -> BuscarDossie
    """
    s = name
    for pref in ("in_", "out_", "io_"):
        if s.startswith(pref):
            s = s[len(pref):]
            break
    if s.startswith(("v", "l")) and len(s) > 1 and s[1].isupper():
        s = s[1:]
    # strip 2-letter type prefix like "St", "Bl", "In", "Dt", "Si", "Ar"
    if len(s) >= 3 and s[0].isupper() and s[1].islower() and s[2].isupper():
        s = s[2:]
    return s


def detect_n13_verb_infinitive(rule, fc, pc):
    """N-13: identificadores iniciados por verbo PT-BR no presente 3sg
    devem usar infinitivo. Targets: filename, x:Class, var, arg.
    """
    p = _params(rule)
    pairs = p.get("verbs") or []
    if not pairs:
        return []
    targets = set(p.get("targets") or ["filename", "xclass", "property_name", "variable_name"])
    content = fc.active_content
    findings = []
    seen_msg_keys = set()

    def emit(line, ident, wrong, right, location):
        key = (location, ident, wrong)
        if key in seen_msg_keys:
            return
        seen_msg_keys.add(key)
        suggested = ident.replace(wrong, right, 1) if ident.startswith(wrong) else ident
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=line,
            message=f"{rule.title}: {location} '{ident}' inicia com '{wrong}' (presente 3sg) — usar infinitivo '{right}' (sugerido: '{suggested}')",
            fix_mechanical=None,
            fix_prose=(rule.fix or {}).get("prose"),
        ))

    # 1. filename + xclass
    if "filename" in targets:
        stem = fc.path.stem
        for pair in pairs:
            w, r = pair.get("wrong",""), pair.get("right","")
            if not w: continue
            if stem.startswith(w) and (len(stem) == len(w) or stem[len(w)].isupper() or stem[len(w)] in "_-"):
                emit(1, stem, w, r, "filename")
                break

    if "xclass" in targets:
        m = _RE_XCLASS.search(content[:3000])
        if m:
            xc = m.group(1)
            for pair in pairs:
                w, r = pair.get("wrong",""), pair.get("right","")
                if not w: continue
                if xc.startswith(w) and (len(xc) == len(w) or xc[len(w)].isupper() or xc[len(w)] in "_-"):
                    emit(_line_for(content, m.start()), xc, w, r, "x:Class")
                    break

    # 2. variables
    if "variable_name" in targets:
        for m in _VAR_NAME_RE.finditer(content):
            name = m.group(1)
            stripped = _strip_arg_prefix(name)
            for pair in pairs:
                w, r = pair.get("wrong",""), pair.get("right","")
                if not w: continue
                if stripped.startswith(w) and (len(stripped) == len(w) or stripped[len(w)].isupper()):
                    emit(_line_for(content, m.start()), name, w, r, "Variable")
                    break

    # 3. properties (args)
    if "property_name" in targets:
        for m in _PROP_NAME_RE.finditer(content):
            name = m.group(1)
            stripped = _strip_arg_prefix(name)
            for pair in pairs:
                w, r = pair.get("wrong",""), pair.get("right","")
                if not w: continue
                if stripped.startswith(w) and (len(stripped) == len(w) or stripped[len(w)].isupper()):
                    emit(_line_for(content, m.start()), name, w, r, "x:Property")
                    break

    return findings
