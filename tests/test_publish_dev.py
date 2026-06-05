import json
from pathlib import Path

import pytest

from uip_engine import publish_dev
from uip_engine.official_uip import OfficialUipEnvelope, OfficialUipResult


def _result(data, *, code="Ok", returncode=0, result="Success"):
    payload = {
        "Result": result,
        "Code": code,
        "Data": data,
    }
    envelope = OfficialUipEnvelope(
        result=result,
        code=code,
        data=data,
        message=None,
        instructions=None,
        context=None,
        log=None,
        raw=payload,
    )
    return OfficialUipResult(
        argv=["uip"],
        returncode=returncode,
        stdout=json.dumps(payload),
        stderr="",
        envelope=envelope,
    )


def test_bump_version_requires_explicit_semver():
    assert publish_dev.bump_version("1.2.3", "major") == "2.0.0"
    assert publish_dev.bump_version("1.2.3", "minor") == "1.3.0"
    assert publish_dev.bump_version("1.2.3", "patch") == "1.2.4"

    with pytest.raises(ValueError):
        publish_dev.bump_version("1.2.3-beta.1", "patch")


def test_select_active_process_prefers_exact_process_name():
    records = [
        {"Name": "Other", "PackageKey": "Invoice", "Version": "9.0.0"},
        {"Name": "InvoiceProcess", "PackageKey": "Invoice", "Version": "1.2.3"},
    ]

    active = publish_dev.select_active_process(
        records,
        process_name="InvoiceProcess",
        package_key="Invoice",
    )

    assert active.version == "1.2.3"


def test_execute_reads_prod_version_uploads_dev_and_downloads(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({"name": "InvoiceProcessing", "projectVersion": "1.0.0"}),
        encoding="utf-8",
    )
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "Producao"},
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["or", "processes", "list"]:
            return _result([
                {
                    "Name": "InvoiceProcessing",
                    "PackageKey": "InvoiceProcessing",
                    "Version": "1.2.3",
                }
            ])
        if command[:2] == ["rpa", "pack"]:
            pack_dir = Path(command[3])
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "InvoiceProcessing.1.2.4.nupkg").write_bytes(b"packed")
            return _result({"Status": "Packed"})
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--prod-folder-path",
        "Shared/RPA",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    plan = publish_dev.execute(args, run_uip=fake_run)

    assert plan.current_version == "1.2.3"
    assert plan.next_version == "1.2.4"
    assert plan.downloaded_nupkg.read_bytes() == b"downloaded"
    assert calls[0] == [
        "login", "status", "--output", "json",
    ]
    assert calls[1] == [
        "login", "tenant", "list", "--output", "json",
    ]
    assert calls[2] == [
        "or", "processes", "list",
        "--tenant", "Producao",
        "--name", "InvoiceProcessing",
        "--output", "json",
        "--folder-path", "Shared/RPA",
    ]
    assert calls[3] == [
        "rpa", "pack", str(project.resolve()), str(tmp_path / "out" / "pack"),
        "--output-type", "Process",
        "--package-version", "1.2.4",
        "--output", "json",
    ]
    assert calls[4][0:4] == [
        "or",
        "packages",
        "upload",
        str(tmp_path / "out" / "pack" / "InvoiceProcessing.1.2.4.nupkg"),
    ]
    assert "--tenant" in calls[4]
    assert "RPA_Desenvolvimento" in calls[4]
    assert calls[5][0:4] == ["or", "packages", "download", "InvoiceProcessing:1.2.4"]


def test_execute_runs_interactive_login_when_status_fails(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({"name": "InvoiceProcessing"}),
        encoding="utf-8",
    )
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Message": "not logged in"}, returncode=1, result="Failure")
        if command[:2] == ["login", "--interactive"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "Producao"},
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["or", "processes", "list"]:
            return _result([
                {"Name": "InvoiceProcessing", "PackageKey": "InvoiceProcessing", "Version": "1.2.3"}
            ])
        if command[:2] == ["rpa", "pack"]:
            pack_dir = Path(command[3])
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "InvoiceProcessing.1.2.4.nupkg").write_bytes(b"packed")
            return _result({"Status": "Packed"})
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--prod-folder-path",
        "Shared/RPA",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    publish_dev.execute(args, run_uip=fake_run)

    assert calls[0] == ["login", "status", "--output", "json"]
    assert calls[1] == ["login", "--interactive", "--output", "json"]
    assert calls[2] == ["login", "tenant", "list", "--output", "json"]
