import json as jsonlib
from pathlib import Path
import pytest
from scripts.rule_engine.detectors import (
    detect_json_field_check, detect_json_version_compare, detect_nuget_version_check,
    REGISTRY,
)
from scripts.rule_engine._types import Rule, Severity
from scripts.rule_engine.context import FileContext, ProjectContext


def make_rule(detect_params, sev=Severity.WARN, category="architectural"):
    return Rule(
        id="X-T", severity=sev, category=category, target="all",
        title="t", description="",
        detect=detect_params,
    )


# ---- Task 21: json_field_check ----

def test_json_field_check_expected_value(tmp_path):
    pj = tmp_path / "project.json"
    pj.write_text(jsonlib.dumps({"studioVersion": "21.10.8.0"}))
    fc = FileContext(pj)
    rule = make_rule({
        "type": "json_field_check",
        "params": {"path": "studioVersion", "expected": "23.10.13"},
    })
    findings = detect_json_field_check(rule, fc, None)
    assert len(findings) == 1


def test_json_field_check_matches_no_finding(tmp_path):
    pj = tmp_path / "project.json"
    pj.write_text(jsonlib.dumps({"studioVersion": "23.10.13"}))
    fc = FileContext(pj)
    rule = make_rule({
        "type": "json_field_check",
        "params": {"path": "studioVersion", "expected": "23.10.13"},
    })
    assert detect_json_field_check(rule, fc, None) == []


def test_json_field_check_in_set(tmp_path):
    pj = tmp_path / "project.json"
    pj.write_text(jsonlib.dumps({"targetFramework": "Bogus"}))
    fc = FileContext(pj)
    rule = make_rule({
        "type": "json_field_check",
        "params": {"path": "targetFramework", "expected_in": ["Windows", "Legacy"]},
    }, sev=Severity.ERROR, category="breaking")
    findings = detect_json_field_check(rule, fc, None)
    assert len(findings) == 1


# ---- Task 22: json_version_compare ----

def test_json_version_compare_below_min(tmp_path):
    pj = tmp_path / "project.json"
    pj.write_text(jsonlib.dumps({"studioVersion": "21.10.8.0"}))
    fc = FileContext(pj)
    rule = make_rule({
        "type": "json_version_compare",
        "params": {"path": "studioVersion", "min": "23.10.0"},
    })
    findings = detect_json_version_compare(rule, fc, None)
    assert len(findings) == 1


def test_json_version_compare_above_min_no_finding(tmp_path):
    pj = tmp_path / "project.json"
    pj.write_text(jsonlib.dumps({"studioVersion": "24.0.0"}))
    fc = FileContext(pj)
    rule = make_rule({
        "type": "json_version_compare",
        "params": {"path": "studioVersion", "min": "23.10.0"},
    })
    assert detect_json_version_compare(rule, fc, None) == []


# ---- Task 23: nuget_version_check ----

def test_nuget_below_min(tmp_path):
    proj = tmp_path / "P"
    proj.mkdir()
    pj = proj / "project.json"
    pj.write_text(jsonlib.dumps({
        "targetFramework": "Windows",
        "dependencies": {"UiPath.UIAutomation.Activities": "[20.0.0]"}
    }))
    f = proj / "Foo.xaml"
    f.write_text("<Activity/>")
    fc = FileContext(f)
    pc = ProjectContext.find_root(f)
    rule = make_rule({
        "type": "nuget_version_check",
        "params": {"package": "UiPath.UIAutomation.Activities", "min": "23.10.0"},
    }, sev=Severity.ERROR, category="breaking")
    findings = detect_nuget_version_check(rule, fc, pc)
    assert len(findings) == 1


def test_nuget_above_min_no_finding(tmp_path):
    proj = tmp_path / "P"
    proj.mkdir()
    pj = proj / "project.json"
    pj.write_text(jsonlib.dumps({
        "targetFramework": "Windows",
        "dependencies": {"UiPath.UIAutomation.Activities": "[25.10.8]"}
    }))
    f = proj / "Foo.xaml"
    f.write_text("<Activity/>")
    fc = FileContext(f)
    pc = ProjectContext.find_root(f)
    rule = make_rule({
        "type": "nuget_version_check",
        "params": {"package": "UiPath.UIAutomation.Activities", "min": "23.10.0"},
    })
    assert detect_nuget_version_check(rule, fc, pc) == []


# ---- Pin EXACT enforcement (Activity Migrator drift protection) ----

def _mk_pkg_ctx(tmp_path, version):
    proj = tmp_path / "P"
    proj.mkdir(exist_ok=True)
    pj = proj / "project.json"
    pj.write_text(jsonlib.dumps({
        "targetFramework": "Windows",
        "dependencies": {"UiPath.UIAutomation.Activities": f"[{version}]"}
    }))
    f = proj / "Foo.xaml"
    f.write_text("<Activity/>")
    return FileContext(f), ProjectContext.find_root(f)


def test_nuget_exact_match_no_finding(tmp_path):
    """actual == exact pin -> 0 findings."""
    fc, pc = _mk_pkg_ctx(tmp_path, "25.10.8")
    rule = make_rule({
        "type": "nuget_version_check",
        "params": {"package": "UiPath.UIAutomation.Activities", "exact": "25.10.8"},
    }, sev=Severity.ERROR, category="breaking")
    assert detect_nuget_version_check(rule, fc, pc) == []


def test_nuget_exact_drift_above_pin_flags(tmp_path):
    """actual > exact pin -> finding (Activity Migrator drift case).

    Caso real: UIA pinado 25.10.8, Migrator instalou 25.10.21, engine
    antiga (só `min:`) deixava passar silente. Com `exact:` flagueia.
    """
    fc, pc = _mk_pkg_ctx(tmp_path, "25.10.21")
    rule = make_rule({
        "type": "nuget_version_check",
        "params": {"package": "UiPath.UIAutomation.Activities", "exact": "25.10.8"},
    }, sev=Severity.ERROR, category="breaking")
    findings = detect_nuget_version_check(rule, fc, pc)
    assert len(findings) == 1
    assert "25.10.8" in findings[0].message
    assert "25.10.21" in findings[0].message


def test_nuget_exact_drift_below_pin_flags(tmp_path):
    """actual < exact pin -> finding."""
    fc, pc = _mk_pkg_ctx(tmp_path, "25.10.7")
    rule = make_rule({
        "type": "nuget_version_check",
        "params": {"package": "UiPath.UIAutomation.Activities", "exact": "25.10.8"},
    }, sev=Severity.ERROR, category="breaking")
    findings = detect_nuget_version_check(rule, fc, pc)
    assert len(findings) == 1
    assert "25.10.7" in findings[0].message


def test_nuget_exact_takes_precedence_over_min(tmp_path):
    """Quando ambos exact+min são declarados, exact prevalece."""
    fc, pc = _mk_pkg_ctx(tmp_path, "25.10.21")
    rule = make_rule({
        "type": "nuget_version_check",
        "params": {
            "package": "UiPath.UIAutomation.Activities",
            "exact": "25.10.8",
            "min": "20.0.0",  # versão atual passa min, mas falha exact
        },
    }, sev=Severity.ERROR, category="breaking")
    findings = detect_nuget_version_check(rule, fc, pc)
    assert len(findings) == 1
    assert "esperado [25.10.8]" in findings[0].message


def test_nuget_min_only_backward_compat(tmp_path):
    """Regras só com `min:` (sem `exact:`) continuam funcionando como antes."""
    # actual >= min -> sem finding
    fc, pc = _mk_pkg_ctx(tmp_path, "25.10.21")
    rule = make_rule({
        "type": "nuget_version_check",
        "params": {"package": "UiPath.UIAutomation.Activities", "min": "23.10.0"},
    })
    assert detect_nuget_version_check(rule, fc, pc) == []

    # actual < min -> finding
    fc2, pc2 = _mk_pkg_ctx(tmp_path, "20.0.0")
    # tmp_path overlap recriou P/project.json -> reload pc
    rule2 = make_rule({
        "type": "nuget_version_check",
        "params": {"package": "UiPath.UIAutomation.Activities", "min": "23.10.0"},
    }, sev=Severity.ERROR, category="breaking")
    findings = detect_nuget_version_check(rule2, fc2, pc2)
    assert len(findings) == 1
    assert "mínimo 23.10.0" in findings[0].message


# ---- Registry ----

def test_registry_has_data_detectors():
    for name in ("json_field_check", "json_version_compare", "nuget_version_check"):
        assert name in REGISTRY


import shutil
from scripts.rule_engine.detectors import detect_config_xlsx_keys


FIX_DIR = Path(__file__).parent / "fixtures"


# ---- Task 24: config_xlsx_keys ----

def test_config_xlsx_keys_missing(tmp_path):
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    cfg_dir = proj / "assets" / "configs"
    cfg_dir.mkdir(parents=True)
    shutil.copy(FIX_DIR / "config_sample.xlsx", cfg_dir / "Config_Performer.xlsx")

    f = proj / "Foo.xaml"
    f.write_text('<Activity>[in_Config(&quot;NonExistentKey&quot;).ToString]</Activity>')
    fc = FileContext(f)
    pc = ProjectContext.find_root(f)

    rule = make_rule({"type": "config_xlsx_keys", "params": {"mode": "missing"}},
                     sev=Severity.ERROR, category="architectural")
    findings = detect_config_xlsx_keys(rule, fc, pc)
    assert len(findings) == 1
    assert "NonExistentKey" in findings[0].message


def test_config_xlsx_keys_existing_no_finding(tmp_path):
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    cfg_dir = proj / "assets" / "configs"
    cfg_dir.mkdir(parents=True)
    shutil.copy(FIX_DIR / "config_sample.xlsx", cfg_dir / "Config_Performer.xlsx")

    f = proj / "Foo.xaml"
    f.write_text('<Activity>[in_Config(&quot;KeyA&quot;).ToString]</Activity>')
    fc = FileContext(f)
    pc = ProjectContext.find_root(f)

    rule = make_rule({"type": "config_xlsx_keys", "params": {"mode": "missing"}})
    assert detect_config_xlsx_keys(rule, fc, pc) == []


def test_registry_has_xlsx_detectors():
    assert "config_xlsx_keys" in REGISTRY
