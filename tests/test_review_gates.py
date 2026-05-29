"""Tests p/ os 3 gates do review (analyzer + nuget restore + uipcli pack).

review é canonical pre-publish gate: SEMPRE roda os 3. --no-analyzer-gate
mantido como flag back-compat (warning + ignore).

Tests mockam invocacoes subprocess (não rodam nuget/uipcli de verdade — CI
não tem esses binarios garantidamente).
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Garante que tests podem importar uip_engine.* sem PYTHONPATH adhoc.
sys.path.insert(0, str(ROOT))

from uip_engine import cli as cli_mod  # noqa: E402
from uip_engine._types import Finding, Severity, ValidationResult  # noqa: E402
from uip_engine.runtime_loadtest import _binary_path as _rlt_binary_path  # noqa: E402

# O gate runtime_loadtest (4o gate do `all`) precisa do binario .NET
# runtime_loadtest.exe. CI / hosts sem `dotnet build` não o têm — igual a
# nuget/uipcli (ver docstring do módulo). Tests que exercem o pipeline `all`
# REAL (sem stub desse gate) skipam quando o binario está ausente, em vez de
# falhar com RT-LOAD-INFRA (rc=1). Mesma política do skipif de test_hooks.
_RLT_BINARY_MISSING = _rlt_binary_path() is None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path) -> Path:
    """Cria um projeto UiPath minimal."""
    p = tmp_path / "TestProj"
    p.mkdir()
    (p / "project.json").write_text(
        '{"name":"test","studioVersion":"23.10.13",'
        '"targetFramework":"Windows","expressionLanguage":"VisualBasic"}',
        encoding="utf-8",
    )
    (p / "Main.xaml").write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"/>',
        encoding="utf-8",
    )
    return p


def _make_completed_proc(stdout: str = "", stderr: str = "", rc: int = 0):
    cp = MagicMock(spec=subprocess.CompletedProcess)
    cp.stdout = stdout
    cp.stderr = stderr
    cp.returncode = rc
    return cp


# ---------------------------------------------------------------------------
# Test 1 — nuget restore output com NU1605 vira finding ERROR
# ---------------------------------------------------------------------------


def test_nuget_gate_emits_finding_on_nu1605(tmp_path):
    proj = _make_project(tmp_path)
    result = ValidationResult()

    nuget_output = (
        "Restoring packages for C:\\proj\\project.json...\n"
        "warning : NU1605: Detected package downgrade: UiPath.System.Activities "
        "from 25.10.8 to 25.4.7. Reference the package directly from the project "
        "to select a different version.\n"
        "warning : NU1701: Package 'Sicoob.Lib' was restored using NetFramework.\n"
        "[Error] NU1101: Unable to find package 'NonExistent.Pkg'. No packages "
        "exist with this id in source(s).\n"
    )
    fake_proc = _make_completed_proc(stdout=nuget_output, rc=1)

    # Stub _discover_nuget_binary → retorna path falso non-dotnet
    with patch.object(cli_mod, "_discover_nuget_binary", return_value="nuget.exe"), \
         patch.object(subprocess, "run", return_value=fake_proc):
        cli_mod._run_nuget_restore_gate(result, str(proj), timeout=10)

    nuget_findings = [f for f in result.findings if f.rule_id.startswith("NUGET:")]
    codes = {f.rule_id for f in nuget_findings}
    assert "NUGET:NU1605" in codes, f"NU1605 não detectado. findings={codes}"
    assert "NUGET:NU1101" in codes, f"NU1101 não detectado. findings={codes}"

    # NU1605 e NU1101 ambos devem ser ERROR (promovidos).
    nu1605 = next(f for f in nuget_findings if f.rule_id == "NUGET:NU1605")
    nu1101 = next(f for f in nuget_findings if f.rule_id == "NUGET:NU1101")
    assert nu1605.severity == Severity.ERROR
    assert nu1101.severity == Severity.ERROR
    assert nu1605.category == "breaking"
    assert nu1605.file == "project.json"
    assert "downgrade" in nu1605.message.lower()

    # NU1701 NÃO está na promote list — fica WARN.
    nu1701 = [f for f in nuget_findings if f.rule_id == "NUGET:NU1701"]
    if nu1701:
        assert nu1701[0].severity == Severity.WARN


# ---------------------------------------------------------------------------
# Test 2 — uipcli publish output com erro vira UIPATH:PACK finding
# ---------------------------------------------------------------------------


def _fake_preflight_ok():
    """PreflightResult OK p/ mock — evita spawn real de uipcli."""
    from uip_engine.uipcli_runner import PreflightResult
    return PreflightResult(
        ok=True, uipcli_responsive=True, uipcli_version="fake-26.0",
        cloud_reachable=True, cloud_host="fake.cloud", diagnose="",
    )


def _fake_uipcli_result(stdout: str, returncode: int = 1):
    """UipcliResult OK p/ mock — evita spawn real Popen."""
    from uip_engine.uipcli_runner import UipcliResult
    return UipcliResult(
        completed=True, returncode=returncode, stdout=stdout, stderr="",
        duration_sec=1.0, halt_reason=None, halt_detail="",
        preflight=_fake_preflight_ok(),
    )


def test_pack_gate_emits_finding_on_bc_error(tmp_path):
    proj = _make_project(tmp_path)
    result = ValidationResult()

    pack_output = (
        "UiPath.Studio.CommandLine 26.0.193\n"
        "DB2/AtualizarFimExecucao.xaml: BC30002: O tipo 'Net.NetworkCredential' "
        "não está definido. Você provavelmente precisa adicionar um Pacote.\n"
        "Tests/Unit/Foo.xaml(45,12): BC30451: 'quot' não está declarado.\n"
        "Tests/Unit/Foo.xaml: BC30037: Caractere inválido.\n"
        "O projeto tem erros de validação e não pode ser publicado.\n"
    )
    fake_cli = MagicMock()
    fake_cli.is_file.return_value = True
    fake_cli.__str__ = lambda self: "fake-uipcli.exe"

    with patch("uip_engine.analyzer.discover_uipcli", return_value=fake_cli), \
         patch("uip_engine.uipcli_runner.preflight", return_value=_fake_preflight_ok()), \
         patch("uip_engine.uipcli_runner.run_uipcli_guarded",
               return_value=_fake_uipcli_result(pack_output, returncode=1)):
        cli_mod._run_uipcli_pack_gate(result, str(proj), timeout=10)

    pack_findings = [f for f in result.findings if f.rule_id == "UIPATH:PACK"]
    assert len(pack_findings) >= 2, f"Esperado >=2 PACK findings, got {len(pack_findings)}"

    msgs = " | ".join(f.message for f in pack_findings)
    assert "BC30002" in msgs
    assert "BC30451" in msgs

    # All PACK findings = ERROR + breaking.
    for f in pack_findings:
        assert f.severity == Severity.ERROR
        assert f.category == "breaking"


def test_pack_gate_restores_source_project_json_after_mutation(tmp_path):
    """REGRESSION (pilot 2026-05-27): uipcli publish NÃO é read-only — bumpa
    projectVersion no SOURCE + normaliza keys ausentes pra defaults. Pack-gate
    é dry-run de validação → source deve ficar byte-idêntico. Sem restore:
    projectVersion drift quebra idempotência (rerun = diff espúrio) + dropa
    keys ENV-1 aplicadas em PHASE 1.
    """
    proj = _make_project(tmp_path)
    pj = proj / "project.json"
    original_bytes = pj.read_bytes()
    result = ValidationResult()

    fake_cli = MagicMock()
    fake_cli.is_file.return_value = True

    def _mutating_publish(*args, **kwargs):
        # Simula uipcli publish: bumpa projectVersion + injeta default key
        import json as _json
        data = _json.loads(pj.read_text(encoding="utf-8-sig"))
        data["projectVersion"] = "9.9.9"  # bump artificial
        data.setdefault("runtimeOptions", {})["mustRestoreAllDependencies"] = False
        pj.write_text(_json.dumps(data), encoding="utf-8")
        return _fake_uipcli_result("", returncode=0)

    with patch("uip_engine.analyzer.discover_uipcli", return_value=fake_cli), \
         patch("uip_engine.uipcli_runner.preflight", return_value=_fake_preflight_ok()), \
         patch("uip_engine.uipcli_runner.run_uipcli_guarded",
               side_effect=_mutating_publish):
        cli_mod._run_uipcli_pack_gate(result, str(proj), timeout=10)

    # Source project.json restaurado byte-a-byte (mutação revertida).
    assert pj.read_bytes() == original_bytes, (
        "pack-gate deve restaurar project.json após uipcli publish mutar source"
    )


def test_pack_gate_fallback_on_unparseable_error(tmp_path):
    """Se uipcli retorna RC != 0 mas nada bate em regex, emit 1 finding."""
    proj = _make_project(tmp_path)
    result = ValidationResult()

    pack_output = "some opaque error message not matching any pattern\n"
    fake_cli = MagicMock()
    fake_cli.is_file.return_value = True

    with patch("uip_engine.analyzer.discover_uipcli", return_value=fake_cli), \
         patch("uip_engine.uipcli_runner.preflight", return_value=_fake_preflight_ok()), \
         patch("uip_engine.uipcli_runner.run_uipcli_guarded",
               return_value=_fake_uipcli_result(pack_output, returncode=1)):
        cli_mod._run_uipcli_pack_gate(result, str(proj), timeout=10)

    pack_findings = [f for f in result.findings if f.rule_id == "UIPATH:PACK"]
    assert len(pack_findings) == 1
    assert pack_findings[0].severity == Severity.ERROR
    assert "exit 1" in pack_findings[0].message


# ---------------------------------------------------------------------------
# Test 3 — Graceful skip se binary ausente
# ---------------------------------------------------------------------------


def test_nuget_gate_graceful_skip_when_binary_absent(tmp_path, capsys):
    proj = _make_project(tmp_path)
    result = ValidationResult()

    with patch.object(cli_mod, "_discover_nuget_binary", return_value=None):
        cli_mod._run_nuget_restore_gate(result, str(proj), timeout=10)

    # Sem findings (gate skipou).
    assert len([f for f in result.findings if f.rule_id.startswith("NUGET:")]) == 0
    captured = capsys.readouterr()
    assert "[NUGET-GATE]" in captured.err
    assert "skipping" in captured.err.lower() or "not found" in captured.err.lower()


def test_pack_gate_graceful_skip_when_uipcli_absent(tmp_path, capsys):
    proj = _make_project(tmp_path)
    result = ValidationResult()

    with patch("uip_engine.analyzer.discover_uipcli", return_value=None):
        cli_mod._run_uipcli_pack_gate(result, str(proj), timeout=10)

    pack_findings = [f for f in result.findings if f.rule_id == "UIPATH:PACK"]
    assert len(pack_findings) == 0
    captured = capsys.readouterr()
    assert "[PACK-GATE]" in captured.err
    assert "skipped" in captured.err.lower() or "not found" in captured.err.lower()


def test_nuget_gate_skip_when_only_dotnet_available(tmp_path, capsys):
    """`dotnet restore` não suporta project.json UiPath — skipa silente."""
    proj = _make_project(tmp_path)
    result = ValidationResult()

    with patch.object(cli_mod, "_discover_nuget_binary", return_value="C:\\Program Files\\dotnet\\dotnet.exe"):
        cli_mod._run_nuget_restore_gate(result, str(proj), timeout=10,
                                          verbose=True)

    assert len([f for f in result.findings if f.rule_id.startswith("NUGET:")]) == 0
    captured = capsys.readouterr()
    assert "dotnet" in captured.err.lower()


# ---------------------------------------------------------------------------
# Test 4 — --no-analyzer-gate emite warning mas analyzer roda
# ---------------------------------------------------------------------------


def test_review_no_analyzer_gate_flag_deprecated_warning(tmp_path):
    """Flag passada via subprocess: deve emitir warning, NÃO desliga gate.

    Para validar: stderr contém "deprecated and ignored".
    """
    proj = _make_project(tmp_path)
    rules_file = tmp_path / "empty_rules.yaml"
    rules_file.write_text("version: 1\nrules: []\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "uip_engine.cli", "review",
         str(proj), "--rules-file", str(rules_file),
         "--no-analyzer-gate", "--format", "json"],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )
    # Exit code 0 ou outro qualquer — mas warning DEVE estar lá.
    assert "deprecated and ignored" in proc.stderr.lower(), (
        f"esperado warning de deprecation, stderr=\n{proc.stderr}"
    )


class _ReviewArgs:
    """Args mock para _cmd_review. Setado via attrs no setUp."""
    def __init__(self, path: str, rules_file: str):
        self.path = path
        self.rules_file = rules_file
        self.format = "json"
        self.multi_project = False
        self.verbose = False
        self.telemetry = False
        self.no_analyzer_gate = False
        self.analyzer_gate_timeout = 60
        self.nuget_gate_timeout = 60
        self.pack_gate_timeout = 60


@pytest.mark.skipif(
    _RLT_BINARY_MISSING,
    reason="runtime_loadtest.exe não buildado (gate env-dependent; CI não faz "
           "dotnet build). Sem stub desse gate, RT-LOAD-INFRA torna rc=1.",
)
def test_review_always_runs_analyzer_gate_even_without_flag(tmp_path, capsys, monkeypatch):
    """Sem --no-analyzer-gate, review chama _inject_analyzer_findings.

    Verifica que a função é INVOCADA (mesmo se uipcli ausente skipa).
    Conftest seta UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES=1 — aqui deletamos p/
    testar o caminho real (com stubs). Skipa se runtime_loadtest.exe ausente
    (4o gate não-stubado emitiria RT-LOAD-INFRA → rc=1).
    """
    monkeypatch.delenv("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", raising=False)

    proj = _make_project(tmp_path)
    rf = tmp_path / "empty_rules.yaml"
    rf.write_text("version: 1\nrules: []\n", encoding="utf-8")

    invoked = {"analyzer": False, "nuget": False, "pack": False}

    def _stub_analyzer(*a, **kw):
        invoked["analyzer"] = True

    def _stub_nuget(*a, **kw):
        invoked["nuget"] = True

    def _stub_pack(*a, **kw):
        invoked["pack"] = True

    args = _ReviewArgs(str(proj), str(rf))

    with patch.object(cli_mod, "_inject_analyzer_findings", side_effect=_stub_analyzer), \
         patch.object(cli_mod, "_run_nuget_restore_gate", side_effect=_stub_nuget), \
         patch.object(cli_mod, "_run_uipcli_pack_gate", side_effect=_stub_pack):
        rc = cli_mod._cmd_review(args)

    assert invoked["analyzer"], "analyzer gate não foi invocado"
    assert invoked["nuget"], "nuget gate não foi invocado"
    assert invoked["pack"], "pack gate não foi invocado"
    assert rc == cli_mod.EXIT_OK


# ---------------------------------------------------------------------------
# Bonus: exit code is EXIT_ERROR (2) when gate finds ERROR-level finding
# ---------------------------------------------------------------------------


def test_review_exit_error_when_pack_gate_adds_error(tmp_path, monkeypatch):
    monkeypatch.delenv("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", raising=False)

    proj = _make_project(tmp_path)
    rf = tmp_path / "empty_rules.yaml"
    rf.write_text("version: 1\nrules: []\n", encoding="utf-8")

    def _stub_pack(result, project_path, **kw):
        result.add(Finding(
            rule_id="UIPATH:PACK", severity=Severity.ERROR,
            category="breaking", file="Foo.xaml", line=0,
            message="BC30002: fake error",
        ))

    args = _ReviewArgs(str(proj), str(rf))

    with patch.object(cli_mod, "_inject_analyzer_findings"), \
         patch.object(cli_mod, "_run_nuget_restore_gate"), \
         patch.object(cli_mod, "_run_uipcli_pack_gate", side_effect=_stub_pack):
        rc = cli_mod._cmd_review(args)

    assert rc == cli_mod.EXIT_ERROR, f"esperado EXIT_ERROR (2), got {rc}"
