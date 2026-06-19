import json
import zipfile
from pathlib import Path

from uip_engine import cli
from uip_engine.official_uip import OfficialUipEnvelope, OfficialUipResult
from uip_engine.orchestrator_sync import sync_orchestrator_process_versions


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


def _write_process_nupkg(path: Path) -> None:
    stem = path.name.removesuffix(".nupkg")
    package_id, major, minor, patch = stem.rsplit(".", 3)
    version = ".".join([major, minor, patch])
    descriptor = {
        "name": package_id,
        "projectVersion": version,
        "targetFramework": "Windows",
        "designOptions": {"outputType": "Process"},
        "main": "Main.xaml",
        "entryPoints": [{"filePath": "Main.xaml"}],
        "dependencies": {
            "UiPath.System.Activities": "[23.10.11]",
        },
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr(
            f"{package_id}.nuspec",
            "\n".join([
                '<?xml version="1.0" encoding="utf-8"?>',
                '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">',
                "  <metadata>",
                f"    <id>{package_id}</id>",
                f"    <version>{version}</version>",
                "    <dependencies>",
                '      <group targetFramework="net6.0-windows7.0" />',
                "    </dependencies>",
                "  </metadata>",
                "</package>",
            ]),
        )
        archive.writestr("lib/net6.0-windows7.0/project.json", json.dumps(descriptor))
        archive.writestr(f"lib/net6.0-windows7.0/{package_id}.dll", b"")
        archive.writestr("content/project.json", json.dumps(descriptor))
        archive.writestr("content/Main.xaml", "<Activity />")


def _fake_run(calls, *, process_version="1.2.3", verify_version="1.2.4", update_ok=True, processes=None):
    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "processes", "list"]:
            return _result(processes or [{
                "Key": "11111111-1111-1111-1111-111111111111",
                "Name": "InvoiceProcessing",
                "ProcessKey": "InvoiceProcessing",
                "ProcessVersion": process_version,
                "FolderPath": "Shared",
                "FolderKey": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            }])
        if command[:3] == ["or", "processes", "update-version"]:
            if update_ok:
                return _result({"ProcessKey": command[3], "Version": command[5]})
            return _result({"Message": "update failed"}, returncode=1, result="Failure")
        if command[:3] == ["or", "processes", "get"]:
            return _result({
                "Key": command[3],
                "Name": "InvoiceProcessing",
                "ProcessKey": "InvoiceProcessing",
                "ProcessVersion": verify_version,
                "FolderPath": "Shared",
            })
        raise AssertionError(command)

    return fake_run


def test_sync_dry_run_does_not_update_process(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)
    calls = []

    result = sync_orchestrator_process_versions(
        [nupkg],
        run_uip=_fake_run(calls),
        execute=False,
    )

    assert result.ok
    assert not result.executed
    assert result.warn_count == 1
    assert result.targets[0].current_version == "1.2.3"
    assert not any(call[:3] == ["or", "processes", "update-version"] for call in calls)


def test_sync_execute_updates_and_verifies_process(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)
    calls = []

    result = sync_orchestrator_process_versions(
        [nupkg],
        run_uip=_fake_run(calls),
        execute=True,
    )

    assert result.ok
    assert result.executed
    assert result.targets[0].updated
    assert ["or", "processes", "update-version", "11111111-1111-1111-1111-111111111111", "--package-version", "1.2.4", "--output", "json", "--folder-key", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"] in calls
    assert ["or", "processes", "get", "11111111-1111-1111-1111-111111111111", "--all-fields", "--output", "json"] in calls


def test_sync_execute_marks_already_current(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)
    calls = []

    result = sync_orchestrator_process_versions(
        [nupkg],
        run_uip=_fake_run(calls, process_version="1.2.4"),
        execute=True,
    )

    assert result.ok
    assert result.targets[0].already_current
    assert not any(call[:3] == ["or", "processes", "update-version"] for call in calls)


def test_sync_blocks_ambiguous_processes(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)
    process = {
        "Name": "InvoiceProcessing",
        "ProcessKey": "InvoiceProcessing",
        "ProcessVersion": "1.2.3",
        "FolderPath": "Shared",
    }

    result = sync_orchestrator_process_versions(
        [nupkg],
        run_uip=_fake_run([], processes=[
            {"Key": "11111111-1111-1111-1111-111111111111", **process},
            {"Key": "22222222-2222-2222-2222-222222222222", **process},
        ]),
        execute=True,
    )

    assert not result.ok
    assert any(issue.code == "SYNC-PROCESS-AMBIGUOUS" for issue in result.issues)


def test_sync_reports_update_failure(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)

    result = sync_orchestrator_process_versions(
        [nupkg],
        run_uip=_fake_run([], update_ok=False),
        execute=True,
    )

    assert not result.ok
    assert any(issue.code == "SYNC-UPDATE-FAILED" for issue in result.issues)


def test_cli_sync_orchestrator_processes(monkeypatch, tmp_path, capsys):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)
    monkeypatch.setattr("uip_engine.official_uip.run_official_uip", _fake_run([]))
    args = cli.build_parser().parse_args([
        "sync-orchestrator-processes",
        str(nupkg),
        "--execute",
    ])

    rc = cli._cmd_sync_orchestrator_processes(args)

    assert rc == cli.EXIT_OK
    assert "ORCHESTRATOR sync: OK" in capsys.readouterr().out
