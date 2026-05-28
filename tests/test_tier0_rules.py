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
