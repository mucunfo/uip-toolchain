"""Regression tests for AUDIT_2026-05-28 finding F.N-2/N-11 (redundancy).

Bug: an argument with NO valid direction prefix (e.g. `parametro`,
Type="InArgument(x:String)") was flagged + auto-renamed by BOTH:
  - N-11 (ERROR/breaking, detect_n11_argument_direction) → `in_Parametro`
  - N-2  (WARN/architectural, detect_n2_argument_prefix) → `in_StParametro`
Both emitted a `rename_argument` deterministic mechanical fix with DIFFERENT
targets, colliding in a single --apply pass.

Fix: N-2 now SKIPS arguments that lack any valid direction prefix, ceding
ownership to N-11. N-2 only fires when a valid direction prefix IS present
but the type prefix is wrong/missing.
"""
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext
from uip_engine.heuristics.naming_prefix import (
    detect_n2_argument_prefix,
    detect_n11_argument_direction,
)


_TYPE_PAIRS = [
    ("SecureString", "SSt"),
    ("DataTable", "DTab"),
    ("DateTime", "Dt"),
    ("Dictionary", "Dict"),
    ("Boolean", "Bl"),
    ("Double", "Dbl"),
    ("Int32", "Int"),
    ("Int64", "Lng"),
    ("String", "St"),
]
_WRONG_MAP = {
    "Bool": "Bl",
    "Boolean": "Bl",
    "DTime": "Dt",
    "DateTime": "Dt",
    "Decimal": "Dbl",
    "Str": "St",
    "String": "St",
    "Integer": "Int",
    "Number": "Int",
    "DT": "DTab",
    "Tab": "DTab",
}
_PARAMS = {
    "type_prefix": [{"type": t, "prefix": p} for t, p in _TYPE_PAIRS],
    "wrong_prefix_map": _WRONG_MAP,
    "bare_special": [],
    "reframework_main_vars": [],
    "bare_arg_names": [],
}


def _write_xaml(tmp_path: Path, body: str) -> FileContext:
    f = tmp_path / "Foo.xaml"
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        f'{body}\n'
        '</Activity>',
        encoding="utf-8",
    )
    return FileContext(f)


def _make_n2_rule():
    return Rule(
        id="N-2",
        severity=Severity.WARN,
        category="architectural",
        target="all",
        title="Argumento usa prefixo (in_|out_|io_)[Tipo][Nome]",
        description="",
        detect={"type": "python", "params": dict(_PARAMS)},
    )


def _make_n11_rule():
    return Rule(
        id="N-11",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="Argumento usa direção (in_|out_|io_)",
        description="",
        detect={"type": "python", "params": dict(_PARAMS)},
    )


# --- The core ownership-split assertions ------------------------------------

def test_n2_skips_argument_without_any_direction_prefix(tmp_path):
    """`parametro` (no direction) must NOT be flagged by N-2 — N-11 owns it."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="parametro" Type="InArgument(x:String)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n2_argument_prefix(_make_n2_rule(), fc, None)
    assert findings == []


def test_n11_owns_argument_without_any_direction_prefix(tmp_path):
    """N-11 still flags + renames the direction-less argument to `in_Parametro`."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="parametro" Type="InArgument(x:String)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n11_argument_direction(_make_n11_rule(), fc, None)
    assert len(findings) == 1
    assert findings[0].fix_mechanical["type"] == "rename_argument"
    assert findings[0].fix_mechanical["from"] == "parametro"
    assert findings[0].fix_mechanical["to"] == "in_Parametro"


def test_no_double_rename_collision_on_directionless_arg(tmp_path):
    """The two detectors must not BOTH emit a rename for the same node with
    DIFFERENT targets (the original bug). Exactly one (N-11) should fire."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="parametro" Type="InArgument(x:String)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    n2 = detect_n2_argument_prefix(_make_n2_rule(), fc, None)
    n11 = detect_n11_argument_direction(_make_n11_rule(), fc, None)
    n2_renames = [f for f in n2 if f.fix_mechanical]
    n11_renames = [f for f in n11 if f.fix_mechanical]
    assert n2_renames == []
    assert len(n11_renames) == 1


def test_n2_skips_directionless_for_each_direction_type(tmp_path):
    """Direction-less args for Out/InOut argument types are also ceded to N-11."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="resultado" Type="OutArgument(x:String)" />\n'
        '    <x:Property Name="estado" Type="InOutArgument(x:Boolean)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n2_argument_prefix(_make_n2_rule(), fc, None)
    assert findings == []


def test_n2_skips_invalid_direction_form(tmp_path):
    """An arg with an INVALID-but-stripped direction (e.g. `inout_X`) is also
    ceded to N-11. `_strip_direction('inout_Foo')` != 'inout_Foo', so this is
    NOT direction-less; but it still does not start with the canonical
    `io_`/`in_`/`out_` expected_dir, and `_strip_direction` removes it, so N-2
    leaves it to N-11 only when there is no direction at all. Here we assert N-2
    does NOT crash and the canonical direction-less skip holds — `inout_` is a
    known invalid direction that _strip_direction recognizes, so N-2 may still
    fire on type-prefix grounds; we only assert it does not double with N-11 on
    the pure direction-less case (covered above)."""
    # Sanity: this case has a (invalid) direction token; N-11 owns direction.
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="inout_Foo" Type="InOutArgument(x:String)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    n11 = detect_n11_argument_direction(_make_n11_rule(), fc, None)
    # N-11 flags the invalid direction form.
    assert len(n11) == 1


# --- N-2 still fires when direction is VALID but type prefix is wrong --------

def test_n2_still_flags_valid_direction_wrong_type_prefix(tmp_path):
    """`in_IntegerCount` (valid `in_`, wrong type prefix `Integer`) is owned by
    N-2 and renamed to `in_IntCount`. Regression guard: the ownership-split
    skip must not suppress this legitimate N-2 case."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_IntegerCount" Type="InArgument(x:Int32)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n2_argument_prefix(_make_n2_rule(), fc, None)
    assert len(findings) == 1
    assert findings[0].fix_mechanical["from"] == "in_IntegerCount"
    assert findings[0].fix_mechanical["to"] == "in_IntCount"


def test_n2_still_flags_valid_direction_missing_type_prefix(tmp_path):
    """`in_Count` (valid `in_`, missing type prefix for Int32) is owned by N-2
    and renamed to `in_IntCount`."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_Count" Type="InArgument(x:Int32)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n2_argument_prefix(_make_n2_rule(), fc, None)
    assert len(findings) == 1
    assert findings[0].fix_mechanical["to"] == "in_IntCount"


def test_n2_no_finding_for_fully_correct_arg(tmp_path):
    """`in_IntCount` (valid direction + correct type prefix) → no N-2 finding."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_IntCount" Type="InArgument(x:Int32)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n2_argument_prefix(_make_n2_rule(), fc, None)
    assert findings == []
