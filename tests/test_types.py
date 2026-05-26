import pytest
from uip_engine._types import Finding, Severity, Category, ValidationResult


def test_finding_creates_with_required_fields():
    f = Finding(
        rule_id="A-3",
        severity=Severity.ERROR,
        category=Category.ARCHITECTURAL,
        file="path/to/file.xaml",
        line=42,
        message="SecureString fora de chain",
    )
    assert f.rule_id == "A-3"
    assert f.severity == Severity.ERROR
    assert f.line == 42


def test_finding_optional_fix_default_none():
    f = Finding(
        rule_id="X-1",
        severity=Severity.ERROR,
        category=Category.BREAKING,
        file="f.xaml",
        line=1,
        message="msg",
    )
    assert f.fix_mechanical is None
    assert f.fix_prose is None


def test_validation_result_aggregates_findings():
    r = ValidationResult()
    r.add(Finding("X-1", Severity.ERROR, Category.BREAKING, "f.xaml", 1, "m1"))
    r.add(Finding("S-8", Severity.WARN, Category.ARCHITECTURAL, "f.xaml", 2, "m2"))

    assert len(r.findings) == 2
    assert r.error_count == 1
    assert r.warn_count == 1
    assert r.has_errors is True


def test_severity_enum_ordering():
    assert Severity.HALT > Severity.ERROR
    assert Severity.ERROR > Severity.WARN
    assert Severity.WARN > Severity.INFO


def test_max_severity_returns_highest():
    r = ValidationResult()
    r.add(Finding("X-1", Severity.WARN, Category.BREAKING, "f.xaml", 1, "m"))
    r.add(Finding("X-2", Severity.ERROR, Category.BREAKING, "f.xaml", 2, "m"))
    r.add(Finding("X-3", Severity.INFO, Category.BREAKING, "f.xaml", 3, "m"))
    assert r.max_severity() == Severity.ERROR
