"""Heuristics for project.json J-* rules."""
from __future__ import annotations

import json

from scripts.rule_engine._types import Finding


def _load(fc):
    if not str(fc.path).endswith("project.json"):
        return None
    try:
        return json.loads(fc.content)
    except Exception:
        return None


def _finding(rule, fc, msg):
    return Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1, message=msg,
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )


def _dotted_get(data, path):
    """Resolve dotted path, e.g. 'runtimeOptions.excludedLoggedData'."""
    if not path:
        return None
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def _skip_by_when(data, skip_when):
    """skip_when: {field: [values...]}. Return True if any matches."""
    if not skip_when:
        return False
    for field, allowed in (skip_when or {}).items():
        val = _dotted_get(data, field)
        if val is None:
            continue
        if isinstance(allowed, (list, tuple)):
            if val in allowed:
                return True
        elif val == allowed:
            return True
    return False


def detect_j3_required_packages(rule, fc, pc):
    data = _load(fc)
    if data is None:
        return []
    params = rule.detect.get("params", {}) or {}
    required = params.get("packages") or []
    if not required:
        return []
    if _skip_by_when(data, params.get("skip_when")):
        return []
    deps = data.get("dependencies", {}) or {}
    missing = [p for p in required if p not in deps]
    if not missing:
        return []
    return [_finding(rule, fc, f"{rule.title}: faltam {missing}")]


def detect_j6_excluded_logged(rule, fc, pc):
    data = _load(fc)
    if data is None:
        return []
    params = rule.detect.get("params", {}) or {}
    path = params.get("path", "runtimeOptions.excludedLoggedData")
    required = params.get("required_patterns") or []
    if not required:
        return []
    excluded = _dotted_get(data, path) or []
    excluded_str = " ".join(str(x) for x in excluded).lower()
    missing = [p for p in required if p.lower() not in excluded_str]
    if not missing:
        return []
    return [_finding(rule, fc, f"{rule.title}: faltam {missing}")]


def detect_j7_user_interaction_consistency(rule, fc, pc):
    data = _load(fc)
    if data is None:
        return []
    params = rule.detect.get("params", {}) or {}
    name_path = params.get("name_path", "name")
    flag_path = params.get("flag_path", "requiresUserInteraction")
    performer_markers = [m.lower() for m in (params.get("performer_markers") or [])]
    attended_markers = [m.lower() for m in (params.get("attended_markers") or [])]
    attended_neg = [m.lower() for m in (params.get("attended_negative_markers") or [])]
    name = str(_dotted_get(data, name_path) or "").lower()
    flag = _dotted_get(data, flag_path)
    if flag is None:
        return []
    is_performer = any(m in name for m in performer_markers)
    is_attended = any(m in name for m in attended_markers) and not any(
        m in name for m in attended_neg
    )
    if is_performer and flag is True:
        return [_finding(rule, fc, f"{rule.title}: performer com {flag_path}=true")]
    if is_attended and flag is False:
        return [_finding(rule, fc, f"{rule.title}: attended com {flag_path}=false")]
    return []
