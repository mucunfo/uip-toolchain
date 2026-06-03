"""Tests Tier 0 regras novas: D-1q-CCS-AUTO, J-MUST-RESTORE-ALL,
J-PIN-BRACKETS, W-MSCORLIB-REF."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.ccs_latest_pin import (
    _parse_semver,
    _scan_latest,
    _scan_project_ccs_assemblies,
    detect_ccs_latest_pin,
)
from uip_engine.heuristics.pin_brackets import detect_pin_brackets


# ---------- helpers ----------

def _mk_rule(rid: str, severity: Severity = Severity.ERROR) -> Rule:
    return Rule(
        id=rid,
        severity=severity,
        category="breaking",
        target="windows",
        title=rid,
        description="",
        detect={"type": "python"},
        fix={"apply_class": "deterministic", "prose": f"prose-{rid}"},
    )


def _mk_pc(tmp_path: Path, project_json: dict) -> ProjectContext:
    proj = tmp_path / "P"
    proj.mkdir(exist_ok=True)
    (proj / "project.json").write_text(json.dumps(project_json), encoding="utf-8")
    return ProjectContext(root=proj, project_json=project_json)


# ---------- D-1q-CCS-AUTO ----------

def test_ccs_semver_parse_orders_release_above_prerelease():
    # Release X.Y.Z deve ordenar acima de X.Y.Z-pre
    assert _parse_semver("1.0.0") > _parse_semver("1.0.0-alpha")
    assert _parse_semver("2.0.0") > _parse_semver("1.9.9")
    assert _parse_semver("1.0.10") > _parse_semver("1.0.9")


def test_ccs_scan_latest_picks_max_per_package(tmp_path):
    nupkgs = tmp_path / "nupkgs"
    nupkgs.mkdir()
    (nupkgs / "CCS_Foo.1.0.0.nupkg").touch()
    (nupkgs / "CCS_Foo.1.2.0.nupkg").touch()
    (nupkgs / "CCS_Foo.1.1.5.nupkg").touch()
    (nupkgs / "CCS_Bar.3.0.3.nupkg").touch()
    # Non-CCS file should be ignored
    (nupkgs / "UiPath.System.Activities.25.4.4.nupkg").touch()
    out = _scan_latest(nupkgs)
    assert out == {"CCS_Foo": "1.2.0", "CCS_Bar": "3.0.3"}


def test_ccs_scan_latest_empty_dir(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert _scan_latest(empty) == {}


def test_scan_project_ccs_assemblies_reads_hard_xaml_usage(tmp_path):
    pc = _mk_pc(tmp_path, {"dependencies": {}})
    xaml = pc.root / "Framework" / "Init.xaml"
    xaml.parent.mkdir()
    xaml.write_text(
        '<Activity xmlns:c="clr-namespace:CCS_SipagNet;assembly=CCS_SipagNet">\n'
        "  <c:Login />\n"
        "  <AssemblyReference>CCS_Controle</AssemblyReference>\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    found = _scan_project_ccs_assemblies(pc.root)
    assert found["CCS_SipagNet"] == xaml
    assert "CCS_Controle" not in found


def test_scan_project_ccs_assemblies_ignores_text_expression_imports(tmp_path):
    pc = _mk_pc(tmp_path, {"dependencies": {}})
    xaml = pc.root / "Framework" / "Init.xaml"
    xaml.parent.mkdir()
    xaml.write_text(
        "<Activity>\n"
        "  <TextExpression.NamespacesForImplementation>\n"
        "    <x:String>CCS_EstruturaPastas.EstruturaPastas</x:String>\n"
        "  </TextExpression.NamespacesForImplementation>\n"
        "  <TextExpression.ReferencesForImplementation>\n"
        "    <AssemblyReference>CCS_EstruturaPastas</AssemblyReference>\n"
        "  </TextExpression.ReferencesForImplementation>\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    assert _scan_project_ccs_assemblies(pc.root) == {}


def test_ccs_latest_pin_detector_emits_finding_on_drift(tmp_path):
    rule = _mk_rule("D-1q-CCS-AUTO")
    pc = _mk_pc(tmp_path, {
        "targetFramework": "Windows",
        "dependencies": {"CCS_Foo": "[1.0.0]", "CCS_Bar": "[3.0.3]"},
    })
    nupkgs = tmp_path / "nupkgs"
    nupkgs.mkdir()
    (nupkgs / "CCS_Foo.1.2.0.nupkg").touch()
    (nupkgs / "CCS_Bar.3.0.3.nupkg").touch()
    with patch("uip_engine.heuristics.ccs_latest_pin._NUPKGS_DIR", nupkgs):
        findings = detect_ccs_latest_pin(rule, FileContext(pc.root / "project.json"), pc)
    # CCS_Foo drift detected, CCS_Bar OK
    assert len(findings) == 1
    f = findings[0]
    assert "CCS_Foo" in f.message
    assert "1.2.0" in f.message
    assert f.fix_mechanical == {
        "type": "set_dependency_pin",
        "package": "CCS_Foo",
        "version": "[1.2.0]",
    }


def test_ccs_latest_pin_adds_missing_dependency_from_hard_xaml_usage(tmp_path):
    rule = _mk_rule("D-1q-CCS-AUTO")
    pc = _mk_pc(tmp_path, {
        "targetFramework": "Windows",
        "dependencies": {"CCS_Controle": "[1.1.0]"},
    })
    xaml = pc.root / "Framework" / "InitAllApplications.xaml"
    xaml.parent.mkdir()
    xaml.write_text(
        '<Activity xmlns:c="clr-namespace:CCS_SipagNet;assembly=CCS_SipagNet">\n'
        "  <c:Login />\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    nupkgs = tmp_path / "nupkgs"
    nupkgs.mkdir()
    (nupkgs / "CCS_Controle.1.1.0.nupkg").touch()
    (nupkgs / "CCS_SipagNet.2.0.0.nupkg").touch()
    with patch("uip_engine.heuristics.ccs_latest_pin._NUPKGS_DIR", nupkgs):
        findings = detect_ccs_latest_pin(rule, FileContext(pc.root / "project.json"), pc)
    assert len(findings) == 1
    f = findings[0]
    assert "CCS_SipagNet" in f.message
    assert "InitAllApplications.xaml" in f.message
    assert f.fix_mechanical == {
        "type": "set_dependency_pin",
        "package": "CCS_SipagNet",
        "version": "[2.0.0]",
    }


def test_ccs_latest_pin_ignores_stale_assembly_reference_only(tmp_path):
    rule = _mk_rule("D-1q-CCS-AUTO")
    pc = _mk_pc(tmp_path, {
        "targetFramework": "Windows",
        "dependencies": {"CCS_Controle": "[1.1.0]"},
    })
    xaml = pc.root / "Framework" / "InitAllApplications.xaml"
    xaml.parent.mkdir()
    xaml.write_text(
        "<Activity>\n"
        "  <TextExpression.ReferencesForImplementation>\n"
        "    <AssemblyReference>CCS_SipagNet</AssemblyReference>\n"
        "  </TextExpression.ReferencesForImplementation>\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    nupkgs = tmp_path / "nupkgs"
    nupkgs.mkdir()
    (nupkgs / "CCS_Controle.1.1.0.nupkg").touch()
    (nupkgs / "CCS_SipagNet.2.0.0.nupkg").touch()
    with patch("uip_engine.heuristics.ccs_latest_pin._NUPKGS_DIR", nupkgs):
        findings = detect_ccs_latest_pin(rule, FileContext(pc.root / "project.json"), pc)
    assert findings == []


def test_ccs_latest_pin_diagnoses_missing_referenced_ccs_package(tmp_path):
    rule = _mk_rule("D-1q-CCS-AUTO")
    pc = _mk_pc(tmp_path, {
        "targetFramework": "Windows",
        "dependencies": {},
    })
    xaml = pc.root / "Framework" / "InitAllApplications.xaml"
    xaml.parent.mkdir()
    xaml.write_text(
        '<Activity xmlns:c="clr-namespace:CCS_SipagNet;assembly=CCS_SipagNet">\n'
        "  <c:Login />\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    nupkgs = tmp_path / "nupkgs"
    nupkgs.mkdir()
    with patch("uip_engine.heuristics.ccs_latest_pin._NUPKGS_DIR", nupkgs):
        findings = detect_ccs_latest_pin(rule, FileContext(pc.root / "project.json"), pc)
    assert len(findings) == 1
    assert "nao existe CCS_SipagNet.*.nupkg" in findings[0].message
    assert findings[0].fix_mechanical is None


def test_ccs_latest_pin_diagnoses_declared_ccs_missing_from_nupkgs(tmp_path):
    rule = _mk_rule("D-1q-CCS-AUTO")
    pc = _mk_pc(tmp_path, {
        "targetFramework": "Windows",
        "dependencies": {"CCS_SipagNet": "[2.0.0]"},
    })
    nupkgs = tmp_path / "nupkgs"
    nupkgs.mkdir()
    with patch("uip_engine.heuristics.ccs_latest_pin._NUPKGS_DIR", nupkgs):
        findings = detect_ccs_latest_pin(rule, FileContext(pc.root / "project.json"), pc)
    assert len(findings) == 1
    assert "project.json declara CCS_SipagNet" in findings[0].message
    assert "nao existe CCS_SipagNet.*.nupkg" in findings[0].message
    assert findings[0].fix_mechanical is None


def test_ccs_latest_pin_skips_non_ccs_deps(tmp_path):
    rule = _mk_rule("D-1q-CCS-AUTO")
    pc = _mk_pc(tmp_path, {
        "targetFramework": "Windows",
        "dependencies": {
            "UiPath.System.Activities": "[25.4.4]",
            "CCS_Foo": "[1.0.0]",
        },
    })
    nupkgs = tmp_path / "nupkgs"
    nupkgs.mkdir()
    (nupkgs / "CCS_Foo.1.2.0.nupkg").touch()
    with patch("uip_engine.heuristics.ccs_latest_pin._NUPKGS_DIR", nupkgs):
        findings = detect_ccs_latest_pin(rule, FileContext(pc.root / "project.json"), pc)
    # Só CCS_Foo flagged, UiPath.System.Activities ignorado (não está em .nupkgs)
    assert len(findings) == 1
    assert "CCS_Foo" in findings[0].message


# ---------- J-PIN-BRACKETS ----------

def test_pin_brackets_passes_when_all_bracketed(tmp_path):
    rule = _mk_rule("J-PIN-BRACKETS")
    pc = _mk_pc(tmp_path, {
        "dependencies": {
            "UiPath.System.Activities": "[25.4.4]",
            "UiPath.OCR.Activities": "[3.22.0]",
        },
    })
    findings = detect_pin_brackets(rule, FileContext(pc.root / "project.json"), pc)
    assert findings == []


def test_pin_brackets_flags_floating_range(tmp_path):
    rule = _mk_rule("J-PIN-BRACKETS")
    pc = _mk_pc(tmp_path, {
        "dependencies": {
            # ComputerVision sem brackets — caso real pilot
            "UiPath.ComputerVision.LocalServer": "21.10.1",
            "UiPath.System.Activities": "[25.4.4]",
        },
    })
    findings = detect_pin_brackets(rule, FileContext(pc.root / "project.json"), pc)
    assert len(findings) == 1
    f = findings[0]
    assert "UiPath.ComputerVision.LocalServer" in f.message
    assert f.fix_mechanical == {
        "type": "set_dependency_pin",
        "package": "UiPath.ComputerVision.LocalServer",
        "version": "[21.10.1]",
    }


def test_pin_brackets_flags_complex_range_no_mechanical_fix(tmp_path):
    rule = _mk_rule("J-PIN-BRACKETS")
    pc = _mk_pc(tmp_path, {
        "dependencies": {
            "Foo.Bar": "[1.0,2.0)",  # NuGet range syntax
        },
    })
    findings = detect_pin_brackets(rule, FileContext(pc.root / "project.json"), pc)
    assert len(findings) == 1
    # Range complexo → sem mechanical fix (decisão manual)
    assert findings[0].fix_mechanical is None
