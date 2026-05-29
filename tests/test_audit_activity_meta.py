"""Regression tests for AUDIT_2026-05-28 finding M-2 (detector side).

M-2 is apply_class=deterministic (rules.yaml) → fix --apply auto-applies the
add_property_element mechanical fixer with no human review. The audit found two
detector-side defects in heuristics/activity_meta._check_required_missing:

  M-2 (a) — the fix_mechanical dict never carried the arg `direction`, so the
            fixer hardcoded <InArgument> even for required Out / InOut args
            (e.g. RemoveDataRow.DataTable is InOut, FindFirstLastDataRowX.
            LastRowIndex is Out). Wrong argument element → Studio load error.
            FIX: detector now passes "direction" (In|Out|InOut) in the mech.

  M-2 (b) — the detector forwarded generic ('IList<T>', 'Nullable<...>') and
            unresolvable ('?', 'T', type-params) types verbatim. The fixer then
            produced x:TypeArguments="...<...>" (malformed XML, rolled back =
            silent no-op on a breaking ERROR) or "System.?" / "System.T"
            (well-formed but an invalid .NET type → persists, Studio load
            error). FIX: detector emits NO fix_mechanical for these types,
            degrading M-2 to a manual/contextual finding for that arg.

These tests exercise ONLY the detector (this lane's owned file). The coupled
fixer change (wrapper-by-direction, Out/InOut no default literal) is verified in
the fixers lane. The detector side is designed to be safe in isolation: passing
"direction" is additive (fixer FALLBACK keeps current <InArgument> behavior when
the key is absent), and emitting None mech short-circuits the bad path.

NOTE: per audit harness policy this file is syntax-validated (py_compile) only;
it runs under pytest in the reconciliation phase.
"""
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity, Category
from uip_engine.context import FileContext
from uip_engine.heuristics.activity_meta import (
    detect_m2_required_missing,
    get_schema,
)
from uip_engine.heuristics import activity_meta as am


FIXTURES = Path(__file__).parent / "fixtures" / "activity_meta"

# The real M-2 rule (rules.yaml) is deterministic AND declares a rule-level
# mechanical fixer. We replicate that here so the test proves _emit_no_mech
# truly forces finding.fix_mechanical=None (it must NOT fall back to this
# rule-level mechanical spec, otherwise _effective_apply_class would still
# treat the finding as deterministic and keep it a blocking ERROR).
_M2_FIX = {
    "apply_class": "deterministic",
    "prose": "Adicionar property element para o arg required.",
    "mechanical": {"type": "add_property_element"},
}


def _rule_m2() -> Rule:
    return Rule(
        id="M-2",
        severity=Severity.ERROR,
        category=Category.METADATA,
        target="all",
        title="Argumento required ausente em activity",
        description="",
        detect={
            "type": "python",
            "params": {
                "module": "uip_engine.heuristics.activity_meta",
                "function": "detect_m2_required_missing",
            },
        },
        fix=_M2_FIX,
    )


def _xaml(*activity_tags: str) -> str:
    body = "\n".join(f"  {t}" for t in activity_tags)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:ui="http://schemas.uipath.com/workflow/activities"\n'
        '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        f"{body}\n"
        "</Activity>\n"
    )


def _run(content: str):
    fixture = FIXTURES / "_tmp_audit_m2.xaml"
    fixture.write_text(content, encoding="utf-8")
    try:
        return detect_m2_required_missing(_rule_m2(), FileContext(path=fixture), None)
    finally:
        fixture.unlink(missing_ok=True)


def _finding_for_arg(findings, arg_name):
    for f in findings:
        # message form: "...falta arg required 'ArgName' (tipo ...)"
        if f"'{arg_name}'" in f.message:
            return f
    return None


# ---------------------------------------------------------------------------
# Unit: _is_mech_unresolvable_type — the pure type-classification helper
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("t", [
    "Collections.Generic.IList<T>",          # open generic, '<' inside
    "Nullable<UiPath.Excel.PivotTableLayoutRowType>",
    "System.Collections.Generic.List<System.String>",
    "?",                                       # schema could not resolve type
    "T",                                       # bare type parameter
    "TResult",                                 # type-param convention (T+Upper)
    "TKey",
    "T1",                                      # type-param convention (T+digit)
])
def test_is_mech_unresolvable_true(t):
    assert am._is_mech_unresolvable_type(t) is True


@pytest.mark.parametrize("t", [
    "System.String",
    "System.Data.DataTable",
    "Data.DataTable",
    "Int32",
    "UiPath.Core.GenericValue",
    "System.Boolean",
    "Table",            # starts with 'T' but second char is lowercase -> concrete
    "TimeSpan",         # 'T' + 'i' (lowercase) -> concrete .NET type, resolvable
    "Type",             # 'T' + 'y' (lowercase) -> concrete .NET System.Type
])
def test_is_mech_unresolvable_false_for_concrete_types(t):
    assert am._is_mech_unresolvable_type(t) is False


def test_is_mech_unresolvable_false_for_none_and_empty():
    # None/"" -> fixer uses x:Object fallback (valid XAML); keep mechanical.
    assert am._is_mech_unresolvable_type(None) is False
    assert am._is_mech_unresolvable_type("") is False


# ---------------------------------------------------------------------------
# Integration: detector emits `direction` in the mech for resolvable args
# (M-2 (a) — fixer needs it to pick <In|Out|InOut Argument>)
# ---------------------------------------------------------------------------

def test_m2_mech_carries_direction_inout():
    """FormatValue.Value is a required InOut arg; the emitted mech must carry
    direction='InOut' so the fixer emits <InOutArgument>, not <InArgument>."""
    schema = get_schema()
    if not _activity_resolves(schema, "FormatValue", "Value", "InOut"):
        pytest.skip("schema no longer has FormatValue.Value required InOut")
    findings = _run(_xaml('<ui:FormatValue DisplayName="Format" />'))
    f = _finding_for_arg(findings, "Value")
    assert f is not None, "expected M-2 finding for missing required Value"
    assert f.fix_mechanical is not None, "InOut arg with concrete type must keep mech"
    assert f.fix_mechanical.get("type") == "add_property_element"
    assert f.fix_mechanical.get("direction") == "InOut"
    # InOut concrete type is resolvable -> prop_type forwarded
    assert "<" not in (f.fix_mechanical.get("prop_type") or "")


def test_m2_mech_carries_direction_out():
    """FindFirstLastDataRowX.LastRowIndex is a required Out arg (Int32) ->
    mech direction must be 'Out'."""
    schema = get_schema()
    if not _activity_resolves(schema, "FindFirstLastDataRowX", "LastRowIndex", "Out"):
        pytest.skip("schema no longer has FindFirstLastDataRowX.LastRowIndex required Out")
    findings = _run(_xaml('<ui:FindFirstLastDataRowX DisplayName="FFL" />'))
    f = _finding_for_arg(findings, "LastRowIndex")
    assert f is not None
    assert f.fix_mechanical is not None
    assert f.fix_mechanical.get("direction") == "Out"


def test_m2_mech_carries_direction_in_default():
    """A plain required In arg (concrete type) still emits a mech and the
    direction defaults to 'In' (backward-compatible with the old behavior)."""
    schema = get_schema()
    if not _activity_resolves(schema, "FindFirstLastDataRowX", "ColumnName", "In"):
        pytest.skip("schema no longer has FindFirstLastDataRowX.ColumnName required In")
    findings = _run(_xaml('<ui:FindFirstLastDataRowX DisplayName="FFL" />'))
    f = _finding_for_arg(findings, "ColumnName")
    assert f is not None
    assert f.fix_mechanical is not None
    assert f.fix_mechanical.get("direction") == "In"


# ---------------------------------------------------------------------------
# Integration: detector emits NO mech for generic / unresolvable types
# (M-2 (b) — would otherwise produce malformed or invalid x:TypeArguments)
# ---------------------------------------------------------------------------

def test_m2_no_mech_for_generic_type():
    """RefreshPivotTableX.LayoutRowType type is 'Nullable<...>' (contains '<').
    The finding must still be EMITTED (breaking ERROR surfaced) but with NO
    mechanical fixer, so --apply does not inject malformed XAML."""
    schema = get_schema()
    if not _has_required_arg(schema, "RefreshPivotTableX", "LayoutRowType", generic=True):
        pytest.skip("schema no longer has RefreshPivotTableX.LayoutRowType generic")
    findings = _run(_xaml('<ui:RefreshPivotTableX DisplayName="Refresh" />'))
    f = _finding_for_arg(findings, "LayoutRowType")
    assert f is not None, "generic-typed required arg must STILL be reported"
    assert f.fix_mechanical is None, (
        "generic '<' type must NOT carry a mechanical fix (would be malformed XML)"
    )
    # Critically: must NOT fall back to the rule-level mechanical spec either.
    # (If it did, _effective_apply_class would keep this a blocking deterministic
    #  ERROR with an un-applyable fixer.)


def test_m2_no_mech_for_typeparam_T():
    """ChangeType.ConvertedValue type is 'T' (bare type parameter) -> no mech."""
    schema = get_schema()
    if not _has_required_arg(schema, "ChangeType", "ConvertedValue", typeparam=True):
        pytest.skip("schema no longer has ChangeType.ConvertedValue type-param")
    findings = _run(_xaml('<ui:ChangeType DisplayName="Change" />'))
    f = _finding_for_arg(findings, "ConvertedValue")
    assert f is not None
    assert f.fix_mechanical is None


def test_m2_no_mech_for_unknown_question_type():
    """A required arg whose schema type is '?' (unresolved) -> no mech.

    Driven from the schema: pick any uniquely-resolving activity that has a
    required arg with type '?'. Skips if none exists."""
    schema = get_schema()
    pick = _find_required_arg_with_type(schema, "?")
    if pick is None:
        pytest.skip("schema has no uniquely-resolving activity with required '?' arg")
    local, arg_name = pick
    findings = _run(_xaml(f'<ui:{local} DisplayName="X" />'))
    f = _finding_for_arg(findings, arg_name)
    assert f is not None
    assert f.fix_mechanical is None


# ---------------------------------------------------------------------------
# Integration: overload-group ENGAGEMENT (batch finding — CloseWindow FP)
# Selector(g="Find Window", r:true) vs UseWindow(g="Use Window", r:false).
# Providing UseWindow engages "Use Window" -> Selector must NOT be demanded.
# ---------------------------------------------------------------------------

def _closewindow_overload_ok(schema) -> bool:
    adef = _resolve_single(schema, "CloseWindow")
    if adef is None:
        return False
    sel = adef.arg_by_name("Selector")
    uw = adef.arg_by_name("UseWindow")
    return bool(
        sel and sel.required and sel.overload_group == "Find Window"
        and uw and uw.overload_group == "Use Window"
    )


def test_m2_overload_engaged_group_suppresses_alternative():
    """CloseWindow using the 'Use Window' group (UseWindow provided) must NOT be
    flagged for the 'Find Window' group's required Selector. This was the lone
    batch FAIL (marcacao-...-performer): Selector="{x:Null}" + UseWindow="[real]"
    -> M-2 falsely demanded Selector."""
    schema = get_schema()
    if not _closewindow_overload_ok(schema):
        pytest.skip("schema CloseWindow overload shape changed")
    findings = _run(_xaml(
        '<ui:CloseWindow Selector="{x:Null}" '
        'UseWindow="[in_Win]" DisplayName="Close" />'
    ))
    assert _finding_for_arg(findings, "Selector") is None, (
        "engaged 'Use Window' group must suppress the alternative 'Find Window' "
        f"Selector requirement; got {[f.message for f in findings]}"
    )


def test_m2_overload_no_engagement_falls_back_to_best_group():
    """With NO overload-group arg provided at all, the activity is ambiguous ->
    M-2 falls back to demanding the least-incomplete group (Find Window/Selector).
    Guards against the fix silently disabling M-2 for genuinely-empty activities."""
    schema = get_schema()
    if not _closewindow_overload_ok(schema):
        pytest.skip("schema CloseWindow overload shape changed")
    findings = _run(_xaml('<ui:CloseWindow DisplayName="Close" />'))
    assert _finding_for_arg(findings, "Selector") is not None, (
        "no group engaged -> ambiguous -> Selector (best_group) must still be flagged"
    )


# ---------------------------------------------------------------------------
# Schema helpers (skip-guards so tests are robust to schema regeneration)
# ---------------------------------------------------------------------------

_UI_XMLNS = "http://schemas.uipath.com/workflow/activities"


def _resolve_single(schema, local):
    cands = schema.candidates(_UI_XMLNS, local)
    return cands[0] if len(cands) == 1 else None


def _activity_resolves(schema, local, arg_name, direction):
    adef = _resolve_single(schema, local)
    if adef is None:
        return False
    arg = adef.arg_by_name(arg_name)
    return bool(arg and arg.required and arg.direction == direction
                and not am._is_mech_unresolvable_type(arg.type))


def _has_required_arg(schema, local, arg_name, generic=False, typeparam=False):
    adef = _resolve_single(schema, local)
    if adef is None:
        return False
    arg = adef.arg_by_name(arg_name)
    if not (arg and arg.required):
        return False
    if generic and "<" not in (arg.type or ""):
        return False
    if typeparam and arg.type not in ("T",) and not (
        arg.type and len(arg.type) >= 2 and arg.type[0] == "T"
        and (arg.type[1].isupper() or arg.type[1].isdigit())
    ):
        return False
    return True


def _find_required_arg_with_type(schema, type_str):
    """Return (local_name, arg_name) of a uniquely-resolving activity whose
    required arg has exactly `type_str`, else None."""
    # iterate the schema's fqn index via the private map is overkill; instead
    # walk known candidates by re-reading the singleton's indexed defs.
    seen = set()
    for (xmlns, local), defs in schema._by_xmlns_local.items():  # noqa: SLF001
        if xmlns != _UI_XMLNS or local in seen:
            continue
        seen.add(local)
        adef = _resolve_single(schema, local)
        if adef is None:
            continue
        for a in adef.args:
            if a.required and (a.type or "?") == type_str:
                return (local, a.name)
    return None
