from pathlib import Path
import pytest
from scripts.rule_engine.detectors import (
    detect_securestring_argument_outside_chain,
    detect_duplicate_id,
    detect_xml_descendant_count,
    detect_structural_order,
    detect_agent_only,
    REGISTRY,
)
from scripts.rule_engine._types import Rule, Severity
from scripts.rule_engine.context import FileContext

FIX = Path(__file__).parent / "fixtures"


def make_rule(rule_id, detect_params, sev=Severity.ERROR):
    return Rule(
        id=rule_id, severity=sev, category="breaking", target="all",
        title=f"{rule_id} title", description="",
        detect=detect_params,
    )


# ---- Task 15: securestring_argument_outside_chain ----

def test_securestring_outside_chain_flags():
    fc = FileContext(FIX / "with_securestring.xaml")
    rule = make_rule("A-3", {
        "type": "securestring_argument_outside_chain",
        "params": {
            "chain_marker_args": ["in_Credenciais", "in_Credentials"],
            "chain_marker_types": ["Tuple", "Dictionary"],
        },
    })
    findings = detect_securestring_argument_outside_chain(rule, fc, None)
    assert len(findings) == 1
    assert "in_SsSenha" in findings[0].message


def test_securestring_inside_chain_no_finding():
    fc = FileContext(FIX / "with_credenciais_tuple.xaml")
    rule = make_rule("A-3", {
        "type": "securestring_argument_outside_chain",
        "params": {
            "chain_marker_args": ["in_Credenciais", "in_Credentials"],
            "chain_marker_types": ["Tuple", "Dictionary"],
        },
    })
    findings = detect_securestring_argument_outside_chain(rule, fc, None)
    assert findings == []


# ---- Task 16: duplicate_id ----

def test_duplicate_id_flags():
    fc = FileContext(FIX / "duplicate_idref.xaml")
    rule = make_rule("X-DUP", {
        "type": "duplicate_id",
        "params": {"attribute": "sap2010:WorkflowViewState.IdRef"},
    })
    findings = detect_duplicate_id(rule, fc, None)
    assert len(findings) >= 1
    assert "Sequence_1" in findings[0].message


# ---- Task 17: xml_descendant_count ----

def test_xml_descendant_count_above_max(tmp_path):
    f = tmp_path / "ui_heavy.xaml"
    nclicks = "".join('<uix:NClick/>' for _ in range(7))
    f.write_text(f"<Activity>{nclicks}</Activity>")
    fc = FileContext(f)
    rule = make_rule("X-UI", {
        "type": "xml_descendant_count",
        "params": {"element": "uix:NClick", "max": 5},
    }, sev=Severity.WARN)
    findings = detect_xml_descendant_count(rule, fc, None)
    assert len(findings) == 1


# ---- Task 18: structural_order ----

def test_structural_order_flags_variables_after_children():
    fc = FileContext(FIX / "bad_variable_order.xaml")
    rule = make_rule("X-VAR", {
        "type": "structural_order",
        "params": {
            "parent_open": r"<Sequence[\s>]",
            "must_be_first_child": "Sequence.Variables",
        },
    })
    findings = detect_structural_order(rule, fc, None)
    assert len(findings) >= 1


# ---- Task 20: agent_only ----

def test_agent_only_returns_empty(tmp_path):
    f = tmp_path / "any.xaml"
    f.write_text("<Activity/>")
    fc = FileContext(f)
    rule = make_rule("I-1", {"type": "agent_only"}, sev=Severity.HALT)
    assert detect_agent_only(rule, fc, None) == []


# ---- Registry sanity ----

def test_registry_has_all_xml_detectors():
    for name in ("securestring_argument_outside_chain", "duplicate_id",
                 "xml_descendant_count", "structural_order", "agent_only"):
        assert name in REGISTRY, f"detector {name} missing"
