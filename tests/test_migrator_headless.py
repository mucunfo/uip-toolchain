"""Tests for ``uip_engine.migrator_headless``.

The .NET host binary is **optional**. We do not require ``dotnet build`` to have
run before pytest invocation — tests that need the binary skip themselves when
it is missing. Synthetic tests covering the Python wrapper's parsing and infra
paths run unconditionally.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from uip_engine import migrator_headless as mh
from uip_engine._types import Category, Severity


# ---------------------------------------------------------------------------
# Synthetic parser / infra-finding tests (no .NET host required)
# ---------------------------------------------------------------------------


def test_binary_missing_returns_infra_finding(monkeypatch, tmp_path):
    """When the host binary is absent, ``run_migrate`` must NOT raise.
    It must return ``(-1, [infra_finding])`` so the orchestrator can decide
    whether to skip or fail. This is the core graceful-degrade contract.
    """
    monkeypatch.setenv(mh._ENV_BIN, str(tmp_path / "nonexistent-migrator.exe"))
    code, findings = mh.run_migrate(tmp_path, dry_run=True)
    assert code == -1
    assert len(findings) == 1
    assert findings[0].rule_id == "MG-INFRA-BIN-MISSING"
    assert findings[0].severity == Severity.WARN
    assert "migrator_headless.exe not found" in findings[0].message


def test_parse_output_empty_returns_no_findings(tmp_path):
    findings = mh._parse_output("", tmp_path)
    assert findings == []


def test_parse_output_clean_run(tmp_path):
    payload = {
        "Success": True,
        "Mode": "project",
        "Probe": {"Resolvable": True, "DllFound": True},
        "Results": [
            {"File": str(tmp_path / "Main.xaml"), "MigratedOk": True, "Events": []},
        ],
    }
    findings = mh._parse_output(json.dumps(payload), tmp_path)
    assert findings == []


def test_parse_output_error_event_promoted(tmp_path):
    payload = {
        "Success": False,
        "Mode": "project",
        "Results": [
            {
                "File": str(tmp_path / "Process.xaml"),
                "MigratedOk": False,
                "Events": [
                    {
                        "Severity": "Error",
                        "Reason": "MigrationNotImplemented",
                        "ActivityType": "UiPath.Core.Activities.ExtractData",
                        "ActivityName": "Extract DT",
                        "Message": "No migrator registered.",
                    },
                ],
            },
        ],
    }
    findings = mh._parse_output(json.dumps(payload), tmp_path)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "MG-NOT_IMPLEMENTED"
    assert f.severity == Severity.ERROR
    assert f.category == Category.BREAKING
    assert "ExtractData" in f.message
    assert "Extract DT" in f.message
    assert f.fix_prose is not None and "Modern equivalent" in f.fix_prose


def test_parse_output_warning_event(tmp_path):
    payload = {
        "Results": [
            {
                "File": "x.xaml",
                "Events": [{"Severity": "Warning", "Reason": "ObsoleteProperty",
                            "Message": "DeprecatedProp used"}],
            }
        ]
    }
    findings = mh._parse_output(json.dumps(payload), tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARN
    assert findings[0].rule_id == "MG-OBSOLETE_PROP"


def test_parse_output_info_events_dropped(tmp_path):
    payload = {
        "Results": [
            {
                "File": "x.xaml",
                "Events": [
                    {"Severity": "Info", "Reason": "Success", "Message": "ok"},
                    {"Severity": "Start", "Reason": "Success", "Message": "begin"},
                    {"Severity": "End", "Reason": "Success", "Message": "done"},
                ],
            }
        ]
    }
    findings = mh._parse_output(json.dumps(payload), tmp_path)
    assert findings == []


def test_parse_output_unknown_reason_passthrough(tmp_path):
    payload = {
        "Results": [
            {
                "File": "x.xaml",
                "Events": [{"Severity": "Error", "Reason": "BrandNewReason",
                            "Message": "future-proofing"}],
            }
        ]
    }
    findings = mh._parse_output(json.dumps(payload), tmp_path)
    assert len(findings) == 1
    # CamelCase -> UPPER_SNAKE fallback.
    assert findings[0].rule_id == "MG-BRAND_NEW_REASON"


def test_parse_output_malformed_json_emits_infra(tmp_path):
    findings = mh._parse_output("{this is not json", tmp_path)
    assert len(findings) == 1
    assert findings[0].rule_id == "MG-INFRA-BAD-JSON"


def test_parse_output_surfaces_probe_error(tmp_path):
    payload = {"Probe": {"Error": "dll not loadable"}, "Results": []}
    findings = mh._parse_output(json.dumps(payload), tmp_path)
    assert any(f.rule_id == "MG-INFRA-PROBE-FAIL" for f in findings)


def test_rule_id_known_mapping():
    assert mh._rule_id("PropertyMigrationNotImplemented") == "MG-PROP_NOT_IMPLEMENTED"
    assert mh._rule_id("ElementScopeInsideElementScope") == "MG-ELEMENT_SCOPE_NESTED"
    assert mh._rule_id(None) == "MG-UNKNOWN"


def test_severity_from_host_variants():
    assert mh._severity_from_host("Error") == Severity.ERROR
    assert mh._severity_from_host("Warning") == Severity.WARN
    assert mh._severity_from_host("warn") == Severity.WARN
    assert mh._severity_from_host("Info") is None
    assert mh._severity_from_host("Start") is None
    assert mh._severity_from_host("anything_else") == Severity.WARN


def test_binary_path_env_override(monkeypatch, tmp_path):
    custom = tmp_path / "custom.exe"
    custom.write_bytes(b"\x00")
    monkeypatch.setenv(mh._ENV_BIN, str(custom))
    info = mh._binary_path()
    assert info.path == custom
    assert info.exists


# ---------------------------------------------------------------------------
# Live .NET host tests (skip if binary missing or pre-migrate sample absent)
# ---------------------------------------------------------------------------


_PRE_MIGRATE_SAMPLE = Path(
    r"C:\Users\lisan\Desktop\temp"
    r"\contestacao-de-compras-ajuste-na-reserva-de-fraude"
    r"\contestacao-de-compras-ajuste-na-reserva-de-fraude-dispatcher"
    r"_BeforeMigration_20260523-221041"
)


def _binary_available() -> bool:
    return mh._binary_path().exists


@pytest.mark.skipif(not _binary_available(), reason="migrator_headless.exe not built")
def test_probe_resolves_dll():
    """Probe should locate Migration.dll and report Resolvable=True on
    a workstation with the NuGet cache populated (25.10.16+)."""
    code, payload = mh.run_probe(timeout=30)
    # Either the DLL is found (code 0) OR not found (code 3); not -1 if built.
    assert code in (0, 3), f"unexpected probe exit code: {code} payload={payload!r}"
    probe = payload.get("Probe") or {}
    assert "DllFound" in probe
    if probe.get("DllFound"):
        # When DLL is loadable, the public types must resolve.
        assert probe.get("ServiceTypeFound") is True
        assert probe.get("OptionsTypeFound") is True


@pytest.mark.skipif(
    not _binary_available() or not _PRE_MIGRATE_SAMPLE.exists(),
    reason="pre-migrate sample project missing or migrator_headless not built",
)
def test_smoke_pre_migrate_sample():
    """Smoke test on a real pre-migrate Sicoob project.

    Headless reflection cannot complete the migration (lacks WPF
    WorkflowDesigner) — we expect either:
      a) MG-HEADLESS_UNSUPPORTED-style events from each XAML, OR
      b) an MG-INFRA-PROBE-FAIL if Migration.dll missing.
    Either way we must NOT crash and must NOT corrupt the project.
    """
    code, findings = mh.run_migrate(_PRE_MIGRATE_SAMPLE, dry_run=True, timeout=120)
    # Acceptable exit codes: 1 (errors surfaced as findings) or 3 (probe failed).
    assert code in (1, 3), f"unexpected code={code}; findings={findings!r}"
    assert all(isinstance(f, type(findings[0])) for f in findings)


@pytest.mark.skipif(
    not _binary_available(),
    reason="migrator_headless not built",
)
def test_smoke_dry_run_on_empty_dir(tmp_path):
    """On a directory with NO xaml files, host should return zero events."""
    code, findings = mh.run_migrate(tmp_path, dry_run=True, timeout=30)
    # Either probe-fail (no DLL) or success-with-zero-results.
    assert code in (0, 1, 3)
    # No file-level results means no migration-related findings, only
    # potential infra/probe finding.
    non_infra = [f for f in findings if not f.rule_id.startswith("MG-INFRA")]
    assert non_infra == []
