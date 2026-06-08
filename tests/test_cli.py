import json
from pathlib import Path
import subprocess
import sys
import tomllib
import pytest
from uip_engine import cli

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


def test_cli_list_enforces_enterprise_rule_quality(tmp_path):
    bad = tmp_path / "bad-quality.yaml"
    bad.write_text(
        """
version: 1
rules:
  - id: X-99
    severity: ERROR
    category: breaking
    target: all
    title: Missing prose
    description: "Valid schema, bad enterprise quality."
    detect: {type: regex, pattern: "X"}
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "-m", "uip_engine.cli", "list",
         "--rules-file", str(bad)],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )

    assert proc.returncode == cli.EXIT_INTERNAL
    assert "RULE-QUALITY" in proc.stderr
    assert "missing fix.prose" in proc.stderr


def test_ccs_uip_public_help_only_documents_two_modes(capsys):
    rc = cli.ccs_uip_main(["--help"])

    out = capsys.readouterr().out
    assert rc == cli.EXIT_OK
    assert "ccs-uip <project_path> [--apply-contextual]" in out
    assert "ccs-uip <subcommand>" not in out
    assert "  uip <project_path>" not in out
    assert "`uip <project_path>`" not in out
    assert "python -m uip_engine.cli <subcommand>" in out


def test_ccs_uip_rejects_internal_subcommands(capsys):
    rc = cli.ccs_uip_main(["review", "C:/tmp/project"])

    captured = capsys.readouterr()
    assert rc == cli.EXIT_ERROR
    assert "não é interface pública" in captured.err
    assert "ccs-uip review" in captured.err
    assert "python -m uip_engine.cli review" in captured.err


def test_ccs_uip_path_injects_all(monkeypatch):
    calls = []

    def fake_main(argv):
        calls.append(argv)
        return cli.EXIT_OK

    monkeypatch.setattr(cli, "main", fake_main)
    monkeypatch.setenv("UIP_TOOLCHAIN_SKIP_DOCTOR", "1")

    rc = cli.ccs_uip_main(["C:/tmp/project", "--apply-contextual"])

    assert rc == cli.EXIT_OK
    assert calls == [["all", "C:/tmp/project", "--apply-contextual"]]


def test_public_console_script_reserves_uip_for_official_cli():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = metadata["project"]["scripts"]

    assert scripts["ccs-uip"] == "uip_engine.cli:ccs_uip_main"
    assert scripts["ccs-uip-publish"] == "uip_engine.publish_done:main"
    assert "uip" not in scripts
    assert "publish" not in scripts
    assert "ccs-uip-publish-dev" not in scripts
    assert "ccs-uip-publish-done" not in scripts
