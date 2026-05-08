"""Heuristics V-* — value-type initialization checks.

V-1: `Default="[Nothing]"` em Variable/Property de value-type (Int32, Int64,
     Boolean, Double, Decimal, Single, Byte, Char, DateTime).
     Compila em VB.NET mas vira `default(T)` implícito (0/False/MinValue),
     mascarando intent. Anti-padrão: use default explícito ou tipo Nullable.
"""
from __future__ import annotations
import re

from scripts.rule_engine._types import Finding


_VALUE_TYPES = frozenset({
    "Int32", "Int64", "Int16",
    "Double", "Single", "Decimal",
    "Boolean",
    "Byte", "SByte",
    "Char",
    "DateTime", "TimeSpan",
})


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _strip_ns(t: str) -> str:
    return t.split(":", 1)[-1] if ":" in t else t


# Variable inline: Default="..."
_RE_VAR_INLINE = re.compile(
    r'<Variable\b(?P<attrs>[^>]*)/?>',
    re.DOTALL,
)
# Variable open + Variable.Default block
_RE_VAR_OPEN = re.compile(
    r'<Variable\b(?P<attrs>[^>]*?)>(?P<inner>.*?)</Variable>',
    re.DOTALL,
)
_RE_VAR_DEFAULT_BLOCK = re.compile(
    r'<Variable\.Default\b[^>]*>\s*(?P<value>.*?)\s*</Variable\.Default>',
    re.DOTALL,
)


def _is_nothing(value: str) -> bool:
    """Match `[Nothing]`, `[ Nothing ]`, plain `Nothing`, ou `{x:Null}`."""
    s = value.strip()
    # XAML literal {x:Null} — UiPath designer placeholder for "unset"
    if s == "{x:Null}":
        return True
    # VB expression brackets [Nothing]
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    return s.lower() == "nothing"


def _extract_attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{re.escape(name)}="([^"]*)"', attrs)
    return m.group(1) if m else None


def detect_v1_nothing_in_value_type(rule, fc, pc):
    """V-1: Variable/Property value-type não deve ter Default=[Nothing] / {x:Null}."""
    p = rule.detect.get("params", {}) or {}
    extra = frozenset(p.get("extra_value_types") or ())
    targets = _VALUE_TYPES | extra

    content = fc.active_content
    findings: list[Finding] = []

    # 1. <Variable ... Default="..."  (inline self-close OR open)
    seen_var_offsets = set()
    for m in re.finditer(
        r'<Variable\b(?P<attrs>[^>]*?)(?P<self>/)?>',
        content,
        re.DOTALL,
    ):
        attrs = m.group("attrs")
        type_args = _extract_attr(attrs, "x:TypeArguments")
        name = _extract_attr(attrs, "Name") or "<unnamed>"
        if not type_args:
            continue
        local = _strip_ns(type_args.strip())
        if local not in targets:
            continue
        seen_var_offsets.add(m.start())
        # check inline Default attribute
        default_inline = _extract_attr(attrs, "Default")
        if default_inline is not None and _is_nothing(default_inline):
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, m.start()),
                message=(
                    f"{rule.title}: Variable '{name}' ({local}) tem Default=[Nothing] "
                    f"— value-type vira default(T) implícito (0/False/MinValue). "
                    f"Use default explícito ou Nullable<{local}>."
                ),
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))

    # 2. <Variable.Default> block child (when Variable has open/close tags)
    for m in _RE_VAR_OPEN.finditer(content):
        attrs = m.group("attrs")
        inner = m.group("inner")
        type_args = _extract_attr(attrs, "x:TypeArguments")
        name = _extract_attr(attrs, "Name") or "<unnamed>"
        if not type_args:
            continue
        local = _strip_ns(type_args.strip())
        if local not in targets:
            continue
        db = _RE_VAR_DEFAULT_BLOCK.search(inner)
        if not db:
            continue
        if _is_nothing(db.group("value")):
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, m.start()),
                message=(
                    f"{rule.title}: Variable '{name}' ({local}) tem "
                    f"<Variable.Default>Nothing</> — value-type vira default(T) implícito. "
                    f"Use default explícito ou Nullable<{local}>."
                ),
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))

    return findings
