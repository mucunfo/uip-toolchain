"""Tests for S-19 — Production XAML invoca workflow em ignoredFiles.

Bug pattern: `<ui:InvokeWorkflowFile WorkflowFileName="Subfolder\\Mock.xaml"/>`
em XAML production, mas `Subfolder/Mock.xaml` está em
`project.json::designOptions.processOptions.ignoredFiles`.

Studio analyzer passa, Studio Publish quebra.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.invoke_refs import (
    detect_invoke_ignoredfile_ref,
    detect_invoke_workflow_file_path_mismatch,
    _normalize,
)


def _mk_rule() -> Rule:
    return Rule(
        id="S-19",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="Production XAML invoca workflow listado em ignoredFiles (publish-breaking)",
        description="",
        detect={"type": "python"},
        fix={
            "apply_class": "structural",
            "prose": "Remover de ignoredFiles ou refatorar caller.",
        },
    )


def _mk_path_rule() -> Rule:
    return Rule(
        id="S-19b",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="InvokeWorkflowFile referencia workflow ausente ou com casing divergente",
        description="",
        detect={"type": "python"},
        fix={
            "apply_class": "structural",
            "prose": "Ajustar WorkflowFileName para o path real.",
        },
    )


def _mk_project(
    tmp_path: Path,
    ignored: list[str] | None = None,
) -> tuple[Path, ProjectContext]:
    proj = tmp_path / "P"
    proj.mkdir(exist_ok=True)
    pj = proj / "project.json"
    pj_content = {
        "targetFramework": "Windows",
        "dependencies": {},
    }
    if ignored is not None:
        pj_content["designOptions"] = {
            "processOptions": {"ignoredFiles": ignored},
        }
    pj.write_text(json.dumps(pj_content), encoding="utf-8")
    return (
        proj,
        ProjectContext(root=proj, project_json=json.loads(pj.read_text(encoding="utf-8"))),
    )


def _write_xaml(proj: Path, body: str, name: str = "Caller.xaml") -> FileContext:
    f = proj / name
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        f"{body}\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    return FileContext(f)


# ============================================================================
# Detect — flagga invoke estático para file em ignoredFiles
# ============================================================================

def test_s19_flags_invoke_of_ignored_file(tmp_path):
    """Caller invoca `Subfolder\\Mock.xaml`; ignoredFiles lista
    `Subfolder/Mock.xaml` → 1 finding ERROR."""
    proj, pc = _mk_project(tmp_path, ignored=["Subfolder/Mock.xaml"])
    body = (
        '  <ui:InvokeWorkflowFile DisplayName="Mock" '
        'WorkflowFileName="Subfolder\\Mock.xaml"/>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "S-19"
    assert f.severity == Severity.ERROR
    assert "Subfolder" in f.message
    assert "Mock.xaml" in f.message
    assert f.fix_prose


def test_s19_normalizes_path_separators(tmp_path):
    """Path com `/` no XAML também deve match contra ignoredFiles com `\\`."""
    proj, pc = _mk_project(tmp_path, ignored=["Subfolder\\Mock.xaml"])
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="Subfolder/Mock.xaml"/>\n'
    )
    fc = _write_xaml(proj, body)
    assert len(detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc)) == 1


def test_s19_silent_when_file_not_in_ignored_list(tmp_path):
    """File invocado NÃO está em ignoredFiles → 0 findings."""
    proj, pc = _mk_project(tmp_path, ignored=["Other/IgnoredOnly.xaml"])
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="Subfolder/Mock.xaml"/>\n'
    )
    fc = _write_xaml(proj, body)
    assert detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc) == []


def test_s19_silent_when_no_ignoredfiles_in_project(tmp_path):
    """project.json sem ignoredFiles → 0 findings (short-circuit)."""
    proj, pc = _mk_project(tmp_path, ignored=None)
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="Mock.xaml"/>\n'
    )
    fc = _write_xaml(proj, body)
    assert detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc) == []


def test_s19_skips_dynamic_workflow_file_name(tmp_path):
    """WorkflowFileName=`[expr]` (VB binding) → 0 findings (não dá pra
    resolver estaticamente)."""
    proj, pc = _mk_project(tmp_path, ignored=["Mock.xaml"])
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="[in_StWorkflow]"/>\n'
    )
    fc = _write_xaml(proj, body)
    assert detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc) == []


def test_s19_handles_case_insensitive_paths(tmp_path):
    """Match insensitive case — Windows filesystems são insensitive."""
    proj, pc = _mk_project(tmp_path, ignored=["subfolder/mock.xaml"])
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="Subfolder\\MOCK.XAML"/>\n'
    )
    fc = _write_xaml(proj, body)
    assert len(detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc)) == 1


def test_s19_multiple_invokes_multiple_findings(tmp_path):
    """Múltiplos invokes para files ignored no mesmo XAML → múltiplos findings."""
    proj, pc = _mk_project(
        tmp_path,
        ignored=["Mock1.xaml", "Subfolder/Mock2.xaml"],
    )
    body = (
        '  <ui:InvokeWorkflowFile WorkflowFileName="Mock1.xaml"/>\n'
        '  <ui:InvokeWorkflowFile WorkflowFileName="Subfolder\\Mock2.xaml"/>\n'
        '  <ui:InvokeWorkflowFile WorkflowFileName="NotIgnored.xaml"/>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc)
    assert len(findings) == 2


def test_s19_real_world_mock_sisbrweb_scenario(tmp_path):
    """Bug exato detectado em PRD: ImportarXmlComRetry.xaml invoca
    MockSisbrWeb.xaml condicional, mas file está em ignoredFiles."""
    proj, pc = _mk_project(
        tmp_path,
        ignored=["Helpers\\MockSisbrWeb.xaml"],
    )
    body = (
        '  <Sequence>\n'
        '    <If Condition="[in_BlUsarMockSisbrWeb]">\n'
        '      <If.Then>\n'
        '        <ui:InvokeWorkflowFile DisplayName="MockSisbrWeb" '
        'WorkflowFileName="Helpers\\MockSisbrWeb.xaml"/>\n'
        '      </If.Then>\n'
        '    </If>\n'
        '  </Sequence>\n'
    )
    fc = _write_xaml(proj, body, name="ImportarXmlComRetry.xaml")
    findings = detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc)
    assert len(findings) == 1
    assert "MockSisbrWeb.xaml" in findings[0].message
    assert "publish" in findings[0].message.lower() or "Publish" in findings[0].message


def test_s19_line_number_reported(tmp_path):
    """Finding aponta linha correta do InvokeWorkflowFile no XAML."""
    proj, pc = _mk_project(tmp_path, ignored=["Mock.xaml"])
    body = (
        '  <ui:Sequence DisplayName="Top">\n'
        '    <ui:InvokeWorkflowFile WorkflowFileName="Mock.xaml"/>\n'
        '  </ui:Sequence>\n'
    )
    fc = _write_xaml(proj, body)
    findings = detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc)
    assert len(findings) == 1
    # Header é linhas 1-2; <Activity> linha 2; <ui:Sequence> linha 3;
    # <ui:InvokeWorkflowFile> linha 4.
    assert findings[0].line == 4


def test_s19_skips_non_xaml_files(tmp_path):
    """Files com suffix != .xaml → 0 findings (guard)."""
    proj, pc = _mk_project(tmp_path, ignored=["Mock.xaml"])
    txt = proj / "notes.txt"
    txt.write_text(
        '<ui:InvokeWorkflowFile WorkflowFileName="Mock.xaml"/>',
        encoding="utf-8",
    )
    fc = FileContext(txt)
    assert detect_invoke_ignoredfile_ref(_mk_rule(), fc, pc) == []


def test_s19_no_project_context_returns_empty(tmp_path):
    """pc=None → 0 findings (sem project.json, não dá pra resolver)."""
    f = tmp_path / "Foo.xaml"
    f.write_text(
        '<?xml version="1.0"?>\n<Activity><Bad/></Activity>',
        encoding="utf-8",
    )
    fc = FileContext(f)
    assert detect_invoke_ignoredfile_ref(_mk_rule(), fc, None) == []


# ============================================================================
# Schema — S-19 carrega corretamente
# ============================================================================

def test_s19_loader_validates_apply_class():
    """S-19 deve declarar apply_class=structural (heurística não emite
    fix_mechanical dinâmico — só prose). Loader valida que python detector
    com fix dinâmico tenha apply_class explícito."""
    from uip_engine.loader import load_rules
    from uip_engine import detectors, fixers

    rules_path = Path(__file__).resolve().parents[1] / "rules.yaml"
    rules = load_rules(
        rules_path,
        registered_detectors=set(detectors.REGISTRY.keys()),
        registered_fixers=set(fixers.REGISTRY.keys()),
    )
    s19 = next((r for r in rules if r.id == "S-19"), None)
    assert s19 is not None
    assert s19.severity == Severity.ERROR
    assert s19.category == "breaking"
    assert s19.fix and s19.fix.get("apply_class") == "structural"


# ============================================================================
# Detect S-19b — flagga workflow ausente ou path com casing divergente
# ============================================================================

def test_s19b_flags_case_mismatch_against_file_on_disk(tmp_path):
    """Caller referencia GetAndCheckFiles.xaml, mas arquivo real e
    GetandCheckFiles.xaml -> finding ERROR."""
    proj, pc = _mk_project(tmp_path, ignored=None)
    processamento = proj / "Processamento"
    processamento.mkdir()
    (processamento / "GetandCheckFiles.xaml").write_text(
        '<?xml version="1.0" encoding="utf-8"?><Activity />',
        encoding="utf-8",
    )
    body = (
        '  <ui:InvokeWorkflowFile DisplayName="GetAndCheckFiles" '
        'WorkflowFileName="Processamento\\GetAndCheckFiles.xaml"/>\n'
    )
    fc = _write_xaml(proj, body, name="Process.xaml")

    findings = detect_invoke_workflow_file_path_mismatch(_mk_path_rule(), fc, pc)

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "S-19b"
    assert f.severity == Severity.ERROR
    assert "GetAndCheckFiles.xaml" in f.message
    assert "GetandCheckFiles.xaml" in f.message


def test_s19b_flags_missing_static_workflow_file(tmp_path):
    """WorkflowFileName estatico sem arquivo correspondente -> finding ERROR."""
    proj, pc = _mk_project(tmp_path, ignored=None)
    body = '  <ui:InvokeWorkflowFile WorkflowFileName="Missing.xaml"/>\n'
    fc = _write_xaml(proj, body, name="Process.xaml")

    findings = detect_invoke_workflow_file_path_mismatch(_mk_path_rule(), fc, pc)

    assert len(findings) == 1
    assert findings[0].rule_id == "S-19b"
    assert "Missing.xaml" in findings[0].message
    assert "nao existe" in findings[0].message


def test_s19b_allows_exact_path_with_different_separator(tmp_path):
    """Separador \\ ou / nao deve importar quando o casing bate."""
    proj, pc = _mk_project(tmp_path, ignored=None)
    processamento = proj / "Processamento"
    processamento.mkdir()
    (processamento / "GetandCheckFiles.xaml").write_text(
        '<?xml version="1.0" encoding="utf-8"?><Activity />',
        encoding="utf-8",
    )
    body = (
        '  <ui:InvokeWorkflowFile '
        'WorkflowFileName="Processamento\\GetandCheckFiles.xaml"/>\n'
    )
    fc = _write_xaml(proj, body, name="Process.xaml")

    findings = detect_invoke_workflow_file_path_mismatch(_mk_path_rule(), fc, pc)

    assert findings == []


def test_s19b_skips_dynamic_workflow_file_name(tmp_path):
    """WorkflowFileName=[expr] nao e resolvido estaticamente."""
    proj, pc = _mk_project(tmp_path, ignored=None)
    body = '  <ui:InvokeWorkflowFile WorkflowFileName="[in_StWorkflow]"/>\n'
    fc = _write_xaml(proj, body, name="Process.xaml")

    findings = detect_invoke_workflow_file_path_mismatch(_mk_path_rule(), fc, pc)

    assert findings == []


def test_s19b_loader_validates_apply_class():
    """S-19b deve carregar como ERROR estrutural."""
    from uip_engine.loader import load_rules
    from uip_engine import detectors, fixers

    rules_path = Path(__file__).resolve().parents[1] / "rules.yaml"
    rules = load_rules(
        rules_path,
        registered_detectors=set(detectors.REGISTRY.keys()),
        registered_fixers=set(fixers.REGISTRY.keys()),
    )
    s19b = next((r for r in rules if r.id == "S-19b"), None)
    assert s19b is not None
    assert s19b.severity == Severity.ERROR
    assert s19b.category == "breaking"
    assert s19b.fix and s19b.fix.get("apply_class") == "structural"


# ============================================================================
# Path normalization unit tests
# ============================================================================

def test_normalize_backslash_to_forward():
    assert _normalize("Subfolder\\Mock.xaml") == "subfolder/mock.xaml"


def test_normalize_lowercases():
    assert _normalize("ABC.XAML") == "abc.xaml"


def test_normalize_strips_leading_dotslash():
    assert _normalize("./Mock.xaml") == "mock.xaml"


def test_normalize_strips_leading_slashes():
    assert _normalize("/Mock.xaml") == "mock.xaml"
