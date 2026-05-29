"""Regression tests for AUDIT_2026-05-28 finding A-19b (detector side).

A-19b detector must propagate the callee arg's declared DIRECTION and
INNER TYPE into the cascade_caller_in_args mechanical spec, and must set
fix_mechanical=None (downgrade to contextual) when the type cannot be
resolved (?, bare generic type-param T/TResult, missing inner). This
prevents the deterministic fixer from auto-applying a hardcoded
`<InArgument x:TypeArguments="x:String">` for InOut / non-string args.

These tests exercise ONLY the detector (heuristics/transaction_item.py).
The fixer side (cascade_caller_in_args) reads direction+inner_type with a
fallback, owned by the fixers lane — not asserted here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from uip_engine._types import Category, Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics import transaction_item as ti


# --- direct unit tests of the new resolution helpers -----------------------

def test_direction_word_mapping():
    assert ti._direction_word("InOutArgument(ui:QueueItem)") == "InOut"
    assert ti._direction_word("OutArgument(x:String)") == "Out"
    assert ti._direction_word("InArgument(x:String)") == "In"
    assert ti._direction_word("System.String") is None


def test_extract_inner_type_simple():
    assert ti._extract_inner_type("InArgument(x:String)") == "x:String"
    assert ti._extract_inner_type("InOutArgument(ui:QueueItem)") == "ui:QueueItem"
    assert ti._extract_inner_type("InArgument(s:Int32)") == "s:Int32"


def test_extract_inner_type_nested_generic_balanced():
    t = ("InArgument(scg:Dictionary(x:String, s:Tuple(x:String, "
         "ss:SecureString)))")
    assert ti._extract_inner_type(t) == (
        "scg:Dictionary(x:String, s:Tuple(x:String, ss:SecureString))"
    )


def test_extract_inner_type_no_parens():
    assert ti._extract_inner_type("InArgument") is None
    assert ti._extract_inner_type("System.String") is None


def test_is_unresolvable_inner():
    # unresolvable
    assert ti._is_unresolvable_inner(None) is True
    assert ti._is_unresolvable_inner("") is True
    assert ti._is_unresolvable_inner("?") is True
    assert ti._is_unresolvable_inner("T") is True
    assert ti._is_unresolvable_inner("TResult") is True
    # resolvable concrete / namespaced / nested generic
    assert ti._is_unresolvable_inner("x:String") is False
    assert ti._is_unresolvable_inner("ui:QueueItem") is False
    assert ti._is_unresolvable_inner("System.Data.DataTable") is False
    assert ti._is_unresolvable_inner("scg:Dictionary(x:String, x:Object)") is False
    # `Type`/`Token` start with T but are concrete (not a bare param)
    assert ti._is_unresolvable_inner("Type") is False
    assert ti._is_unresolvable_inner("Token") is False


# --- integration tests of detect_a19b_in_args_missing ----------------------

def _a19b_rule() -> Rule:
    """Mirror rules.yaml A-19b fix.mechanical (params: {})."""
    return Rule(
        id="A-19b",
        severity=Severity.WARN,
        category=Category.ARCHITECTURAL,
        target="all",
        title="Caller falta argumento In declarado pelo callee",
        description="test",
        detect={"type": "python", "params": {
            "module": "uip_engine.heuristics.transaction_item",
            "function": "detect_a19b_in_args_missing",
        }},
        fix={
            "apply_class": "deterministic",
            "mechanical": {"type": "cascade_caller_in_args", "params": {}},
        },
    )


def _callee_xaml(props: str) -> str:
    return (
        '<Activity x:Class="Callee" '
        'xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:s="clr-namespace:System;assembly=mscorlib" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
        'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib">\n'
        f'{props}\n'
        '  <Sequence />\n'
        '</Activity>\n'
    )


def _caller_xaml(callee_rel: str) -> str:
    """Caller invokes callee but passes NO arguments (all missing)."""
    return (
        '<Activity x:Class="Caller" '
        'xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">\n'
        '  <Sequence>\n'
        f'    <ui:InvokeWorkflowFile WorkflowFileName="{callee_rel}" '
        'sap2010:WorkflowViewState.IdRef="InvokeWorkflowFile_1">\n'
        '      <ui:InvokeWorkflowFile.Arguments>\n'
        '      </ui:InvokeWorkflowFile.Arguments>\n'
        '    </ui:InvokeWorkflowFile>\n'
        '  </Sequence>\n'
        '</Activity>\n'
    )


def _build_project(tmp_path: Path, callee_props: str):
    (tmp_path / "project.json").write_text(
        json.dumps({"name": "T", "targetFramework": "Windows"}),
        encoding="utf-8",
    )
    callee = tmp_path / "Callee.xaml"
    callee.write_text(_callee_xaml(callee_props), encoding="utf-8")
    caller = tmp_path / "Caller.xaml"
    caller.write_text(_caller_xaml("Callee.xaml"), encoding="utf-8")
    pc = ProjectContext.find_root(caller)
    fc = FileContext(caller)
    return fc, pc


def _findings_by_arg(findings):
    out = {}
    for f in findings:
        # message ends with "falta '<arg>'"
        m = f.message.rsplit("falta '", 1)
        if len(m) == 2:
            out[m[1].rstrip("'")] = f
    return out


def test_a19b_in_string_arg_gets_in_direction(tmp_path):
    props = '  <x:Property Name="in_StName" Type="InArgument(x:String)" />'
    fc, pc = _build_project(tmp_path, props)
    findings = ti.detect_a19b_in_args_missing(_a19b_rule(), fc, pc)
    by = _findings_by_arg(findings)
    assert "in_StName" in by
    mech = by["in_StName"].fix_mechanical
    assert mech is not None
    assert mech["type"] == "cascade_caller_in_args"
    assert mech["params"]["direction"] == "In"
    assert mech["params"]["inner_type"] == "x:String"
    assert mech["params"]["arg_name"] == "in_StName"


def test_a19b_inout_queueitem_gets_inout_direction_and_type(tmp_path):
    # The exact bug from the audit: io_TransactionItem InOutArgument(ui:QueueItem)
    props = ('  <x:Property Name="io_TransactionItem" '
             'Type="InOutArgument(ui:QueueItem)" />')
    fc, pc = _build_project(tmp_path, props)
    findings = ti.detect_a19b_in_args_missing(_a19b_rule(), fc, pc)
    by = _findings_by_arg(findings)
    assert "io_TransactionItem" in by
    mech = by["io_TransactionItem"].fix_mechanical
    assert mech is not None, "InOut arg with concrete type must still auto-fix"
    assert mech["params"]["direction"] == "InOut"
    assert mech["params"]["inner_type"] == "ui:QueueItem"


def test_a19b_non_string_in_arg_keeps_real_type(tmp_path):
    props = '  <x:Property Name="in_IntCount" Type="InArgument(s:Int32)" />'
    fc, pc = _build_project(tmp_path, props)
    findings = ti.detect_a19b_in_args_missing(_a19b_rule(), fc, pc)
    by = _findings_by_arg(findings)
    mech = by["in_IntCount"].fix_mechanical
    assert mech is not None
    assert mech["params"]["direction"] == "In"
    assert mech["params"]["inner_type"] == "s:Int32"


def test_a19b_unknown_type_question_mark_is_contextual(tmp_path):
    props = '  <x:Property Name="in_Value" Type="InArgument(?)" />'
    fc, pc = _build_project(tmp_path, props)
    findings = ti.detect_a19b_in_args_missing(_a19b_rule(), fc, pc)
    by = _findings_by_arg(findings)
    # finding still surfaces, but mech is None -> NOT auto-applied
    assert "in_Value" in by
    assert by["in_Value"].fix_mechanical is None


def test_a19b_bare_generic_type_param_is_contextual(tmp_path):
    props = '  <x:Property Name="in_Generic" Type="InArgument(T)" />'
    fc, pc = _build_project(tmp_path, props)
    findings = ti.detect_a19b_in_args_missing(_a19b_rule(), fc, pc)
    by = _findings_by_arg(findings)
    assert "in_Generic" in by
    assert by["in_Generic"].fix_mechanical is None


def test_a19b_nested_generic_concrete_is_resolvable(tmp_path):
    props = ('  <x:Property Name="in_Dict" '
             'Type="InArgument(scg:Dictionary(x:String, x:Object))" />')
    fc, pc = _build_project(tmp_path, props)
    findings = ti.detect_a19b_in_args_missing(_a19b_rule(), fc, pc)
    by = _findings_by_arg(findings)
    mech = by["in_Dict"].fix_mechanical
    # nested generic with concrete args is a valid XAML TypeArguments value
    assert mech is not None
    assert mech["params"]["inner_type"] == "scg:Dictionary(x:String, x:Object)"
    assert mech["params"]["direction"] == "In"


def test_a19b_carries_invoke_idref(tmp_path):
    props = '  <x:Property Name="in_StName" Type="InArgument(x:String)" />'
    fc, pc = _build_project(tmp_path, props)
    findings = ti.detect_a19b_in_args_missing(_a19b_rule(), fc, pc)
    by = _findings_by_arg(findings)
    assert by["in_StName"].fix_mechanical["params"]["invoke_idref"] == (
        "InvokeWorkflowFile_1"
    )


def test_a19b_out_only_arg_not_flagged(tmp_path):
    # Out args missing are a legitimate discard -> A-19b must not fire.
    props = '  <x:Property Name="out_Result" Type="OutArgument(x:String)" />'
    fc, pc = _build_project(tmp_path, props)
    findings = ti.detect_a19b_in_args_missing(_a19b_rule(), fc, pc)
    assert _findings_by_arg(findings) == {}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
