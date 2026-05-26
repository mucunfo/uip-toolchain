"""Tests for cli fix + phase-out subcommands."""
from pathlib import Path
import subprocess
import sys
import shutil
import pytest

ROOT = Path(__file__).resolve().parent.parent


SAMPLE_BAD_XAML = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Foo" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:s="clr-namespace:System;assembly=mscorlib"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members />
  <Sequence>
    <ui:Assign DisplayName="bad" />
  </Sequence>
</Activity>
"""

SAMPLE_GOOD_PROJECT_JSON = """{
  "name": "test",
  "studioVersion": "23.10.13",
  "targetFramework": "Windows",
  "expressionLanguage": "VisualBasic"
}
"""


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    p = tmp_path / "Proj"
    p.mkdir()
    (p / "project.json").write_text(SAMPLE_GOOD_PROJECT_JSON, encoding="utf-8")
    (p / "Bad.xaml").write_text(SAMPLE_BAD_XAML, encoding="utf-8")
    return p


def _run_cli(*args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, "-m", "uip_engine.cli", *args],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )


def test_fix_dry_run_no_change(fake_project):
    original = (fake_project / "Bad.xaml").read_text(encoding="utf-8")
    proc = _run_cli("fix", str(fake_project))
    assert proc.returncode == 0, proc.stderr
    assert "would-fix" in proc.stdout
    assert (fake_project / "Bad.xaml").read_text(encoding="utf-8") == original


def test_fix_apply_writes(fake_project):
    original = (fake_project / "Bad.xaml").read_text(encoding="utf-8")
    proc = _run_cli("fix", str(fake_project), "--apply")
    assert proc.returncode == 0, proc.stderr
    after = (fake_project / "Bad.xaml").read_text(encoding="utf-8")
    assert after != original
    # S-1 fix: <x:Members /> → <x:Members></x:Members>
    assert "<x:Members></x:Members>" in after
    assert "<x:Members />" not in after


def test_fix_idempotent(fake_project):
    proc1 = _run_cli("fix", str(fake_project), "--apply")
    after_first = (fake_project / "Bad.xaml").read_text(encoding="utf-8")
    proc2 = _run_cli("fix", str(fake_project), "--apply")
    after_second = (fake_project / "Bad.xaml").read_text(encoding="utf-8")
    assert after_first == after_second, "fix is not idempotent"
    assert "applied=0" in proc2.stdout, "second pass should be no-op"


def test_fix_filter_rules(fake_project):
    # --rules S-1 deve só aplicar S-1 (não S-3)
    original = (fake_project / "Bad.xaml").read_text(encoding="utf-8")
    proc = _run_cli("fix", str(fake_project), "--apply", "--rules", "S-1")
    after = (fake_project / "Bad.xaml").read_text(encoding="utf-8")
    assert "<x:Members></x:Members>" in after  # S-1 applied
    assert "<ui:Assign" in after  # S-3 NOT applied (no fix.mechanical anyway, ok)


def test_phase_out_dry_run_no_change():
    rules_file = ROOT / "rules.yaml"
    original = rules_file.read_text(encoding="utf-8")
    proc = _run_cli("phase-out", "windows-only")
    assert proc.returncode == 0, proc.stderr
    assert rules_file.read_text(encoding="utf-8") == original
    assert "Dry-run" in proc.stdout


def test_phase_out_apply(tmp_path: Path):
    # Use isolated copy of rules.yaml
    src = ROOT / "rules.yaml"
    dst = tmp_path / "rules.yaml"
    shutil.copy(src, dst)
    proc = _run_cli("phase-out", "windows-only", "--apply",
                    "--rules-file", str(dst))
    assert proc.returncode == 0, proc.stderr
    after = dst.read_text(encoding="utf-8")
    # W-3, W-10, W-12, W-16, W-17 devem virar target: all
    # Spot check: a regra W-3 não pode mais ter target: windows na sua linha
    import re
    rule_w3_idx = after.find("- id: W-3\n")
    assert rule_w3_idx > 0
    block = after[rule_w3_idx:rule_w3_idx + 500]
    assert "target: all" in block
    assert "target: windows" not in block

    # W-1 deve continuar windows
    rule_w1_idx = after.find("- id: W-1\n")
    block_w1 = after[rule_w1_idx:rule_w1_idx + 500]
    assert "target: windows" in block_w1


def test_phase_out_idempotent(tmp_path: Path):
    src = ROOT / "rules.yaml"
    dst = tmp_path / "rules.yaml"
    shutil.copy(src, dst)
    _run_cli("phase-out", "windows-only", "--apply", "--rules-file", str(dst))
    proc2 = _run_cli("phase-out", "windows-only", "--rules-file", str(dst))
    assert "Nada para universalizar" in proc2.stdout
