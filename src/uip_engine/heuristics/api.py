"""API heuristics."""
from __future__ import annotations

import re

from .._types import Finding


_MUTATING_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_RE_HTTP_CLIENT_TAG = re.compile(
    r'<(?P<prefix>[A-Za-z_][\w.-]*):HttpClient\b(?P<attrs>[^>]*?)(?P<closer>/?>)',
    re.DOTALL,
)
_RE_ATTR_KV = re.compile(r'([A-Za-z_][\w.:.-]*)="([^"]*)"')


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def detect_api1_mutating_http_continue_on_error(rule, fc, pc) -> list[Finding]:
    """API-1: mutating HTTP methods must not swallow failures.

    Emits a scoped mechanical fix per offending open-tag. The fixer requires
    both guards (`Method=<mutating>` and `ContinueOnError=True`) so it does not
    add explicit `False` to safe calls that simply rely on UiPath's default.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content or ""
    fix_prose = (rule.fix or {}).get("prose")
    findings: list[Finding] = []

    for m in _RE_HTTP_CLIENT_TAG.finditer(content):
        attrs = {am.group(1): am.group(2) for am in _RE_ATTR_KV.finditer(m.group("attrs"))}
        method_raw = (attrs.get("Method") or "").strip()
        if method_raw.upper() not in _MUTATING_HTTP_METHODS:
            continue
        if attrs.get("ContinueOnError") != "True":
            continue

        line = _line_for(content, m.start())
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=line,
                message=(
                    f'{rule.title}: <{m.group("prefix")}:HttpClient> '
                    f'Method="{method_raw}" com ContinueOnError="True"'
                ),
                fix_mechanical={
                    "type": "force_attribute_in_activity_with_guards",
                    "prefix": m.group("prefix"),
                    "activity_local": "HttpClient",
                    "guards": {
                        "Method": method_raw,
                        "ContinueOnError": "True",
                    },
                    "attr_name": "ContinueOnError",
                    "target_value": "False",
                    "tag_line": line,
                },
                fix_prose=fix_prose,
            )
        )

    return findings
