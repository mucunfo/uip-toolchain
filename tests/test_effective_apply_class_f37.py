"""F37 tests — effective apply_class per-finding.

`apply_class` describes fix ownership, not deploy safety. Any active ERROR
blocks PASS; contextual/structural WARN/INFO remain PENDING_REVIEW notes.

Cobertura:
  - Rule deterministic + fix_mechanical=dict → deterministic (blocking)
  - Rule deterministic + fix_mechanical=None → contextual, still blocking if ERROR
  - Rule contextual → contextual, still blocking if ERROR
  - Rule structural → structural, still blocking if ERROR
  - Gate-injected UIPATH:PREFLIGHT/ANALYZE_HALT/PACK_HALT/CLI_REQUIRED_PACKAGE_MISSING → deterministic (blocking)
  - Gate-injected UIPATH:LOAD/ST-SEC-008/PACK → contextual, still blocking if ERROR
  - Gate-injected NU1605 → contextual, still blocking if ERROR
"""
from __future__ import annotations

import pytest

from uip_engine._types import Finding, Rule, Severity, ValidationResult
from uip_engine.cli import (
    _effective_apply_class,
    _is_blocking_error,
    _classify_contextual_pending,
    _classify_deploy_blockers,
)


def _det_rule():
    return Rule(
        id="DET-RULE",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="",
        description="",
        detect={"type": "python"},
        fix={"apply_class": "deterministic"},
    )


def _ctx_rule():
    return Rule(
        id="CTX-RULE",
        severity=Severity.ERROR,
        category="quality",
        target="all",
        title="",
        description="",
        detect={"type": "python"},
        fix={"apply_class": "contextual"},
    )


def _struct_rule():
    return Rule(
        id="STR-RULE",
        severity=Severity.ERROR,
        category="quality",
        target="all",
        title="",
        description="",
        detect={"type": "python"},
        fix={"apply_class": "structural"},
    )


def _finding(rule_id, sev=Severity.ERROR, fix_mech=None):
    return Finding(
        rule_id=rule_id, severity=sev, category="x",
        file="f.xaml", line=1, message="",
        fix_mechanical=fix_mech,
    )


def test_deterministic_with_fix_mechanical_blocks():
    ridx = {"DET-RULE": _det_rule()}
    f = _finding("DET-RULE", fix_mech={"type": "rename_attribute", "from": "x", "to": "y"})
    assert _effective_apply_class(f, ridx) == "deterministic"
    assert _is_blocking_error(f, ridx) is True


def test_deterministic_without_fix_mechanical_downgrades_to_contextual():
    """F36 CCS-1 SecureString guard case: detector promete fix mas safety
    guard sets fix_mechanical=None → fix é manual, mas ERROR bloqueia PASS."""
    ridx = {"DET-RULE": _det_rule()}
    f = _finding("DET-RULE", fix_mech=None)
    assert _effective_apply_class(f, ridx) == "contextual"
    assert _is_blocking_error(f, ridx) is True


def test_contextual_error_blocks():
    ridx = {"CTX-RULE": _ctx_rule()}
    f = _finding("CTX-RULE")
    assert _effective_apply_class(f, ridx) == "contextual"
    assert _is_blocking_error(f, ridx) is True


def test_structural_error_blocks():
    ridx = {"STR-RULE": _struct_rule()}
    f = _finding("STR-RULE")
    assert _effective_apply_class(f, ridx) == "structural"
    assert _is_blocking_error(f, ridx) is True


@pytest.mark.parametrize("rid", [
    "UIPATH:PREFLIGHT",
    "UIPATH:ANALYZE_HALT",
    "UIPATH:PACK_HALT",
    "UIPATH:CLI_REQUIRED_PACKAGE_MISSING",
])
def test_pipeline_integrity_unknown_rules_block(rid):
    """Pipeline-integrity rule_ids = engine não pôde validar projeto.
    BLOQUEIA PASS por segurança (resultado do pipeline não confiável)."""
    ridx = {}
    f = _finding(rid)
    assert _effective_apply_class(f, ridx) == "deterministic"
    assert _is_blocking_error(f, ridx) is True


@pytest.mark.parametrize("rid", [
    "UIPATH:LOAD",
    "UIPATH:ST-SEC-008",
    "UIPATH:ST-NMG-004",
    "UIPATH:PACK",
    "UIPATH:NU1605",
])
def test_studio_analyzer_unknown_rules_are_contextual(rid):
    """Studio analyzer findings keep contextual fix ownership, but ERROR blocks."""
    ridx = {}
    f = _finding(rid)
    assert _effective_apply_class(f, ridx) == "contextual"
    assert _is_blocking_error(f, ridx) is True


def test_warn_severity_never_blocks():
    """Severity != ERROR → nunca blocking, independente de class."""
    ridx = {"DET-RULE": _det_rule()}
    f = _finding("DET-RULE", sev=Severity.WARN,
                 fix_mech={"type": "rename_attribute", "from": "x", "to": "y"})
    assert _is_blocking_error(f, ridx) is False


def test_suppressed_finding_never_blocks():
    ridx = {"DET-RULE": _det_rule()}
    f = _finding("DET-RULE", fix_mech={"type": "x"})
    f.suppressed = True
    assert _is_blocking_error(f, ridx) is False


def test_pending_excludes_errors_even_when_contextual():
    """ERROR manual/contextual is a deploy blocker, not PASS_WITH_NOTES."""
    ridx = {"DET-RULE": _det_rule()}
    result = ValidationResult()
    result.add(_finding("DET-RULE", fix_mech=None))     # safety-guarded
    result.add(_finding("DET-RULE", fix_mech={"x": 1}))  # normal blocking
    pending = _classify_contextual_pending(result, ridx)
    assert pending == []


def test_pending_includes_contextual_warns():
    """PASS_WITH_NOTES is for non-error contextual findings."""
    ridx = {}
    result = ValidationResult()
    result.add(_finding("UIPATH:LOAD", sev=Severity.WARN))
    result.add(_finding("UIPATH:ST-SEC-008", sev=Severity.WARN))
    result.add(_finding("UIPATH:PREFLIGHT"))  # integrity → NOT pending
    pending = _classify_contextual_pending(result, ridx)
    ids = sorted(f.rule_id for f in pending)
    assert ids == ["UIPATH:LOAD", "UIPATH:ST-SEC-008"]


def test_pending_excludes_halt_severity():
    ridx = {"DET-RULE": _det_rule()}
    result = ValidationResult()
    result.add(_finding("DET-RULE", sev=Severity.HALT))
    pending = _classify_contextual_pending(result, ridx)
    assert len(pending) == 0


def test_deploy_blockers_include_all_errors_and_halt():
    ridx = {
        "DET-RULE": _det_rule(),
        "CTX-RULE": _ctx_rule(),
        "STR-RULE": _struct_rule(),
    }
    result = ValidationResult()
    result.add(_finding("DET-RULE", fix_mech={"type": "x"}))
    result.add(_finding("CTX-RULE"))
    result.add(_finding("STR-RULE"))
    result.add(_finding("UIPATH:LOAD"))
    result.add(_finding("DET-RULE", sev=Severity.HALT))

    blockers = _classify_deploy_blockers(result, ridx)

    assert [f.rule_id for f in blockers] == [
        "DET-RULE",
        "CTX-RULE",
        "STR-RULE",
        "UIPATH:LOAD",
        "DET-RULE",
    ]
