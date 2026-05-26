"""CCS-1 detector tests — emite rename_attribute fix em casing mismatch.

F36 safety guard REMOVIDO 2026-05-21: empiricamente Studio 23.10 reporta
`Cannot set unknown member` independente de SecureString sibling. Engine
cascade rollback gate (analyzer-gate F35) isola ST-SEC-008 regression
per-file caso aconteça. Guard só deferia fix manual que nunca era feito.

Tests cobrem:
  - Casing mismatch SEM SecureString sibling → fix_mechanical present
  - Casing mismatch COM SecureString sibling → fix_mechanical STILL present
    (mensagem inclui aviso sobre rollback gate)
  - Casing exato → 0 findings (idempotente)
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
    """Wrap body em activity com xmlns:c CCS_SipagDirect + xmlns:ss SecureString."""
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
    """Mock _load_ccs_contracts — não depender de .nupkgs/ real."""
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


def test_ccs1_emits_rename_when_no_securestring(tmp_path):
    """Login invocation sem SecureString sibling → fix_mechanical=rename_attribute."""
    proj, pc = _mk_project(tmp_path)
    body = (
        '  <c:Login in_Url="http://x" in_Usuario="u" in_JanelaAnonima="False"\n'
        '           out_UiESipagDirect="{x:Null}"\n'
        '           in_Senha="senha_plain_text" />\n'
    )
    fc = _write_xaml(proj, body)
    findings = cc.detect_ccs_contract_check(_mk_rule(), fc, pc)
    # 2 findings: in_Url + out_UiESipagDirect
    assert len(findings) == 2
    for f in findings:
        assert f.fix_mechanical is not None
        assert f.fix_mechanical.get("type") == "rename_attribute"
        assert "NEEDS_REVIEW" not in f.message


def test_ccs1_emits_rename_when_securestring_sibling(tmp_path):
    """Login invocation com SecureString-bound sibling → fix_mechanical STILL present.

    F36 guard removido: engine cascade rollback gate isola ST-SEC-008
    regression caso rename dispare. Mensagem mantém aviso pra auditoria.
    """
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
    # 2 findings com fix_mechanical present (sem guard)
    assert len(findings) == 2
    for f in findings:
        assert f.fix_mechanical is not None, (
            f"F36 removido — fix_mechanical SHOULD be present mesmo com "
            f"SecureString sibling. got {f.fix_mechanical}"
        )
        assert f.fix_mechanical.get("type") == "rename_attribute"
        # Mensagem inclui aviso sobre rollback gate
        assert "SecureString" in f.message
        assert "vSsSenha" in f.message
        assert "rollback" in f.message.lower()


def test_ccs1_emits_rename_when_securestring_unrelated_invocation(tmp_path):
    """SecureString var existe no doc mas Login invocation NÃO referencia
    → fix_mechanical permanece (sem regressão potencial)."""
    proj, pc = _mk_project(tmp_path)
    body = (
        '  <Sequence>\n'
        '    <Sequence.Variables>\n'
        '      <Variable x:TypeArguments="ss:SecureString" Name="vSsOutra"/>\n'
        '    </Sequence.Variables>\n'
        '    <c:Login in_Url="http://x" in_Usuario="u" in_JanelaAnonima="False"\n'
        '             out_UiESipagDirect="{x:Null}"\n'
        '             in_Senha="senha_literal" />\n'
        '  </Sequence>\n'
    )
    fc = _write_xaml(proj, body)
    findings = cc.detect_ccs_contract_check(_mk_rule(), fc, pc)
    assert len(findings) == 2
    for f in findings:
        assert f.fix_mechanical is not None, (
            "SecureString var NÃO referenciada por Login — fix_mechanical "
            "deveria permanecer"
        )


def test_ccs1_no_findings_when_casing_correct(tmp_path):
    """Casing exato match contract → 0 findings (não emite ruído)."""
    proj, pc = _mk_project(tmp_path)
    body = (
        '  <c:Login in_URL="http://x" in_Usuario="u" in_JanelaAnonima="False"\n'
        '           out_UIESipagDirect="{x:Null}"\n'
        '           in_Senha="literal" />\n'
    )
    fc = _write_xaml(proj, body)
    findings = cc.detect_ccs_contract_check(_mk_rule(), fc, pc)
    assert len(findings) == 0
