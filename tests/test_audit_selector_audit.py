"""Regression tests for AUDIT_2026-05-28 selector_audit findings.

Covers two S-SEMANTIC_LEAK defects:
  1. (inconsistency) detect_semantic_leak default category was "security",
     which is NOT a member of Category.ALL. It must default to "breaking"
     to match the YAML rule + sibling detect_healchain.
  2. (bug) SearchSteps expressed as a non-text property element (e.g. an
     <x:Static .../> markup reference) yielded child.text='' -> value_int=0,
     so the cloud-leak check silently passed. The detector now scans the
     element's serialized inner XML for the Semantic/SemanticSelector enum
     names so the compliance rule is not silently under-matched.
"""
from __future__ import annotations

from pathlib import Path

from uip_engine._types import Category
from uip_engine.heuristics.selector_audit import (
    detect_semantic_leak,
    _scan_serialized_search_steps,
    _iter_target_anchorables,
)

import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Finding: default category must be a valid Category (was invalid "security").
# ---------------------------------------------------------------------------

def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


_SEMANTIC_TEXT_XAML = """<Activity xmlns:uix="http://schemas.uipath.com/workflow/activities/uix">
  <uix:TargetAnchorable SearchSteps="Selector | SemanticSelector" />
</Activity>
"""


def test_semantic_leak_default_category_is_valid(tmp_path: Path) -> None:
    """Standalone calling convention (rule is None) must NOT emit the invalid
    'security' category. It must be a schema-valid Category member."""
    xaml = _write(tmp_path, "semantic_text.xaml", _SEMANTIC_TEXT_XAML)
    findings = detect_semantic_leak(xaml)
    assert findings, "expected a S-SEMANTIC_LEAK finding for text-form SemanticSelector"
    for f in findings:
        assert f.category == Category.BREAKING
        assert f.category in Category.ALL
        assert f.category != "security"


# ---------------------------------------------------------------------------
# Finding: property-element (non-text markup) SearchSteps must not silently
# under-match. The serialized inner XML is scanned for the enum names.
# ---------------------------------------------------------------------------

_SEMANTIC_STATIC_XAML = """<Activity xmlns:uix="http://schemas.uipath.com/workflow/activities/uix" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <uix:TargetAnchorable>
    <uix:TargetAnchorable.SearchSteps>
      <x:Static Member="uix:TargetSearchStep.SemanticSelector" />
    </uix:TargetAnchorable.SearchSteps>
  </uix:TargetAnchorable>
</Activity>
"""

_SELECTOR_STATIC_XAML = """<Activity xmlns:uix="http://schemas.uipath.com/workflow/activities/uix" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <uix:TargetAnchorable>
    <uix:TargetAnchorable.SearchSteps>
      <x:Static Member="uix:TargetSearchStep.Selector" />
    </uix:TargetAnchorable.SearchSteps>
  </uix:TargetAnchorable>
</Activity>
"""


def test_semantic_leak_static_member_form_is_detected(tmp_path: Path) -> None:
    """A SemanticSelector expressed as <x:Static> markup (no literal text)
    must still trip the cloud-leak check rather than passing silently."""
    xaml = _write(tmp_path, "semantic_static.xaml", _SEMANTIC_STATIC_XAML)
    findings = detect_semantic_leak(xaml)
    assert findings, (
        "non-text SearchSteps (x:Static SemanticSelector) must NOT silently "
        "under-match the breaking cloud-leak rule"
    )
    assert any("SemanticSelector" in f.message for f in findings)


def test_selector_only_static_member_is_clean(tmp_path: Path) -> None:
    """A benign Selector-only static reference must NOT trip the leak check
    (no false positive from the serialized scan)."""
    xaml = _write(tmp_path, "selector_static.xaml", _SELECTOR_STATIC_XAML)
    findings = detect_semantic_leak(xaml)
    assert findings == [], "Selector-only static SearchSteps must not be flagged"


def test_scan_serialized_search_steps_helper() -> None:
    """Unit-level check of the recovery helper on bad/good inner markup."""
    SS_SEMANTIC = 0x80
    SS_SEMANTIC_SELECTOR = 0x100
    leak_mask = SS_SEMANTIC | SS_SEMANTIC_SELECTOR

    bad = ET.fromstring(
        '<SearchSteps xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        '<x:Static Member="X.SemanticSelector" /></SearchSteps>'
    )
    assert _scan_serialized_search_steps(bad) & leak_mask

    semantic = ET.fromstring(
        '<SearchSteps xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        '<x:Static Member="X.Semantic" /></SearchSteps>'
    )
    assert _scan_serialized_search_steps(semantic) & leak_mask

    good = ET.fromstring(
        '<SearchSteps xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        '<x:Static Member="X.Selector" /></SearchSteps>'
    )
    assert _scan_serialized_search_steps(good) & leak_mask == 0


def test_iter_target_anchorables_recovers_static_form(tmp_path: Path) -> None:
    """The iterator now yields a non-zero value_int for the static-markup form
    (previously yielded 0 due to empty child.text)."""
    xaml = _write(tmp_path, "iter_static.xaml", _SEMANTIC_STATIC_XAML)
    rows = list(_iter_target_anchorables(xaml))
    assert rows, "expected one TargetAnchorable row"
    assert any(value_int != 0 for _line, _raw, value_int in rows)
