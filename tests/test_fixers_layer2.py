"""Tests pra fixers novos da sessão Layer 2 (F21-F28).

Cobre:
  - insert_trace_log (N-5 fixer): walker tag-name-exact, restrictive parent
    skip, collection skip, wrap em Sequence p/ wrap-able parents,
    Message bracketed, DisplayName uniqueness.
  - remove_anticipatory_log (N-10 fixer): line-based locate + paired-tag walk.
  - add_prefixo_arg (N-3 fixer): xmlns:this auto, x:Property, default-value,
    Message rewrite.
  - duplicate_id skip_patterns: auto-generated IdRefs ignored.
"""
from pathlib import Path
import pytest

from scripts.rule_engine.fixers import (
    apply_insert_trace_log,
    apply_remove_anticipatory_log,
    apply_add_prefixo_arg,
)


XAML_HEAD = (
    '<Activity mc:Ignorable="sap sap2010" x:Class="TestWf" '
    'xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation" '
    'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
    'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib" '
    'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
    '  <x:Members></x:Members>\n'
)
XAML_TAIL = '</Activity>\n'


# ---- insert_trace_log ----

def test_insert_trace_log_basic_assign(tmp_path):
    """Inserir Trace após Assign em Sequence (parent não restritivo)."""
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence DisplayName="Main">\n'
        '    <Assign DisplayName="Soma" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '      <Assign.To><OutArgument x:TypeArguments="x:Int32">[vResult]</OutArgument></Assign.To>\n'
        '      <Assign.Value><InArgument x:TypeArguments="x:Int32">[1+1]</InArgument></Assign.Value>\n'
        '    </Assign>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    # Line of <Assign>: head=2 lines + Sequence=1 line → Assign at line 4.
    spec = {
        "activity_name": "Assign", "activity_line": 4,
        "trace_level": "Trace", "has_prefixo": False, "proximity_window": 600,
    }
    changed = apply_insert_trace_log(f, spec, dry_run=False)
    assert changed is True
    out = f.read_text(encoding="utf-8")
    assert '<ui:LogMessage' in out
    assert 'Level="Trace"' in out
    # Bracketed Message form (compile-safe).
    assert '[&quot;Concluído: Soma&quot;]' in out


def test_insert_trace_log_skips_assign_to_property(tmp_path):
    """Parent <Assign.Value> = qualified-property restritivo. Skip."""
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence>\n'
        '    <Assign DisplayName="Soma" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '      <Assign.To><OutArgument x:TypeArguments="x:Int32">[vResult]</OutArgument></Assign.To>\n'
        '      <Assign.Value>\n'
        '        <InArgument x:TypeArguments="x:Int32">[1+1]</InArgument>\n'
        '      </Assign.Value>\n'
        '    </Assign>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    # InArgument inside Assign.Value — parent é Assign.Value (restritivo)
    spec = {
        "activity_name": "InArgument", "activity_line": 7,
        "trace_level": "Trace", "has_prefixo": False, "proximity_window": 600,
    }
    # Should NOT insert (restritivo parent).
    changed = apply_insert_trace_log(f, spec, dry_run=False)
    assert changed is False


def test_insert_trace_log_idempotent_when_trace_already_present(tmp_path):
    """Skip se Trace já existe na proximity_window."""
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence>\n'
        '    <Assign DisplayName="X" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v]</OutArgument></Assign.To>\n'
        '      <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>\n'
        '    </Assign>\n'
        '    <ui:LogMessage Level="Trace" Message="[&quot;already&quot;]"/>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    spec = {
        "activity_name": "Assign", "activity_line": 5,
        "trace_level": "Trace", "has_prefixo": False, "proximity_window": 600,
    }
    changed = apply_insert_trace_log(f, spec, dry_run=False)
    assert changed is False


def test_insert_trace_log_uses_prefixo_when_declared(tmp_path):
    """has_prefixo=True → Message uses in_StPrefixoLog."""
    f = tmp_path / "wf.xaml"
    head = XAML_HEAD.replace(
        '<x:Members></x:Members>',
        '<x:Members>\n'
        '    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />\n'
        '  </x:Members>'
    )
    body = (
        '  <Sequence>\n'
        '    <Assign DisplayName="X" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v]</OutArgument></Assign.To>\n'
        '      <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>\n'
        '    </Assign>\n'
        '  </Sequence>\n'
    )
    f.write_text(head + body + XAML_TAIL, encoding="utf-8")
    # head extended to 4 lines (x:Members 3-line block) + Sequence 1 line →
    # Assign at line 6.
    spec = {
        "activity_name": "Assign", "activity_line": 6,
        "trace_level": "Trace", "has_prefixo": True, "proximity_window": 600,
    }
    changed = apply_insert_trace_log(f, spec, dry_run=False)
    assert changed is True
    out = f.read_text(encoding="utf-8")
    assert 'in_StPrefixoLog +' in out


def test_insert_trace_log_unique_displayname(tmp_path):
    """Suffix #2 quando DisplayName base já usado no arquivo.

    Naming convention atual (N-17): `Log Message - <ctx> concluido`.
    Para disparar disambiguation, arquivo precisa já conter o DN base
    que será gerado pelo fixer.
    """
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence>\n'
        '    <ui:LogMessage DisplayName="Log Message - X concluido" '
        'sap2010:WorkflowViewState.IdRef="Log_pre" Level="Info" Message="[&quot;old&quot;]" />\n'
        '    <Assign DisplayName="X" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v]</OutArgument></Assign.To>\n'
        '      <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>\n'
        '    </Assign>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    # head=2 + Sequence=1 + LogMessage=1 → second activity (Assign) at line 5.
    spec = {
        "activity_name": "Assign", "activity_line": 5,
        "trace_level": "Trace", "has_prefixo": False, "proximity_window": 600,
    }
    changed = apply_insert_trace_log(f, spec, dry_run=False)
    assert changed is True
    out = f.read_text(encoding="utf-8")
    # Base "Log Message - X concluido" já presente → novo deve disambiguar #2.
    assert 'DisplayName="Log Message - X concluido #2"' in out


# ---- F24: insert_trace_log wrap em parents wrap-able ----

def test_insert_trace_log_wraps_then_branch(tmp_path):
    """If.Then com 1 child Activity — fixer wrap em <Sequence>."""
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence>\n'
        '    <If Condition="[True]">\n'
        '      <If.Then>\n'
        '        <Assign DisplayName="X" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '          <Assign.To><OutArgument x:TypeArguments="x:Int32">[v]</OutArgument></Assign.To>\n'
        '          <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>\n'
        '        </Assign>\n'
        '      </If.Then>\n'
        '    </If>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    # Assign at line 6 (head=2 + Sequence=1 + If=1 + If.Then=1)
    spec = {
        "activity_name": "Assign", "activity_line": 6,
        "trace_level": "Trace", "has_prefixo": False, "proximity_window": 600,
    }
    changed = apply_insert_trace_log(f, spec, dry_run=False)
    assert changed is True
    out = f.read_text(encoding="utf-8")
    # Deve haver Sequence wrapper + Trace + Assign original.
    assert '<Sequence DisplayName="Sequence (wrap N-5: X)' in out
    assert '<ui:LogMessage' in out
    assert 'Level="Trace"' in out


def test_insert_trace_log_wraps_flowstep_action(tmp_path):
    """FlowStep parent — fixer DEVE wrap em <Sequence>.

    Regression: anteriormente fixer inseria LogMessage como sibling do
    Activity dentro do FlowStep, causando 'Action' property has already
    been set on 'FlowStep' (FlowStep aceita 1 Activity no slot Action).
    Fix: FlowStep adicionado a _N5_WRAP_ABLE_NON_QUALIFIED → wrap em
    Sequence (Activity-shape) preserva slot Action single-child.
    """
    f = tmp_path / "wf.xaml"
    body = (
        '  <Flowchart>\n'
        '    <FlowStep x:Name="__ReferenceID1">\n'
        '      <Assign DisplayName="X" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '        <Assign.To><OutArgument x:TypeArguments="x:Int32">[v]</OutArgument></Assign.To>\n'
        '        <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>\n'
        '      </Assign>\n'
        '    </FlowStep>\n'
        '  </Flowchart>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    # head=2 + Flowchart=1 + FlowStep=1 → Assign at line 5.
    spec = {
        "activity_name": "Assign", "activity_line": 5,
        "trace_level": "Trace", "has_prefixo": False, "proximity_window": 600,
    }
    changed = apply_insert_trace_log(f, spec, dry_run=False)
    assert changed is True
    out = f.read_text(encoding="utf-8")
    # Sequence wrapper present.
    assert '<Sequence DisplayName="Sequence (wrap N-5: X)' in out
    # Trace LogMessage present.
    assert '<ui:LogMessage' in out
    assert 'Level="Trace"' in out
    # Parse via lxml: FlowStep must contain exactly ONE direct element child
    # that is an Activity (the Sequence wrapper) + zero or one FlowStep.Next.
    # Critical assertion: FlowStep does NOT have 2 sibling Activity children
    # (which would emit Studio's 'Action property already set on FlowStep').
    from lxml import etree
    root = etree.fromstring(out.encode("utf-8"))
    ns = {
        "sas": "clr-namespace:System.Activities.Statements;assembly=System.Activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "default": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
    }
    # FlowStep lives in default activities namespace (sem prefix). lxml
    # localname-based query é mais robusto pra evitar issues de xmlns.
    flowsteps = root.xpath("//*[local-name()='FlowStep']")
    assert len(flowsteps) == 1
    fs = flowsteps[0]
    # Drop the qualified property children (FlowStep.Next, FlowStep.Action,
    # ViewState attaches) — count only direct Activity children.
    activity_children = [
        c for c in fs
        if not (
            isinstance(c.tag, str)
            and "." in c.tag.split("}", 1)[-1]
        )
    ]
    assert len(activity_children) == 1, (
        f"FlowStep deve ter 1 Activity child (Sequence wrap), got "
        f"{len(activity_children)}: {[c.tag for c in activity_children]}"
    )
    assert activity_children[0].tag.split("}", 1)[-1] == "Sequence"


def test_insert_trace_log_skip_assign_value_property(tmp_path):
    """Assign.Value não é wrap-safe — skip even se na safe-suffix list."""
    f = tmp_path / "wf.xaml"
    # Try inserting on InArgument inside Assign.Value (parent .Value).
    body = (
        '  <Sequence>\n'
        '    <Assign DisplayName="X" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v]</OutArgument></Assign.To>\n'
        '      <Assign.Value>\n'
        '        <InArgument x:TypeArguments="x:Int32">[1+1]</InArgument>\n'
        '      </Assign.Value>\n'
        '    </Assign>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    # Try inserting after InArgument inside Assign.Value (parent restritivo)
    spec = {
        "activity_name": "InArgument", "activity_line": 7,
        "trace_level": "Trace", "has_prefixo": False, "proximity_window": 600,
    }
    changed = apply_insert_trace_log(f, spec, dry_run=False)
    # Should skip — Assign.Value não tem suffix wrap-safe (Value não em
    # whitelist). Non-modificado.
    assert changed is False


# ---- remove_anticipatory_log ----

def test_remove_anticipatory_log_basic(tmp_path):
    """Remove LogMessage self-closed em line apontada."""
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence>\n'
        '    <ui:LogMessage Level="Trace" Message="[&quot;ant&quot;]" sap2010:WorkflowViewState.IdRef="Log_1"/>\n'
        '    <Assign DisplayName="X" sap2010:WorkflowViewState.IdRef="Assign_1">\n'
        '      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v]</OutArgument></Assign.To>\n'
        '      <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>\n'
        '    </Assign>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    spec = {"log_line": 4, "parent_name": "Sequence"}
    changed = apply_remove_anticipatory_log(f, spec, dry_run=False)
    assert changed is True
    out = f.read_text(encoding="utf-8")
    assert '<ui:LogMessage' not in out


def test_remove_anticipatory_log_idempotent(tmp_path):
    """Re-call em line sem LogMessage = no-op."""
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence>\n'
        '    <Assign DisplayName="X" sap2010:WorkflowViewState.IdRef="Assign_1"/>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    spec = {"log_line": 4, "parent_name": "Sequence"}
    changed = apply_remove_anticipatory_log(f, spec, dry_run=False)
    assert changed is False


# ---- add_prefixo_arg ----

def test_add_prefixo_arg_full_pipeline(tmp_path):
    """Adiciona x:Property + xmlns:this + default-value + reescreve Messages."""
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence>\n'
        '    <ui:LogMessage Level="Trace" Message="[&quot;Concluído: X&quot;]" '
        'sap2010:WorkflowViewState.IdRef="Log_1"/>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    spec = {"prefixo_arg": "in_StPrefixoLog"}
    changed = apply_add_prefixo_arg(f, spec, dry_run=False)
    assert changed is True
    out = f.read_text(encoding="utf-8")
    # x:Property added
    assert '<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />' in out
    # xmlns:this added
    assert 'xmlns:this="clr-namespace:"' in out
    # Default value block added
    assert 'this:TestWf.in_StPrefixoLog' in out
    # Message rewritten
    assert '[in_StPrefixoLog + &quot;Concluído: X&quot;]' in out


def test_add_prefixo_arg_idempotent_when_already_declared(tmp_path):
    """Já declarado → no-op."""
    f = tmp_path / "wf.xaml"
    head = XAML_HEAD.replace(
        '<x:Members></x:Members>',
        '<x:Members>\n'
        '    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />\n'
        '  </x:Members>'
    )
    body = '  <Sequence/>\n'
    f.write_text(head + body + XAML_TAIL, encoding="utf-8")
    spec = {"prefixo_arg": "in_StPrefixoLog"}
    changed = apply_add_prefixo_arg(f, spec, dry_run=False)
    assert changed is False


# ---- F34: schema-driven parent classification ----

def test_classify_parent_for_logmessage_unknown_falls_through():
    """Schema classifier retorna 'unknown' quando parent não em schema —
    caller fallback hardcoded list."""
    from scripts.rule_engine.heuristics.activity_meta import (
        classify_parent_for_logmessage,
    )
    # Random non-existent activity → unknown
    result = classify_parent_for_logmessage("ui:NonExistentActivity")
    assert result in ("unknown", "open", "restrictive", "wrap_able")


def test_classify_parent_known_top_level_containers():
    """Sequence/Flowchart/StateMachine = open (multi-child)."""
    from scripts.rule_engine.heuristics.activity_meta import (
        classify_parent_for_logmessage,
    )
    assert classify_parent_for_logmessage("Sequence") == "open"
    assert classify_parent_for_logmessage("Flowchart") == "open"


def test_classify_activity_action_is_wrap_able():
    """ActivityAction (delegate body) = wrap_able."""
    from scripts.rule_engine.heuristics.activity_meta import (
        classify_parent_for_logmessage,
    )
    assert classify_parent_for_logmessage("ActivityAction") == "wrap_able"
    assert classify_parent_for_logmessage("ActivityFunc") == "restrictive"


# ---- duplicate_id skip_patterns (X-1 reconciliation) ----

def test_duplicate_id_skips_auto_generated_pattern(tmp_path):
    """X-1 detector skip `<TypeName>``\\d+_\\d+` IdRefs (Studio auto-gen)."""
    from scripts.rule_engine.detectors import detect_duplicate_id
    from scripts.rule_engine._types import Rule
    f = tmp_path / "wf.xaml"
    body = (
        '  <Sequence>\n'
        '    <VisualBasicValue x:TypeArguments="x:Boolean" '
        'sap2010:WorkflowViewState.IdRef="VisualBasicValue`1_1"/>\n'
        '    <VisualBasicValue x:TypeArguments="x:Boolean" '
        'sap2010:WorkflowViewState.IdRef="VisualBasicValue`1_1"/>\n'
        '    <Assign sap2010:WorkflowViewState.IdRef="Assign_99"/>\n'
        '    <Assign sap2010:WorkflowViewState.IdRef="Assign_99"/>\n'
        '  </Sequence>\n'
    )
    f.write_text(XAML_HEAD + body + XAML_TAIL, encoding="utf-8")
    from scripts.rule_engine.context import FileContext

    class FakeRule:
        id = "X-1"
        severity = "ERROR"
        category = "breaking"
        title = "Duplicate IdRef em XAML"
        detect = {
            "type": "duplicate_id",
            "params": {
                "attribute": "IdRef",
                "skip_patterns": [r"^[A-Za-z][A-Za-z0-9]*`\d+_\d+$"],
            },
        }
        fix = {}

    fc = FileContext(f)
    findings = detect_duplicate_id(FakeRule(), fc, None)
    # Só Assign_99 deve disparar — VisualBasicValue`1_1 skipped.
    assert len(findings) == 1
    assert "Assign_99" in findings[0].message
