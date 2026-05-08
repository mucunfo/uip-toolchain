from pathlib import Path
import pytest
from scripts.rule_engine.loader import load_rules, SchemaError
from scripts.rule_engine._types import Severity, Category, Target

FIX = Path(__file__).parent / "fixtures"


def test_load_sample_rules_returns_list():
    rules = load_rules(FIX / "rules_sample.yaml")
    assert len(rules) == 2
    ids = {r.id for r in rules}
    assert ids == {"X-1", "A-3"}


def test_load_sets_severity_enum():
    rules = load_rules(FIX / "rules_sample.yaml")
    by_id = {r.id: r for r in rules}
    assert by_id["X-1"].severity == Severity.ERROR
    assert by_id["A-3"].severity == Severity.WARN


def test_load_validates_category():
    rules = load_rules(FIX / "rules_sample.yaml")
    by_id = {r.id: r for r in rules}
    assert by_id["X-1"].category == Category.BREAKING
    assert by_id["A-3"].category == Category.ARCHITECTURAL


def test_load_validates_target():
    rules = load_rules(FIX / "rules_sample.yaml")
    for r in rules:
        assert r.target in Target.VALID


def test_load_rejects_duplicate_ids():
    with pytest.raises(SchemaError, match="duplicate"):
        load_rules(FIX / "rules_invalid.yaml")


def test_load_rejects_invalid_severity(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("""
version: 1
rules:
  - id: X-99
    severity: BOGUS
    category: breaking
    target: all
    title: t
    description: ""
    detect: {type: regex, pattern: "X"}
""")
    with pytest.raises(SchemaError, match="severity"):
        load_rules(bad)


def test_load_rejects_unknown_detector_type(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("""
version: 1
rules:
  - id: X-99
    severity: ERROR
    category: breaking
    target: all
    title: t
    description: ""
    detect: {type: nonexistent_detector}
""")
    with pytest.raises(SchemaError, match="detect.type"):
        load_rules(bad, registered_detectors={"regex", "regex_pair"})


def test_load_compiles_regex_at_load_time(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("""
version: 1
rules:
  - id: X-99
    severity: ERROR
    category: breaking
    target: all
    title: t
    description: ""
    detect: {type: regex, pattern: "[invalid"}
""")
    with pytest.raises(SchemaError, match="regex"):
        load_rules(bad)


def test_load_empty_rules_file(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("version: 1\nrules: []\n")
    rules = load_rules(empty)
    assert rules == []
