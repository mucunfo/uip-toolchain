"""Regression tests for audit finding X-2 (migrator_regress detector tighten).

X-2: the X-2 detector `_PROPELEM_ATTR_RE` previously flagged ANY property
element (`prefix:Type.Prop`) carrying ANY attribute, including legit generic
property elements that only carry XAML directive attributes such as
`x:TypeArguments`, `x:Key`, `xml:space`. Stripping those breaks valid XAML.

The tightened detector flags ONLY the actual Migrator regression signature:
a property element whose attribute NAME equals the property local-name, e.g.
`<ui:LogMessage.Level Level="Trace">` (attr == prop).

These tests exercise BOTH the raw `_PROPELEM_ATTR_RE` pattern (pure-regex,
no engine state) AND the public `detect_x2_property_element_with_attribute`
entry point with a minimal stand-in rule/file-context.
"""
from __future__ import annotations

import re

import pytest

from uip_engine.heuristics import migrator_regress as mr


# --------------------------------------------------------------------------
# Lightweight stand-ins so we exercise the real detector without booting the
# whole engine. The detector only touches fc.active_content / fc.path and
# rule.id/severity/category/title/fix.
# --------------------------------------------------------------------------
class _Rule:
    id = "X-2"
    severity = "ERROR"
    category = "breaking"
    title = "Property element com attribute"
    fix = {"mechanical": {"type": "fix_property_element_hybrid"}, "prose": "strip"}


class _FC:
    def __init__(self, content: str):
        self.active_content = content
        self.path = "Dummy.xaml"


def _detect(content: str):
    return mr.detect_x2_property_element_with_attribute(_Rule(), _FC(content), None)


# --------------------------------------------------------------------------
# Cases: (xaml_fragment, should_be_flagged)
# --------------------------------------------------------------------------
REGRESSION_CASES = [
    # Intended Migrator regression: attr NAME == prop local-name.
    ('<ui:LogMessage.Level Level="Trace"><Literal Value="x"/></ui:LogMessage.Level>', True),
    # attr==prop with extra directive present alongside -> still flagged.
    ('<ui:LogMessage.Level Level="Trace" x:Key="k">c</ui:LogMessage.Level>', True),
    ('<scg:List.Items x:TypeArguments="x:String" Items="v">c</scg:List.Items>', True),
]

VALID_CASES = [
    # Generic property element with x:TypeArguments directive ONLY -> NOT flagged.
    ('<scg:List.Items x:TypeArguments="x:String"><x:String>a</x:String></scg:List.Items>', False),
    # x:Key directive only.
    ('<ui:LogMessage.Level x:Key="k">c</ui:LogMessage.Level>', False),
    # xml:space directive only.
    ('<ui:LogMessage.Level xml:space="preserve">c</ui:LogMessage.Level>', False),
    # No attribute at all.
    ('<ui:LogMessage.Level><Literal Value="x"/></ui:LogMessage.Level>', False),
    # Attribute present but name differs from prop local-name.
    ('<ui:LogMessage.Level Other="v">c</ui:LogMessage.Level>', False),
]


@pytest.mark.parametrize("frag,flagged", REGRESSION_CASES)
def test_regex_flags_real_migrator_regression(frag, flagged):
    assert bool(mr._PROPELEM_ATTR_RE.search(frag)) is flagged


@pytest.mark.parametrize("frag,flagged", VALID_CASES)
def test_regex_does_not_flag_valid_property_elements(frag, flagged):
    assert bool(mr._PROPELEM_ATTR_RE.search(frag)) is flagged


@pytest.mark.parametrize("frag,flagged", REGRESSION_CASES + VALID_CASES)
def test_detector_entrypoint_matches_regex(frag, flagged):
    findings = _detect(frag)
    assert bool(findings) is flagged


def test_directive_only_generic_element_no_longer_stripped():
    """The exact over-match case cited in the audit: a generic property
    element carrying only x:TypeArguments must produce zero findings."""
    frag = (
        '<scg:List.Items x:TypeArguments="x:String">'
        '<x:String>a</x:String>'
        '</scg:List.Items>'
    )
    assert _detect(frag) == []


def test_intended_regression_still_detected():
    """The genuine Migrator regression must keep producing a finding."""
    frag = (
        '<ui:LogMessage.Level Level="Trace">'
        '<Literal Value="Trace"/>'
        '</ui:LogMessage.Level>'
    )
    findings = _detect(frag)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "X-2"
    assert "LogMessage.Level" in f.message


def test_backreference_group_is_property_local_name():
    """Sanity: the matched attribute name equals the property local-name."""
    frag = '<ui:LogMessage.Level Level="Trace">c</ui:LogMessage.Level>'
    m = mr._PROPELEM_ATTR_RE.search(frag)
    assert m is not None
    assert m.group("prop") == "Level"
    assert m.group("elem") == "ui:LogMessage.Level"


def test_pattern_compiles_standalone():
    """The tightened pattern is a valid regex with the backreference."""
    # Re-derive the source to confirm it round-trips through re.compile.
    assert re.compile(mr._PROPELEM_ATTR_RE.pattern) is not None
