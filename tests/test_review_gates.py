"""Review gate wiring for the modern official-`uip` contract."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from uip_engine import cli as cli_mod  # noqa: E402
from uip_engine._types import Finding, Severity  # noqa: E402
from uip_engine.official_uip import OfficialUipResult  # noqa: E402


def _make_project(tmp_path: Path) -> Path:
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


class _ReviewArgs:
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
        self.build_gate_timeout = 60
        self.pack_gate_timeout = 60


def test_review_no_analyzer_gate_flag_deprecated_warning(tmp_path):
    proj = _make_project(tmp_path)
    rules_file = tmp_path / "empty_rules.yaml"
    rules_file.write_text("version: 1\nrules: []\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable, "-m", "uip_engine.cli", "review",
            str(proj), "--rules-file", str(rules_file),
            "--no-analyzer-gate", "--format", "json",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )

    assert "deprecated and ignored" in proc.stderr.lower()


def test_review_runs_official_restore_analyzer_build_and_pack(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", raising=False)

    proj = _make_project(tmp_path)
    rf = tmp_path / "empty_rules.yaml"
    rf.write_text("version: 1\nrules: []\n", encoding="utf-8")

    invoked = {"restore": False, "analyzer": False, "build": False, "pack": False}

    def _stub_restore(*a, **kw):
        invoked["restore"] = True
        return True, False

    def _mark(name):
        def _inner(*a, **kw):
            invoked[name] = True
        return _inner

    args = _ReviewArgs(str(proj), str(rf))

    with patch.object(cli_mod, "_run_official_restore_gate", side_effect=_stub_restore), \
         patch.object(cli_mod, "_inject_analyzer_findings", side_effect=_mark("analyzer")), \
         patch.object(cli_mod, "_run_official_build_gate", side_effect=_mark("build")), \
         patch.object(cli_mod, "_run_pack_gate", side_effect=_mark("pack")):
        rc = cli_mod._cmd_review(args)

    assert invoked == {"restore": True, "analyzer": True, "build": True, "pack": True}
    assert rc == cli_mod.EXIT_OK


def test_review_exit_error_when_pack_gate_adds_error(tmp_path, monkeypatch):
    monkeypatch.delenv("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", raising=False)

    proj = _make_project(tmp_path)
    rf = tmp_path / "empty_rules.yaml"
    rf.write_text("version: 1\nrules: []\n", encoding="utf-8")

    def _stub_pack(result, project_path, **kw):
        result.add(Finding(
            rule_id="UIPATH:PACK",
            severity=Severity.ERROR,
            category="breaking",
            file="Foo.xaml",
            line=0,
            message="BC30002: fake error",
        ))

    args = _ReviewArgs(str(proj), str(rf))

    with patch.object(cli_mod, "_run_official_restore_gate", return_value=(True, False)), \
         patch.object(cli_mod, "_inject_analyzer_findings"), \
         patch.object(cli_mod, "_run_official_build_gate"), \
         patch.object(cli_mod, "_run_pack_gate", side_effect=_stub_pack):
        rc = cli_mod._cmd_review(args)

    assert rc == cli_mod.EXIT_ERROR


def test_build_gate_reports_fallback_error_without_name_error(tmp_path):
    proj = _make_project(tmp_path)
    result = cli_mod.ValidationResult()
    fake_result = OfficialUipResult(
        argv=["uip", "rpa", "build"],
        returncode=1,
        stdout="",
        stderr="plain build failure",
        envelope=None,
    )

    with patch.object(cli_mod, "_check_official_uip_compatibility", return_value=True), \
         patch.object(cli_mod, "_parse_pack_output_and_inject", return_value=0), \
         patch("uip_engine.official_uip.discover_official_uip", return_value=Path("uip.cmd")), \
         patch("uip_engine.official_uip.run_official_uip", return_value=fake_result), \
         patch("uip_engine.official_uip.iter_analyzer_records", return_value=[]), \
         patch("uip_engine.official_uip.diagnose_official_uip_failure", return_value=[]):
        cli_mod._run_official_build_gate(result, str(proj))

    assert result.error_count == 1
    assert result.findings[0].rule_id == "UIPATH:BUILD"
    assert "official uip rpa build returned exit 1" in result.findings[0].message


def test_review_restore_block_skips_analyzer_build_and_pack(tmp_path, monkeypatch):
    monkeypatch.delenv("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", raising=False)

    proj = _make_project(tmp_path)
    rf = tmp_path / "empty_rules.yaml"
    rf.write_text("version: 1\nrules: []\n", encoding="utf-8")
    invoked = {"analyzer": False, "build": False, "pack": False}

    def _stub_restore(result, project_root, **kw):
        result.add(Finding(
            rule_id="UIPATH:RESTORE_PACKAGE_MISSING",
            severity=Severity.ERROR,
            category="breaking",
            file="project.json",
            line=0,
            message="missing package",
        ))
        return True, True

    def _mark(name):
        def _inner(*a, **kw):
            invoked[name] = True
        return _inner

    args = _ReviewArgs(str(proj), str(rf))

    with patch.object(cli_mod, "_run_official_restore_gate", side_effect=_stub_restore), \
         patch.object(cli_mod, "_inject_analyzer_findings", side_effect=_mark("analyzer")), \
         patch.object(cli_mod, "_run_official_build_gate", side_effect=_mark("build")), \
         patch.object(cli_mod, "_run_pack_gate", side_effect=_mark("pack")):
        rc = cli_mod._cmd_review(args)

    assert rc == cli_mod.EXIT_ERROR
    assert invoked == {"analyzer": False, "build": False, "pack": False}


def test_review_publish_readiness_precondition_skips_external_gates(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", raising=False)

    proj = _make_project(tmp_path)
    rf = tmp_path / "j9_rules.yaml"
    rf.write_text(
        """
version: 1
rules:
  - id: J-9
    severity: ERROR
    category: breaking
    target: all
    title: project.uiproj synced
    description: descriptor required
    applies_to:
      include: ["project.json"]
    detect:
      type: python
      params:
        module: uip_engine.heuristics.project_manifest
        function: detect_j9_project_uiproj_synced
    fix:
      apply_class: deterministic
      mechanical:
        type: sync_project_uiproj
      prose: sync
""",
        encoding="utf-8",
    )
    invoked = {"restore": False, "analyzer": False, "build": False, "pack": False}

    def _mark(name):
        def _inner(*a, **kw):
            invoked[name] = True
            if name == "restore":
                return True, False
            return None
        return _inner

    args = _ReviewArgs(str(proj), str(rf))

    with patch.object(cli_mod, "_run_official_restore_gate", side_effect=_mark("restore")), \
         patch.object(cli_mod, "_inject_analyzer_findings", side_effect=_mark("analyzer")), \
         patch.object(cli_mod, "_run_official_build_gate", side_effect=_mark("build")), \
         patch.object(cli_mod, "_run_pack_gate", side_effect=_mark("pack")):
        rc = cli_mod._cmd_review(args)

    assert rc == cli_mod.EXIT_ERROR
    assert invoked == {"restore": False, "analyzer": False, "build": False, "pack": False}
