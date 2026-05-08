from pathlib import Path
import pytest
from scripts.rule_engine.detectors import detect_python, REGISTRY
from scripts.rule_engine._types import Rule, Severity, Finding
from scripts.rule_engine.context import FileContext


def make_rule(detect_params, **kwargs):
    defaults = {
        "id": "A-VAR", "severity": Severity.INFO, "category": "architectural",
        "target": "all", "title": "t", "description": "",
    }
    defaults.update(kwargs)
    defaults["detect"] = detect_params
    return Rule(**defaults)


# ---- Task 26: python ----

def test_python_calls_registered_function(tmp_path):
    f = tmp_path / "Foo.xaml"
    f.write_text("<Activity><BulkAddQueueItems/></Activity>")
    fc = FileContext(f)
    rule = make_rule({
        "type": "python",
        "params": {
            "module": "scripts.rule_engine.heuristics.refrwk_variant",
            "function": "is_dispatcher",
            "markers": ["BulkAddQueueItems"],
        }
    })
    findings = detect_python(rule, fc, None)
    assert len(findings) == 1
    assert findings[0].rule_id == "A-VAR"
    assert findings[0].line == 1


def test_python_module_not_found_returns_internal_finding(tmp_path):
    f = tmp_path / "Foo.xaml"
    f.write_text("<Activity/>")
    fc = FileContext(f)
    rule = make_rule({
        "type": "python",
        "params": {
            "module": "non.existent.module",
            "function": "anything"
        }
    })
    findings = detect_python(rule, fc, None)
    assert len(findings) == 1
    assert "[INTERNAL]" in findings[0].message


def test_registry_has_python():
    assert "python" in REGISTRY
