"""Tests for S-HEALCHAIN + S-SEMANTIC-LEAK detectors (selector_audit)."""
from __future__ import annotations

from pathlib import Path

import pytest

from uip_engine.heuristics.selector_audit import (
    detect_healchain, detect_semantic_leak,
    _parse_search_steps_value,
    HEALCHAIN_MASK, SEMANTIC_LEAK_MASK,
    SS_SELECTOR, SS_FUZZY_SELECTOR, SS_IMAGE, SS_TEXT_OCR, SS_TEXT_NATIVE,
    SS_CV, SS_SEMANTIC, SS_SEMANTIC_SELECTOR,
)


# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------

def test_parse_decimal():
    assert _parse_search_steps_value("4") == 4


def test_parse_hex_lowercase():
    assert _parse_search_steps_value("0x10") == 0x10


def test_parse_hex_uppercase():
    assert _parse_search_steps_value("0X80") == 0x80


def test_parse_pipe_separated():
    assert _parse_search_steps_value("Selector | FuzzySelector | Image") == 1 | 2 | 4


def test_parse_pipe_separated_no_spaces():
    assert _parse_search_steps_value("Selector|FuzzySelector|Image") == 7


def test_parse_case_insensitive_enum():
    assert _parse_search_steps_value("SELECTOR | image") == SS_SELECTOR | SS_IMAGE


def test_parse_unknown_token_ignored():
    """Unknown enum names are best-effort skipped (not raised)."""
    assert _parse_search_steps_value("Selector | BogusValue | Image") == SS_SELECTOR | SS_IMAGE


def test_parse_empty_and_none():
    assert _parse_search_steps_value("") == 0
    assert _parse_search_steps_value(None) == 0
    assert _parse_search_steps_value("   ") == 0


# ---------------------------------------------------------------------------
# Mask sanity
# ---------------------------------------------------------------------------

def test_healchain_mask_hits():
    """Healchain mask captures Image, TextOcr, TextNative, CV."""
    assert (SS_IMAGE & HEALCHAIN_MASK) != 0
    assert (SS_TEXT_OCR & HEALCHAIN_MASK) != 0
    assert (SS_TEXT_NATIVE & HEALCHAIN_MASK) != 0
    assert (SS_CV & HEALCHAIN_MASK) != 0


def test_healchain_mask_safe_steps():
    """Selector + FuzzySelector are safe — not hit by HEALCHAIN_MASK."""
    assert ((SS_SELECTOR | SS_FUZZY_SELECTOR) & HEALCHAIN_MASK) == 0


def test_semantic_leak_mask_hits():
    assert (SS_SEMANTIC & SEMANTIC_LEAK_MASK) != 0
    assert (SS_SEMANTIC_SELECTOR & SEMANTIC_LEAK_MASK) != 0


def test_semantic_leak_mask_safe_steps():
    assert ((SS_SELECTOR | SS_FUZZY_SELECTOR | SS_IMAGE) & SEMANTIC_LEAK_MASK) == 0


# ---------------------------------------------------------------------------
# XAML fixtures
# ---------------------------------------------------------------------------

def _write_xaml(tmp_path: Path, body: str, name: str = "Main.xaml") -> Path:
    """Wrap `body` (one TargetAnchorable) in a valid XAML root with UiPath xmlns."""
    xaml = tmp_path / name
    xaml.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:ui="http://schemas.uipath.com/workflow/activities"\n'
        '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        f"  {body}\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    return xaml


def test_detect_healchain_pipe_enum(tmp_path):
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable SearchSteps="Selector | FuzzySelector | Image" />')
    findings = list(detect_healchain(xaml))
    assert len(findings) == 1
    assert findings[0].rule_id == "S-HEALCHAIN"
    assert "Image" in findings[0].message


def test_detect_healchain_hex_value(tmp_path):
    """SearchSteps as hex int (TextOcr=0x10)."""
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable SearchSteps="0x10" />')
    findings = list(detect_healchain(xaml))
    assert len(findings) == 1
    assert "TextOcr" in findings[0].message


def test_detect_healchain_multiple_targets(tmp_path):
    """Two TargetAnchorables in one XAML — both flagged independently."""
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable SearchSteps="Selector | Image" />\n'
        '  <ui:TargetAnchorable SearchSteps="Selector | CV" />')
    findings = list(detect_healchain(xaml))
    assert len(findings) == 2


def test_detect_semantic_leak_semantic_flag(tmp_path):
    """Semantic = 0x80."""
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable SearchSteps="0x80" />')
    findings = list(detect_semantic_leak(xaml))
    assert len(findings) == 1
    assert findings[0].rule_id == "S-SEMANTIC_LEAK"
    assert "Semantic" in findings[0].message


def test_detect_semantic_leak_semantic_selector(tmp_path):
    """SemanticSelector = 0x100."""
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable SearchSteps="Selector | SemanticSelector" />')
    findings = list(detect_semantic_leak(xaml))
    assert len(findings) == 1
    assert "SemanticSelector" in findings[0].message


def test_detect_clean(tmp_path):
    """SearchSteps=Selector|FuzzySelector only -> no findings."""
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable SearchSteps="Selector | FuzzySelector" />')
    assert detect_healchain(xaml) == []
    assert detect_semantic_leak(xaml) == []


def test_detect_search_steps_absent(tmp_path):
    """No SearchSteps attribute -> assume default, no findings."""
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable Element="[someVar]" />')
    assert detect_healchain(xaml) == []
    assert detect_semantic_leak(xaml) == []


def test_detect_no_target_anchorable_at_all(tmp_path):
    """XAML without TargetAnchorable elements -> no findings."""
    xaml = _write_xaml(tmp_path, '<ui:LogMessage Message="hi" />')
    assert detect_healchain(xaml) == []
    assert detect_semantic_leak(xaml) == []


def test_malformed_xaml_returns_empty(tmp_path):
    """Broken XML -> no exception, no findings (be conservative)."""
    xaml = tmp_path / "Broken.xaml"
    xaml.write_text("<Activity><ui:TargetAnchorable SearchSteps=", encoding="utf-8")
    assert detect_healchain(xaml) == []
    assert detect_semantic_leak(xaml) == []


def test_healchain_and_semantic_in_same_xaml(tmp_path):
    """Same TargetAnchorable with both brittle steps + semantic -> BOTH rules fire."""
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable SearchSteps="Image | Semantic" />')
    healchain = list(detect_healchain(xaml))
    semantic = list(detect_semantic_leak(xaml))
    assert len(healchain) == 1
    assert len(semantic) == 1


def test_line_number_reported(tmp_path):
    """Line numbers should be 1-indexed and reflect the source position."""
    xaml = tmp_path / "Main.xaml"
    xaml.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'  # line 1
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'  # 2
        '          xmlns:ui="http://schemas.uipath.com/workflow/activities">\n'  # 3
        '  <ui:LogMessage Message="hi" />\n'  # 4
        '  <ui:LogMessage Message="hi2" />\n'  # 5
        '  <ui:TargetAnchorable SearchSteps="Image" />\n'  # 6 -- target
        '</Activity>\n',
        encoding="utf-8",
    )
    findings = list(detect_healchain(xaml))
    assert len(findings) == 1
    assert findings[0].line == 6


# ---------------------------------------------------------------------------
# Engine calling convention compatibility
# ---------------------------------------------------------------------------

def test_modern_ui_uix_namespace(tmp_path):
    """Real Sicoob XAMLs use the `uix` Modern UI namespace
    (http://schemas.uipath.com/workflow/activities/uix). Detector must match."""
    xaml = tmp_path / "Main.xaml"
    xaml.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:uix="http://schemas.uipath.com/workflow/activities/uix">\n'
        '  <uix:TargetAnchorable SearchSteps="Selector | Image" />\n'
        '</Activity>\n',
        encoding="utf-8",
    )
    findings = list(detect_healchain(xaml))
    assert len(findings) == 1
    assert "Image" in findings[0].message


def test_modern_ui_uix_clean_selector_only(tmp_path):
    """`uix:TargetAnchorable SearchSteps="Selector"` (most common Modern UI
    real-world value) -> no findings."""
    xaml = tmp_path / "Main.xaml"
    xaml.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:uix="http://schemas.uipath.com/workflow/activities/uix">\n'
        '  <uix:TargetAnchorable SearchSteps="Selector" />\n'
        '</Activity>\n',
        encoding="utf-8",
    )
    assert detect_healchain(xaml) == []
    assert detect_semantic_leak(xaml) == []


def test_engine_calling_convention(tmp_path):
    """Engine calls detect(rule, fc, pc). Path goes through fc.path attribute."""
    from uip_engine._types import Rule, Severity
    from uip_engine.context import FileContext

    rule = Rule(
        id="S-HEALCHAIN",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="t",
        description="d",
        detect={"type": "python"},
        fix={"apply_class": "contextual", "prose": "FIX_PROSE_TEXT"},
    )
    xaml = _write_xaml(tmp_path,
        '<ui:TargetAnchorable SearchSteps="Image" />')
    fc = FileContext(xaml)
    findings = detect_healchain(rule, fc, None)
    assert len(findings) == 1
    assert findings[0].fix_prose == "FIX_PROSE_TEXT"
    assert findings[0].rule_id == "S-HEALCHAIN"
