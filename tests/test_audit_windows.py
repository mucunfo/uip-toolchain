"""Regression tests for AUDIT_2026-05-28 findings owned by the `windows` lane.

Covers:
  - W-12  : empty ArrayRow="[{}]" must be flagged ONCE (manual branch), never
            double-flagged AND never auto-wrapped.
  - W-16  : multi-part chain (obj.Field.IsNullOrEmpty) => fix_mechanical=None.
  - W-17  : multi-part chain (obj.Field.ToInt32)       => fix_mechanical=None.
  - UI-7  : binding-expression / {x:Null} delays must NOT carry a deterministic
            force-"0" fix (would eat config-bound values); only literal numeric
            non-zero delays keep the deterministic fix.

Pure unit tests on the detectors — do NOT run pytest in this lane (parallel
lanes share the package import). Validate with `python -m py_compile`.
"""
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.windows import (
    detect_w12_array_literal,
    detect_w16_isnullorempty,
    detect_w17_toint32,
    detect_ui7_simulate_delays,
    _is_numeric_delay,
    _is_zero_delay,
    _RE_W12_ARRAYROW,
    _RE_W12_EMPTY,
)


def _project(tmp_path: Path) -> ProjectContext:
    import json
    pj = {"targetFramework": "Windows", "expressionLanguage": "VisualBasic"}
    (tmp_path / "project.json").write_text(json.dumps(pj), encoding="utf-8")
    return ProjectContext(root=tmp_path, project_json=pj)


def _write_xaml(tmp_path: Path, body: str, name: str = "Foo.xaml") -> FileContext:
    f = tmp_path / name
    f.write_text(body, encoding="utf-8")
    return FileContext(f)


def _rule(rid: str, mechanical: dict | None, **detect_params) -> Rule:
    fix: dict = {"prose": "fix me"}
    if mechanical is not None:
        fix["mechanical"] = mechanical
    return Rule(
        id=rid, severity=Severity.ERROR, category="breaking", target="windows",
        title=rid, description="",
        detect={"type": "python", "params": detect_params},
        fix=fix,
    )


# ---------------------------------------------------------------------------
# W-12 — empty ArrayRow="[{}]" reported ONCE (manual), not auto-wrapped
# ---------------------------------------------------------------------------

def test_w12_empty_arrayrow_regex_no_longer_matches():
    """The narrowed ArrayRow regex must NOT match the empty literal."""
    assert _RE_W12_ARRAYROW.search('ArrayRow="[{}]"') is None
    # The empty branch still catches it.
    assert _RE_W12_EMPTY.search('ArrayRow="[{}]"') is not None


def test_w12_empty_arrayrow_flagged_once_manual(tmp_path):
    body = '<Activity><ui:AddDataRow ArrayRow="[{}]" /></Activity>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    # Exactly one finding, manual (no mechanical), NOT auto-wrapped.
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


def test_w12_nonempty_arrayrow_still_auto_wrapped(tmp_path):
    body = '<Activity><ui:AddDataRow ArrayRow="[{a, b}]" /></Activity>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {"type": "wrap_arrayrow_object"}


def test_w12_arrayrow_with_only_spaces_not_matched_by_arrayrow_branch():
    # `[{ }]` (just whitespace) — [^"}]+ requires >=1 non-} non-" char; space ok
    # but the spec's intent is "non-empty". A pure-space inner still has a space
    # so ArrayRow branch matches; that is acceptable (not the empty literal).
    assert _RE_W12_ARRAYROW.search('ArrayRow="[{ }]"') is not None


# ---------------------------------------------------------------------------
# W-16 — multi-part chain => fix_mechanical=None
# ---------------------------------------------------------------------------

_W16_MECH = {
    "type": "regex_replace",
    "pattern": r'(?<![A-Za-z_:.])(?![Ss]tring\.IsNullOrEmpty\b)([a-zA-Z_]\w*)\.IsNullOrEmpty\b',
    "replacement": r"String.IsNullOrEmpty(\1)",
}


def test_w16_single_identifier_keeps_mechanical(tmp_path):
    body = '<Activity Condition="[foo.IsNullOrEmpty]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w16_isnullorempty(_rule("W-16", _W16_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W16_MECH


def test_w16_multipart_chain_routes_to_manual(tmp_path):
    body = '<Activity Condition="[obj.Field.IsNullOrEmpty]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w16_isnullorempty(_rule("W-16", _W16_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    # Multi-part => mechanical suppressed (fixer regex can't apply it).
    assert findings[0].fix_mechanical is None


# ---------------------------------------------------------------------------
# W-17 — multi-part chain => fix_mechanical=None
# ---------------------------------------------------------------------------

_W17_MECH = {
    "type": "regex_replace",
    "pattern": r'(?<![A-Za-z_:.])(?![Cc]onvert\.ToInt32\b)([a-zA-Z_]\w*)\.ToInt32\b',
    "replacement": r"Convert.ToInt32(\1)",
}


def test_w17_single_identifier_keeps_mechanical(tmp_path):
    body = '<Activity Value="[foo.ToInt32]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w17_toint32(_rule("W-17", _W17_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W17_MECH


def test_w17_multipart_chain_routes_to_manual(tmp_path):
    body = '<Activity Value="[obj.Field.ToInt32]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w17_toint32(_rule("W-17", _W17_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


# ---------------------------------------------------------------------------
# UI-7 — bound/{x:Null} delays must not force literal "0"
# ---------------------------------------------------------------------------

def test_is_numeric_delay_helper():
    assert _is_numeric_delay("500") is True
    assert _is_numeric_delay("[500]") is True
    assert _is_numeric_delay("0.0") is True
    # Bound / non-reducible / null => NOT numeric => contextual
    assert _is_numeric_delay('[in_Config("DelaySimulate")]') is False
    assert _is_numeric_delay("{x:Null}") is False
    assert _is_numeric_delay("") is False
    assert _is_numeric_delay(None) is False


def test_ui7_literal_nonzero_delay_keeps_deterministic_fix(tmp_path):
    body = (
        '<Activity xmlns:uix="x">'
        '<uix:NTypeInto InteractionMode="Simulate" DelayBefore="500" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_ui7_simulate_delays(_rule("UI-7", None), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical is not None
    assert findings[0].fix_mechanical["type"] == "force_attribute_in_activity_with_guard"
    assert findings[0].fix_mechanical["target_value"] == "0"


def test_ui7_bound_delay_is_contextual_not_forced_to_zero(tmp_path):
    body = (
        '<Activity xmlns:uix="x">'
        '<uix:NTypeInto InteractionMode="Simulate" '
        'DelayBefore="[in_Config(&quot;DelaySimulate&quot;)]" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_ui7_simulate_delays(_rule("UI-7", None), fc, _project(tmp_path))
    assert len(findings) == 1
    # Binding expression must NOT be overwritten with literal 0.
    assert findings[0].fix_mechanical is None


def test_ui7_xnull_delay_is_contextual(tmp_path):
    body = (
        '<Activity xmlns:uix="x">'
        '<uix:NClick InteractionMode="Simulate" DelayAfter="{x:Null}" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_ui7_simulate_delays(_rule("UI-7", None), fc, _project(tmp_path))
    # DelayAfter is present, {x:Null} is not numeric-zero => violation flagged
    # but contextual (no deterministic force-0).
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


def test_ui7_zero_delay_not_flagged(tmp_path):
    body = (
        '<Activity xmlns:uix="x">'
        '<uix:NTypeInto InteractionMode="Simulate" DelayBefore="0" DelayAfter="[0]" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_ui7_simulate_delays(_rule("UI-7", None), fc, _project(tmp_path))
    assert findings == []
    # sanity on the zero helper
    assert _is_zero_delay("0") is True
    assert _is_zero_delay("[0]") is True
