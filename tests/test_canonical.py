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
    ("UiPath.ComputerVision.LocalServer", "21.10.1"),
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
