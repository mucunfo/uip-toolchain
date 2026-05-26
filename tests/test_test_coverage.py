"""Tests for heuristics/test_coverage.py — TCC-1/3/4."""
import json
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.test_coverage import (
    detect_tc_cov_1_missing,
    detect_tc_cov_3_no_tests_folder,
    detect_tc_cov_4_low_arg_variation,
)


_HEADER = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
)
_FOOTER = '</Activity>\n'


def _rule(rid: str) -> Rule:
    return Rule(
        id=rid, severity=Severity.WARN, category="testing", target="all",
        title=f"test {rid}", description="",
        detect={"type": "python", "params": {}},
        fix={"apply_class": "contextual", "prose": "write TC"},
    )


def _make_perf_project(tmp_path: Path, name: str = "X_Performer") -> ProjectContext:
    pj = tmp_path / "project.json"
    manifest = {"name": name, "description": "x"}
    pj.write_text(json.dumps(manifest), encoding="utf-8")
    return ProjectContext(root=tmp_path, project_json=manifest)


def _write_wf(path: Path, in_args: int = 0) -> None:
    args_xml = "".join(
        f'<x:Property Name="in_arg{i}" Type="InArgument(x:String)" />' for i in range(in_args)
    )
    body = f'<x:Members>{args_xml}</x:Members>\n<Sequence />\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_HEADER + body + _FOOTER, encoding="utf-8")


# ---------- TCC-1 ----------

def test_tcc1_no_tc_emits(tmp_path):
    pc = _make_perf_project(tmp_path)
    wf = tmp_path / "Process.xaml"
    _write_wf(wf)
    fc = FileContext(wf)
    findings = detect_tc_cov_1_missing(_rule("TCC-1"), fc, pc)
    assert len(findings) == 1
    assert "TC_Process.xaml" in findings[0].message


def test_tcc1_tc_present_no_finding(tmp_path):
    pc = _make_perf_project(tmp_path)
    wf = tmp_path / "Process.xaml"
    _write_wf(wf)
    tc = tmp_path / "Tests" / "TC_Process.xaml"
    _write_wf(tc)
    fc = FileContext(wf)
    assert detect_tc_cov_1_missing(_rule("TCC-1"), fc, pc) == []


def test_tcc1_main_skipped(tmp_path):
    pc = _make_perf_project(tmp_path)
    main = tmp_path / "Main.xaml"
    _write_wf(main)
    fc = FileContext(main)
    assert detect_tc_cov_1_missing(_rule("TCC-1"), fc, pc) == []


def test_tcc1_framework_excluded(tmp_path):
    pc = _make_perf_project(tmp_path)
    wf = tmp_path / "Framework" / "InitAllSettings.xaml"
    _write_wf(wf)
    fc = FileContext(wf)
    assert detect_tc_cov_1_missing(_rule("TCC-1"), fc, pc) == []


def test_tcc1_non_performer_skip(tmp_path):
    pc = _make_perf_project(tmp_path, name="Dispatcher")  # sem suffix _Performer
    wf = tmp_path / "Process.xaml"
    _write_wf(wf)
    fc = FileContext(wf)
    assert detect_tc_cov_1_missing(_rule("TCC-1"), fc, pc) == []


# ---------- TCC-3 ----------

def test_tcc3_no_tests_folder(tmp_path):
    pc = _make_perf_project(tmp_path)
    fc = FileContext(pc.root / "project.json")
    findings = detect_tc_cov_3_no_tests_folder(_rule("TCC-3"), fc, pc)
    assert len(findings) == 1


def test_tcc3_empty_tests_folder(tmp_path):
    pc = _make_perf_project(tmp_path)
    (tmp_path / "Tests").mkdir()
    fc = FileContext(pc.root / "project.json")
    findings = detect_tc_cov_3_no_tests_folder(_rule("TCC-3"), fc, pc)
    assert len(findings) == 1


def test_tcc3_populated_tests_folder(tmp_path):
    pc = _make_perf_project(tmp_path)
    tdir = tmp_path / "Tests"
    tdir.mkdir()
    _write_wf(tdir / "TC_Sample.xaml")
    fc = FileContext(pc.root / "project.json")
    assert detect_tc_cov_3_no_tests_folder(_rule("TCC-3"), fc, pc) == []


def test_tcc3_non_performer(tmp_path):
    pc = _make_perf_project(tmp_path, name="Dispatcher")
    fc = FileContext(pc.root / "project.json")
    assert detect_tc_cov_3_no_tests_folder(_rule("TCC-3"), fc, pc) == []


# ---------- TCC-4 ----------

def _rule_tcc4() -> Rule:
    return Rule(
        id="TCC-4", severity=Severity.INFO, category="testing", target="all",
        title="low variation", description="",
        detect={"type": "python", "params": {"arg_threshold": 3}},
        fix={"apply_class": "contextual", "prose": "add TC"},
    )


def test_tcc4_low_args_skip(tmp_path):
    pc = _make_perf_project(tmp_path)
    wf = tmp_path / "X.xaml"
    _write_wf(wf, in_args=2)
    fc = FileContext(wf)
    assert detect_tc_cov_4_low_arg_variation(_rule_tcc4(), fc, pc) == []


def test_tcc4_high_args_no_tc(tmp_path):
    pc = _make_perf_project(tmp_path)
    wf = tmp_path / "X.xaml"
    _write_wf(wf, in_args=5)
    fc = FileContext(wf)
    findings = detect_tc_cov_4_low_arg_variation(_rule_tcc4(), fc, pc)
    assert len(findings) == 1


def test_tcc4_high_args_multiple_tc(tmp_path):
    pc = _make_perf_project(tmp_path)
    wf = tmp_path / "X.xaml"
    _write_wf(wf, in_args=5)
    tdir = tmp_path / "Tests"
    tdir.mkdir()
    _write_wf(tdir / "TC_X.xaml")
    _write_wf(tdir / "TC_X_edge.xaml")
    fc = FileContext(wf)
    assert detect_tc_cov_4_low_arg_variation(_rule_tcc4(), fc, pc) == []
