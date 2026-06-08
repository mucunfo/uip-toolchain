"""Analyzer-gate per-file rollback and fix-loop retry tests.

Expected behavior:
  - When analyzer-gate detects a new post-fix Error, rollback is per-file.
  - The failed file is frozen for retries.
  - Retry runs the fix loop and analyzer again; clean retry returns EXIT_OK.
  - Exhausted retries or impossible rollback stop without aborting pipeline.

Tests mock `discover_official_uip` and `run_analyzer`; no real UiPath CLI is
required.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from uip_engine import analyzer as _analyzer
from uip_engine import cli as _cli
from uip_engine import official_uip as _official_uip


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
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
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
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    baseline_bytes = (fake_project / "Bad.xaml").read_bytes()
    project_json_baseline = (fake_project / "project.json").read_bytes()
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
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
    reverte XAML/config modificado (engine NUNCA deixa workflow pior) → loop sai
    gracefully, EXIT_OK.

    Atualizado 2026-05-27: pré-fix esse caso simplesmente abortava com
    'rollback inexequível'. Novo comportamento (B2 fix): granular falha →
    fallback restaura TODO XAML divergente do snapshot. Pilot regression:
    sem fallback, engine deixava 3 XAMLs com duplicate Property injection.
    """
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    baseline_bytes = (fake_project / "Bad.xaml").read_bytes()
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
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
    # Bad.xaml restaurado pra estado pré-loop (engine NUNCA deixa workflow pior)
    assert (fake_project / "Bad.xaml").read_bytes() == baseline_bytes


def test_gate_empty_filepath_triggers_full_snapshot_rollback(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """REGRESSION (pilot contestacao-de-compras 2026-05-27): analyzer reporta
    error PROJECT-LEVEL (FilePath vazio no envelope do analyzer → AnalyzerIssue.file = "").
    Pré-fix: err_files = {""}, granular filter nunca casa, rollback inexequível,
    engine deixa projeto com regressões aplicadas. Fix B2: FULL-SNAPSHOT
    fallback ativa quando granular não restaura nada AND existem new errors.
    """
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    baseline_bytes = (fake_project / "Bad.xaml").read_bytes()
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
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


def test_full_snapshot_rollback_preserves_project_metadata_pins(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Project-level analyzer regressions must not undo dependency fixes.

    This emulates a deterministic D-2/project.json pin fix followed by an
    analyzer error with empty FilePath. The XAML fallback should restore XAML
    bytes, but the dependency metadata must remain available to restore/pack
    gates instead of being reverted to stale pins.
    """
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    baseline_bytes = (fake_project / "Bad.xaml").read_bytes()
    project_json = fake_project / "project.json"
    fixed_project_json = """{
  "name": "test",
  "studioVersion": "23.10.13",
  "targetFramework": "Windows",
  "expressionLanguage": "VisualBasic",
  "dependencies": {
    "UiPath.System.Activities": "[25.4.4]"
  }
}
"""
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
        call_log.append("run")
        if len(call_log) == 1:
            return set()
        project_json.write_text(fixed_project_json, encoding="utf-8")
        return {_make_issue("", "ST-PROJECT-LEVEL", "Error",
                            "Não foi possível realizar análise")}

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "FULL-SNAPSHOT rollback" in out
    assert (fake_project / "Bad.xaml").read_bytes() == baseline_bytes
    assert project_json.read_text(encoding="utf-8") == fixed_project_json


def test_granular_rollback_preserves_project_metadata_pins(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Analyzer FilePath=project.json must not revert deterministic pins."""
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    project_json = fake_project / "project.json"
    fixed_project_json = """{
  "name": "test",
  "studioVersion": "23.10.13",
  "targetFramework": "Windows",
  "expressionLanguage": "VisualBasic",
  "dependencies": {
    "UiPath.System.Activities": "[25.4.4]"
  }
}
"""
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
        call_log.append("run")
        if len(call_log) == 1:
            return set()
        project_json.write_text(fixed_project_json, encoding="utf-8")
        return {_make_issue("project.json", "ST-PROJECT-JSON", "Error",
                            "Analyze failed")}

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "preservando metadata em rollback granular" in out
    assert project_json.read_text(encoding="utf-8") == fixed_project_json


def test_cli_assembly_missing_does_not_full_snapshot_rollback_xamls(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Official CLI dependency/restore infra errors must not undo XAML fixes."""
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    baseline_bytes = (fake_project / "Bad.xaml").read_bytes()
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
        call_log.append("run")
        if len(call_log) == 1:
            return set()
        return {
            _make_issue(
                "project.json",
                "CLI_ASSEMBLY_MISSING",
                "Error",
                "official uip rpa analyze cannot load assembly "
                "'Microsoft.VisualStudio.Services.Common'",
            )
        }

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "metadata/infra-only" in out
    assert "granular rollback inexequível" not in out
    assert (fake_project / "Bad.xaml").read_bytes() != baseline_bytes


def test_full_snapshot_rollback_preserves_reference_only_xaml_delta(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Fallback rollback must not undo W-11/ENV ref/import-only fixes.

    When analyzer reports a project-level error with no FilePath, the engine
    cannot know the culprit. It should still roll back functional XAML changes,
    but preserve XAMLs whose only delta is TextExpression refs/imports so those
    deterministic blockers do not reappear in PHASE 2.
    """
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    refs = fake_project / "RefsOnly.xaml"
    refs.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="RefsOnly" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:sco="clr-namespace:System.Collections.ObjectModel;assembly=System.ObjectModel"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <TextExpression.ReferencesForImplementation>
    <sco:Collection x:TypeArguments="AssemblyReference">
      <AssemblyReference>System</AssemblyReference>
    </sco:Collection>
  </TextExpression.ReferencesForImplementation>
  <Sequence />
</Activity>
""",
        encoding="utf-8",
    )
    bad_baseline = (fake_project / "Bad.xaml").read_bytes()
    refs_baseline = refs.read_text(encoding="utf-8")
    refs_fixed = refs_baseline.replace(
        "      <AssemblyReference>System</AssemblyReference>\n",
        "      <AssemblyReference>System</AssemblyReference>\n"
        "      <AssemblyReference>System.Security</AssemblyReference>\n",
    )
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
        call_log.append("run")
        if len(call_log) == 1:
            return set()
        refs.write_text(refs_fixed, encoding="utf-8")
        return {_make_issue("", "ST-PROJECT-LEVEL", "Error",
                            "Não foi possível realizar análise")}

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "FULL-SNAPSHOT rollback" in out
    assert "preservando refs/imports" in out
    assert (fake_project / "Bad.xaml").read_bytes() == bad_baseline
    assert refs.read_text(encoding="utf-8") == refs_fixed


def test_granular_rollback_preserves_current_refs_imports(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Per-file rollback should keep W-11/ENV blocks from current XAML."""
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    bad = fake_project / "Bad.xaml"
    bad.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Foo" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:sco="clr-namespace:System.Collections.ObjectModel;assembly=System.ObjectModel"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members />
  <TextExpression.ReferencesForImplementation>
    <sco:Collection x:TypeArguments="AssemblyReference">
      <AssemblyReference>System</AssemblyReference>
    </sco:Collection>
  </TextExpression.ReferencesForImplementation>
  <Sequence />
</Activity>
""",
        encoding="utf-8",
    )
    baseline_text = bad.read_text(encoding="utf-8")
    current_ref = "      <AssemblyReference>System.Security</AssemblyReference>\n"
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
        call_log.append("run")
        if len(call_log) == 1:
            return set()
        current = bad.read_text(encoding="utf-8")
        if "System.Security" not in current:
            current = current.replace(
                "      <AssemblyReference>System</AssemblyReference>\n",
                "      <AssemblyReference>System</AssemblyReference>\n"
                + current_ref,
            )
            bad.write_text(current, encoding="utf-8")
        if len(call_log) > 2:
            return set()
        return {_make_issue("Bad.xaml", "ST-FAKE-001", "Error")}

    monkeypatch.setattr(_analyzer, "run_analyzer", fake_run)

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out
    after = bad.read_text(encoding="utf-8")

    assert rc == _cli.EXIT_OK
    assert "rollback preservou refs/imports" in out
    assert current_ref.strip() in after
    assert "<x:Members />" in after
    assert after != baseline_text


def test_diff_new_issues_suppresses_existing_project_level_analyze_halt():
    baseline = {
        _analyzer.AnalyzerIssue(
            file="",
            error_code="ANALYZE_HALT",
            severity="Error",
            description="Analyze failed: old compiler halt",
        )
    }
    post = {
        _analyzer.AnalyzerIssue(
            file="",
            error_code="ANALYZE_HALT",
            severity="Error",
            description="Analyze failed: different compiler halt",
        )
    }

    assert _analyzer.diff_new_issues(baseline, post) == set()


def test_gate_empty_filepath_with_xaml_description_rolls_back_granular(
    fake_project: Path, monkeypatch, capsys, disable_baseline_cache
):
    """Studio sometimes leaves FilePath empty but includes the XAML path in
    Description. Analyzer parsing should infer the basename so the gate rolls
    back only the failing file, not every changed XAML in the project.
    """
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
    )

    other = fake_project / "Other.xaml"
    other.write_text(SAMPLE_BAD_XAML.replace("Foo", "Other"), encoding="utf-8")
    bad_baseline = (fake_project / "Bad.xaml").read_bytes()
    other_baseline = other.read_bytes()
    call_log: list = []

    def fake_run(project_root, *args, **kwargs):
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
        _official_uip, "discover_official_uip", lambda: Path("fake/uip.cmd")
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


def test_no_analyzer_cli_found_skips_gate(
    fake_project: Path, monkeypatch, capsys
):
    """Sem official uip instalado, o baseline do fix é pulado."""
    monkeypatch.setattr(
        _official_uip, "discover_official_uip", lambda: None
    )
    monkeypatch.setattr(
        "uip_engine.official_uip.discover_official_uip", lambda: None
    )

    rc = _cli._cmd_fix(_mk_fix_args(fake_project))
    out = capsys.readouterr().out

    assert rc == _cli.EXIT_OK
    assert "official uip" in out
    assert "Skipping baseline" in out
    assert "ANALYZER REGRESSION" not in out
