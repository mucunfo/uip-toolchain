"""Tests for heuristics in logs.py — focused on N-7 (InvokeWorkflowFile LogEntry/LogExit)."""
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.logs import (
    detect_n5_trace_log_significant,
    detect_n7_invoke_log_entry_exit,
)


_N7_PARAMS = {
    "exclude_paths": ["framework/", "tests/", "/launch.xaml", "launch.xaml"],
    "expected_attributes": {
        "LogEntry": "OnlyInvocation",
        "LogExit": "OnlySuccessfulReturn",
    },
}


def _make_rule():
    return Rule(
        id="N-7",
        severity=Severity.WARN,
        category="architectural",
        target="all",
        title="InvokeWorkflowFile com LogEntry=OnlyInvocation e LogExit=OnlySuccessfulReturn",
        description="",
        detect={"type": "python", "params": dict(_N7_PARAMS)},
    )


def _write_xaml(tmp_path: Path, body: str, name: str = "Foo.xaml") -> FileContext:
    f = tmp_path / name
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        f'{body}\n'
        '</Activity>',
        encoding="utf-8",
    )
    return FileContext(f)


# ---- N-7 ----

def test_n7_flags_when_both_attrs_missing(tmp_path):
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" Level="Info"/>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc, None)
    assert len(findings) == 2
    msgs = " ".join(f.message for f in findings)
    assert "LogEntry" in msgs and "LogExit" in msgs


def test_n7_flags_when_only_logentry_missing(tmp_path):
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" Level="Info" '
        'LogExit="OnlySuccessfulReturn"/>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc, None)
    assert len(findings) == 1
    assert "LogEntry" in findings[0].message


def test_n7_flags_when_only_logexit_missing(tmp_path):
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" Level="Info" '
        'LogEntry="OnlyInvocation"/>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc, None)
    assert len(findings) == 1
    assert "LogExit" in findings[0].message


def test_n7_no_flag_when_both_attrs_correct(tmp_path):
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" Level="Info" '
        'LogEntry="OnlyInvocation" LogExit="OnlySuccessfulReturn"/>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc, None)
    assert findings == []


def test_n7_flags_wrong_value(tmp_path):
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" '
        'LogEntry="Always" LogExit="Always"/>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc, None)
    assert len(findings) == 2
    msgs = " ".join(f.message for f in findings)
    assert 'LogEntry="Always"' in msgs
    assert 'LogExit="Always"' in msgs


def test_n7_fix_inserts_attribute_when_missing(tmp_path):
    """Re-detect between fixes — mimics CLI fix loop (fix invalidates pattern)."""
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" Level="Info"/>'
    )
    fc = _write_xaml(tmp_path, body)
    from uip_engine.fixers import apply_regex_replace
    for _ in range(5):
        fc2 = FileContext(fc.path)
        findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc2, None)
        if not findings:
            break
        apply_regex_replace(fc.path, findings[0].fix_mechanical, dry_run=False)
    text = fc.path.read_text(encoding="utf-8-sig")
    assert 'LogEntry="OnlyInvocation"' in text
    assert 'LogExit="OnlySuccessfulReturn"' in text


def test_n7_fix_replaces_wrong_value(tmp_path):
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" '
        'LogEntry="Always" LogExit="Never"/>'
    )
    fc = _write_xaml(tmp_path, body)
    from uip_engine.fixers import apply_regex_replace
    for _ in range(5):
        fc2 = FileContext(fc.path)
        findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc2, None)
        if not findings:
            break
        apply_regex_replace(fc.path, findings[0].fix_mechanical, dry_run=False)
    text = fc.path.read_text(encoding="utf-8-sig")
    assert 'LogEntry="OnlyInvocation"' in text
    assert 'LogExit="OnlySuccessfulReturn"' in text
    assert 'LogEntry="Always"' not in text
    assert 'LogExit="Never"' not in text


def test_n7_skips_framework_path(tmp_path):
    proj = tmp_path / "proj"
    fw = proj / "Framework"
    fw.mkdir(parents=True)
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    f = fw / "Whatever.xaml"
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" Level="Info"/>\n'
        '</Activity>',
        encoding="utf-8",
    )
    pc = ProjectContext(root=proj, project_json={"targetFramework": "Windows"})
    fc = FileContext(f)
    findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc, pc)
    assert findings == []


def test_n7_handles_invoke_with_arguments_block(tmp_path):
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="X.xaml" Level="Info">\n'
        '    <ui:InvokeWorkflowFile.Arguments>\n'
        '      <InArgument x:Key="in_X">[v]</InArgument>\n'
        '    </ui:InvokeWorkflowFile.Arguments>\n'
        '  </ui:InvokeWorkflowFile>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc, None)
    # Should still flag both attrs missing on the opening tag
    assert len(findings) == 2


_N5_PARAMS = {
    "exclude_paths": ["framework/", "tests/", "/launch.xaml", "launch.xaml"],
    "proximity_window": 600,
    "trace_level": "Trace",
    "include_default_activities": ["Assign", "AddDataRow"],
    "exclude_ui_activities": [
        "LogMessage", "InvokeWorkflowFile", "Comment", "CommentOut", "Annotation",
    ],
}


def _make_n5_rule():
    return Rule(
        id="N-5",
        severity=Severity.INFO,
        category="architectural",
        target="all",
        title="Toda activity precisa LogMessage Level=Trace próximo",
        description="",
        detect={"type": "python", "params": dict(_N5_PARAMS)},
    )


# ---- N-5 (independente de N-3) ----

def test_n5_emits_regardless_of_prefixolog_declaration(tmp_path):
    """N-5 detecta ausência de Trace independentemente de N-3.
    Convenção de prefixo é responsabilidade do FIXER, não do detector."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_Config" Type="InArgument(x:Object)" />\n'
        '  </x:Members>\n'
        '  <Sequence>\n'
        '    <ui:HttpClient Endpoint="x"/>\n'
        '    <Assign To="x" Value="1"/>\n'
        '  </Sequence>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n5_trace_log_significant(_make_n5_rule(), fc, None)
    assert len(findings) >= 1, "N-5 emite mesmo sem in_StPrefixoLog declarado"


def test_n5_emits_when_workflow_declares_prefixolog(tmp_path):
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />\n'
        '  </x:Members>\n'
        '  <Sequence>\n'
        '    <ui:HttpClient Endpoint="x"/>\n'
        '    <Assign To="x" Value="1"/>\n'
        '  </Sequence>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n5_trace_log_significant(_make_n5_rule(), fc, None)
    assert len(findings) >= 1


def test_n5_no_finding_when_trace_after_activity(tmp_path):
    """Log DEPOIS da activity satisfaz N-5 (rastreabilidade pós-execução)."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />\n'
        '  </x:Members>\n'
        '  <Sequence>\n'
        '    <ui:HttpClient Endpoint="x"/>\n'
        '    <ui:LogMessage Level="Trace" Message="recuperou status 200"/>\n'
        '  </Sequence>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n5_trace_log_significant(_make_n5_rule(), fc, None)
    assert findings == []


def test_n5_finding_when_trace_only_before_activity(tmp_path):
    """Log ANTES da activity NÃO satisfaz N-5 (semântica é pós-execução)."""
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />\n'
        '  </x:Members>\n'
        '  <Sequence>\n'
        '    <ui:LogMessage Level="Trace" Message="iniciando"/>\n'
        '    <ui:HttpClient Endpoint="x"/>\n'
        '  </Sequence>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n5_trace_log_significant(_make_n5_rule(), fc, None)
    assert any("HttpClient" in f.message for f in findings)


def test_n7_no_invoke_no_finding(tmp_path):
    body = '  <Sequence/>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n7_invoke_log_entry_exit(_make_rule(), fc, None)
    assert findings == []
