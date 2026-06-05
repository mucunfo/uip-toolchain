from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext
from uip_engine.heuristics.api import detect_api1_mutating_http_continue_on_error


def _write_xaml(tmp_path: Path, body: str) -> FileContext:
    f = tmp_path / "Main.xaml"
    f.write_text(body, encoding="utf-8")
    return FileContext(f)


def _rule() -> Rule:
    return Rule(
        id="API-1",
        severity=Severity.HALT,
        category="architectural",
        target="windows",
        title="API-1",
        description="",
        detect={"type": "python"},
        fix={"apply_class": "deterministic", "prose": "fix me"},
    )


def test_api1_detects_mutating_http_continue_on_error_order_independent(tmp_path):
    fc = _write_xaml(
        tmp_path,
        '<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<ui:HttpClient ContinueOnError="True" DisplayName="POST x" '
        'Method="POST" Endpoint="u" />'
        '<ui:HttpClient Method="GET" ContinueOnError="True" />'
        '<ui:HttpClient Method="PATCH" Endpoint="u" />'
        '</Activity>',
    )

    findings = detect_api1_mutating_http_continue_on_error(_rule(), fc, None)

    assert len(findings) == 1
    assert findings[0].severity == Severity.HALT
    assert findings[0].fix_mechanical == {
        "type": "force_attribute_in_activity_with_guards",
        "prefix": "ui",
        "activity_local": "HttpClient",
        "guards": {"Method": "POST", "ContinueOnError": "True"},
        "attr_name": "ContinueOnError",
        "target_value": "False",
        "tag_line": 1,
    }


def test_api1_detects_mutating_http_method_case_insensitive(tmp_path):
    fc = _write_xaml(
        tmp_path,
        '<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<ui:HttpClient Method="delete" ContinueOnError="True" />'
        '</Activity>',
    )

    findings = detect_api1_mutating_http_continue_on_error(_rule(), fc, None)

    assert len(findings) == 1
    assert findings[0].fix_mechanical["guards"]["Method"] == "delete"
