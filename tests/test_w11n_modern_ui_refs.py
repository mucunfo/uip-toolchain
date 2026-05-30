"""Tests for W-11n: modern UIAutomation (uix:) requires UIAutomationNext refs.

XAML que usa atividades modern (prefixo `uix:` — NApplicationCard/NClick/
NTypeInto/etc) precisa dos AssemblyReference do stack UIAutomationNext no bloco
ReferencesForImplementation. O xmlns uix é schema-URI (não clr-namespace;
assembly=), então W-11x não pega e a baseline W-11y não lista os refs Next.

Cobre:
  - uix usado + refs faltando → finding por ref ausente, fix insert_assembly_reference
  - uix usado + refs presentes → no-op
  - XAML SEM uix → no-op (condicional)
  - XAML sem bloco refs → no-op (não dá pra inserir)
  - non-xaml → no-op
  - required_refs custom via rule.detect.params
  - detect→(fix simulado)→re-detect = vazio
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from uip_engine.context import FileContext
from uip_engine.heuristics.xmlns_refs import detect_modern_ui_refs


_REQUIRED = [
    "UiPath.UIAutomationNext.Activities",
    "UiPath.UIAutomationNext",
    "UiPath.UIAutomationCore",
]


def _make_rule(required_refs=None) -> SimpleNamespace:
    return SimpleNamespace(
        id="W-11n",
        severity=1,
        category="architectural",
        detect={"params": {"required_refs": required_refs if required_refs is not None else list(_REQUIRED)}},
    )


def _make_fc(tmp_path: Path, content: str, name: str = "x.xaml") -> FileContext:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return FileContext(path=p)


def _xaml(refs: list[str], uses_uix: bool = True) -> str:
    ref_lines = "\n".join(f"      <AssemblyReference>{r}</AssemblyReference>" for r in refs)
    body = (
        '    <uix:NClick DisplayName="Click" />' if uses_uix
        else '    <ui:Click DisplayName="Click" />'
    )
    return (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:uix="http://schemas.uipath.com/workflow/activities/uix" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
        'xmlns:sco="clr-namespace:System.Collections.ObjectModel;assembly=System.Private.CoreLib" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        "  <TextExpression.ReferencesForImplementation>\n"
        '    <sco:Collection x:TypeArguments="AssemblyReference">\n'
        f"{ref_lines}\n"
        "    </sco:Collection>\n"
        "  </TextExpression.ReferencesForImplementation>\n"
        "  <Sequence>\n"
        f"{body}\n"
        "  </Sequence>\n"
        "</Activity>\n"
    )


# ---------- Detector tests ----------


def test_emits_for_missing_refs_when_uix_used(tmp_path: Path) -> None:
    fc = _make_fc(tmp_path, _xaml(["UiPath.System.Activities"], uses_uix=True))
    findings = detect_modern_ui_refs(_make_rule(), fc, None)
    names = sorted(f.fix_mechanical["name"] for f in findings)
    assert names == sorted(_REQUIRED)
    assert all(f.rule_id == "W-11n" for f in findings)
    assert all(f.fix_mechanical["type"] == "insert_assembly_reference" for f in findings)


def test_emits_only_for_actually_missing(tmp_path: Path) -> None:
    # já tem 1 dos 3 → faltam 2
    fc = _make_fc(tmp_path, _xaml(
        ["UiPath.System.Activities", "UiPath.UIAutomationCore"], uses_uix=True))
    findings = detect_modern_ui_refs(_make_rule(), fc, None)
    names = sorted(f.fix_mechanical["name"] for f in findings)
    assert names == ["UiPath.UIAutomationNext", "UiPath.UIAutomationNext.Activities"]


def test_noop_when_all_refs_present(tmp_path: Path) -> None:
    fc = _make_fc(tmp_path, _xaml(["UiPath.System.Activities", *_REQUIRED], uses_uix=True))
    findings = detect_modern_ui_refs(_make_rule(), fc, None)
    assert findings == []


def test_noop_when_no_uix_usage(tmp_path: Path) -> None:
    # refs faltando MAS XAML não usa uix → condicional não dispara
    fc = _make_fc(tmp_path, _xaml(["UiPath.System.Activities"], uses_uix=False))
    findings = detect_modern_ui_refs(_make_rule(), fc, None)
    assert findings == []


def test_noop_when_no_refs_block(tmp_path: Path) -> None:
    content = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:uix="http://schemas.uipath.com/workflow/activities/uix">\n'
        "  <Sequence><uix:NClick /></Sequence>\n"
        "</Activity>\n"
    )
    fc = _make_fc(tmp_path, content)
    findings = detect_modern_ui_refs(_make_rule(), fc, None)
    assert findings == []


def test_noop_non_xaml(tmp_path: Path) -> None:
    f = tmp_path / "project.json"
    f.write_text('{"name":"X"}', encoding="utf-8")
    fc = FileContext(path=f)
    findings = detect_modern_ui_refs(_make_rule(), fc, None)
    assert findings == []


def test_custom_required_refs_from_params(tmp_path: Path) -> None:
    fc = _make_fc(tmp_path, _xaml(["UiPath.System.Activities"], uses_uix=True))
    findings = detect_modern_ui_refs(_make_rule(required_refs=["UiPath.Foo.Bar"]), fc, None)
    names = [f.fix_mechanical["name"] for f in findings]
    assert names == ["UiPath.Foo.Bar"]


def test_detect_then_fix_then_redetect(tmp_path: Path) -> None:
    """Simula o fix (insert refs) e confirma re-detect vazio."""
    fc = _make_fc(tmp_path, _xaml(["UiPath.System.Activities"], uses_uix=True))
    findings = detect_modern_ui_refs(_make_rule(), fc, None)
    assert len(findings) == 3
    # simula insert_assembly_reference dos 3 refs
    fixed = _make_fc(tmp_path, _xaml(["UiPath.System.Activities", *_REQUIRED], uses_uix=True), name="y.xaml")
    assert detect_modern_ui_refs(_make_rule(), fixed, None) == []
