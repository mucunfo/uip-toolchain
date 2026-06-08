import json
from pathlib import Path

import pytest

from uip_engine import cli
from uip_engine import analyzer
from uip_engine import official_uip
from uip_engine._types import Severity, ValidationResult


def test_parse_uip_envelope_success():
    payload = {
        "Result": "Success",
        "Code": "FolderList",
        "Data": [{"Name": "Shared"}],
    }

    envelope = official_uip.parse_uip_envelope(json.dumps(payload))

    assert envelope is not None
    assert envelope.ok
    assert envelope.code == "FolderList"
    assert envelope.data == [{"Name": "Shared"}]


def test_parse_uip_envelope_failure():
    payload = {
        "Result": "ValidationError",
        "Message": "Unknown option",
        "Instructions": "Run help",
    }

    envelope = official_uip.parse_uip_envelope(json.dumps(payload))

    assert envelope is not None
    assert not envelope.ok
    assert envelope.message == "Unknown option"
    assert envelope.instructions == "Run help"


def test_parse_uip_envelope_accepts_logs_around_json():
    stdout = (
        "Restoring UiPath.Studio.Helm.Windows@1.1.195 from NuGet...\n"
        '{"Result":"Failure","Message":"Pack failed","Instructions":"Check project"}\n'
        "[WARN] [Telemetry] flush timed out after 1000ms\n"
    )

    envelope = official_uip.parse_uip_envelope(stdout)

    assert envelope is not None
    assert not envelope.ok
    assert envelope.message == "Pack failed"
    assert envelope.instructions == "Check project"


def test_parse_uip_envelope_returns_none_for_non_json():
    assert official_uip.parse_uip_envelope("plain text") is None


def test_discover_official_uip_prefers_env(monkeypatch, tmp_path):
    cli = tmp_path / "uip.exe"
    cli.write_text("", encoding="utf-8")

    monkeypatch.setenv("UIPATH_UIP_CLI", str(cli))
    monkeypatch.setattr(official_uip.shutil, "which", lambda _: None)

    assert official_uip.discover_official_uip() == Path(cli)


def test_run_official_uip_requires_binary(monkeypatch):
    monkeypatch.delenv("UIPATH_UIP_CLI", raising=False)
    monkeypatch.setattr(official_uip.shutil, "which", lambda _: None)

    with pytest.raises(FileNotFoundError):
        official_uip.run_official_uip(["rpa", "analyze", "--help"])


def test_parse_semver_and_compatibility_contract():
    version = official_uip.parse_semver("1.1.0\n")

    assert version is not None
    assert version.line == "1.1.x"
    assert official_uip.compatibility_diagnostic(version) is None
    assert official_uip.compatibility_diagnostic(
        official_uip.OfficialUipVersion("0.9.0", 0, 9, 0)
    ).code == "CLI_VERSION_UNSUPPORTED"
    assert official_uip.compatibility_diagnostic(
        official_uip.OfficialUipVersion("2.0.0", 2, 0, 0)
    ).code == "CLI_VERSION_UNSUPPORTED"


def test_diagnose_official_uip_failure_assembly_missing():
    diagnostics = official_uip.diagnose_official_uip_failure(
        "Analyze failed: Could not load file or assembly 'NPOI, Culture=neutral'",
        "rpa analyze",
    )

    assert [d.code for d in diagnostics] == ["CLI_ASSEMBLY_MISSING"]
    assert "NPOI" in diagnostics[0].message


def test_diagnose_official_restore_package_missing():
    diagnostics = official_uip.diagnose_official_uip_failure(
        "NU1101: Unable to find package CCS_Controle. No packages exist with this id in source(s).",
        "rpa restore",
    )

    assert [d.code for d in diagnostics] == [
        "RESTORE_PACKAGE_MISSING",
        "RESTORE_FEED_UNAVAILABLE",
    ]
    assert "CCS_Controle" in diagnostics[0].message


def test_diagnose_official_analyze_required_package_missing():
    diagnostics = official_uip.diagnose_official_uip_failure(
        (
            "Analyze failed: In order to use this activity in this Studio "
            "version, please install the UiPath.CoreIPC package, version "
            "2.0.1 or higher."
        ),
        "rpa analyze",
    )

    assert [d.code for d in diagnostics] == ["CLI_REQUIRED_PACKAGE_MISSING"]
    assert "UiPath.CoreIpc" in diagnostics[0].message
    assert "[2.0.1]" in diagnostics[0].message


def test_diagnose_official_analyze_make_sure_package_installed():
    diagnostics = official_uip.diagnose_official_uip_failure(
        (
            "Please make sure you have the UiPath.ComputerVision.LocalServer "
            "package version 21.6 or higher installed in order to use local "
            "server mode."
        ),
        "rpa analyze",
    )

    assert [d.code for d in diagnostics] == ["CLI_REQUIRED_PACKAGE_MISSING"]
    assert "UiPath.ComputerVision.LocalServer" in diagnostics[0].message
    assert "21.6" in diagnostics[0].message


def _official_result(payload, returncode=0):
    stdout = json.dumps(payload)
    return official_uip.OfficialUipResult(
        argv=["uip", "rpa"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
        envelope=official_uip.parse_uip_envelope(stdout),
    )


def test_official_analyzer_gate_injects_records(monkeypatch, tmp_path):
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "project.json").write_text("{}", encoding="utf-8")

    payload = {
        "Result": "Error",
        "Data": [
            {
                "ErrorCode": "ST-MRD-002",
                "ErrorSeverity": "Error",
                "Description": "DisplayName default",
                "FilePath": str(project / "Main.xaml"),
            }
        ],
    }
    result = ValidationResult()
    fake_uip = tmp_path / "uip.cmd"
    fake_uip.write_text("", encoding="utf-8")

    monkeypatch.setattr(official_uip, "discover_official_uip", lambda: fake_uip)
    monkeypatch.setattr(
        official_uip,
        "get_official_uip_version",
        lambda _: official_uip.OfficialUipVersion("1.1.0", 1, 1, 0),
    )
    monkeypatch.setattr(official_uip, "run_official_uip", lambda *a, **k: _official_result(payload, 1))

    assert cli._inject_official_analyzer_findings(result, project, 10, False)

    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "UIPATH:ST-MRD-002"
    assert result.findings[0].severity == Severity.INFO


def test_review_analyzer_prefers_official_uip_without_legacy_uipcli(
    monkeypatch,
    tmp_path,
):
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "project.json").write_text("{}", encoding="utf-8")
    payload = {
        "Result": "Error",
        "Data": [
            {
                "ErrorCode": "ST-MRD-002",
                "ErrorSeverity": "Error",
                "Description": "DisplayName default",
                "FilePath": str(project / "Main.xaml"),
            }
        ],
    }
    result = ValidationResult()
    fake_uip = tmp_path / "uip.cmd"
    fake_uip.write_text("", encoding="utf-8")
    calls = []

    monkeypatch.setattr(analyzer, "discover_uipcli", lambda: None)
    monkeypatch.setattr(official_uip, "discover_official_uip", lambda: fake_uip)
    monkeypatch.setattr(
        official_uip,
        "get_official_uip_version",
        lambda _: official_uip.OfficialUipVersion("1.1.0", 1, 1, 0),
    )

    def fake_run(args, **kwargs):
        calls.append(args)
        return _official_result(payload, 1)

    monkeypatch.setattr(official_uip, "run_official_uip", fake_run)

    cli._inject_analyzer_findings(result, str(project), 10, False)

    assert calls
    assert calls[0][:2] == ["rpa", "analyze"]
    assert {finding.rule_id for finding in result.findings} == {"UIPATH:ST-MRD-002"}


def test_official_pack_gate_falls_back_to_pack_finding(monkeypatch, tmp_path):
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "Proj",
            "projectVersion": "1.0.0",
            "targetFramework": "Windows",
            "designOptions": {"outputType": "Process"},
        }),
        encoding="utf-8",
    )
    payload = {"Result": "Error", "Message": "Project has validation errors"}
    result = ValidationResult()
    fake_uip = tmp_path / "uip.cmd"
    fake_uip.write_text("", encoding="utf-8")
    calls = []

    monkeypatch.setattr(official_uip, "discover_official_uip", lambda: fake_uip)
    monkeypatch.setattr(
        official_uip,
        "get_official_uip_version",
        lambda _: official_uip.OfficialUipVersion("1.1.0", 1, 1, 0),
    )
    def fake_run(args, **kwargs):
        calls.append(args)
        return _official_result(payload, 1)

    monkeypatch.setattr(official_uip, "run_official_uip", fake_run)

    assert cli._run_official_pack_gate(result, project, 10, False)

    assert any(f.rule_id == "UIPATH:PACK" for f in result.findings)
    assert calls
    assert "--skip-analyze" in calls[0]
    assert Path(calls[0][2]) != project


def test_official_restore_gate_success(monkeypatch, tmp_path):
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "project.json").write_text("{}", encoding="utf-8")
    payload = {"Result": "Success", "Code": "Restore"}
    result = ValidationResult()
    fake_uip = tmp_path / "uip.cmd"
    fake_uip.write_text("", encoding="utf-8")

    monkeypatch.setattr(official_uip, "discover_official_uip", lambda: fake_uip)
    monkeypatch.setattr(
        official_uip,
        "get_official_uip_version",
        lambda _: official_uip.OfficialUipVersion("1.1.0", 1, 1, 0),
    )
    monkeypatch.setattr(
        official_uip,
        "run_official_uip",
        lambda *a, **k: _official_result(payload, 0),
    )

    handled, blocked = cli._run_official_restore_gate(result, project, 10, False)

    assert handled
    assert not blocked
    assert result.findings == []


def test_official_restore_gate_classifies_package_failure(monkeypatch, tmp_path):
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "project.json").write_text("{}", encoding="utf-8")
    payload = {
        "Result": "Error",
        "Message": "NU1101: Unable to find package CCS_Controle. No packages exist with this id in source(s).",
    }
    result = ValidationResult()
    fake_uip = tmp_path / "uip.cmd"
    fake_uip.write_text("", encoding="utf-8")

    monkeypatch.setattr(official_uip, "discover_official_uip", lambda: fake_uip)
    monkeypatch.setattr(
        official_uip,
        "get_official_uip_version",
        lambda _: official_uip.OfficialUipVersion("1.1.0", 1, 1, 0),
    )
    monkeypatch.setattr(
        official_uip,
        "run_official_uip",
        lambda *a, **k: _official_result(payload, 1),
    )

    handled, blocked = cli._run_official_restore_gate(result, project, 10, False)

    assert handled
    assert blocked
    assert any(f.rule_id == "UIPATH:RESTORE_PACKAGE_MISSING" for f in result.findings)


def test_run_analyzer_uses_official_uip_without_legacy_uipcli(monkeypatch, tmp_path):
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "project.json").write_text("{}", encoding="utf-8")
    fake_uip = tmp_path / "uip.cmd"
    fake_uip.write_text("", encoding="utf-8")
    payload = {
        "Result": "Error",
        "Data": [
            {
                "ErrorCode": "ST-MRD-002",
                "ErrorSeverity": "Error",
                "Description": "DisplayName default",
                "FilePath": str(project / "Main.xaml"),
            }
        ],
    }

    monkeypatch.setattr(analyzer, "discover_uipcli", lambda: None)
    monkeypatch.setattr(official_uip, "discover_official_uip", lambda: fake_uip)
    monkeypatch.setattr(
        official_uip,
        "get_official_uip_version",
        lambda _: official_uip.OfficialUipVersion("1.1.0", 1, 1, 0),
    )
    monkeypatch.setattr(
        official_uip,
        "run_official_uip",
        lambda *a, **k: _official_result(payload, 1),
    )

    issues = analyzer.run_analyzer(project)

    assert issues is not None
    assert {issue.error_code for issue in issues} == {"ST-MRD-002"}


def test_run_analyzer_infers_file_from_official_detailed_log(monkeypatch, tmp_path):
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "project.json").write_text("{}", encoding="utf-8")
    fake_uip = tmp_path / "uip.cmd"
    fake_uip.write_text("", encoding="utf-8")
    payload = {
        "Result": "Error",
        "Message": (
            "Analyze failed: BC36915: Cannot infer an element type because "
            "more than one type is possible."
        ),
    }

    def fake_run(args, **kwargs):
        log_path = Path(args[args.index("--detailed-log-path") + 1])
        log_path.write_text(
            "[ValidateWorkflowStep] [Functions\\ConfigSicoob\\FiltroQueueItems.xaml] "
            "Validation error: BC36915: Nao e possivel deduzir um tipo de elemento.\n",
            encoding="utf-8",
        )
        return _official_result(payload, 1)

    monkeypatch.setattr(analyzer, "discover_uipcli", lambda: None)
    monkeypatch.setattr(official_uip, "discover_official_uip", lambda: fake_uip)
    monkeypatch.setattr(
        official_uip,
        "get_official_uip_version",
        lambda _: official_uip.OfficialUipVersion("1.1.0", 1, 1, 0),
    )
    monkeypatch.setattr(official_uip, "run_official_uip", fake_run)

    issues = analyzer.run_analyzer(project)

    assert issues is not None
    assert {(issue.file, issue.error_code) for issue in issues} == {
        ("FiltroQueueItems.xaml", "ANALYZE_HALT")
    }


def test_official_analyzer_gate_classifies_assembly_failure(monkeypatch, tmp_path):
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "project.json").write_text("{}", encoding="utf-8")
    payload = {
        "Result": "Error",
        "Message": "Analyze failed: Could not load file or assembly 'Microsoft.VisualStudio.Services.Common, Culture=neutral'",
    }
    result = ValidationResult()
    fake_uip = tmp_path / "uip.cmd"
    fake_uip.write_text("", encoding="utf-8")

    monkeypatch.setattr(official_uip, "discover_official_uip", lambda: fake_uip)
    monkeypatch.setattr(
        official_uip,
        "get_official_uip_version",
        lambda _: official_uip.OfficialUipVersion("1.1.0", 1, 1, 0),
    )
    monkeypatch.setattr(
        official_uip,
        "run_official_uip",
        lambda *a, **k: _official_result(payload, 1),
    )

    assert cli._inject_official_analyzer_findings(result, project, 10, False)

    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "UIPATH:CLI_ASSEMBLY_MISSING"
    assert "Microsoft.VisualStudio.Services.Common" in result.findings[0].message
