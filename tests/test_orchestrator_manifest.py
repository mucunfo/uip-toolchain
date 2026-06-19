import json
import zipfile
from pathlib import Path

from uip_engine import cli
from uip_engine.official_uip import OfficialUipEnvelope, OfficialUipResult
from uip_engine.orchestrator_manifest import build_orchestrator_manifest


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


def _fake_run_with_processes(calls, processes):
    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "processes", "list"]:
            return _result(processes)
        raise AssertionError(command)

    return fake_run


def _write_source_project(path: Path, name: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "project.json").write_text(
        json.dumps({
            "name": name,
            "projectVersion": "1.2.3",
            "main": "Main.xaml",
            "arguments": {
                "input": [{
                    "name": "in_RequiredTicket",
                    "type": "System.String",
                    "required": True,
                    "hasDefault": False,
                }]
            },
        }),
        encoding="utf-8",
    )
    (path / "Main.xaml").write_text(
        "\n".join([
            '<Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">',
            "  <this:Main.in_StAssetArquivoConfiguracao>",
            '    <InArgument x:TypeArguments="x:String">["ArquivoConfiguracao_Performer"]</InArgument>',
            "  </this:Main.in_StAssetArquivoConfiguracao>",
            '  <ui:GetRobotCredential AssetName="[Config(&quot;NomeCredencialDB2&quot;).ToString]" />',
            '  <ui:BulkAddQueueItems QueueName="[in_Config(&quot;OrchestratorQueueName&quot;).ToString]" />',
            '  <ui:OrchestratorHttpRequest RelativeEndpoint="[&quot;/odata/Calendars?$filter=Name%20eq%20\'&quot; + in_Config(&quot;CalendarioOrq&quot;).ToString + &quot;\'&quot;]" />',
            "</Activity>",
        ]),
        encoding="utf-8",
    )
    return path


def test_build_orchestrator_manifest_resolves_package_to_process(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)
    out = tmp_path / "manifest.json"
    calls = []

    result = build_orchestrator_manifest(
        [nupkg],
        run_uip=_fake_run_with_processes(calls, [{
            "Key": "11111111-1111-1111-1111-111111111111",
            "Name": "InvoiceProcessing",
            "ProcessKey": "InvoiceProcessing",
            "ProcessVersion": "1.2.4",
            "FolderPath": "Shared",
            "FolderKey": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        }]),
        output_path=out,
    )

    assert result.ok
    assert out.is_file()
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["tenant"] == "RPA_Desenvolvimento"
    assert manifest["items"] == [{
        "packageId": "InvoiceProcessing",
        "packageVersion": "1.2.4",
        "processKey": "11111111-1111-1111-1111-111111111111",
        "runtimeType": "Unattended",
        "folderPath": "Shared",
        "folderKey": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "processName": "InvoiceProcessing",
        "targetFramework": "Windows",
        "entryPointPath": "Main.xaml",
    }]
    assert ["or", "processes", "list", "--all-folders", "--name", "InvoiceProcessing", "--all-fields", "--limit", "1000", "--output", "json"] in calls


def test_build_orchestrator_manifest_infers_source_runtime_resources(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    source_root = tmp_path / "src"
    _write_process_nupkg(nupkg)
    _write_source_project(source_root / "invoice-processing", "InvoiceProcessing")

    result = build_orchestrator_manifest(
        [nupkg],
        run_uip=_fake_run_with_processes([], [{
            "Key": "11111111-1111-1111-1111-111111111111",
            "Name": "InvoiceProcessing",
            "ProcessKey": "InvoiceProcessing",
            "ProcessVersion": "1.2.4",
            "FolderPath": "Shared",
        }]),
        source_root=source_root,
    )

    assert result.ok
    assert result.warn_count == 1
    assert any(issue.code == "MANIFEST-DYNAMIC-RESOURCE-KEYS" for issue in result.issues)
    item = result.manifest["items"][0]
    assert item["targetFramework"] == "Windows"
    assert item["entryPointPath"] == "Main.xaml"
    assert item["requiredResources"] == [{
        "type": "asset",
        "name": "ArquivoConfiguracao_Performer",
        "valueType": "Text",
        "source": "source:ArquivoConfiguracao",
    }]
    assert {
        "type": "credential",
        "configKey": "NomeCredencialDB2",
        "source": "source:Config",
    } in item["runtimeResourceHints"]
    assert {
        "type": "queue",
        "configKey": "OrchestratorQueueName",
        "source": "source:Config",
    } in item["runtimeResourceHints"]
    assert {
        "type": "calendar",
        "configKey": "CalendarioOrq",
        "source": "source:Config",
    } in item["runtimeResourceHints"]
    assert item["requiredInputArguments"] == ["in_RequiredTicket"]


def test_build_orchestrator_manifest_flags_version_not_bound(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)

    result = build_orchestrator_manifest(
        [nupkg],
        run_uip=_fake_run_with_processes([], [{
            "Key": "11111111-1111-1111-1111-111111111111",
            "Name": "InvoiceProcessing",
            "ProcessKey": "InvoiceProcessing",
            "ProcessVersion": "1.2.3",
            "FolderPath": "Shared",
        }]),
    )

    assert not result.ok
    assert any(issue.code == "MANIFEST-PROCESS-VERSION-NOT-BOUND" for issue in result.issues)


def test_build_orchestrator_manifest_blocks_ambiguous_processes(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)
    process = {
        "Name": "InvoiceProcessing",
        "ProcessKey": "InvoiceProcessing",
        "ProcessVersion": "1.2.4",
        "FolderPath": "Shared",
    }

    result = build_orchestrator_manifest(
        [nupkg],
        run_uip=_fake_run_with_processes([], [
            {"Key": "11111111-1111-1111-1111-111111111111", **process},
            {"Key": "22222222-2222-2222-2222-222222222222", **process},
        ]),
    )

    assert not result.ok
    assert any(issue.code == "MANIFEST-PROCESS-AMBIGUOUS" for issue in result.issues)


def test_cli_build_orchestrator_manifest(monkeypatch, tmp_path, capsys):
    nupkg = tmp_path / "InvoiceProcessing.1.2.4.nupkg"
    _write_process_nupkg(nupkg)
    out = tmp_path / "manifest.json"
    monkeypatch.setattr(
        "uip_engine.official_uip.run_official_uip",
        _fake_run_with_processes([], [{
            "Key": "11111111-1111-1111-1111-111111111111",
            "Name": "InvoiceProcessing",
            "ProcessKey": "InvoiceProcessing",
            "ProcessVersion": "1.2.4",
            "FolderPath": "Shared",
        }]),
    )
    args = cli.build_parser().parse_args([
        "build-orchestrator-manifest",
        str(nupkg),
        "--out",
        str(out),
    ])

    rc = cli._cmd_build_orchestrator_manifest(args)

    assert rc == cli.EXIT_OK
    assert out.is_file()
    assert "ORCHESTRATOR manifest: OK" in capsys.readouterr().out
