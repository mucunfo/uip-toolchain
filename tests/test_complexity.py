"""Tests for heuristics/complexity.py — CX-1..5."""
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.complexity import (
    detect_cx1_cyclomatic,
    detect_cx2_depth,
    detect_cx3_fanout,
    detect_cx4_activities,
    detect_cx5_god_workflow,
    _cyclomatic,
    _max_nesting_depth,
    _activity_count,
    _parse_xaml,
)


_XAML_HEADER = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
    '          xmlns:ui="http://schemas.uipath.com/workflow/activities"\n'
    '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
)
_XAML_FOOTER = '</Activity>\n'


def _wrap(body: str) -> str:
    return _XAML_HEADER + body + _XAML_FOOTER


def _rule(rid: str, fn: str, params: dict | None = None) -> Rule:
    return Rule(
        id=rid, severity=Severity.WARN, category="architectural", target="all",
        title=f"test {rid}", description="",
        detect={"type": "python", "params": {
            "module": "uip_engine.heuristics.complexity",
            "function": fn,
            **(params or {}),
        }},
        fix={"apply_class": "contextual", "prose": "refactor"},
    )


def _fc(tmp_path: Path, content: str, name: str = "S.xaml") -> FileContext:
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return FileContext(f)


# ---------- CX-1 cyclomatic ----------

def test_cx1_low_no_finding(tmp_path):
    body = '<Sequence />'
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-1", "detect_cx1_cyclomatic", {"threshold_warn": 10})
    assert detect_cx1_cyclomatic(r, fc, None) == []


def test_cx1_high_warn(tmp_path):
    body = "<Sequence>" + "".join(
        f'<If Condition="[v{i}]"><If.Then /></If>' for i in range(12)
    ) + "</Sequence>"
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-1", "detect_cx1_cyclomatic", {"threshold_warn": 10, "threshold_error": 20})
    findings = detect_cx1_cyclomatic(r, fc, None)
    assert len(findings) == 1
    assert "cyclomatic=" in findings[0].message
    assert findings[0].severity == Severity.WARN


def test_cx1_high_error(tmp_path):
    body = "<Sequence>" + "".join(
        f'<If Condition="[v{i}]"><If.Then /></If>' for i in range(22)
    ) + "</Sequence>"
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-1", "detect_cx1_cyclomatic", {"threshold_warn": 10, "threshold_error": 20})
    findings = detect_cx1_cyclomatic(r, fc, None)
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR


def test_cx1_counts_switch_cases(tmp_path):
    body = (
        '<Sequence>'
        '<Switch x:TypeArguments="x:String">'
        '<Sequence x:Key="a"/><Sequence x:Key="b"/><Sequence x:Key="c"/>'
        '</Switch>'
        '</Sequence>'
    )
    fc = _fc(tmp_path, _wrap(body))
    # 3 cases + 0 default = 3 ramos + baseline 1 = 4
    assert _cyclomatic(fc.active_content) == 4


def test_cx1_counts_catches(tmp_path):
    body = (
        '<Sequence>'
        '<TryCatch><TryCatch.Catches>'
        '<Catch x:TypeArguments="s:Exception" />'
        '<Catch x:TypeArguments="s:IOException" />'
        '</TryCatch.Catches></TryCatch>'
        '</Sequence>'
    )
    fc = _fc(tmp_path, _wrap(body))
    assert _cyclomatic(fc.active_content) == 3  # 1 base + 2 catches


# ---------- CX-2 nesting depth ----------

def test_cx2_shallow_no_finding(tmp_path):
    body = '<Sequence><ui:LogMessage /></Sequence>'
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-2", "detect_cx2_depth", {"threshold_warn": 5})
    assert detect_cx2_depth(r, fc, None) == []


def test_cx2_deep_warn(tmp_path):
    inner = '<ui:LogMessage />'
    for _ in range(7):
        inner = f'<Sequence>{inner}</Sequence>'
    fc = _fc(tmp_path, _wrap(inner))
    r = _rule("CX-2", "detect_cx2_depth", {"threshold_warn": 5, "threshold_error": 8})
    findings = detect_cx2_depth(r, fc, None)
    assert len(findings) == 1
    assert "nesting_depth=" in findings[0].message


def test_cx2_property_element_does_not_count(tmp_path):
    body = (
        '<Sequence>'
        '<Sequence.Variables>'
        '<Variable x:TypeArguments="x:String" Name="v1" />'
        '</Sequence.Variables>'
        '<ui:LogMessage />'
        '</Sequence>'
    )
    root = _parse_xaml(_wrap(body))
    # Activity → Sequence → LogMessage = depth 3 raw - 1 = 2.
    # Sequence.Variables é property element (não conta).
    assert _max_nesting_depth(root) == 2


# ---------- CX-3 fan-out ----------

def test_cx3_low(tmp_path):
    body = '<Sequence><ui:InvokeWorkflowFile WorkflowFileName="A.xaml" /></Sequence>'
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-3", "detect_cx3_fanout", {"threshold_warn": 10})
    assert detect_cx3_fanout(r, fc, None) == []


def test_cx3_high(tmp_path):
    invokes = "".join(
        f'<ui:InvokeWorkflowFile WorkflowFileName="W{i}.xaml" />' for i in range(12)
    )
    body = f'<Sequence>{invokes}</Sequence>'
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-3", "detect_cx3_fanout", {"threshold_warn": 10, "threshold_error": 15})
    findings = detect_cx3_fanout(r, fc, None)
    assert len(findings) == 1


def test_cx3_distinct_only(tmp_path):
    # Mesmo callee invocado 5x conta 1
    body = '<Sequence>' + '<ui:InvokeWorkflowFile WorkflowFileName="A.xaml" />' * 5 + '</Sequence>'
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-3", "detect_cx3_fanout", {"threshold_warn": 0})
    findings = detect_cx3_fanout(r, fc, None)
    assert len(findings) == 1
    assert "fan_out=1" in findings[0].message


# ---------- CX-4 activity count ----------

def test_cx4_low(tmp_path):
    body = '<Sequence><ui:LogMessage /></Sequence>'
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-4", "detect_cx4_activities", {"threshold_warn": 100})
    assert detect_cx4_activities(r, fc, None) == []


def test_cx4_high(tmp_path):
    activities = "<ui:LogMessage />" * 110
    body = f'<Sequence>{activities}</Sequence>'
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-4", "detect_cx4_activities", {"threshold_warn": 100, "threshold_error": 300})
    findings = detect_cx4_activities(r, fc, None)
    assert len(findings) == 1


# ---------- CX-5 god-workflow composite ----------

def test_cx5_no_trip(tmp_path):
    body = '<Sequence><ui:LogMessage /></Sequence>'
    fc = _fc(tmp_path, _wrap(body))
    r = _rule("CX-5", "detect_cx5_god_workflow")
    assert detect_cx5_god_workflow(r, fc, None) == []


def test_cx5_three_metrics_tripped(tmp_path):
    # Força ≥3 métricas: lines>200, activities>50, depth>5.
    inner = '<ui:LogMessage />\n' * 250  # 250 activities + 250 linhas
    for _ in range(7):                    # depth ~9
        inner = f'<Sequence>\n{inner}\n</Sequence>'
    body = f'<Sequence>\n{inner}\n</Sequence>'
    content = _wrap(body)
    fc = _fc(tmp_path, content)
    r = _rule("CX-5", "detect_cx5_god_workflow")
    findings = detect_cx5_god_workflow(r, fc, None)
    assert len(findings) == 1
    assert "métricas excedidas" in findings[0].message
