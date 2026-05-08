"""Heuristic S-8b: InvokeWorkflowFile DisplayName != basename(WorkflowFileName).

Permitido: `Foo` ou `Foo (suffix)` quando workflow é `Foo.xaml`.
Flagged: `Step 3` invocando `RealizarTransferencia.xaml`.
"""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


_RE_INVOKE = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*?DisplayName="([^"]+)"[^>]*?WorkflowFileName="([^"]+)"',
    re.DOTALL,
)
_RE_INVOKE_REVERSED = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*?WorkflowFileName="([^"]+)"[^>]*?DisplayName="([^"]+)"',
    re.DOTALL,
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _basename(path: str) -> str:
    p = path.replace("\\", "/").rstrip("/")
    name = p.rsplit("/", 1)[-1]
    if name.lower().endswith(".xaml"):
        name = name[:-5]
    return name


def detect_s8b_displayname_mismatch(rule, fc, pc):
    """DisplayName must equal basename(WorkflowFileName), with optional `(suffix)`.

    Skip dynamic WorkflowFileName (`[expr]`) since basename can't be resolved.
    """
    content = fc.active_content
    findings = []
    seen: set[int] = set()

    for regex, dn_first in [(_RE_INVOKE, True), (_RE_INVOKE_REVERSED, False)]:
        for m in regex.finditer(content):
            if m.start() in seen:
                continue
            seen.add(m.start())
            if dn_first:
                display, file = m.group(1), m.group(2)
            else:
                file, display = m.group(1), m.group(2)
            if file.startswith("[") or "{" in file:
                continue
            expected = _basename(file)
            # Allow exact match OR `<expected> (suffix)` (any context).
            if display == expected:
                continue
            if re.fullmatch(rf'{re.escape(expected)}\s*\([^)]+\)', display):
                continue
            # Studio default verbose handled by S-8 — skip to avoid duplicate.
            if display.lower().endswith(".xaml - invoke workflow file") or \
               display.lower().endswith("- invoke workflow file"):
                continue
            # Per-finding mechanical: anchor regex on InvokeWorkflowFile tag
            # with this exact (DisplayName, WorkflowFileName) pair.
            file_esc = re.escape(file)
            display_esc = re.escape(display)
            if dn_first:
                fix_pattern = (
                    rf'(<ui:InvokeWorkflowFile\b[^>]*?)DisplayName="{display_esc}"'
                    rf'([^>]*?WorkflowFileName="{file_esc}")'
                )
            else:
                fix_pattern = (
                    rf'(<ui:InvokeWorkflowFile\b[^>]*?WorkflowFileName="{file_esc}"[^>]*?)'
                    rf'DisplayName="{display_esc}"'
                )
            mech = {
                "type": "regex_replace",
                "pattern": fix_pattern,
                "replacement": (
                    rf'\1DisplayName="{expected}"\2' if dn_first
                    else rf'\1DisplayName="{expected}"'
                ),
            }
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, m.start()),
                message=f"{rule.title}: DisplayName='{display}' ≠ '{expected}'",
                fix_mechanical=mech,
                fix_prose=(rule.fix or {}).get("prose"),
            ))
    return findings
