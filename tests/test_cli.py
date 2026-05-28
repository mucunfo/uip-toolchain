import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_cli_help_runs():
    proc = subprocess.run(
        [sys.executable, "-m", "uip_engine.cli", "--help"],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0
    assert "review" in proc.stdout.lower()


def test_cli_review_empty_rules_returns_zero(tmp_path):
    proj = tmp_path / "Proj"
    proj.mkdir()
    (proj / "project.json").write_text(
        '{"studioVersion":"23.10.13","targetFramework":"Windows",'
        '"runtimeOptions":{"mustRestoreAllDependencies":true}}'
    )
    (proj / "Foo.xaml").write_text("<Activity/>")

    rules_file = tmp_path / "empty_rules.yaml"
    rules_file.write_text("version: 1\nrules: []\n")

    proc = subprocess.run(
        [sys.executable, "-m", "uip_engine.cli", "review",
         str(proj), "--rules-file", str(rules_file)],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0


def test_cli_review_format_json(tmp_path):
    proj = tmp_path / "Proj"
    proj.mkdir()
    (proj / "project.json").write_text(
        '{"studioVersion":"23.10.13","targetFramework":"Windows",'
        '"runtimeOptions":{"mustRestoreAllDependencies":true}}'
    )
    (proj / "Foo.xaml").write_text("<Activity/>")

    rules_file = tmp_path / "empty_rules.yaml"
    rules_file.write_text("version: 1\nrules: []\n")

    proc = subprocess.run(
        [sys.executable, "-m", "uip_engine.cli", "review",
         str(proj), "--rules-file", str(rules_file), "--format", "json"],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert "summary" in out
    assert out["summary"]["files_scanned"] >= 0
    assert "findings" in out


def test_cli_validate_command_checks_schema(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\nrules:\n  - id: X-99\n")  # missing required fields

    proc = subprocess.run(
        [sys.executable, "-m", "uip_engine.cli", "validate",
         "--rules-file", str(bad)],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert proc.returncode >= 10  # internal error range
