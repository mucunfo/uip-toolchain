"""Audit CCS-1 — detector emite mech type novo + element scope.

AUDIT_2026-05-28 finding CCS-1 (HIGH, detector!=fixer surface): o mech
`rename_attribute` é no-op pra attribute NAMES (fixer skip-by-design via
_is_attribute_name_context). Fix prescrito: detector passa a emitir
`rename_attribute_name_in_tag` + `element` (o tag de invocação
`<prefix:Workflow>`) pro novo fixer renomear o atributo NAME escopado ao
open tag daquela invocação.

Estes testes asseguram APENAS o lado detector (lane ccs_contract):
  - mech type == "rename_attribute_name_in_tag"
  - mech contém "element" == "<prefix>:<wf_name>"
  - from/to continuam corretos (attr errado → casing do contract)
  - casing correto → 0 findings (sem regressão de ruído)

NÃO edita test_ccs_contract_securestring_guard.py (que ainda assere o type
antigo) — aquele quebra de propósito e é reconciliado no Phase 3.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics import ccs_contract as cc


def _mk_rule():
    return Rule(
        id="CCS-1",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="CCS_* workflow attribute usa casing errado vs lib contract",
        description="",
        detect={"type": "python"},
        fix={"apply_class": "deterministic"},
    )


def _mk_project(tmp_path: Path) -> tuple[Path, ProjectContext]:
    proj = tmp_path / "P"
    proj.mkdir(exist_ok=True)
    pj = proj / "project.json"
    pj.write_text(
        json.dumps({"targetFramework": "Windows", "dependencies": {}}),
        encoding="utf-8",
    )
    return proj, ProjectContext(
        root=proj,
        project_json=json.loads(pj.read_text(encoding="utf-8")),
    )


def _write_xaml(proj: Path, body: str, name: str = "Foo.xaml") -> FileContext:
    f = proj / name
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        '          xmlns:c="clr-namespace:CCS_SipagDirect;assembly=CCS_SipagDirect"\n'
        '          xmlns:ss="clr-namespace:System.Security;assembly=mscorlib"\n'
        '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        f"{body}\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    return FileContext(f)


@pytest.fixture(autouse=True)
def _stub_ccs_contracts(monkeypatch):
    fake_catalog = {
        "CCS_SipagDirect": {
            "Login": [
                "in_URL", "in_Usuario", "in_Senha",
                "in_JanelaAnonima", "out_UIESipagDirect",
            ],
        },
    }
    monkeypatch.setattr(cc, "_CCS_CONTRACTS", fake_catalog)
    yield


def test_ccs1_mech_type_is_rename_attribute_name_in_tag(tmp_path):
    """Post-audit: mech type troca de rename_attribute → rename_attribute_name_in_tag."""
    proj, pc = _mk_project(tmp_path)
    body = (
        '  <c:Login in_Url="http://x" in_Usuario="u" in_JanelaAnonima="False"\n'
        '           out_UiESipagDirect="{x:Null}"\n'
        '           in_Senha="senha_plain_text" />\n'
    )
    fc = _write_xaml(proj, body)
    findings = cc.detect_ccs_contract_check(_mk_rule(), fc, pc)
    # 2 findings: in_Url (→ in_URL) + out_UiESipagDirect (→ out_UIESipagDirect)
    assert len(findings) == 2
    for f in findings:
        assert f.fix_mechanical is not None
        assert f.fix_mechanical.get("type") == "rename_attribute_name_in_tag"


def test_ccs1_mech_carries_element_scope(tmp_path):
    """Mech inclui `element` = <prefix>:<wf_name> da invocação alvo."""
    proj, pc = _mk_project(tmp_path)
    body = (
        '  <c:Login in_Url="http://x" in_Usuario="u" in_JanelaAnonima="False"\n'
        '           out_UiESipagDirect="{x:Null}"\n'
        '           in_Senha="senha_plain_text" />\n'
    )
    fc = _write_xaml(proj, body)
    findings = cc.detect_ccs_contract_check(_mk_rule(), fc, pc)
    assert len(findings) == 2
    for f in findings:
        assert f.fix_mechanical is not None
        assert f.fix_mechanical.get("element") == "c:Login"


def test_ccs1_mech_from_to_casing(tmp_path):
    """from = attr errado; to = casing do contract; mapeados por finding."""
    proj, pc = _mk_project(tmp_path)
    body = (
        '  <c:Login in_Url="http://x" in_Usuario="u" in_JanelaAnonima="False"\n'
        '           out_UiESipagDirect="{x:Null}"\n'
        '           in_Senha="senha_plain_text" />\n'
    )
    fc = _write_xaml(proj, body)
    findings = cc.detect_ccs_contract_check(_mk_rule(), fc, pc)
    pairs = {
        (f.fix_mechanical["from"], f.fix_mechanical["to"]) for f in findings
    }
    assert ("in_Url", "in_URL") in pairs
    assert ("out_UiESipagDirect", "out_UIESipagDirect") in pairs


def test_ccs1_element_scope_with_securestring_sibling(tmp_path):
    """Mesmo com SecureString sibling, mech mantém novo type + element."""
    proj, pc = _mk_project(tmp_path)
    body = (
        '  <Sequence>\n'
        '    <Sequence.Variables>\n'
        '      <Variable x:TypeArguments="ss:SecureString" Name="vSsSenha"/>\n'
        '    </Sequence.Variables>\n'
        '    <c:Login in_Url="http://x" in_Usuario="u" in_JanelaAnonima="False"\n'
        '             out_UiESipagDirect="{x:Null}"\n'
        '             in_Senha="[vSsSenha]" />\n'
        '  </Sequence>\n'
    )
    fc = _write_xaml(proj, body)
    findings = cc.detect_ccs_contract_check(_mk_rule(), fc, pc)
    assert len(findings) == 2
    for f in findings:
        assert f.fix_mechanical is not None
        assert f.fix_mechanical.get("type") == "rename_attribute_name_in_tag"
        assert f.fix_mechanical.get("element") == "c:Login"


def test_ccs1_no_findings_when_casing_correct(tmp_path):
    """Casing exato match contract → 0 findings (não emite mech algum)."""
    proj, pc = _mk_project(tmp_path)
    body = (
        '  <c:Login in_URL="http://x" in_Usuario="u" in_JanelaAnonima="False"\n'
        '           out_UIESipagDirect="{x:Null}"\n'
        '           in_Senha="literal" />\n'
    )
    fc = _write_xaml(proj, body)
    findings = cc.detect_ccs_contract_check(_mk_rule(), fc, pc)
    assert len(findings) == 0
