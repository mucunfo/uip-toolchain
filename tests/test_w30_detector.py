from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext
from uip_engine.heuristics.windows import (
    detect_w30_hostile_unicode,
    detect_w34_invoke_arguments_variable_duplicate,
)


def _rule() -> Rule:
    return Rule(
        id="W-30",
        severity=Severity.ERROR,
        category="breaking",
        target="windows",
        title="hostile unicode",
        description="",
        detect={
            "type": "python",
            "params": {
                "module": "uip_engine.heuristics.windows",
                "function": "detect_w30_hostile_unicode",
            },
        },
        fix={
            "apply_class": "deterministic",
            "mechanical": {"type": "replace_hostile_unicode_chars"},
        },
    )


def _w34_rule() -> Rule:
    return Rule(
        id="W-34",
        severity=Severity.ERROR,
        category="breaking",
        target="windows",
        title="duplicate invoke arguments",
        description="",
        detect={
            "type": "python",
            "params": {
                "module": "uip_engine.heuristics.windows",
                "function": "detect_w34_invoke_arguments_variable_duplicate",
            },
        },
        fix={
            "apply_class": "deterministic",
            "mechanical": {
                "type": "strip_invoke_arguments_variable_when_args_element"
            },
        },
    )


def test_w30_detector_ignores_protected_annotation_and_displayname(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(
        '<Activity sap2010:Annotation.AnnotationText="texto “ok”" '
        'DisplayName="rotulo “ok”" />',
        encoding="utf-8",
    )

    assert detect_w30_hostile_unicode(_rule(), FileContext(f), None) == []


def test_w30_detector_reports_expression_text_outside_protected_attrs(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(
        '<Activity sap2010:Annotation.AnnotationText="texto “ok”">'
        '<Assign.To>[vStValor.TrimStart(“0”c)]</Assign.To>'
        '</Activity>',
        encoding="utf-8",
    )

    findings = detect_w30_hostile_unicode(_rule(), FileContext(f), None)

    assert len(findings) == 2
    assert all(f.fix_mechanical for f in findings)


def test_w34_detector_reports_null_arguments_variable_with_args_element(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(
        '<Activity><ui:InvokeWorkflowFile ArgumentsVariable="{x:Null}" '
        'WorkflowFileName="Sub.xaml">'
        '<ui:InvokeWorkflowFile.Arguments />'
        '</ui:InvokeWorkflowFile></Activity>',
        encoding="utf-8",
    )

    findings = detect_w34_invoke_arguments_variable_duplicate(
        _w34_rule(), FileContext(f), None
    )

    assert len(findings) == 1
    assert findings[0].fix_mechanical


def test_w34_detector_ignores_non_null_or_missing_args_element(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(
        '<Activity>'
        '<ui:InvokeWorkflowFile ArgumentsVariable="[args]" WorkflowFileName="A.xaml">'
        '<ui:InvokeWorkflowFile.Arguments />'
        '</ui:InvokeWorkflowFile>'
        '<ui:InvokeWorkflowFile ArgumentsVariable="{x:Null}" WorkflowFileName="B.xaml">'
        '</ui:InvokeWorkflowFile>'
        '</Activity>',
        encoding="utf-8",
    )

    assert detect_w34_invoke_arguments_variable_duplicate(
        _w34_rule(), FileContext(f), None
    ) == []
