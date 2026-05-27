from pathlib import Path
import pytest
from uip_engine.detectors import detect_python, REGISTRY
from uip_engine._types import Rule, Severity, Finding
from uip_engine.context import FileContext


def make_rule(detect_params, **kwargs):
    defaults = {
        "id": "A-VAR", "severity": Severity.INFO, "category": "architectural",
        "target": "all", "title": "t", "description": "",
    }
    defaults.update(kwargs)
    defaults["detect"] = detect_params
    return Rule(**defaults)


# ---- Task 26: python ----

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
