"""J-PIN-BRACKETS — toda dependency em `project.json` deve usar `[X.Y.Z]`.

Range flutuante (`"X.Y.Z"` sem brackets) deixa NuGet resolver pegar versão
diferente em re-restore. Pin estrito Sicoob exige `[X.Y.Z]`.

Detector emite finding por dep mal-formada com fix mecânico dinâmico
(`set_dependency_pin` injetando o version no formato canônico).
"""
from __future__ import annotations

import re

from uip_engine._types import Finding


_BRACKETED_RE = re.compile(r"^\[\s*\d+\.\d+\.\d+(?:[-.][A-Za-z0-9.+_-]+)?\s*\]$")
_PLAIN_RE = re.compile(r"^\s*(\d+\.\d+\.\d+(?:[-.][A-Za-z0-9.+_-]+)?)\s*$")


def detect_pin_brackets(rule, fc, pc) -> list[Finding]:
    """Para cada dep, exige `[X.Y.Z]`. Range/sem-brackets → finding."""
    if pc is None:
        return []
    deps = pc.project_json.get("dependencies", {})
    if not isinstance(deps, dict):
        return []
    findings: list[Finding] = []
    for pkg, raw in deps.items():
        s = str(raw)
        if _BRACKETED_RE.match(s):
            continue
        # Caso simples: "21.10.1" → wrap em "[21.10.1]"
        m = _PLAIN_RE.match(s)
        if m:
            target = f"[{m.group(1)}]"
        else:
            # Range complexo (`[1.0,2.0)`, `1.0.*`, etc.) — sem fix mecânico.
            # Emit finding com prose orientando para pin exato manual.
            target = None
        fix_mechanical = None
        if target is not None:
            fix_mechanical = {
                "type": "set_dependency_pin",
                "package": pkg,
                "version": target,
            }
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(pc.root / "project.json"),
            line=1,
            message=f"{rule.title}: {pkg}={raw!r} (esperado formato [X.Y.Z])",
            fix_mechanical=fix_mechanical,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
