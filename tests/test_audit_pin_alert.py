"""Regression tests for AUDIT_2026-05-28 D-PINALERT fix (lane: pin_alert).

Finding D-PINALERT (HIGH bug): the deterministic `strip_xml_attribute`
mechanical fixer was emitted with ONLY {type, attribute} — no element
scope — so an `--apply` run stripped the attribute file-wide, including
unrelated valid activities (e.g. a generic `Folder` arg on CreateDirectory).
Silent data loss with no rollback (XAML stays well-formed).

Per the D-PINALERT CONTRACT, the DETECTOR now adds an `element` key to the
strip_xml_attribute mech = the activity element name from the matched
pattern (e.g. "uma:Office365ApplicationScope", "ui:CopyFile"), so the
fixer can scope the strip to that element's open tag only.

These tests cover the DETECTOR side only (this lane owns pin_alert.py).
They build lightweight duck-typed stand-ins for Rule/FileContext/
ProjectContext to stay isolated from the rest of the package.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from uip_engine.heuristics.pin_alert import (
    _element_from_pattern,
    _reset_cache_for_tests,
    _scoped_mech,
    detect_pin_alert,
)


# --------------------------------------------------------------------------
# pure-helper unit tests (no detector, no YAML)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "pattern,expected",
    [
        (r"<uma:Office365ApplicationScope\b[^>]*\bFolder\s*=",
         "uma:Office365ApplicationScope"),
        (r"<ui:CopyFile\b[^>]*\bDestinationResource\s*=", "ui:CopyFile"),
        (r"<ui:CopyFile\b[^>]*\bPathResource\s*=", "ui:CopyFile"),
        (r"<ui:RetryScope\b[^>]*\bLogRetriedExceptions\s*=", "ui:RetryScope"),
        (r"<uix:NWindowOperation\b", "uix:NWindowOperation"),
    ],
)
def test_element_from_pattern_extracts_prefixed_tag(pattern, expected):
    assert _element_from_pattern(pattern) == expected


def test_element_from_pattern_returns_none_without_tag_anchor():
    # pattern not anchored on `<tag\b` -> no reliable element -> None
    assert _element_from_pattern(r"Folder\s*=") is None
    assert _element_from_pattern(r"") is None


def test_scoped_mech_adds_element_for_strip_xml_attribute():
    mech = {"type": "strip_xml_attribute", "attribute": "Folder"}
    out = _scoped_mech(mech, r"<uma:Office365ApplicationScope\b[^>]*\bFolder\s*=")
    assert out["type"] == "strip_xml_attribute"
    assert out["attribute"] == "Folder"
    assert out["element"] == "uma:Office365ApplicationScope"


def test_scoped_mech_does_not_mutate_source_dict():
    # MUST NOT mutate the cached YAML dict — work on a copy.
    mech = {"type": "strip_xml_attribute", "attribute": "Folder"}
    out = _scoped_mech(mech, r"<uma:Office365ApplicationScope\b[^>]*\bFolder\s*=")
    assert "element" not in mech  # original untouched
    assert out is not mech


def test_scoped_mech_preserves_explicit_catalog_element():
    # if the catalog already pins `element`, respect it (no override).
    mech = {"type": "strip_xml_attribute", "attribute": "Folder",
            "element": "uma:Custom"}
    out = _scoped_mech(mech, r"<uma:Office365ApplicationScope\b[^>]*\bFolder\s*=")
    assert out["element"] == "uma:Custom"


def test_scoped_mech_ignores_non_strip_mech():
    # strip_nwindow_operation and other types must pass through unchanged.
    mech = {"type": "strip_nwindow_operation"}
    out = _scoped_mech(mech, r"<uix:NWindowOperation\b")
    assert out == {"type": "strip_nwindow_operation"}
    assert "element" not in out


def test_scoped_mech_none_passthrough():
    assert _scoped_mech(None, r"<ui:CopyFile\b") is None


def test_scoped_mech_no_element_when_pattern_unanchored():
    # pattern with no `<tag\b` anchor -> cannot scope -> stays file-wide.
    mech = {"type": "strip_xml_attribute", "attribute": "Folder"}
    out = _scoped_mech(mech, r"Folder\s*=")
    assert "element" not in out
    assert out == {"type": "strip_xml_attribute", "attribute": "Folder"}


# --------------------------------------------------------------------------
# detector integration tests (drive detect_pin_alert against real catalog)
# --------------------------------------------------------------------------

def _engine_root() -> Path:
    # .../tests/test_audit_pin_alert.py -> repo root is parents[1]
    return Path(__file__).resolve().parents[1]


def _make_rule():
    from uip_engine._types import Severity
    return SimpleNamespace(
        id="D-PINALERT",
        severity=Severity.ERROR,
        category="breaking",
        title="D-PINALERT",
    )


def _make_fc(content: str):
    # duck-typed FileContext: only .path and .active_content are read.
    return SimpleNamespace(
        path=Path("Main.xaml"),
        active_content=content,
    )


def _make_pc(deps: dict):
    return SimpleNamespace(project_json={"dependencies": deps})


def test_detector_scopes_removed_api_folder_to_office365_element():
    """removed_apis Folder case (the high-severity data-loss case)."""
    _reset_cache_for_tests()
    # pin AT/ABOVE removed_in 3.0.0 (Migrator post-bump) so the removed_api
    # alert fires on the orphaned legacy Folder attr (logic: pinned_v >= rem_v)
    deps = {"UiPath.MicrosoftOffice365.Activities": "[3.1.0]"}
    content = (
        '<uma:Office365ApplicationScope Folder="{x:Null}">'
        "</uma:Office365ApplicationScope>"
    )
    findings = detect_pin_alert(_make_rule(), _make_fc(content), _make_pc(deps))
    assert findings, "expected a D-PINALERT finding for orphaned Folder attr"
    folder_findings = [
        f for f in findings
        if isinstance(f.fix_mechanical, dict)
        and f.fix_mechanical.get("attribute") == "Folder"
    ]
    assert folder_findings, "no strip_xml_attribute(Folder) mech emitted"
    mech = folder_findings[0].fix_mechanical
    assert mech["type"] == "strip_xml_attribute"
    # THE FIX: element scope is present so the fixer won't strip Folder
    # off unrelated activities (e.g. CreateDirectory) file-wide.
    assert mech["element"] == "uma:Office365ApplicationScope"
    _reset_cache_for_tests()


def test_detector_scopes_copyfile_destination_resource():
    """apis (introduced_in) CopyFile.DestinationResource case."""
    _reset_cache_for_tests()
    # pin below introduced_in 25.10.21 so the alert fires
    deps = {"UiPath.UIAutomation.Activities": "[25.10.8]"}
    content = '<ui:CopyFile DestinationResource="x" DisplayName="cp" />'
    findings = detect_pin_alert(_make_rule(), _make_fc(content), _make_pc(deps))
    dr = [
        f for f in findings
        if isinstance(f.fix_mechanical, dict)
        and f.fix_mechanical.get("attribute") == "DestinationResource"
    ]
    assert dr, "no strip_xml_attribute(DestinationResource) mech emitted"
    mech = dr[0].fix_mechanical
    assert mech["type"] == "strip_xml_attribute"
    assert mech["element"] == "ui:CopyFile"
    _reset_cache_for_tests()


def test_detector_does_not_scope_nwindow_operation_element_mech():
    """strip_nwindow_operation must remain unchanged (no element key)."""
    _reset_cache_for_tests()
    deps = {"UiPath.UIAutomation.Activities": "[25.10.8]"}
    content = '<uix:NWindowOperation Mode="Close" />'
    findings = detect_pin_alert(_make_rule(), _make_fc(content), _make_pc(deps))
    nwin = [
        f for f in findings
        if isinstance(f.fix_mechanical, dict)
        and f.fix_mechanical.get("type") == "strip_nwindow_operation"
    ]
    assert nwin, "expected NWindowOperation finding"
    assert "element" not in nwin[0].fix_mechanical
    _reset_cache_for_tests()


def test_detector_does_not_mutate_cached_catalog():
    """Two consecutive runs must not see element leak into the cache."""
    _reset_cache_for_tests()
    deps = {"UiPath.MicrosoftOffice365.Activities": "[3.1.0]"}
    content = '<uma:Office365ApplicationScope Folder="{x:Null}" />'
    rule, fc, pc = _make_rule(), _make_fc(content), _make_pc(deps)
    first = detect_pin_alert(rule, fc, pc)
    second = detect_pin_alert(rule, fc, pc)
    # both runs produce identical scoped mechs; cache dict never gained
    # an 'element' key in place (would corrupt other shared consumers).
    from uip_engine.heuristics import pin_alert as pa
    cached = pa._CACHE["UiPath.MicrosoftOffice365.Activities"]
    cached_mech = cached["removed_apis"][0]["mechanical"]
    assert "element" not in cached_mech, "cached catalog mech was mutated!"
    assert first[0].fix_mechanical["element"] == "uma:Office365ApplicationScope"
    assert second[0].fix_mechanical["element"] == "uma:Office365ApplicationScope"
    _reset_cache_for_tests()
