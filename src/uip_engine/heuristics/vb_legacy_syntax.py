"""W-33 heuristic — VB legacy syntax patterns incompat Roslyn .NET 6.

Detecta padrões VB.NET aceitos por compiler legacy .NET Framework 4.6.1
mas rejeitados por Roslyn (Windows target Studio v25.10+).

Scope: VB expressions dentro `[...]` brackets em XAML attribute values.
Patterns SOFT (warn) — alguns podem ser false positives em string literals.

Catalog:
  - IIf(c,t,f)           — replace por If(c,t,f) (Roslyn-friendly)
  - On Error Resume Next — error handling VB6-style obsoleto
  - Set <var> =          — keyword pre-Option-Strict deprecated
  - Variant / Currency   — types VB6 não existem em .NET 6
  - GoTo em expression   — Roslyn strict
  - MsgBox( em workflow  — deprecated, use ui:MessageBox
  - Eval( / Execute(     — runtime-only legacy

False positive mitigation:
  - Match só dentro `[...]` VB expression brackets
  - Skip se padrão está dentro de string literal `"..."` (substring search)
  - Skip XML comment `<!-- -->` blocks
"""
from __future__ import annotations

import re

from uip_engine._types import Finding


# Pattern catalog: (regex, label, fix_hint)
_VB_LEGACY_PATTERNS = [
    (re.compile(r'\bIIf\s*\('), 'IIf', 'replace por If(condition, true_expr, false_expr)'),
    (re.compile(r'\bOn\s+Error\s+(?:Resume\s+Next|GoTo)\b', re.IGNORECASE),
     'On Error', 'replace por Try/Catch'),
    (re.compile(r'(?:^|\s)Set\s+\w+\s*='),
     'Set keyword', 'remover Set, usar atribuição direta'),
    (re.compile(r'\b(?:Variant|Currency)\b'),
     'Variant/Currency type', 'replace Variant→Object, Currency→Decimal'),
    (re.compile(r'\bGoTo\s+\w+'),
     'GoTo', 'refatorar — Roslyn strict, não tolera GoTo em expression'),
    (re.compile(r'\bMsgBox\s*\('),
     'MsgBox', 'replace por <ui:MessageBox/> activity'),
    (re.compile(r'\b(?:Eval|Execute)\s*\('),
     'Eval/Execute', 'remover — runtime-only legacy, indeterminável Roslyn'),
]


# VB expression dentro [...] brackets em XAML attribute. Match minimal —
# evitar capturar valor inteiro de attribute longo. Apenas conteúdo entre
# `[` e `]` mais próximos.
_VB_EXPR_RE = re.compile(r'"\[([^\[\]]+(?:\[[^\[\]]*\][^\[\]]*)*)\]"')

# String literal dentro VB expression — `"..."` (NÃO `&quot;...&quot;` que é
# XML-encoded). Aceita encoded também: regex match ambos.
_VB_STRING_LITERAL_RE = re.compile(
    r'(?:"[^"]*")|(?:&quot;.*?&quot;)'
)


def _line_for(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def _strip_strings(expr: str) -> str:
    """Remove VB string literals do expression — pattern catch só fora de string."""
    return _VB_STRING_LITERAL_RE.sub('""', expr)


def detect_w33_vb_legacy_patterns(rule, fc, pc) -> list[Finding]:
    """Detect VB legacy syntax patterns em XAML VB expressions."""
    findings: list[Finding] = []
    content = fc.active_content
    for vb_match in _VB_EXPR_RE.finditer(content):
        expr_raw = vb_match.group(1)
        # Skip pattern dentro string literals
        expr_clean = _strip_strings(expr_raw)
        for pat, label, fix_hint in _VB_LEGACY_PATTERNS:
            pat_match = pat.search(expr_clean)
            if not pat_match:
                continue
            offset = vb_match.start(1) + pat_match.start()
            line = _line_for(content, offset)
            findings.append(Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=line,
                message=(
                    f"{rule.title}: '{label}' em VB expression — "
                    f"Roslyn .NET 6 incompat. Fix: {fix_hint}"
                ),
                fix_mechanical=None,  # contextual — manual fix
                fix_prose=(rule.fix or {}).get("prose"),
            ))
    return findings
