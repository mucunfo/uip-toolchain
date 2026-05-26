"""S-17: XML comment as direct child of <Activity> root quebra Studio compiler.

Background:
  Studio 23.10+ compiler XAML loader itera children de <Activity> esperando
  XmlElement. Comment direct child causa `Unable to cast XmlComment to XmlElement`
  durante preprocessing — build da biblioteca aborta.

  Comments DIRECT inside <Activity> root geralmente vêm de:
    - Mass-suppress scripts cosmeticos (VIOLA CLAUDE.md, build break confirmado)
    - Notas de documentacao mal-posicionadas (devem ir em sap2010:Annotation)

  Comments DENTRO de containers (Sequence, etc.) sao OK — Studio loader so quebra
  no root level.

Detector: scan first ~500 bytes pos `<Activity` open tag. Se `<!--` aparece
ANTES do primeiro child element (x:Members, x:Property, Sequence, etc.), flag.

Fix mecanico: remover o comment (linha inteira + trailing newline).
"""
from __future__ import annotations

import re
from uip_engine._types import Finding


# Match Activity root open tag (with all xmlns attrs) followed by content
# until first child element.
_ACTIVITY_OPEN_RE = re.compile(r'<Activity\b[^>]*?>', re.DOTALL)

# XmlComment in the gap between Activity-open and first child element.
# Comment pattern: <!-- ... -->. Capture full match for fix.
_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)

# Detect the first non-comment, non-whitespace element AFTER Activity open.
# Look for `<NamePrefix:Name` or `<Name` start (excluding `<!--` and `<?`).
_FIRST_ELEMENT_RE = re.compile(r'<(?!!|\?)[A-Za-z]')


def _line_for(content: str, offset: int) -> int:
    return content.count('\n', 0, offset) + 1


def detect_s17_xml_comment_root(rule, fc, pc):
    """Detect XmlComment as direct child of <Activity> root."""
    content = fc.active_content
    m = _ACTIVITY_OPEN_RE.search(content)
    if not m:
        return []
    activity_end = m.end()
    # Find first element after Activity open
    first_elem_m = _FIRST_ELEMENT_RE.search(content, activity_end)
    if not first_elem_m:
        return []
    first_elem_start = first_elem_m.start()
    # Region between Activity open and first child element
    gap = content[activity_end:first_elem_start]
    findings = []
    for cm in _COMMENT_RE.finditer(gap):
        comment_abs = activity_end + cm.start()
        line = _line_for(content, comment_abs)
        body = cm.group(0)[4:-3].strip()[:80]
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=line,
            message=(
                f"{rule.title}: comment '<!-- {body} -->' como direct child de "
                f"<Activity>. Studio compiler aborta com 'Unable to cast XmlComment "
                f"to XmlElement'. Mover para sap2010:Annotation ou remover."
            ),
            fix_mechanical={"type": "remove_xml_comment_root"},
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
