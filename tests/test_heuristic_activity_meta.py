"""Tests for heuristics/activity_meta.py — M-1, M-2."""
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity, Category
from uip_engine.context import FileContext
from uip_engine.heuristics.activity_meta import (
    detect_m1_activity_unknown,
    detect_m2_required_missing,
    detect_m3_unknown_arg,
    detect_m4_overload_conflict,
    detect_m5_type_mismatch,
    detect_m6_xmlns_missing,
    detect_m7_redundant_default,
    detect_m8_nothing_in_value_type,
    get_schema,
    parse_activities,
)


FIXTURES = Path(__file__).parent / "fixtures" / "activity_meta"


def _rule(rid: str, fn_name: str) -> Rule:
    return Rule(
        id=rid,
        severity=Severity.ERROR,
        category=Category.METADATA,
        target="all",
        title=f"{rid} test rule",
        description="",
        detect={
            "type": "python",
            "params": {
                "module": "uip_engine.heuristics.activity_meta",
                "function": fn_name,
            },
        },
    )


def _fc(name: str) -> FileContext:
    return FileContext(path=FIXTURES / name)


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

def test_schema_loads_and_indexes():
    s = get_schema()
    assert s.size > 500, f"Schema empty? size={s.size}"
    wr = s.by_fqn("UiPath.Excel.Activities.WriteRange")
    assert wr is not None
    assert any(a.name == "WorkbookPath" and a.required for a in wr.args)
    assert any(a.name == "WorkbookPath" and a.overload_group == "File" for a in wr.args)


def test_parse_activities_picks_up_qualified_tags():
    content = (FIXTURES / "ok_writerange.xaml").read_text(encoding="utf-8")
    decls, refs = parse_activities(content)
    assert decls.get("ui") == "http://schemas.uipath.com/workflow/activities"
    locals_found = {r.local_name for r in refs}
    assert "WriteRange" in locals_found


# ---------------------------------------------------------------------------
# M-1 — unknown activity
# ---------------------------------------------------------------------------

def test_m1_emits_for_unknown_activity():
    findings = detect_m1_activity_unknown(_rule("M-1", "detect_m1_activity_unknown"), _fc("bad_unknown_activity.xaml"), None)
    assert len(findings) == 1
    assert "NaoExisteEsta" in findings[0].message


def test_m1_silent_for_known_activity():
    findings = detect_m1_activity_unknown(_rule("M-1", "detect_m1_activity_unknown"), _fc("ok_writerange.xaml"), None)
    assert findings == []


# ---------------------------------------------------------------------------
# M-2 — required missing
# ---------------------------------------------------------------------------

def test_m2_emits_when_required_missing():
    """WriteRange sem WorkbookPath nem alternativas → falta File / FileResource / Use Workbook + DataTable."""
    findings = detect_m2_required_missing(_rule("M-2", "detect_m2_required_missing"), _fc("bad_missing_required.xaml"), None)
    missing_names = {f.message.split("'")[1] for f in findings}
    # DataTable e pelo menos um dos workbook-path overload groups precisam aparecer
    assert "DataTable" in missing_names
    assert any(n in missing_names for n in ("WorkbookPath", "WorkbookPathResource", "Workbook"))


def test_m2_silent_when_overload_group_satisfied():
    """WriteRange com WorkbookPath preenchido → grupo File satisfeito; FileResource/Workbook NÃO devem alertar."""
    findings = detect_m2_required_missing(_rule("M-2", "detect_m2_required_missing"), _fc("ok_writerange.xaml"), None)
    missing_names = {f.message.split("'")[1] for f in findings if "'" in f.message}
    assert "WorkbookPath" not in missing_names
    assert "WorkbookPathResource" not in missing_names
    assert "Workbook" not in missing_names
    # SheetName, DataTable estão preenchidos no fixture → zero findings
    assert findings == []


# ---------------------------------------------------------------------------
# M-3 — unknown arg
# ---------------------------------------------------------------------------

def test_m3_emits_for_typo_arg():
    findings = detect_m3_unknown_arg(_rule("M-3", "detect_m3_unknown_arg"), _fc("bad_unknown_arg.xaml"), None)
    msgs = " ".join(f.message for f in findings)
    assert "FooBarTypoArg" in msgs


def test_m3_includes_levenshtein_suggestion():
    """SheetNam (typo) → sugere SheetName."""
    from pathlib import Path
    fixture = FIXTURES / "_tmp_m3_suggest.xaml"
    fixture.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:ui="http://schemas.uipath.com/workflow/activities"\n'
        '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '  <ui:WriteRange WorkbookPath="C:\\foo.xlsx" SheetNam="Plan1"/>\n'
        '</Activity>\n', encoding="utf-8")
    try:
        findings = detect_m3_unknown_arg(_rule("M-3", "detect_m3_unknown_arg"), FileContext(path=fixture), None)
        msgs = " ".join(f.message for f in findings)
        assert "SheetNam" in msgs
        assert "SheetName" in msgs
        assert "você quis dizer" in msgs
    finally:
        fixture.unlink(missing_ok=True)


def test_m3_silent_on_valid_args():
    findings = detect_m3_unknown_arg(_rule("M-3", "detect_m3_unknown_arg"), _fc("ok_writerange.xaml"), None)
    assert findings == []


# ---------------------------------------------------------------------------
# M-4 — overload conflict
# ---------------------------------------------------------------------------

def test_m4_emits_on_mixed_groups():
    findings = detect_m4_overload_conflict(_rule("M-4", "detect_m4_overload_conflict"), _fc("bad_overload_conflict.xaml"), None)
    assert len(findings) == 1
    msg = findings[0].message
    assert "File" in msg and "FileResource" in msg


def test_m4_silent_on_single_group():
    findings = detect_m4_overload_conflict(_rule("M-4", "detect_m4_overload_conflict"), _fc("ok_writerange.xaml"), None)
    assert findings == []


# ---------------------------------------------------------------------------
# M-6 — xmlns missing
# ---------------------------------------------------------------------------

def test_m6_emits_when_xmlns_undeclared():
    findings = detect_m6_xmlns_missing(_rule("M-6", "detect_m6_xmlns_missing"), _fc("bad_xmlns_missing.xaml"), None)
    assert len(findings) == 1
    assert "ui" in findings[0].message


def test_m6_silent_when_xmlns_declared():
    findings = detect_m6_xmlns_missing(_rule("M-6", "detect_m6_xmlns_missing"), _fc("ok_writerange.xaml"), None)
    assert findings == []


# ---------------------------------------------------------------------------
# M-7 — redundant default
# ---------------------------------------------------------------------------

def test_m7_emits_when_default_is_redundant():
    findings = detect_m7_redundant_default(_rule("M-7", "detect_m7_redundant_default"), _fc("bad_redundant_default.xaml"), None)
    msgs = " ".join(f.message for f in findings)
    # WriteRange StartingCell default = "A1"; SheetName default = "Sheet1"
    assert "StartingCell" in msgs or "SheetName" in msgs


def test_m7_silent_when_no_redundant_default():
    findings = detect_m7_redundant_default(_rule("M-7", "detect_m7_redundant_default"), _fc("ok_writerange.xaml"), None)
    # ok fixture usa SheetName="Plan1" (não default) e nenhum StartingCell
    assert findings == []


# ---------------------------------------------------------------------------
# M-5 — type mismatch
# ---------------------------------------------------------------------------

def test_m5_emits_for_string_in_boolean():
    """AddHeaders='yes' deve emitir — literal string em arg Boolean."""
    findings = detect_m5_type_mismatch(_rule("M-5", "detect_m5_type_mismatch"), _fc("bad_type_mismatch.xaml"), None)
    msgs = " ".join(f.message for f in findings)
    assert "AddHeaders" in msgs
    assert "Boolean" in msgs


def test_m5_silent_for_correct_types():
    """ok_types fixture usa AddHeaders='True' e StartingCell='A1' — todos compatíveis."""
    findings = detect_m5_type_mismatch(_rule("M-5", "detect_m5_type_mismatch"), _fc("ok_types.xaml"), None)
    assert findings == []


def test_m5_silent_on_bind_expression():
    """Bind expression sem cast óbvio não dispara M-5 (sem inferência)."""
    from pathlib import Path
    fixture = FIXTURES / "_tmp_m5_bind.xaml"
    fixture.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:ui="http://schemas.uipath.com/workflow/activities"\n'
        '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '  <ui:WriteRange WorkbookPath="C:\\foo.xlsx" SheetName="Plan1" AddHeaders="[isHeader]"/>\n'
        '</Activity>\n', encoding="utf-8")
    try:
        findings = detect_m5_type_mismatch(_rule("M-5", "detect_m5_type_mismatch"), FileContext(path=fixture), None)
        assert findings == []
    finally:
        fixture.unlink(missing_ok=True)


def test_m5_emits_for_vb_cast_mismatch():
    """[CStr(...)] em arg Boolean → flag (CStr infere string)."""
    findings = detect_m5_type_mismatch(_rule("M-5", "detect_m5_type_mismatch"), _fc("bad_vb_cast_mismatch.xaml"), None)
    msgs = " ".join(f.message for f in findings)
    assert "AddHeaders" in msgs
    assert "VB infere string" in msgs


def test_m5_silent_for_correct_vb_cast():
    """[CBool(...)] em arg Boolean → OK."""
    findings = detect_m5_type_mismatch(_rule("M-5", "detect_m5_type_mismatch"), _fc("ok_vb_cast.xaml"), None)
    assert findings == []


# ---------------------------------------------------------------------------
# M-8 — Nothing/x:Null em value type
# ---------------------------------------------------------------------------

def test_m8_emits_for_nothing_in_boolean():
    """[Nothing] em AddHeaders (Boolean) → flag."""
    findings = detect_m8_nothing_in_value_type(_rule("M-8", "detect_m8_nothing_in_value_type"), _fc("bad_nothing_value_type.xaml"), None)
    msgs = " ".join(f.message for f in findings)
    assert "AddHeaders" in msgs
    assert "Boolean" in msgs


def test_m8_silent_for_xnull_attribute_form():
    """{x:Null} em InArgument value type → silent (significa arg não-fornecido)."""
    from pathlib import Path
    fixture = FIXTURES / "_tmp_m8_xnull.xaml"
    fixture.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:ui="http://schemas.uipath.com/workflow/activities"\n'
        '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '  <ui:WriteRange WorkbookPath="C:\\foo.xlsx" SheetName="Plan1" AddHeaders="{x:Null}"/>\n'
        '</Activity>\n', encoding="utf-8")
    try:
        findings = detect_m8_nothing_in_value_type(_rule("M-8", "detect_m8_nothing_in_value_type"), FileContext(path=fixture), None)
        assert findings == []
    finally:
        fixture.unlink(missing_ok=True)


def test_m8_silent_for_nothing_in_reference():
    """[Nothing] em arg String/reference → OK."""
    from pathlib import Path
    fixture = FIXTURES / "_tmp_m8_ref.xaml"
    fixture.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:ui="http://schemas.uipath.com/workflow/activities"\n'
        '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '  <ui:WriteRange WorkbookPath="C:\\foo.xlsx" SheetName="Plan1" Password="[Nothing]"/>\n'
        '</Activity>\n', encoding="utf-8")
    try:
        findings = detect_m8_nothing_in_value_type(_rule("M-8", "detect_m8_nothing_in_value_type"), FileContext(path=fixture), None)
        assert findings == []
    finally:
        fixture.unlink(missing_ok=True)
