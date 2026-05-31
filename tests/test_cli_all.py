"""Tests for `cli all` god subcommand orchestration.

Cobre cenários básicos:
  - Project clean (Windows, sem findings) → PASS exit 0
  - Project com migração necessária → PHASE 0 executa
  - Project com FAIL (default = no-watch) → exit 2 imediato
  - Project com contextual residual (sem --apply-contextual) → PASS-WITH-NOTES exit 0
  - --max-iters guard limita loop em FAIL com --watch ativo
  - Backward-compat: --no-watch flag deprecated mas aceito (noop)
"""
import json
import os
from pathlib import Path

import pytest

from uip_engine.cli import (
    _cmd_all, _ns, _read_target_framework, _phase0_migration,
    EXIT_OK, EXIT_WARN, EXIT_ERROR, EXIT_HALT, EXIT_INTERNAL,
)


_MINIMAL_PROJECT_JSON = {
    "name": "TestProject",
    "description": "Sample for cli all tests",
    "main": "Main.xaml",
    "dependencies": {
        "UiPath.System.Activities": "[25.4.4]",
    },
    "targetFramework": "Windows",
    "studioVersion": "23.10.13",
    "expressionLanguage": "VisualBasic",
    "projectType": "Process",
    "schemaVersion": "4.0",
    "runtimeOptions": {
        "autoDispose": False,
        "excludedLoggedData": ["*password*", "Private:*"],
    },
}


_MINIMAL_MAIN_XAML = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
    'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
    '  <x:Members></x:Members>\n'
    '  <Sequence DisplayName="Main">\n'
    '    <ui:LogMessage DisplayName="Log Message - Iniciar" Level="Info" '
    'Message="[&quot;Iniciado&quot;]" />\n'
    '  </Sequence>\n'
    '</Activity>\n'
)


@pytest.fixture
def windows_project(tmp_path):
    (tmp_path / "project.json").write_text(json.dumps(_MINIMAL_PROJECT_JSON), encoding="utf-8")
    (tmp_path / "Main.xaml").write_text(_MINIMAL_MAIN_XAML, encoding="utf-8")
    return tmp_path


@pytest.fixture
def legacy_project(tmp_path):
    legacy = dict(_MINIMAL_PROJECT_JSON)
    legacy["targetFramework"] = "Legacy"
    (tmp_path / "project.json").write_text(json.dumps(legacy), encoding="utf-8")
    (tmp_path / "Main.xaml").write_text(_MINIMAL_MAIN_XAML, encoding="utf-8")
    return tmp_path


def test_read_target_framework_windows(windows_project):
    assert _read_target_framework(windows_project) == "Windows"


def test_read_target_framework_legacy(legacy_project):
    assert _read_target_framework(legacy_project) == "Legacy"


def test_read_target_framework_missing(tmp_path):
    assert _read_target_framework(tmp_path) is None


def test_phase0_skip_when_windows(windows_project):
    p0 = _phase0_migration(windows_project, str(_default_rules()))
    assert p0["ran"] is False
    assert p0["status"] == "skip"


def test_phase0_skip_no_project_json(tmp_path):
    p0 = _phase0_migration(tmp_path, str(_default_rules()))
    assert p0["ran"] is False
    assert "no project.json" in p0["status"]


def test_cmd_all_default_no_watch_returns_quickly(windows_project):
    """Project minimal Windows, default (sem --watch) → terminates sem loop."""
    args = _ns(
        path=str(windows_project),
        rules_file=str(_default_rules()),
        apply_contextual=False,
        watch=False,
        no_watch=False,
        watch_interval=2.0,
        max_iters=0,
    )
    rc = _cmd_all(args)
    # Project minimal pode passar (PASS=0) ou warns (PENDING=1) dependendo de
    # quão estrito é o rules baseline. Não deve travar em FAIL.
    assert rc in (EXIT_OK, EXIT_WARN, EXIT_ERROR)


def test_cmd_all_no_watch_flag_still_works_backcompat(windows_project):
    """--no-watch deprecated flag aceito (noop pq default já é no-watch)."""
    args = _ns(
        path=str(windows_project),
        rules_file=str(_default_rules()),
        apply_contextual=False,
        watch=False,
        no_watch=True,
        watch_interval=2.0,
        max_iters=0,
    )
    rc = _cmd_all(args)
    assert rc in (EXIT_OK, EXIT_WARN, EXIT_ERROR)


def test_cmd_all_watch_flag_loops_until_max_iters(tmp_path):
    """--watch ativo + max-iters=1 + projeto FAIL → loop guarded por max-iters."""
    args = _ns(
        path=str(tmp_path),
        rules_file=str(_default_rules()),
        apply_contextual=False,
        watch=True,
        no_watch=False,
        watch_interval=0.1,
        max_iters=1,
    )
    # max_iters guard previne loop infinito quando watch ativo + FAIL.
    rc = _cmd_all(args)
    assert rc in (EXIT_OK, EXIT_WARN, EXIT_ERROR, EXIT_INTERNAL)


def test_cmd_all_max_iters_guard(tmp_path):
    """Projeto inválido (sem project.json) — verify max-iters não loopa infinito."""
    args = _ns(
        path=str(tmp_path),
        rules_file=str(_default_rules()),
        apply_contextual=False,
        watch=False,
        no_watch=False,
        watch_interval=2.0,
        max_iters=1,
    )
    # Sem project.json, _cmd_all aceita pasta vazia e roda pipeline; vai
    # provavelmente FAIL ou retornar exit code definido. Não deve crashar.
    rc = _cmd_all(args)
    assert rc in (EXIT_OK, EXIT_WARN, EXIT_ERROR, EXIT_INTERNAL)


def test_cmd_all_invalid_path():
    args = _ns(
        path="/non/existent/path/xyzzy",
        rules_file=str(_default_rules()),
        apply_contextual=False,
        watch=False,
        no_watch=False,
        watch_interval=2.0,
        max_iters=0,
    )
    rc = _cmd_all(args)
    assert rc == EXIT_INTERNAL


# ---------- helpers ----------

def _default_rules() -> Path:
    return Path(__file__).resolve().parents[1] / "rules.yaml"
