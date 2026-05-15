"""Tests for V-4 — DisplayName/Annotation com entity double-escape.

V-4 cobre attrs plain-text (DisplayName, AnnotationText) — diferente de
V-3 que cobre attrs de expressão VB (Expression, Condition, ExpressionText).

Bug pattern no FILE: `DisplayName="texto -&amp;amp;gt; algo"`.
Studio UI renderiza literal `&gt;` em vez de `>`.
Fix mecânico: `&amp;amp;` → `&amp;` (single-encode).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.rule_engine._types import Rule, Severity
from scripts.rule_engine.context import FileContext
from scripts.rule_engine.detectors import detect_regex
from scripts.rule_engine.fixers import apply_regex_replace
from scripts.rule_engine.loader import load_rules
from scripts.rule_engine import detectors as det_mod
from scripts.rule_engine import fixers as fix_mod


def _v4_rule_from_yaml() -> Rule:
    """Load V-4 directly from rules.yaml — confirma schema válido + pin do
    pattern/replacement reais que vão pro fixer."""
    rules_path = Path(__file__).resolve().parents[1] / "rules.yaml"
    rules = load_rules(
        rules_path,
        registered_detectors=set(det_mod.REGISTRY.keys()),
        registered_fixers=set(fix_mod.REGISTRY.keys()),
    )
    v4 = next((r for r in rules if r.id == "V-4"), None)
    assert v4 is not None, "V-4 not loaded from rules.yaml"
    return v4


def _write_xaml(tmp_path: Path, body: str, name: str = "Foo.xaml") -> FileContext:
    f = tmp_path / name
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        f"{body}\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    return FileContext(f)


# ============================================================================
# Detect — V-4 flags double-encode em DisplayName / AnnotationText
# ============================================================================

def test_v4_flags_displayname_double_amp_gt(tmp_path):
    """`DisplayName="Item -&amp;amp;gt; Próximo"` → 1 finding WARN."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:Sequence DisplayName="Item -&amp;amp;gt; Próximo"/>\n',
    )
    findings = detect_regex(rule, fc, None)
    assert len(findings) == 1
    assert findings[0].rule_id == "V-4"
    assert findings[0].severity == Severity.WARN
    assert findings[0].fix_mechanical is not None
    assert findings[0].fix_mechanical.get("type") == "regex_replace"


def test_v4_flags_annotation_text_double_amp_lt(tmp_path):
    """`AnnotationText` também — não só DisplayName."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:Sequence sap2010:Annotation.AnnotationText="x &amp;amp;lt; y"/>\n',
    )
    findings = detect_regex(rule, fc, None)
    assert len(findings) == 1


def test_v4_silent_on_single_encode(tmp_path):
    """`DisplayName="Item -&amp;gt; Próximo"` (single-encode correto)
    → 0 findings."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:Sequence DisplayName="Item -&amp;gt; Próximo"/>\n',
    )
    assert detect_regex(rule, fc, None) == []


def test_v4_silent_on_plain_displayname(tmp_path):
    """DisplayName sem entity entities — não toca."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:Sequence DisplayName="Tudo normal"/>\n',
    )
    assert detect_regex(rule, fc, None) == []


def test_v4_does_not_match_vb_expression_context(tmp_path):
    """V-4 escope = DisplayName/AnnotationText only. `Expression=...` é
    coberto por V-3. V-4 NÃO deve disparar nele."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <something Expression="[x &amp;amp;gt; 0]"/>\n',
    )
    assert detect_regex(rule, fc, None) == []


def test_v4_multiple_matches_same_file(tmp_path):
    """Duas violations no mesmo arquivo → dois findings."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:A DisplayName="X -&amp;amp;gt; Y"/>\n'
        '  <ui:B DisplayName="Q -&amp;amp;lt; R"/>\n',
    )
    findings = detect_regex(rule, fc, None)
    assert len(findings) == 2


# ============================================================================
# Fix — V-4 mechanical regex_replace converge para single-encode
# ============================================================================

def test_v4_fix_converts_double_to_single_encode(tmp_path):
    """Fix mecânico transforma `&amp;amp;gt;` → `&amp;gt;`. Aplicado pelo
    fixer registry `regex_replace` com pattern/replacement do YAML."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:Sequence DisplayName="Item -&amp;amp;gt; Próximo"/>\n',
    )
    mech = rule.fix["mechanical"]
    changed = apply_regex_replace(fc.path, mech, dry_run=False)
    assert changed is True

    # Após fix, file content tem `&amp;gt;` (single-encode).
    after = fc.path.read_text(encoding="utf-8")
    assert 'DisplayName="Item -&amp;gt; Próximo"' in after
    assert "&amp;amp;" not in after

    # Re-run detect → 0 findings (idempotente).
    fc2 = FileContext(fc.path)
    assert detect_regex(rule, fc2, None) == []


def test_v4_fix_handles_quot_entity(tmp_path):
    """Pattern cobre gt|lt|quot|amp — testa `quot` que não era V-3."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:A DisplayName="x &amp;amp;quot; y"/>\n',
    )
    findings = detect_regex(rule, fc, None)
    assert len(findings) == 1

    mech = rule.fix["mechanical"]
    apply_regex_replace(fc.path, mech, dry_run=False)
    after = fc.path.read_text(encoding="utf-8")
    assert "&amp;amp;" not in after
    assert "&amp;quot;" in after


def test_v4_fix_converges_via_fixpoint_loop(tmp_path):
    """Triple-encode `&amp;amp;amp;gt;` requer 2 passes pra convergir.
    Cada pass strip uma camada — engine usa fixpoint loop em produção."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:A DisplayName="triple &amp;amp;amp;gt; encoded"/>\n',
    )
    mech = rule.fix["mechanical"]

    # Pass 1: detect emite finding, fix strip 1 camada
    assert len(detect_regex(rule, fc, None)) == 1
    apply_regex_replace(fc.path, mech, dry_run=False)

    # Pass 2: ainda detect (sobrou 1 camada), fix converge
    fc2 = FileContext(fc.path)
    if detect_regex(rule, fc2, None):
        apply_regex_replace(fc.path, mech, dry_run=False)

    # Final: zero findings
    fc3 = FileContext(fc.path)
    assert detect_regex(rule, fc3, None) == []
    after = fc.path.read_text(encoding="utf-8")
    assert "&amp;amp;" not in after
    assert "&amp;gt;" in after


def test_v4_fix_is_idempotent_after_convergence(tmp_path):
    """Re-aplicar fix após convergir → False (no-change)."""
    rule = _v4_rule_from_yaml()
    fc = _write_xaml(
        tmp_path,
        '  <ui:Sequence DisplayName="OK -&amp;gt; Próximo"/>\n',
    )
    mech = rule.fix["mechanical"]
    # File já está single-encode — fixer NÃO deve mudar.
    assert apply_regex_replace(fc.path, mech, dry_run=False) is False


# ============================================================================
# Schema — V-4 carrega corretamente
# ============================================================================

def test_v4_loaded_with_apply_class_deterministic():
    """V-4 deve declarar fix.apply_class=deterministic + mechanical regex_replace."""
    rule = _v4_rule_from_yaml()
    assert rule.severity == Severity.WARN
    assert rule.category == "architectural"
    assert rule.target == "all"
    assert rule.fix is not None
    assert rule.fix.get("apply_class") == "deterministic"
    mech = rule.fix.get("mechanical") or {}
    assert mech.get("type") == "regex_replace"
    # Confirma pattern compila (loader já valida, mas sanity check)
    assert re.compile(mech["pattern"])
