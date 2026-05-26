"""Heuristic W-3: Default value de argumento via attribute form on root.

Detecta `<Activity ... this:Class.<arg>="value" ...>` e emite finding com
mechanical p/ converter em element form.
"""
from __future__ import annotations

import re
from uip_engine._types import Finding


_RE_ACTIVITY_ROOT = re.compile(r'<Activity\b[^>]*?>', re.DOTALL)
_RE_THIS_ATTR = re.compile(
    r'this:(?P<cls>\w+)\.(?P<arg>(?:in_|io_|out_)\w+)="(?P<val>[^"]*)"'
)
_RE_X_CLASS = re.compile(r'\bx:Class="([^"]+)"')
_RE_PROPERTY = re.compile(
    r'<x:Property\b[^>]*\bName="([^"]+)"[^>]*\bType="InArgument\(([^)]+)\)"'
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def detect_w3_arg_default_attribute_form(rule, fc, pc):
    content = fc.active_content
    findings: list[Finding] = []

    root_m = _RE_ACTIVITY_ROOT.search(content)
    if not root_m:
        return []
    root_text = root_m.group(0)

    xclass_m = _RE_X_CLASS.search(root_text)
    if not xclass_m:
        return []
    self_class = xclass_m.group(1)

    # Build property name → type map
    prop_types: dict[str, str] = {}
    for m in _RE_PROPERTY.finditer(content):
        prop_types[m.group(1)] = m.group(2)

    for m in _RE_THIS_ATTR.finditer(root_text):
        cls = m.group("cls")
        arg = m.group("arg")
        val = m.group("val")
        # Só converter se class_name match self class (default-value scope).
        if cls != self_class:
            continue
        arg_type = prop_types.get(arg)
        if not arg_type:
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path),
            line=_line_for(content, root_m.start() + m.start()),
            message=f"{rule.title}: this:{cls}.{arg}=\"...\" — converter para element form",
            fix_mechanical={
                "type": "arg_default_to_element_form",
                "class_name": cls,
                "arg_name": arg,
                "arg_type": arg_type,
                "value": val,
            },
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
