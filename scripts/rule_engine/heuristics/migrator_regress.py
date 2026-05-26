"""Heuristics for Activity Migrator post-output regressions.

X-2 Property element with attribute (XAML invalid).

Activity Migrator UiPath GA (v25.10+) por vezes converte forma inline
de attribute (`<Foo Bar="v"/>`) para forma híbrida MAL-formada:

    <Foo Bar="v">
      <Foo.Bar Bar="v">   <-- INVALID: property element não aceita attribute
        <Literal Value="v"/>
      </Foo.Bar>
    </Foo>

Studio XAML parser rejeita c/ `XamlUnexpectedParseException: 'ATTRIBUTE'
inesperado na regra de análise 'NonemptyPropertyElement ::= . PROPERTYELEMENT
Content? ENDTAG.'`.

Caso real (2026-05-25): monitorar-transacoes-pendentes-performer,
contestacao-de-compras-coleta-anexos-performer — `<ui:LogMessage.Level
Level="Trace">...</ui:LogMessage.Level>` após upgrade Migrator.

Fixer: remove o bloco property element inteiro QUANDO parent tem
attr inline equivalente. Senão, strip apenas attribute do property
element (preserva inner content).
"""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


_PROPELEM_ATTR_RE = re.compile(
    r'<(?P<elem>[A-Za-z_][\w]*:[A-Za-z_][\w]*\.[A-Za-z_][\w]*)'
    r'(?P<attrs>\s+[A-Za-z_][\w:]*="[^"]*")+\s*>',
)


def _line_for(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def detect_x2_property_element_with_attribute(rule, fc, pc) -> list[Finding]:
    """Detect `<NS:Activity.Prop Attr="v">` (property element with attr).

    Property elements (containing `.` in tag name) cannot have attributes
    per XAML 2009 grammar. Migrator regression.
    """
    findings: list[Finding] = []
    content = fc.active_content
    for m in _PROPELEM_ATTR_RE.finditer(content):
        elem = m.group("elem")
        line = _line_for(content, m.start())
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=line,
            message=f"{rule.title}: <{elem} ...> property element c/ attribute",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
