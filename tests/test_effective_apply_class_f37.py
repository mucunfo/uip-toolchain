"""F37 tests — effective apply_class per-finding.

Engine só bloqueia PASS pelo que pode auto-fixar mecanicamente. Findings
que sinalizam problema real mas SEM fix_mechanical (safety guard preventiva,
gate-injected do Studio analyzer) → effective contextual → PENDING_REVIEW.

Cobertura:
  - Rule deterministic + fix_mechanical=dict → deterministic (blocking)
  - Rule deterministic + fix_mechanical=None → contextual (PENDING)
  - Rule contextual → contextual (existing)
  - Rule structural → structural (existing)
  - Gate-injected UIPATH:PREFLIGHT/ANALYZE_HALT/PACK_HALT → deterministic (blocking)
  - Gate-injected UIPATH:LOAD/ST-SEC-008/PACK → contextual (PENDING)
  - Gate-injected NU1605 → contextual (PENDING)
"""
from __future__ import annotations

import pytest

from scripts.rule_engine._types import Finding, Rule, Severity, ValidationResult
from scripts.rule_engine.cli import (
    _effective_apply_class,
    _is_blocking_error,
    _classify_contextual_pending,
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
    guard sets fix_mechanical=None → não bloqueia PASS, vai pra PENDING."""
    ridx = {"DET-RULE": _det_rule()}
    f = _finding("DET-RULE", fix_mech=None)
    assert _effective_apply_class(f, ridx) == "contextual"
    assert _is_blocking_error(f, ridx) is False


def test_contextual_rule_never_blocks():
    ridx = {"CTX-RULE": _ctx_rule()}
    f = _finding("CTX-RULE")
    assert _effective_apply_class(f, ridx) == "contextual"
    assert _is_blocking_error(f, ridx) is False


def test_structural_rule_never_blocks():
    ridx = {"STR-RULE": _struct_rule()}
    f = _finding("STR-RULE")
    assert _effective_apply_class(f, ridx) == "structural"
    assert _is_blocking_error(f, ridx) is False


@pytest.mark.parametrize("rid", [
    "UIPATH:PREFLIGHT",
    "UIPATH:ANALYZE_HALT",
    "UIPATH:PACK_HALT",
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
    """Studio analyzer findings (qualquer UIPATH:*) NÃO bloqueiam.
    Engine não auto-fixa Studio analyzer issues — user revisa via Studio UI."""
    ridx = {}
    f = _finding(rid)
    assert _effective_apply_class(f, ridx) == "contextual"
    assert _is_blocking_error(f, ridx) is False


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


def test_pending_includes_deterministic_without_fix_mechanical():
    """F37: PENDING_REVIEW list inclui findings safety-guarded (rule
    deterministic mas fix_mechanical=None)."""
    ridx = {"DET-RULE": _det_rule()}
    result = ValidationResult()
    result.add(_finding("DET-RULE", fix_mech=None))     # safety-guarded
    result.add(_finding("DET-RULE", fix_mech={"x": 1}))  # normal blocking
    pending = _classify_contextual_pending(result, ridx)
    assert len(pending) == 1
    assert pending[0].fix_mechanical is None


def test_pending_includes_studio_analyzer_unknown_rules():
    """PENDING_REVIEW list inclui UIPATH:LOAD/ST-*/PACK (gate-injected,
    unknown rule) pra que usuário veja sem precisar abrir Studio."""
    ridx = {}
    result = ValidationResult()
    result.add(_finding("UIPATH:LOAD"))
    result.add(_finding("UIPATH:ST-SEC-008"))
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
