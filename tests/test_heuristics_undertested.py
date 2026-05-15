"""Smoke unit-tests pra heuristics sem cobertura direta:
arg_default, empty_sequence, json_checks, testing, transaction_item, value_types.

Nao reescreve smoke completo — só garante que cada função roda + emite/não
emite findings em caso óbvio. Detalhes de cada heuristic ficam em REF baseline.
"""
from pathlib import Path

import pytest

from scripts.rule_engine._types import Rule, Severity
from scripts.rule_engine.context import FileContext, ProjectContext
from scripts.rule_engine.heuristics.arg_default import (
    detect_w3_arg_default_attribute_form,
)
from scripts.rule_engine.heuristics.empty_sequence import detect_empty_sequence
from scripts.rule_engine.heuristics.json_checks import (
    detect_j3_required_packages,
    detect_j6_excluded_logged,
    detect_j7_user_interaction_consistency,
)
from scripts.rule_engine.heuristics.testing import detect_t5_missing_workflow
from scripts.rule_engine.heuristics.transaction_item import (
    detect_a19_io_transaction_item,
)
from scripts.rule_engine.heuristics.value_types import (
    detect_v1_nothing_in_value_type,
)


def _project(tmp_path: Path, pj_data: dict | None = None) -> ProjectContext:
    import json
    pj = pj_data or {"targetFramework": "Windows", "expressionLanguage": "VisualBasic"}
    (tmp_path / "project.json").write_text(json.dumps(pj), encoding="utf-8")
    return ProjectContext(root=tmp_path, project_json=pj)


def _write_xaml(tmp_path: Path, body: str, name: str = "Foo.xaml") -> FileContext:
    f = tmp_path / name
    f.write_text(body, encoding="utf-8")
    return FileContext(f)


def _rule(rid: str, **detect_params) -> Rule:
    return Rule(
        id=rid, severity=Severity.WARN, category="architectural", target="all",
        title=rid, description="",
        detect={"type": "python", "params": detect_params},
        fix={"prose": "fix me"},
    )


# ---------------------------------------------------------------------------
# arg_default — W-3
# ---------------------------------------------------------------------------

def test_w3_attribute_form_detected(tmp_path):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" xmlns:this="" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" x:Class="Foo" this:Foo.in_Path="C:\\x">
  <x:Members>
    <x:Property Name="in_Path" Type="InArgument(x:String)" />
  </x:Members>
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_w3_arg_default_attribute_form(_rule("W-3"), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical["type"] == "arg_default_to_element_form"
    assert findings[0].fix_mechanical["arg_name"] == "in_Path"


def test_w3_no_match_when_no_this_attr(tmp_path):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Foo" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members><x:Property Name="in_Path" Type="InArgument(x:String)" /></x:Members>
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_w3_arg_default_attribute_form(_rule("W-3"), fc, _project(tmp_path))
    assert findings == []


# ---------------------------------------------------------------------------
# empty_sequence — S-15
# ---------------------------------------------------------------------------

def test_s15_empty_inside_outer_sequence_flagged(tmp_path):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns="x" xmlns:x="x">
  <Sequence>
    <Sequence />
  </Sequence>
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_empty_sequence(_rule("S-15"), fc, _project(tmp_path))
    assert len(findings) >= 1


def test_s15_empty_in_required_parent_skipped(tmp_path):
    # empty_sequence.py:19-39 lista If.Then E If.Else como required (Studio
    # exige child em ambos branches quando If.Else está presente).
    # Catch handler é optional → empty Sequence dentro de Catch flagged.
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns="x" xmlns:x="x">
  <TryCatch>
    <TryCatch.Try><Sequence /></TryCatch.Try>
    <TryCatch.Catches>
      <Catch x:TypeArguments="s:Exception"><Sequence /></Catch>
    </TryCatch.Catches>
  </TryCatch>
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_empty_sequence(_rule("S-15"), fc, _project(tmp_path))
    # TryCatch.Try required → skip; Catch optional → flagged.
    flagged_parents = [f.message for f in findings]
    assert any("Catch" in m for m in flagged_parents)
    assert not any("TryCatch.Try" in m for m in flagged_parents)


# ---------------------------------------------------------------------------
# json_checks — J-3, J-6, J-7
# ---------------------------------------------------------------------------

def test_j3_missing_package_detected(tmp_path):
    pj = {"targetFramework": "Windows",
          "dependencies": {"UiPath.System.Activities": "[25.4.4]"}}
    pc = _project(tmp_path, pj)
    fc = FileContext(tmp_path / "project.json")
    rule = _rule("J-3", packages=["UiPath.System.Activities", "UiPath.UIAutomation.Activities"])
    findings = detect_j3_required_packages(rule, fc, pc)
    assert len(findings) == 1
    assert "UiPath.UIAutomation.Activities" in findings[0].message


def test_j6_missing_excluded_pattern(tmp_path):
    pj = {"targetFramework": "Windows",
          "runtimeOptions": {"excludedLoggedData": ["*token*"]}}
    pc = _project(tmp_path, pj)
    fc = FileContext(tmp_path / "project.json")
    rule = _rule("J-6", required_patterns=["*password*", "Private:*"])
    findings = detect_j6_excluded_logged(rule, fc, pc)
    assert len(findings) == 1


def test_j7_attended_with_flag_false_flagged(tmp_path):
    pj = {"targetFramework": "Windows", "name": "MeuAttendedRobo",
          "requiresUserInteraction": False}
    pc = _project(tmp_path, pj)
    fc = FileContext(tmp_path / "project.json")
    rule = _rule(
        "J-7",
        performer_markers=["performer"],
        attended_markers=["attended"],
        attended_negative_markers=[],
    )
    findings = detect_j7_user_interaction_consistency(rule, fc, pc)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# testing — T-5
# ---------------------------------------------------------------------------

def test_t5_missing_workflow_flagged(tmp_path):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
  <ui:InvokeWorkflowFile WorkflowFileName="DoesNotExist.xaml" />
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_t5_missing_workflow(_rule("T-5"), fc, _project(tmp_path))
    assert len(findings) == 1


def test_t5_existing_workflow_ok(tmp_path):
    (tmp_path / "Real.xaml").write_text("<Activity/>", encoding="utf-8")
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
  <ui:InvokeWorkflowFile WorkflowFileName="Real.xaml" />
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_t5_missing_workflow(_rule("T-5"), fc, _project(tmp_path))
    assert findings == []


# ---------------------------------------------------------------------------
# transaction_item — A-19
# ---------------------------------------------------------------------------

def test_a19_callee_writes_io_caller_misses_binding(tmp_path):
    callee_body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" x:Class="Callee">
  <x:Members>
    <x:Property Name="io_TransactionItem" Type="InOutArgument(x:Object)" />
  </x:Members>
  <Sequence>
    <Assign>
      <Assign.To><OutArgument>[io_TransactionItem.Output]</OutArgument></Assign.To>
    </Assign>
  </Sequence>
</Activity>
'''
    (tmp_path / "Callee.xaml").write_text(callee_body, encoding="utf-8")

    caller_body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
  <ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">
    <ui:InvokeWorkflowFile.Arguments>
      <InArgument x:Key="in_Other">[42]</InArgument>
    </ui:InvokeWorkflowFile.Arguments>
  </ui:InvokeWorkflowFile>
</Activity>
'''
    fc = _write_xaml(tmp_path, caller_body, name="Caller.xaml")
    findings = detect_a19_io_transaction_item(_rule("A-19"), fc, _project(tmp_path))
    assert len(findings) == 1
    assert "io_TransactionItem" in findings[0].message


# ---------------------------------------------------------------------------
# value_types — V-1
# ---------------------------------------------------------------------------

def test_v1_nothing_in_int_variable_inline(tmp_path):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" xmlns:scg="clr-namespace:System.Collections.Generic">
  <Sequence>
    <Sequence.Variables>
      <Variable x:TypeArguments="x:Int32" Default="[Nothing]" Name="vCount" />
    </Sequence.Variables>
  </Sequence>
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_v1_nothing_in_value_type(_rule("V-1"), fc, _project(tmp_path))
    assert len(findings) == 1
    assert "vCount" in findings[0].message


def test_v1_nothing_in_reference_type_skipped(tmp_path):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <Sequence.Variables>
      <Variable x:TypeArguments="x:String" Default="[Nothing]" Name="vText" />
    </Sequence.Variables>
  </Sequence>
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_v1_nothing_in_value_type(_rule("V-1"), fc, _project(tmp_path))
    assert findings == []


def test_v1_nothing_via_default_block(tmp_path):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <Sequence.Variables>
      <Variable x:TypeArguments="x:Boolean" Name="vFlag">
        <Variable.Default>[Nothing]</Variable.Default>
      </Variable>
    </Sequence.Variables>
  </Sequence>
</Activity>
'''
    fc = _write_xaml(tmp_path, body)
    findings = detect_v1_nothing_in_value_type(_rule("V-1"), fc, _project(tmp_path))
    assert len(findings) == 1
