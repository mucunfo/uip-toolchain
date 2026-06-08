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


def test_project_version_comes_from_project_json(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({"name": "InvoiceProcessing", "projectVersion": "1.5.7"}),
        encoding="utf-8",
    )

    assert publish_dev._project_version(project) == "1.5.7"


def test_execute_reads_prod_version_uploads_dev_and_downloads(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
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
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:2] == ["rpa", "pack"]:
            pack_dir = Path(command[3])
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "InvoiceProcessing.1.0.1.nupkg").write_bytes(b"packed")
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
        "--out-dir",
        str(tmp_path / "out"),
        "--download-dir",
        str(tmp_path / "downloads"),
    ])

    plan = publish_dev.execute(args, run_uip=fake_run)

    assert plan.current_version == "1.0.0"
    assert plan.next_version == "1.0.1"
    assert plan.downloaded_nupkg.read_bytes() == b"downloaded"
    assert calls[0] == [
        "login", "status", "--output", "json",
    ]
    assert calls[1] == [
        "login", "tenant", "list", "--output", "json",
    ]
    assert calls[2] == [
        "rpa", "pack", str(project.resolve()), str(tmp_path / "out" / "pack"),
        "--package-version", "1.0.1",
        "--skip-analyze",
        "--output", "json",
    ]
    assert calls[3][0:4] == [
        "or",
        "packages",
        "upload",
        str(tmp_path / "out" / "pack" / "InvoiceProcessing.1.0.1.nupkg"),
    ]
    assert "--tenant" in calls[3]
    assert "RPA_Desenvolvimento" in calls[3]
    assert calls[4][0:4] == ["or", "packages", "download", "InvoiceProcessing:1.0.1"]
    assert calls[4][calls[4].index("--destination") + 1] == str(
        tmp_path / "downloads" / "InvoiceProcessing.1.0.1.nupkg"
    )


def test_execute_runs_interactive_login_when_status_fails(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
    (project / "project.json").write_text(
        json.dumps({"name": "InvoiceProcessing", "projectVersion": "1.2.3"}),
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
                {"TenantName": "RPA_Desenvolvimento"},
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
        "--out-dir",
        str(tmp_path / "out"),
    ])

    publish_dev.execute(args, run_uip=fake_run)

    assert calls[0] == ["login", "status", "--output", "json"]
    assert calls[1] == ["login", "--interactive", "--output", "json"]
    assert calls[2] == ["login", "tenant", "list", "--output", "json"]


def test_execute_syncs_project_uiproj_before_modern_pack(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.2.3",
            "designOptions": {"outputType": "Process"},
        }),
        encoding="utf-8",
    )
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:2] == ["rpa", "pack"]:
            assert Path(command[2]) == project.resolve()
            generated_uiproj = json.loads((project / "project.uiproj").read_text())
            assert generated_uiproj == {
                "Name": "InvoiceProcessing",
                "ProjectType": "Process",
                "Description": "",
                "MainFile": "Main.xaml",
            }
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
        "--out-dir",
        str(tmp_path / "out"),
    ])

    plan = publish_dev.execute(args, run_uip=fake_run)

    assert plan.next_version == "1.2.4"
    assert calls[2][:2] == ["rpa", "pack"]
    assert (project / "project.uiproj").is_file()
    assert not (project / ".local").exists()
    assert not (project / "InvoiceProcessing.dll").exists()
    assert not (project / "InvoiceProcessing_Expressions.dll").exists()


def test_execute_scrubs_stale_python_assembly_refs_before_modern_pack(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.2.3",
            "designOptions": {"outputType": "Process"},
            "dependencies": {
                "UiPath.System.Activities": "25.10.1",
            },
        }),
        encoding="utf-8",
    )
    workflow = project / "Main.xaml"
    workflow.write_text(
        "\n".join([
            "<Activity>",
            "  <TextExpression.NamespacesForImplementation>",
            "    <x:String>UiPath.Python</x:String>",
            "  </TextExpression.NamespacesForImplementation>",
            "  <TextExpression.ReferencesForImplementation>",
            "    <sco:Collection x:TypeArguments=\"AssemblyReference\">",
            "      <AssemblyReference>BalaReva.EasyExcel</AssemblyReference>",
            "      <AssemblyReference>BalaReva.EasyExcel.Utilities</AssemblyReference>",
            "      <AssemblyReference>BalaReva.Excel</AssemblyReference>",
            "      <AssemblyReference>CCS_DataUtil</AssemblyReference>",
            "      <AssemblyReference>CCS_EstruturaPastas</AssemblyReference>",
            "      <AssemblyReference>CCS_SipagDirect</AssemblyReference>",
            "      <AssemblyReference>CCS_SipagNet</AssemblyReference>",
            "      <AssemblyReference>CCS_Sisbr_2_0</AssemblyReference>",
            "      <AssemblyReference>CCS_TOPdesk</AssemblyReference>",
            "      <AssemblyReference>Microsoft.Activities</AssemblyReference>",
            "      <AssemblyReference>System</AssemblyReference>",
            "      <AssemblyReference>Microsoft.VisualStudio.Services.Common</AssemblyReference>",
            "      <AssemblyReference>NPOI</AssemblyReference>",
            "      <AssemblyReference>TimeSpan2</AssemblyReference>",
            "      <AssemblyReference>UiPath.IntelligentOCR</AssemblyReference>",
            "      <AssemblyReference>UiPath.Python</AssemblyReference>",
            "      <AssemblyReference>UiPath.Python.Activities</AssemblyReference>",
            "      <AssemblyReference>UiPath.Word.Activities</AssemblyReference>",
            "      <AssemblyReference>UiPath.Word.Activities.Design</AssemblyReference>",
            "    </sco:Collection>",
            "  </TextExpression.ReferencesForImplementation>",
            "</Activity>",
            "",
        ]),
        encoding="utf-8",
    )
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:2] == ["rpa", "pack"]:
            text = workflow.read_text(encoding="utf-8")
            assert "<x:String>UiPath.Python</x:String>" in text
            assert "<AssemblyReference>BalaReva.EasyExcel</AssemblyReference>" not in text
            assert "<AssemblyReference>BalaReva.EasyExcel.Utilities</AssemblyReference>" not in text
            assert "<AssemblyReference>BalaReva.Excel</AssemblyReference>" not in text
            assert "<AssemblyReference>CCS_DataUtil</AssemblyReference>" not in text
            assert "<AssemblyReference>CCS_EstruturaPastas</AssemblyReference>" not in text
            assert "<AssemblyReference>CCS_SipagDirect</AssemblyReference>" not in text
            assert "<AssemblyReference>CCS_SipagNet</AssemblyReference>" not in text
            assert "<AssemblyReference>CCS_Sisbr_2_0</AssemblyReference>" not in text
            assert "<AssemblyReference>CCS_TOPdesk</AssemblyReference>" not in text
            assert "<AssemblyReference>Microsoft.Activities</AssemblyReference>" not in text
            assert "<AssemblyReference>Microsoft.VisualStudio.Services.Common</AssemblyReference>" not in text
            assert "<AssemblyReference>NPOI</AssemblyReference>" not in text
            assert "<AssemblyReference>TimeSpan2</AssemblyReference>" not in text
            assert "<AssemblyReference>UiPath.IntelligentOCR</AssemblyReference>" not in text
            assert "<AssemblyReference>UiPath.Python</AssemblyReference>" not in text
            assert "<AssemblyReference>UiPath.Python.Activities</AssemblyReference>" not in text
            assert "<AssemblyReference>UiPath.Word.Activities</AssemblyReference>" not in text
            assert "<AssemblyReference>UiPath.Word.Activities.Design</AssemblyReference>" not in text
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
        "--out-dir",
        str(tmp_path / "out"),
    ])

    publish_dev.execute(args, run_uip=fake_run)

    assert calls[2][:2] == ["rpa", "pack"]


def test_scrub_pack_incompatible_refs_keeps_declared_dependency(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.2.3",
            "dependencies": {
                "UiPath.Python.Activities": "1.8.0",
            },
        }),
        encoding="utf-8",
    )
    workflow = project / "Main.xaml"
    workflow.write_text(
        "\n".join([
            "<Activity>",
            "  <AssemblyReference>UiPath.Python</AssemblyReference>",
            "  <AssemblyReference>UiPath.Python.Activities</AssemblyReference>",
            "</Activity>",
            "",
        ]),
        encoding="utf-8",
    )

    changed = publish_dev.scrub_pack_incompatible_assembly_references(project)

    text = workflow.read_text(encoding="utf-8")
    assert changed == []
    assert "<AssemblyReference>UiPath.Python</AssemblyReference>" in text
    assert "<AssemblyReference>UiPath.Python.Activities</AssemblyReference>" in text


def test_scrub_pack_incompatible_refs_skips_technical_dirs(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.2.3",
            "dependencies": {},
        }),
        encoding="utf-8",
    )
    cache_dir = project / ".tmp"
    cache_dir.mkdir()
    cached = cache_dir / "Cached.xaml"
    cached.write_text(
        "<Activity>\n"
        "  <AssemblyReference>UiPath.Python</AssemblyReference>\n"
        "</Activity>\n",
        encoding="utf-8",
    )

    changed = publish_dev.scrub_pack_incompatible_assembly_references(project)

    assert changed == []
    assert "<AssemblyReference>UiPath.Python</AssemblyReference>" in cached.read_text(
        encoding="utf-8"
    )
