"""Heuristics for UiPathTeam.SharePoint.Activities migration leftovers."""
from __future__ import annotations

import re

from uip_engine._types import Finding


_RE_MSC_USER_VAR = re.compile(
    r'<Variable\b(?=[^>]*\bx:TypeArguments="msc:User")'
    r'(?=[^>]*\bName="(?P<name>[A-Za-z_]\w*)")[^>]*/>'
)
_RE_GET_WEB_LOGIN_USER = (
    r'<usa:GetWebLoginUser\b(?=[^>]*\bSharePointUser="\[{var}\]")[^>]*/>'
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _sharepoint_dep_is_2x(pc) -> bool:
    if pc is None:
        return True
    deps = pc.project_json.get("dependencies", {}) or {}
    raw = str(deps.get("UiPathTeam.SharePoint.Activities", ""))
    return bool(re.match(r"\[?2\.", raw))


def _whole_word_count(content: str, name: str) -> int:
    return len(re.findall(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", content))


def _safe_current_user_probe(content: str, var: str) -> bool:
    if not re.search(_RE_GET_WEB_LOGIN_USER.format(var=re.escape(var)), content):
        return False
    if f"{var}.Email" not in content:
        return False
    if f"{var} IsNot Nothing" not in content:
        return False
    # Strict shape: declaration, GetWebLoginUser output, null check, Email.
    return _whole_word_count(content, var) == 4


def detect_sharepoint_2x_csom_user_leftovers(rule, fc, pc):
    """SP-7: SharePoint 2.x REST no longer needs CSOM User probe."""
    if fc.path.suffix.lower() != ".xaml":
        return []
    if not _sharepoint_dep_is_2x(pc):
        return []
    content = fc.active_content
    if "msc:User" not in content or "usa:GetWebLoginUser" not in content:
        return []
    findings: list[Finding] = []
    for m in _RE_MSC_USER_VAR.finditer(content):
        var = m.group("name")
        if not _safe_current_user_probe(content, var):
            continue
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=_line_for(content, m.start()),
            message=f"{rule.title}: remover probe CSOM legacy de {var}",
            fix_mechanical={
                "type": "remove_sharepoint_2x_current_user_probe",
                "variable": var,
            },
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def _has_msc_usage(content: str) -> bool:
    without_xmlns = re.sub(r'\s+xmlns:msc="[^"]+"', "", content, count=1)
    return "msc:" in without_xmlns


def detect_sharepoint_2x_stale_csom_imports(rule, fc, pc):
    """SP-8: remove CSOM xmlns/import refs once no msc:* type remains."""
    if fc.path.suffix.lower() != ".xaml":
        return []
    if not _sharepoint_dep_is_2x(pc):
        return []
    content = fc.active_content
    if "Microsoft.SharePoint.Client" not in content and 'xmlns:msc="' not in content:
        return []
    if _has_msc_usage(content):
        return []
    marker = content.find("Microsoft.SharePoint.Client")
    if marker < 0:
        marker = content.find('xmlns:msc="')
    return [Finding(
        rule_id=rule.id,
        severity=rule.severity,
        category=rule.category,
        file=str(fc.path),
        line=_line_for(content, max(marker, 0)),
        message=f"{rule.title}: remover imports/references CSOM sem uso",
        fix_mechanical={"type": "remove_stale_csom_imports_and_refs"},
        fix_prose=(rule.fix or {}).get("prose"),
    )]
