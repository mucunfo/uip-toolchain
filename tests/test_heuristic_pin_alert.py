"""Tests for D-PINALERT — XAML APIs exclusivas de versão > pin."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.rule_engine._types import Rule, Severity
from scripts.rule_engine.context import FileContext, ProjectContext
from scripts.rule_engine.heuristics.pin_alert import (
    detect_pin_alert,
    _reset_cache_for_tests,
)


def _mk_rule():
    return Rule(
        id="D-PINALERT",
        severity=Severity.ERROR,
        category="breaking",
        target="windows",
        title="API exclusiva de versão > pin detectada em XAML",
        description="",
        detect={"type": "python"},
    )


def _mk_project(tmp_path: Path, deps: dict) -> tuple[Path, ProjectContext]:
    proj = tmp_path / "P"
    proj.mkdir(exist_ok=True)
    pj = proj / "project.json"
    pj.write_text(
        json.dumps({"targetFramework": "Windows", "dependencies": deps}),
        encoding="utf-8",
    )
    return proj, ProjectContext(root=proj, project_json=json.loads(pj.read_text(encoding="utf-8")))


def _write_xaml(proj: Path, body: str, name: str = "Foo.xaml") -> FileContext:
    f = proj / name
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:uix="uix" xmlns:x="x">\n'
        f"{body}\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    return FileContext(f)


@pytest.fixture(autouse=True)
def _clear_cache():
    _reset_cache_for_tests()
    yield
    _reset_cache_for_tests()


def test_pin_alert_flags_when_pin_below_introduced(tmp_path):
    """UIA pinado [25.10.8] + XAML usa RetryScope.LogRetriedExceptions
    (introduzido em 25.10.21) -> 1 finding ERROR."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    body = (
        '  <ui:RetryScope RetryScope.LogRetriedExceptions="True" '
        'DisplayName="Tentar"/>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert findings[0].rule_id == "D-PINALERT"
    assert findings[0].severity == Severity.ERROR
    # Pattern aparece com regex escape (`\.`); checar fragmentos significativos.
    assert "RetryScope" in findings[0].message
    assert "LogRetriedExceptions" in findings[0].message
    assert "25.10.21" in findings[0].message
    assert "25.10.8" in findings[0].message
    assert findings[0].fix_prose  # tem prose explicando fix


def test_pin_alert_silent_when_pin_covers_api(tmp_path):
    """UIA pinado [25.10.21] (>= introduced_in) -> 0 findings (pin cobre)."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.21]"},
    )
    body = (
        '  <ui:RetryScope RetryScope.LogRetriedExceptions="True" '
        'DisplayName="Tentar"/>\n'
    )
    fc = _write_xaml(proj, body)
    assert detect_pin_alert(_mk_rule(), fc, pc) == []


def test_pin_alert_silent_when_xaml_clean(tmp_path):
    """XAML sem padrão -> 0 findings mesmo com pin baixa."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    body = '  <ui:Sequence DisplayName="OK"/>\n'
    fc = _write_xaml(proj, body)
    assert detect_pin_alert(_mk_rule(), fc, pc) == []


def test_pin_alert_silent_when_package_not_in_deps(tmp_path):
    """Pacote não declarado em deps -> 0 findings (não aplicável)."""
    proj, pc = _mk_project(tmp_path, {"UiPath.System.Activities": "[25.4.4]"})
    body = (
        '  <ui:RetryScope RetryScope.LogRetriedExceptions="True"/>\n'
    )
    fc = _write_xaml(proj, body)
    assert detect_pin_alert(_mk_rule(), fc, pc) == []


def test_pin_alert_flags_copyfile_destinationresource(tmp_path):
    """CopyFile.DestinationResource é outro pattern listado."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    body = (
        '  <ui:CopyFile CopyFile.DestinationResource="x" DisplayName="cp"/>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert "CopyFile" in findings[0].message
    assert "DestinationResource" in findings[0].message


def test_pin_alert_flags_nwindowoperation_element(tmp_path):
    """Activity exclusiva como elemento (xaml_element)."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    body = '  <uix:NWindowOperation DisplayName="Janela"/>\n'
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert "NWindowOperation" in findings[0].message
    assert "NApplicationCard" in findings[0].fix_prose  # fix sugere replace


def test_pin_alert_multiple_matches_same_xaml(tmp_path):
    """Múltiplas violations no mesmo XAML -> múltiplos findings."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    body = (
        '  <ui:RetryScope RetryScope.LogRetriedExceptions="True"/>\n'
        '  <ui:CopyFile CopyFile.DestinationResource="x"/>\n'
        '  <ui:CopyFile CopyFile.PathResource="y"/>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 3
    # Cada finding inclui o pattern (com regex escape) no message.
    all_msgs = " ".join(f.message for f in findings)
    assert "LogRetriedExceptions" in all_msgs
    assert "DestinationResource" in all_msgs
    assert "PathResource" in all_msgs


def test_pin_alert_skips_non_xaml(tmp_path):
    """Files com suffix != .xaml -> 0 findings (heuristic guard)."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    txt = proj / "notes.txt"
    txt.write_text("RetryScope.LogRetriedExceptions everywhere", encoding="utf-8")
    fc = FileContext(txt)
    assert detect_pin_alert(_mk_rule(), fc, pc) == []


def test_pin_alert_line_number_reported(tmp_path):
    """Finding aponta para linha correta do match no XAML."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    body = (
        '  <ui:Sequence DisplayName="Top"/>\n'
        '  <ui:RetryScope RetryScope.LogRetriedExceptions="True"/>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    # XAML head é linha 1-2, body começa linha 3.
    # Sequence está em linha 3, RetryScope em linha 4.
    assert findings[0].line == 4


def test_pin_alert_loader_validates_apply_class(tmp_path):
    """Regra D-PINALERT em rules.yaml deve declarar apply_class
    (loader rejeita python detector com fix dinâmico sem apply_class).
    Aqui validamos que a rule yaml carrega sem erro."""
    from scripts.rule_engine.loader import load_rules
    from scripts.rule_engine import detectors, fixers

    rules_path = Path(__file__).resolve().parents[1] / "rules.yaml"
    rules = load_rules(
        rules_path,
        registered_detectors=set(detectors.REGISTRY.keys()),
        registered_fixers=set(fixers.REGISTRY.keys()),
    )
    pin_alert = next((r for r in rules if r.id == "D-PINALERT"), None)
    assert pin_alert is not None
    assert pin_alert.severity == Severity.ERROR
    # D-PINALERT é mixed: attribute strips (strip_xml_attribute) → deterministic
    # per-finding, element replaces (NWindowOperation) → contextual per-finding.
    # YAML declara `deterministic` (default) e check_perfect.py refina per
    # finding. Loader requer apply_class declarado quando fix_mechanical
    # é dinâmico — `deterministic` ou `contextual` ambos válidos.
    assert pin_alert.fix and pin_alert.fix.get("apply_class") in {"deterministic", "contextual"}
