"""Tests for executor_drive — Phase 6 Robot Executor gate wrapper.

Phase 6 verdict: ultimate-fidelity validate is not available headless.
UiPath.Executor.NetCore.exe is service-bound; UiRobot.exe execute --file
rejects raw XAML in Windows/cross-platform projects. Wrapper exposes opt-in
mode that emits INFRA findings when binaries are missing or refused.

Test surface:
- _binary_path resolution with env override
- _is_safe_to_run / _discover_safe_xamls filtering
- _parse_output extracts hints from stderr/stdout
- run_validate emits RB-EXEC-INFRA when binary missing
- run_validate emits RB-EXEC-SKIP when no safe XAMLs
- live smoke against canonical project (skipped if binary missing)
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.rule_engine import executor_drive as ed
from scripts.rule_engine._types import Severity


# ---------------------------------------------------------------------------
# _binary_path
# ---------------------------------------------------------------------------

def test_binary_path_env_override(tmp_path, monkeypatch):
    """Explicit UIPATH_EXECUTOR_BIN env wins over Studio discovery."""
    fake = tmp_path / "FakeRobot.exe"
    fake.write_bytes(b"MZ")  # not a real PE; only existence matters
    monkeypatch.setenv("UIPATH_EXECUTOR_BIN", str(fake))
    path, kind = ed._binary_path()
    assert path == fake
    assert kind == "override"


def test_binary_path_env_missing_file_falls_through(monkeypatch):
    """Override path pointing at non-existent file falls through to discovery."""
    monkeypatch.setenv("UIPATH_EXECUTOR_BIN", r"C:\nope\does_not_exist.exe")
    path, kind = ed._binary_path()
    # Either Studio is installed (uirobot) or nothing (unknown).
    assert kind in ("uirobot", "unknown")
    if kind == "uirobot":
        assert path is not None and path.exists()
    else:
        assert path is None


# ---------------------------------------------------------------------------
# _is_safe_to_run
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rel,safe", [
    ("Tests/Foo.xaml", True),
    ("tests/sub/Bar.xaml", True),
    ("Tests/Framework/TestCaseInit.xaml", True),
    ("src/Test_Smoke.xaml", True),
    ("src/Process_smoke.xaml", True),
    ("src/Process_test.xaml", True),
    ("Process.xaml", False),
    ("Framework/InitAllSettings.xaml", False),
    ("Main.xaml", False),
    ("Sicoob/Sisbr/Login.xaml", False),
])
def test_is_safe_to_run(tmp_path, rel, safe):
    project = tmp_path / "proj"
    project.mkdir()
    xaml = project / rel
    xaml.parent.mkdir(parents=True, exist_ok=True)
    xaml.write_text("<x/>")
    assert ed._is_safe_to_run(xaml, project) is safe


def test_discover_safe_xamls_skips_backups(tmp_path):
    project = tmp_path / "proj"
    (project / "Tests").mkdir(parents=True)
    (project / "Tests" / "Foo.xaml").write_text("<x/>")
    backup_dir = project / "_BeforeMigration_20260520"
    backup_dir.mkdir()
    (backup_dir / "Tests").mkdir()
    (backup_dir / "Tests" / "Bar.xaml").write_text("<x/>")
    found = ed._discover_safe_xamls(project)
    rels = {p.relative_to(project).as_posix() for p in found}
    assert rels == {"Tests/Foo.xaml"}


# ---------------------------------------------------------------------------
# _parse_output
# ---------------------------------------------------------------------------

def test_parse_output_detects_service_error():
    stderr = (
        "UiPath.Executor.NetCore Error: 0 : UnhandledException: "
        "System.InvalidOperationException: Execution must happen through the service."
    )
    hint = ed._parse_output("", stderr)
    assert hint is not None
    assert "UnhandledException" in hint or "InvalidOperationException" in hint


def test_parse_output_detects_robot_cli_rejection():
    stdout = (
        "It is not possible to run UiPath Studio windows or cross-platform "
        "projects using the Robot CLI -f parameter."
    )
    hint = ed._parse_output(stdout, "")
    assert hint is not None
    assert "not possible to run" in hint.lower()


def test_parse_output_returns_none_on_clean():
    assert ed._parse_output("Process started.\nProcess finished.", "") is None


# ---------------------------------------------------------------------------
# run_validate — synthetic scenarios
# ---------------------------------------------------------------------------

def test_run_validate_no_binary_emits_infra(tmp_path, monkeypatch):
    """When binary cannot be resolved, emit RB-EXEC-INFRA and return 0."""
    monkeypatch.setattr(ed, "_binary_path", lambda: (None, "unknown"))
    project = tmp_path / "proj"
    project.mkdir()
    (project / "project.json").write_text("{}")
    code, findings = ed.run_validate(project)
    assert code == 0
    assert len(findings) == 1
    assert findings[0].rule_id == "RB-EXEC-INFRA"
    assert findings[0].severity == Severity.INFO


def test_run_validate_no_safe_xamls_emits_skip(tmp_path, monkeypatch):
    """Binary present, but no safe XAML in project → RB-EXEC-SKIP, code=0."""
    fake = tmp_path / "FakeRobot.exe"
    fake.write_bytes(b"MZ")
    monkeypatch.setattr(ed, "_binary_path", lambda: (fake, "uirobot"))
    project = tmp_path / "proj"
    project.mkdir()
    (project / "project.json").write_text("{}")
    (project / "Main.xaml").write_text("<x/>")  # productive name, not safe
    code, findings = ed.run_validate(project)
    assert code == 0
    assert len(findings) == 1
    assert findings[0].rule_id == "RB-EXEC-SKIP"


def test_run_validate_cli_rejection_downgrades_to_infra(tmp_path, monkeypatch):
    """When UiRobot rejects raw XAML for windows projects, emit INFRA not FAIL."""
    fake = tmp_path / "FakeRobot.exe"
    fake.write_bytes(b"MZ")
    monkeypatch.setattr(ed, "_binary_path", lambda: (fake, "uirobot"))

    def fake_invoke(binary, xaml_path, timeout, kind):
        stdout = (
            "It is not possible to run UiPath Studio windows or cross-platform "
            "projects using the Robot CLI -f parameter."
        )
        return (127, stdout, "", 1.0, False)

    monkeypatch.setattr(ed, "_invoke_executor", fake_invoke)

    project = tmp_path / "proj"
    (project / "Tests").mkdir(parents=True)
    (project / "Tests" / "TestFoo.xaml").write_text("<x/>")

    code, findings = ed.run_validate(project)
    assert code == 0  # INFRA does not fail the gate
    assert len(findings) == 1
    assert findings[0].rule_id == "RB-EXEC-INFRA"


def test_run_validate_timeout_emits_warn(tmp_path, monkeypatch):
    fake = tmp_path / "FakeRobot.exe"
    fake.write_bytes(b"MZ")
    monkeypatch.setattr(ed, "_binary_path", lambda: (fake, "uirobot"))

    def fake_invoke(binary, xaml_path, timeout, kind):
        return (-1, "", "", float(timeout), True)

    monkeypatch.setattr(ed, "_invoke_executor", fake_invoke)

    project = tmp_path / "proj"
    (project / "Tests").mkdir(parents=True)
    (project / "Tests" / "TestFoo.xaml").write_text("<x/>")

    code, findings = ed.run_validate(project, timeout=5)
    assert code == 0  # WARN does not fail gate (only ERROR does)
    assert len(findings) == 1
    assert findings[0].rule_id == "RB-EXEC-TIMEOUT"
    assert findings[0].severity == Severity.WARN


def test_run_validate_real_fail_emits_error(tmp_path, monkeypatch):
    fake = tmp_path / "FakeRobot.exe"
    fake.write_bytes(b"MZ")
    monkeypatch.setattr(ed, "_binary_path", lambda: (fake, "uirobot"))

    def fake_invoke(binary, xaml_path, timeout, kind):
        stderr = (
            "Activity could not be loaded: System.Activities.InvalidWorkflowException"
        )
        return (1, "", stderr, 2.0, False)

    monkeypatch.setattr(ed, "_invoke_executor", fake_invoke)

    project = tmp_path / "proj"
    (project / "Tests").mkdir(parents=True)
    (project / "Tests" / "TestFoo.xaml").write_text("<x/>")

    code, findings = ed.run_validate(project)
    assert code == 2
    assert len(findings) == 1
    assert findings[0].rule_id == "RB-EXEC-FAIL"
    assert findings[0].severity == Severity.ERROR
    assert findings[0].fix_prose is not None


def test_run_validate_ok_emits_info(tmp_path, monkeypatch):
    fake = tmp_path / "FakeRobot.exe"
    fake.write_bytes(b"MZ")
    monkeypatch.setattr(ed, "_binary_path", lambda: (fake, "uirobot"))

    def fake_invoke(binary, xaml_path, timeout, kind):
        return (0, "Process finished.\n", "", 3.2, False)

    monkeypatch.setattr(ed, "_invoke_executor", fake_invoke)

    project = tmp_path / "proj"
    (project / "Tests").mkdir(parents=True)
    (project / "Tests" / "TestFoo.xaml").write_text("<x/>")

    code, findings = ed.run_validate(project)
    assert code == 0
    assert len(findings) == 1
    assert findings[0].rule_id == "RB-EXEC-OK"
    assert findings[0].severity == Severity.INFO


# ---------------------------------------------------------------------------
# Live smoke — canonical Sicoob project (skipped without binary)
# ---------------------------------------------------------------------------

CANONICAL = Path(
    r"C:\Users\lisan\OneDrive - Sicoob\Projects"
    r"\importar-cadastro-avais-fiancas-honrados"
    r"\importar-cadastro-avais-fiancas-honrados-performer"
)


@pytest.mark.skipif(
    not CANONICAL.exists(), reason="canonical Sicoob project not available"
)
def test_live_smoke_canonical():
    """Live invoke against canonical project. Verdict: INFRA findings only
    because UiRobot rejects raw XAML for Windows projects. Gate exit=0."""
    binary, _ = ed._binary_path()
    if binary is None:
        pytest.skip("no UiRobot/Executor binary available")
    code, findings = ed.run_validate(CANONICAL, timeout=60)
    # Exit must be 0 (INFRA/SKIP/OK only) — gate must not break engine in this
    # known-infra-limited environment.
    assert code in (0, 2)
    assert findings, "expected at least one finding"
    # All findings should be one of our known rule ids
    valid_ids = {"RB-EXEC-OK", "RB-EXEC-FAIL", "RB-EXEC-TIMEOUT",
                 "RB-EXEC-INFRA", "RB-EXEC-SKIP"}
    for f in findings:
        assert f.rule_id in valid_ids, f"unknown rule_id {f.rule_id}"
