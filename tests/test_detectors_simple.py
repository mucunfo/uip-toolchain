from pathlib import Path
import pytest
from scripts.rule_engine.detectors import (
    detect_regex, detect_regex_with_context, detect_regex_pair,
    REGISTRY,
)
from scripts.rule_engine._types import Rule, Severity
from scripts.rule_engine.context import FileContext


def make_rule(detect_params, **kwargs):
    defaults = {
        "id": "X-T", "severity": Severity.ERROR, "category": "breaking",
        "target": "all", "title": "t", "description": "",
    }
    defaults.update(kwargs)
    defaults["detect"] = detect_params
    return Rule(**defaults)


# ---- Task 11: regex ----

def test_regex_detector_finds_match(tmp_path):
    f = tmp_path / "foo.xaml"
    f.write_text("<Activity><Bad/></Activity>")
    fc = FileContext(f)
    rule = make_rule({"type": "regex", "pattern": r"<Bad/>"})
    findings = detect_regex(rule, fc, None)
    assert len(findings) == 1
    assert findings[0].rule_id == "X-T"
    assert findings[0].line == 1


def test_regex_detector_no_match(tmp_path):
    f = tmp_path / "foo.xaml"
    f.write_text("<Activity/>")
    fc = FileContext(f)
    rule = make_rule({"type": "regex", "pattern": r"<NotPresent/>"})
    assert detect_regex(rule, fc, None) == []


def test_regex_detector_multiline_finds_correct_line(tmp_path):
    f = tmp_path / "foo.xaml"
    f.write_text("line1\nline2\n<Bad/>\nline4")
    fc = FileContext(f)
    rule = make_rule({"type": "regex", "pattern": r"<Bad/>"})
    findings = detect_regex(rule, fc, None)
    assert len(findings) == 1
    assert findings[0].line == 3


# ---- Task 13: regex_with_context ----

def test_regex_with_context_skips_safe_prefix(tmp_path):
    f = tmp_path / "foo.xaml"
    f.write_text('value="[CBool(in_Config("X"))]"\nvalue="[in_Config("Y")]"')
    fc = FileContext(f)
    rule = make_rule({
        "type": "regex_with_context",
        "params": {
            "pattern": r'in_Config\("[^"]+"\)',
            "safe_prefix": [r"CBool\s*\(\s*$"],
            "safe_suffix": [],
        },
    })
    findings = detect_regex_with_context(rule, fc, None)
    assert len(findings) == 1


def test_regex_with_context_skips_safe_suffix(tmp_path):
    f = tmp_path / "foo.xaml"
    f.write_text('"[in_Config("X").ToString]"\n"[in_Config("Y")]"')
    fc = FileContext(f)
    rule = make_rule({
        "type": "regex_with_context",
        "params": {
            "pattern": r'in_Config\("[^"]+"\)',
            "safe_prefix": [],
            "safe_suffix": [r"^\.ToString"],
        },
    })
    findings = detect_regex_with_context(rule, fc, None)
    assert len(findings) == 1


# ---- Task 14: regex_pair ----

def test_regex_pair_must_have_only_match(tmp_path):
    f = tmp_path / "foo.xaml"
    f.write_text("<GetRobotCredential/><NClick/>")
    fc = FileContext(f)
    rule = make_rule({
        "type": "regex_pair",
        "params": {"must_have": ["GetRobotCredential", "NClick"], "must_not_have": []},
    })
    findings = detect_regex_pair(rule, fc, None)
    assert len(findings) == 1


def test_regex_pair_must_not_have_blocks(tmp_path):
    f = tmp_path / "foo.xaml"
    f.write_text("<GetRobotCredential/><NClick/><Pick/>")
    fc = FileContext(f)
    rule = make_rule({
        "type": "regex_pair",
        "params": {
            "must_have": ["GetRobotCredential", "NClick"],
            "must_not_have": ["<Pick"],
        },
    })
    findings = detect_regex_pair(rule, fc, None)
    assert findings == []


def test_regex_pair_missing_must_have_no_finding(tmp_path):
    f = tmp_path / "foo.xaml"
    f.write_text("<GetRobotCredential/>")
    fc = FileContext(f)
    rule = make_rule({
        "type": "regex_pair",
        "params": {"must_have": ["GetRobotCredential", "NClick"], "must_not_have": []},
    })
    assert detect_regex_pair(rule, fc, None) == []


# ---- Registry sanity ----

def test_registry_has_simple_detectors():
    for name in ("regex", "regex_with_context", "regex_pair"):
        assert name in REGISTRY, f"detector {name} missing from REGISTRY"
