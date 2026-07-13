"""Tests for D-PINALERT — XAML APIs exclusivas de versão > pin."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.fixers import REGISTRY
from uip_engine.heuristics.pin_alert import (
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
    """System pinado [25.4.4] + XAML usa RetryScope.LogRetriedExceptions
    (introduzido em 25.8.1, pacote UiPath.System.Activities — catálogo
    corrigido 2026-07-03) -> 1 finding ERROR."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.System.Activities": "[25.4.4]"},
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
    assert "25.8.1" in findings[0].message
    assert "25.4.4" in findings[0].message
    assert findings[0].fix_prose  # tem prose explicando fix


def test_pin_alert_dotted_attribute_mechanical_fix_applies(tmp_path):
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.System.Activities": "[25.4.4]"},
    )
    fc = _write_xaml(
        proj,
        '  <ui:RetryScope RetryScope.LogRetriedExceptions="True" DisplayName="Tentar"/>',
    )

    findings = detect_pin_alert(_mk_rule(), fc, pc)
    mech = findings[0].fix_mechanical
    assert mech["type"] == "strip_xml_attribute"
    assert mech["attribute"] == "LogRetriedExceptions"

    ok = REGISTRY[mech["type"]](Path(fc.path), mech, dry_run=False, project_root=proj)
    out = Path(fc.path).read_text(encoding="utf-8")

    assert ok is True
    assert "RetryScope.LogRetriedExceptions=" not in out
    assert 'DisplayName="Tentar"' in out


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
    proj, pc = _mk_project(tmp_path, {"UiPath.Excel.Activities": "[3.1.2]"})
    body = '  <uix:NWindowOperation DisplayName="Janela"/>\n'
    fc = _write_xaml(proj, body)
    assert detect_pin_alert(_mk_rule(), fc, pc) == []


def test_pin_alert_uses_canonical_pin_when_package_assembly_is_in_xaml(tmp_path):
    """Some migrated XAMLs reference a pinned package assembly without deps."""
    proj, pc = _mk_project(tmp_path, {"UiPath.System.Activities": "[25.4.4]"})
    body = (
        '  <AssemblyReference>UiPath.OCR.Activities</AssemblyReference>\n'
        '  <p1:UiPathScreenOCR UseSeparateOcrProcess="True" />\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert "UiPathScreenOCR" in findings[0].message
    assert "UseSeparateOcrProcess" in findings[0].message
    assert findings[0].fix_mechanical == {
        "type": "strip_xml_attribute",
        "attribute": "UseSeparateOcrProcess",
    }


def test_pin_alert_flags_copyfile_destinationresource(tmp_path):
    """CopyFile.DestinationResource é outro pattern listado (System,
    introduzido 23.10.6 — pin abaixo disso dispara)."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.System.Activities": "[23.10.2]"},
    )
    body = (
        '  <ui:CopyFile CopyFile.DestinationResource="x" DisplayName="cp"/>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert "CopyFile" in findings[0].message
    assert "DestinationResource" in findings[0].message


def test_pin_alert_flags_movefile_resource_attrs(tmp_path):
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.System.Activities": "[23.10.2]"},
    )
    body = (
        '  <ui:MoveFile DestinationResource="{x:Null}" '
        'PathResource="{x:Null}" DisplayName="mv"/>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    attrs = {
        f.fix_mechanical["attribute"]: f.fix_mechanical
        for f in findings
        if f.fix_mechanical
    }
    assert attrs["DestinationResource"]["element"] == "ui:MoveFile"
    assert attrs["PathResource"]["element"] == "ui:MoveFile"


def test_pin_alert_flags_ntake_screenshot_with_rewrite_mech(tmp_path):
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    body = '  <uix:NTakeScreenshot OutImage="[Screenshot]" Version="V5" />\n'
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert "NTakeScreenshot" in findings[0].message
    assert findings[0].fix_mechanical == {
        "type": "rewrite_ntake_screenshot_to_classic",
    }


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


def test_pin_alert_flags_targetanchorable_elementvisibilityargument(tmp_path):
    """TargetAnchorable.ElementVisibilityArgument is newer than the UIA pin."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    body = '  <uix:TargetAnchorable ElementVisibilityArgument="Interactive"/>\n'
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert "TargetAnchorable" in findings[0].message
    assert "ElementVisibilityArgument" in findings[0].message
    assert findings[0].fix_mechanical == {
        "type": "strip_xml_attribute",
        "attribute": "ElementVisibilityArgument",
        "element": "uix:TargetAnchorable",
    }


@pytest.mark.parametrize(
    ("body", "attr", "element"),
    [
        ('  <uix:TargetAnchorable ImageAccuracyArgument="0.99"/>\n',
         "ImageAccuracyArgument", "uix:TargetAnchorable"),
        ('  <uix:Target ImageAccuracyArgument="0.85"/>\n',
         "ImageAccuracyArgument", "uix:Target"),
    ],
)
def test_pin_alert_flags_uia_imageaccuracyargument(tmp_path, body, attr, element):
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.UIAutomation.Activities": "[25.10.8]"},
    )
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert attr in findings[0].message
    assert findings[0].fix_mechanical == {
        "type": "strip_xml_attribute",
        "attribute": attr,
        "element": element,
    }


def test_pin_alert_flags_sendmail_connectionmode(tmp_path):
    """SendMail.ConnectionMode is newer than the Mail pin."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.Mail.Activities": "[1.24.2]"},
    )
    body = '  <ui:SendMail ConnectionMode="Undefined"/>\n'
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert "SendMail" in findings[0].message
    assert "ConnectionMode" in findings[0].message
    assert findings[0].fix_mechanical == {
        "type": "strip_xml_attribute",
        "attribute": "ConnectionMode",
        "element": "ui:SendMail",
    }


def test_pin_alert_does_not_flag_office365_scope_folder_on_current_pins(tmp_path):
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.MicrosoftOffice365.Activities": "[3.2.11]"},
    )
    body = '  <uma:Office365ApplicationScope Folder="{x:Null}"/>\n'
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert findings == []


def test_pin_alert_does_not_flag_office365_scope_datastorelocation_on_current_pins(tmp_path):
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.MicrosoftOffice365.Activities": "[3.2.11]"},
    )
    body = '  <uma:Office365ApplicationScope DataStoreLocation="DISK"/>\n'
    fc = _write_xaml(proj, body)
    findings = detect_pin_alert(_mk_rule(), fc, pc)
    assert findings == []


def test_pin_alert_multiple_matches_same_xaml(tmp_path):
    """Múltiplas violations no mesmo XAML -> múltiplos findings."""
    proj, pc = _mk_project(
        tmp_path,
        {"UiPath.System.Activities": "[23.10.2]"},
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
        {"UiPath.System.Activities": "[25.4.4]"},
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
    from uip_engine.loader import load_rules
    from uip_engine import detectors, fixers

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
