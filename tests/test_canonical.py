"""Tests canonical_pins.yaml + synthesis + loader injection."""
from __future__ import annotations

from pathlib import Path

import pytest

from uip_engine.canonical import (
    canonical_pin_for,
    canonical_studio_version,
    load_canonical,
    synthesize_canonical_rules,
)
from uip_engine.context import FileContext, ProjectContext
from uip_engine.detectors import detect_nuget_version_check
from uip_engine.detectors import REGISTRY as DETECTORS
from uip_engine.fixers import REGISTRY as FIXERS
from uip_engine.loader import load_rules


REPO = Path(__file__).resolve().parents[1]
RULES_YAML = REPO / "rules.yaml"
CANONICAL_YAML = REPO / "assets" / "canonical_pins.yaml"


# ---------- canonical_pins.yaml schema ----------

def test_canonical_yaml_exists_and_parses():
    data = load_canonical()
    assert data["version"] == 1
    assert "studio" in data and "version" in data["studio"]
    assert isinstance(data["pins"], list) and len(data["pins"]) >= 16


def test_studio_pin_is_23_10_13():
    assert canonical_studio_version() == "23.10.13"


@pytest.mark.parametrize("package,expected", [
    ("UiPath.System.Activities", "25.4.4"),
    ("UiPath.UIAutomation.Activities", "25.10.8"),
    ("UiPath.Excel.Activities", "3.1.2"),
    ("UiPath.Database.Activities", "1.10.1"),
    ("UiPath.WebAPI.Activities", "1.20.1"),
    ("UiPath.Cryptography.Activities", "1.4.2"),
    ("UiPath.DocumentUnderstanding.OCR.LocalServer", "1.5.1"),
    ("UiPath.IntelligentOCR.Activities", "6.24.0"),
    ("UiPath.Mail.Activities", "1.24.2"),
    ("UiPath.MicrosoftOffice365.Activities", "2.7.24"),
    ("UiPath.OCR.Activities", "3.22.0"),
    ("UiPath.PDF.Activities", "3.22.1"),
    ("UiPath.Testing.Activities", "24.10.4"),
    ("UiPathTeam.SharePoint.Activities", "2.0.3"),
    ("UipathTeam.XML.Activities", "1.1.0"),
    ("UiPath.ComputerVision.LocalServer", "25.10.0"),
    ("UiPath.CoreIpc", "2.0.1"),
])
def test_canonical_pins_match_user_canonical(package, expected):
    assert canonical_pin_for(package) == expected


def test_canonical_pins_unique_ids_and_packages():
    data = load_canonical()
    ids = [e["id"] for e in data["pins"]]
    pkgs = [e["package"] for e in data["pins"]]
    assert len(ids) == len(set(ids)), "duplicate rule ids"
    assert len(pkgs) == len(set(pkgs)), "duplicate package names"


# ---------- Synthesis emits schema-conformant rules ----------

def test_synthesis_emits_d1_and_studio_rules():
    rules = synthesize_canonical_rules()
    ids = {r["id"] for r in rules}
    assert "J-1" in ids  # studio pin
    for letter in "abcdefghijklmnop":
        assert f"D-1{letter}" in ids, f"missing D-1{letter}"


def test_mail_pin_is_required_when_mail_assembly_is_referenced(tmp_path):
    rules = synthesize_canonical_rules()
    rule_dict = next(r for r in rules if r["id"] == "D-1i")
    project_json = tmp_path / "project.json"
    project_json.write_text('{"dependencies": {}}', encoding="utf-8")
    xaml = tmp_path / "Main.xaml"
    xaml.write_text(
        "<Activity>\n"
        "  <AssemblyReference>UiPath.Mail</AssemblyReference>\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    rules_loaded = load_rules(
        RULES_YAML,
        registered_detectors=set(DETECTORS.keys()),
        registered_fixers=set(FIXERS.keys()),
    )
    rule = next(r for r in rules_loaded if r.id == "D-1i")
    pc = ProjectContext(root=tmp_path, project_json={"dependencies": {}})
    findings = detect_nuget_version_check(rule, FileContext(project_json), pc)
    assert "UiPath.Mail" in rule_dict["detect"]["params"]["required_when_assemblies"]
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {
        "type": "set_dependency_pin",
        "package": "UiPath.Mail.Activities",
        "version": "[1.24.2]",
    }


def test_computervision_pin_is_required_when_use_local_server_is_true(tmp_path):
    rules = synthesize_canonical_rules()
    rule_dict = next(r for r in rules if r["id"] == "D-1p")
    project_json = tmp_path / "project.json"
    project_json.write_text('{"dependencies": {}}', encoding="utf-8")
    xaml = tmp_path / "Main.xaml"
    xaml.write_text('<Activity UseLocalServer="True" />', encoding="utf-8")
    rules_loaded = load_rules(
        RULES_YAML,
        registered_detectors=set(DETECTORS.keys()),
        registered_fixers=set(FIXERS.keys()),
    )
    rule = next(r for r in rules_loaded if r.id == "D-1p")
    pc = ProjectContext(root=tmp_path, project_json={"dependencies": {}})
    findings = detect_nuget_version_check(rule, FileContext(project_json), pc)
    assert rule_dict["detect"]["params"]["required_when_xaml_patterns"] == [
        'UseLocalServer="True"'
    ]
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {
        "type": "set_dependency_pin",
        "package": "UiPath.ComputerVision.LocalServer",
        "version": "[25.10.0]",
    }


def test_canonical_package_casing_is_enforced(tmp_path):
    rules_loaded = load_rules(
        RULES_YAML,
        registered_detectors=set(DETECTORS.keys()),
        registered_fixers=set(FIXERS.keys()),
    )
    rule = next(r for r in rules_loaded if r.id == "D-1r")
    project_json = tmp_path / "project.json"
    project_json.write_text(
        '{"dependencies": {"UiPath.CoreIPC": "[2.0.1]"}}',
        encoding="utf-8",
    )
    pc = ProjectContext(
        root=tmp_path,
        project_json={"dependencies": {"UiPath.CoreIPC": "[2.0.1]"}},
    )
    findings = detect_nuget_version_check(rule, FileContext(project_json), pc)
    assert len(findings) == 1
    assert "UiPath.CoreIPC" in findings[0].message
    assert findings[0].fix_mechanical == {
        "type": "set_dependency_pin",
        "package": "UiPath.CoreIpc",
        "version": "[2.0.1]",
    }


def test_synthesized_rules_use_registered_types():
    rules = synthesize_canonical_rules()
    for r in rules:
        det = r["detect"]["type"]
        assert det in DETECTORS, f"unknown detector {det} em {r['id']}"
        mech = (r["fix"] or {}).get("mechanical") or {}
        if mech:
            ft = mech.get("type")
            assert ft in FIXERS, f"unknown fixer {ft} em {r['id']}"


# ---------- Loader injection idempotent ----------

def test_loader_injects_canonical_rules():
    rules = load_rules(
        RULES_YAML,
        registered_detectors=set(DETECTORS.keys()),
        registered_fixers=set(FIXERS.keys()),
    )
    rule_ids = {r.id for r in rules}
    # Canonical IDs sempre presentes (via injection ou rules.yaml legado).
    assert "J-1" in rule_ids  # studio pin
    for letter in "abcdefghijklmnop":
        assert f"D-1{letter}" in rule_ids, f"missing D-1{letter} pós-load"


def test_loader_idempotent_no_duplicates():
    """Carregar rules.yaml duas vezes não duplica IDs."""
    r1 = load_rules(
        RULES_YAML,
        registered_detectors=set(DETECTORS.keys()),
        registered_fixers=set(FIXERS.keys()),
    )
    r2 = load_rules(
        RULES_YAML,
        registered_detectors=set(DETECTORS.keys()),
        registered_fixers=set(FIXERS.keys()),
    )
    assert {r.id for r in r1} == {r.id for r in r2}
    # rules.yaml legado tem D-1a..D-1o; injection deve SKIP esses (idempotente)
    # e injetar somente D-1p + J-STUDIO-PIN. Sem SchemaError de duplicate id.
    ids_count_1 = sorted([r.id for r in r1])
    ids_count_2 = sorted([r.id for r in r2])
    assert ids_count_1 == ids_count_2
