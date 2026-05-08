"""REFramework variant detection helpers.

Markers configured via rules.yaml params (no hardcoded activity names).
"""
from __future__ import annotations

from scripts.rule_engine._types import Finding


def is_dispatcher(rule, fc, pc):
    """Detect dispatcher variant via marker activity declared em params.markers."""
    params = rule.detect.get("params", {}) or {}
    markers = params.get("markers") or []
    if not markers:
        return []
    if any(m in fc.active_content for m in markers):
        return [Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=1, message=rule.title,
        )]
    return []
