"""F35 tests — analyzer-gate per-file rollback + retomar fix loop.

Comportamento esperado pós-F35:
  - Quando analyzer-gate detecta new Error pós-fix: rollback per-file
    (file específico revertido pra pre-loop bytes), file frozen pra retries.
  - Retry roda fix loop novamente skipando frozen files.
  - Retry roda analyzer novamente. Se limpo → break, EXIT_OK.
  - Se retries exauridos OU rollback inexequível → break sem abortar pipeline.
  - Retorna EXIT_OK em qualquer caso (vs EXIT_INTERNAL pré-F35).

Tests mockam `discover_uipcli`/`run_analyzer` via monkeypatch — não dependem
de uipcli real instalado.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from uip_engine import analyzer as _analyzer
from uip_engine import cli as _cli


# Fixture XAML que dispara fix S-1 (`<x:Members />` → `<x:Members></x:Members>`).
SAMPLE_BAD_XAML = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Foo" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:s="clr-namespace:System;assembly=mscorlib"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members />
  <Sequence />
</Activity>
"""

SAMPLE_PROJECT_JSON = """{
  "name": "test",
  "studioVersion": "23.10.13",
  "targetFramework": "Windows",
  "expressionLanguage": "VisualBasic"
}
"""


def _mk_fix_args(project_path: Path) -> argparse.Namespace:
    """Build argparse Namespace simulando `cli fix --apply <project>`."""
    return argparse.Namespace(
        path=str(project_path),
        rules_file=str(Path(_cli.DEFAULT_RULES_FILE)),
        apply=True,
        rules="",
        include_class="deterministic",
        no_analyzer_gate=False,
        verbose=False,
    )


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    """Project com 1 XAML que dispara fix S-1."""
    p = tmp_path / "Proj"
    p.mkdir()
    (p / "project.json").write_text(SAMPLE_PROJECT_JSON, encoding="utf-8")
    (p / "Bad.xaml").write_text(SAMPLE_BAD_XAML, encoding="utf-8")
    return p


@pytest.fixture
def disable_baseline_cache(monkeypatch):
    """Force baseline cache miss em cada test."""
    monkeypatch.setattr(
        _analyzer, "load_cached_baseline", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        _analyzer, "save_cached_baseline", lambda *a, **kw: None
    )


def _make_issue(file: str, code: str, sev: str = "Error", desc: str = "fake") -> _analyzer.AnalyzerIssue:
    return _analyzer.AnalyzerIssue(
        file=file, error_code=code, severity=sev, description=desc
    )


def test_gate_clean_no_retry(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Analyzer-gate retorna 0 new errors → outer loop sai imediato."""
    monkeypatch.setattr(
        _analyzer, "discover_uipcli", lambda: Path("fake/uipcli.exe")
    )

    calls = {"count": 0}

    def fake_run(*args, **kwargs):
        calls["count"] += 1
        return set()  # always empty — clean

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "ANALYZER REGRESSION" not in out
    assert "ANALYZER ROLLBACK" not in out
    # baseline run + post-fix run = 2 calls
    assert calls["count"] == 2


def test_gate_regression_rolls_back_and_retries(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Analyzer reporta new Error em Bad.xaml → rollback file + retomar loop."""
    monkeypatch.setattr(
        _analyzer, "discover_uipcli", lambda: Path("fake/uipcli.exe")
    )

    baseline_bytes = (fake_project / "Bad.xaml").read_bytes()
    call_log: list = []

    def fake_run(project_root, cli_path, **kwargs):
        call_log.append("run")
        n = len(call_log)
        if n == 1:
            # baseline pré-fix: vazio
            return set()
        elif n == 2:
            # post-fix iter 1: novo Error em Bad.xaml
            return {_make_issue("Bad.xaml", "ST-FAKE-001", "Error")}
        else:
            # retry post-fix: limpo (file foi rollback'd, frozen)
            return set()

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK, "F35: EXIT_OK mesmo com gate fail inicial"
    assert "ANALYZER REGRESSION" in out
    assert "ANALYZER ROLLBACK" in out
    assert "Bad.xaml" in out
    assert "retomando fix loop" in out
    # File revertido pra pre-loop bytes
    assert (fake_project / "Bad.xaml").read_bytes() == baseline_bytes
    # 3 analyzer runs: baseline + post-iter1 + post-retry1
    assert len(call_log) == 3
    # Frozen files reported
    assert "frozen files" in out


def test_gate_persistent_regression_exits_after_retries(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Regression persiste em file fora do snapshot → FULL-SNAPSHOT fallback
    reverte tudo modificado (engine NUNCA deixa projeto pior) → loop sai
    gracefully, EXIT_OK.

    Atualizado 2026-05-27: pré-fix esse caso simplesmente abortava com
    'rollback inexequível'. Novo comportamento (B2 fix): granular falha →
    fallback restaura TODO XAML divergente do snapshot. Pilot regression:
    sem fallback, engine deixava 3 XAMLs com duplicate Property injection.
    """
    monkeypatch.setattr(
        _analyzer, "discover_uipcli", lambda: Path("fake/uipcli.exe")
    )

    baseline_bytes = (fake_project / "Bad.xaml").read_bytes()
    call_log: list = []

    def fake_run(project_root, cli_path, **kwargs):
        call_log.append("run")
        n = len(call_log)
        if n == 1:
            return set()
        # Post-fix sempre reporta error em file fantasma fora snapshot
        # → granular rollback falha → FULL-SNAPSHOT fallback restaura Bad.xaml
        return {_make_issue("Phantom.xaml", "ST-FAKE-002", "Error")}

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK, "EXIT_OK mesmo após FULL-SNAPSHOT fallback"
    assert "ANALYZER REGRESSION" in out
    # Mensagem "granular rollback inexequível" sinaliza fallback ativo
    assert "rollback inexequível" in out
    assert "FULL-SNAPSHOT rollback" in out
    # Bad.xaml restaurado pra estado pré-loop (engine NUNCA deixa pior)
    assert (fake_project / "Bad.xaml").read_bytes() == baseline_bytes


def test_gate_empty_filepath_triggers_full_snapshot_rollback(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """REGRESSION (pilot contestacao-de-compras 2026-05-27): analyzer reporta
    error PROJECT-LEVEL (FilePath vazio em uipcli JSON → AnalyzerIssue.file = "").
    Pré-fix: err_files = {""}, granular filter nunca casa, rollback inexequível,
    engine deixa projeto com regressões aplicadas. Fix B2: FULL-SNAPSHOT
    fallback ativa quando granular não restaura nada AND existem new errors.
    """
    monkeypatch.setattr(
        _analyzer, "discover_uipcli", lambda: Path("fake/uipcli.exe")
    )

    baseline_bytes = (fake_project / "Bad.xaml").read_bytes()
    call_log: list = []

    def fake_run(project_root, cli_path, **kwargs):
        call_log.append("run")
        n = len(call_log)
        if n == 1:
            return set()
        # Project-level error: FilePath vazio → basename = ""
        # Reproduz pilot pré-fix: "Não foi possível realizar a análise do projeto"
        return {_make_issue("", "ST-PROJECT-LEVEL", "Error",
                            "Não foi possível realizar análise")}

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "ANALYZER REGRESSION" in out
    assert "FULL-SNAPSHOT rollback" in out, (
        "Empty-FilePath analyzer error deve disparar full-snapshot fallback"
    )
    # Bad.xaml restaurado mesmo sem basename match
    assert (fake_project / "Bad.xaml").read_bytes() == baseline_bytes


def test_parse_analyzer_output_infers_file_from_empty_filepath_description():
    guid = "11111111-1111-1111-1111-111111111111"
    payload = {
        f"{guid}-FilePath": "",
        f"{guid}-ErrorCode": "",
        f"{guid}-ErrorSeverity": "Error",
        f"{guid}-Description": (
            r"Não foi possível carregar o arquivo C:\Work\Proj\Cases\TC_ObterRelatorio.xaml. "
            r"Motivo: Falha ao criar um 'InArgument' do texto '\"\"'."
        ),
    }
    stdout = "#json" + __import__("json").dumps(payload, ensure_ascii=False) + "#json"

    issues = _analyzer.parse_analyzer_output(stdout)

    assert issues == {
        _analyzer.AnalyzerIssue(
            file="TC_ObterRelatorio.xaml",
            error_code="",
            severity="Error",
            description=(
                "Não foi possível carregar o arquivo <PATH> "
                "Motivo: Falha ao criar um 'InArgument' do texto '\\\"\\\"'."
            ),
        )
    }


def test_gate_empty_filepath_with_xaml_description_rolls_back_granular(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Studio sometimes leaves FilePath empty but includes the XAML path in
    Description. Analyzer parsing should infer the basename so the gate rolls
    back only the failing file, not every changed XAML in the project.
    """
    monkeypatch.setattr(
        _analyzer, "discover_uipcli", lambda: Path("fake/uipcli.exe")
    )

    other = fake_project / "Other.xaml"
    other.write_text(SAMPLE_BAD_XAML.replace("Foo", "Other"), encoding="utf-8")
    bad_baseline = (fake_project / "Bad.xaml").read_bytes()
    other_baseline = other.read_bytes()
    call_log: list = []

    def fake_run(project_root, cli_path, **kwargs):
        call_log.append("run")
        if len(call_log) == 1:
            return set()
        if len(call_log) > 2:
            return set()
        return {
            _analyzer.AnalyzerIssue(
                file="Bad.xaml",
                error_code="",
                severity="Error",
                description="Nao foi possivel carregar o arquivo <PATH> Bad.xaml. Motivo: Falha",
            )
        }

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "FULL-SNAPSHOT rollback" not in out
    assert "ANALYZER ROLLBACK" in out
    assert (fake_project / "Bad.xaml").read_bytes() == bad_baseline
    assert other.read_bytes() != other_baseline, "unrelated changed file should stay fixed"


def test_gate_disabled_no_retry_logic(
    fake_project: Path, monkeypatch, capsys
):
    """`--no-analyzer-gate` desabilita gate completamente → loop normal sem
    outer retry, sem chamadas analyzer."""
    monkeypatch.setattr(
        _analyzer, "discover_uipcli", lambda: Path("fake/uipcli.exe")
    )
    calls = {"count": 0}

    def fake_run(*a, **kw):
        calls["count"] += 1
        return set()

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    args = _mk_fix_args(fake_project)
    args.no_analyzer_gate = True

    rc = _cli._cmd_fix(args)
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "analyzer-gate" not in out
    assert calls["count"] == 0  # gate desabilitado → sem analyzer call


def test_uipcli_not_found_skips_gate(
    fake_project: Path, monkeypatch, capsys
):
    """Sem uipcli instalado (discover_uipcli=None) → gate skipped graceful."""
    monkeypatch.setattr(
        _analyzer, "discover_uipcli", lambda: None
    )

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "uipcli não encontrado" in out
    assert "ANALYZER REGRESSION" not in out
