import json
import zipfile
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


def _write_nupkg(path: Path, *, tfm: str = "net6.0-windows7.0") -> None:
    stem = path.name.removesuffix(".nupkg")
    package_id, major, minor, patch = stem.rsplit(".", 3)
    version = ".".join([major, minor, patch])
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{package_id}.nuspec",
            "\n".join([
                '<?xml version="1.0" encoding="utf-8"?>',
                '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">',
                "  <metadata>",
                f"    <id>{package_id}</id>",
                f"    <version>{version}</version>",
                "    <dependencies>",
                f'      <group targetFramework="{tfm}" />',
                "    </dependencies>",
                "  </metadata>",
                "</package>",
            ]),
        )
        archive.writestr(f"lib/{tfm}/{package_id}.dll", b"")


def _review_ok(project: Path) -> None:
    assert (project / "project.json").is_file()


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
    pack_calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_calls.append((project_json, pack_dir, version, timeout))
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(pack_dir / "InvoiceProcessing.1.0.1.nupkg")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
        "--download-dir",
        str(tmp_path / "downloads"),
    ])

    plan = publish_dev.execute(
        args,
        run_uip=fake_run,
        run_pack=fake_pack,
        run_review=_review_ok,
    )

    assert plan.current_version == "1.0.0"
    assert plan.next_version == "1.0.1"
    assert json.loads((project / "project.json").read_text())["projectVersion"] == "1.0.1"
    assert project / "project.json" in plan.changed_files
    assert plan.downloaded_nupkg.read_bytes() == b"downloaded"
    assert calls[0] == [
        "login", "status", "--output", "json",
    ]
    assert calls[1] == [
        "login", "tenant", "list", "--output", "json",
    ]
    assert pack_calls == [
        (project / "project.json", tmp_path / "out" / "pack", "1.0.1", 600),
    ]
    assert calls[2][0:4] == [
        "or",
        "packages",
        "upload",
        str(tmp_path / "out" / "pack" / "InvoiceProcessing.1.0.1.nupkg"),
    ]
    assert "--tenant" in calls[2]
    assert "RPA_Desenvolvimento" in calls[2]
    assert calls[3][0:4] == ["or", "packages", "download", "InvoiceProcessing:1.0.1"]
    assert calls[3][calls[3].index("--destination") + 1] == str(
        tmp_path / "downloads" / "InvoiceProcessing.1.0.1.nupkg"
    )


def test_execute_blocks_net8_package_before_upload(tmp_path):
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
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(
            pack_dir / "InvoiceProcessing.1.0.1.nupkg",
            tfm="net8.0-windows7.0",
        )

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    with pytest.raises(RuntimeError, match="not compatible with the DEV Robot net6"):
        publish_dev.execute(
            args,
            run_uip=fake_run,
            run_pack=fake_pack,
            run_review=_review_ok,
        )

    assert not any(command[:3] == ["or", "packages", "upload"] for command in calls)


def test_execute_blocks_when_pre_publish_review_fails(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
    original = {"name": "InvoiceProcessing", "projectVersion": "1.0.0"}
    (project / "project.json").write_text(json.dumps(original), encoding="utf-8")
    calls = []
    pack_calls = []

    def fake_run(command):
        calls.append(command)
        raise AssertionError(f"publish should fail before auth: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_calls.append((project_json, pack_dir, version, timeout))
        raise AssertionError("publish should fail before pack")

    def review_fail(project_root):
        assert project_root == project.resolve()
        raise RuntimeError("pre-publish review found blocking ERROR/HALT findings")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    with pytest.raises(RuntimeError, match="pre-publish review"):
        publish_dev.execute(
            args,
            run_uip=fake_run,
            run_pack=fake_pack,
            run_review=review_fail,
        )

    assert calls == []
    assert pack_calls == []
    assert json.loads((project / "project.json").read_text()) == original


def test_execute_rolls_back_project_version_when_pack_fails(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
    original = {"name": "InvoiceProcessing", "projectVersion": "1.0.0"}
    (project / "project.json").write_text(json.dumps(original), encoding="utf-8")

    def fake_run(command):
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        assert json.loads((project / "project.json").read_text())["projectVersion"] == "1.0.1"
        raise RuntimeError("pack failed")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    with pytest.raises(RuntimeError):
        publish_dev.execute(
            args,
            run_uip=fake_run,
            run_pack=fake_pack,
            run_review=_review_ok,
        )

    assert (project / "project.json").read_text(encoding="utf-8") == json.dumps(original)


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
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(pack_dir / "InvoiceProcessing.1.2.4.nupkg")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    publish_dev.execute(
        args,
        run_uip=fake_run,
        run_pack=fake_pack,
        run_review=_review_ok,
    )

    assert calls[0] == ["login", "status", "--output", "json"]
    assert calls[1] == ["login", "--interactive", "--output", "json"]
    assert calls[2] == ["login", "tenant", "list", "--output", "json"]


def test_publish_ccs_validation_uses_orchestrator_versions(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.0.0",
            "dependencies": {
                "CCS_Controle": "[1.1.0]",
                "CCS_SipagDirect": "[3.0.3]",
            },
        }),
        encoding="utf-8",
    )
    calls = []

    def fake_run(command):
        calls.append(command)
        assert command[:3] == ["or", "packages", "versions"]
        package = command[3]
        if package == "CCS_Controle":
            return _result([{"Version": "1.1.0"}])
        if package == "CCS_SipagDirect":
            return _result([{"Version": "3.0.3"}])
        raise AssertionError(package)

    findings = publish_dev.validate_ccs_packages_against_orchestrator(
        project,
        run_uip=fake_run,
        dev_tenant="RPA_Desenvolvimento",
    )

    assert findings == []
    assert calls == [
        [
            "or", "packages", "versions", "CCS_Controle",
            "--tenant", "RPA_Desenvolvimento",
            "--output", "json",
        ],
        [
            "or", "packages", "versions", "CCS_SipagDirect",
            "--tenant", "RPA_Desenvolvimento",
            "--output", "json",
        ],
    ]


def test_publish_ccs_validation_blocks_when_declared_version_is_not_remote_latest(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.0.0",
            "dependencies": {
                "CCS_Controle": "[1.0.0]",
            },
        }),
        encoding="utf-8",
    )

    def fake_run(command):
        return _result([
            {"Version": "1.0.0"},
            {"Version": "1.1.0"},
        ])

    findings = publish_dev.validate_ccs_packages_against_orchestrator(
        project,
        run_uip=fake_run,
        dev_tenant="RPA_Desenvolvimento",
    )

    assert len(findings) == 1
    assert findings[0].rule_id == publish_dev.CCS_LATEST_PIN_RULE_ID
    assert "Orchestrator RPA_Desenvolvimento" in findings[0].message
    assert "1.1.0" in findings[0].message


def test_publish_ccs_validation_has_no_local_nupkgs_fallback_on_remote_failure(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.0.0",
            "dependencies": {
                "CCS_Controle": "[1.1.0]",
            },
        }),
        encoding="utf-8",
    )

    def fake_run(command):
        return _result({"Message": "tenant unavailable"}, returncode=1, result="Failure")

    findings = publish_dev.validate_ccs_packages_against_orchestrator(
        project,
        run_uip=fake_run,
        dev_tenant="RPA_Desenvolvimento",
    )

    assert len(findings) == 1
    assert "Nao ha fallback local para .nupkgs no publish" in findings[0].message


def test_publish_ccs_validation_flags_referenced_ccs_without_dependency_using_remote_latest(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.0.0",
            "dependencies": {},
        }),
        encoding="utf-8",
    )
    xaml = project / "Framework" / "Init.xaml"
    xaml.parent.mkdir()
    xaml.write_text(
        '<Activity xmlns:c="clr-namespace:CCS_SipagNet;assembly=CCS_SipagNet">\n'
        "  <c:Login />\n"
        "</Activity>\n",
        encoding="utf-8",
    )

    def fake_run(command):
        assert command[:4] == ["or", "packages", "versions", "CCS_SipagNet"]
        return _result([{"Version": "2.0.0"}])

    findings = publish_dev.validate_ccs_packages_against_orchestrator(
        project,
        run_uip=fake_run,
        dev_tenant="RPA_Desenvolvimento",
    )

    assert len(findings) == 1
    assert "dependencies nao declara" in findings[0].message
    assert "2.0.0" in findings[0].message


def test_execute_authenticates_before_default_publish_review(monkeypatch, tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.0.0",
            "dependencies": {},
        }),
        encoding="utf-8",
    )
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(command)

    review_seen = []

    def fake_review(project_root, *, run_uip, dev_tenant):
        review_seen.append((project_root, dev_tenant, list(calls)))

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(pack_dir / "InvoiceProcessing.1.0.1.nupkg")

    monkeypatch.setattr(publish_dev, "run_publish_review_gate", fake_review)
    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    publish_dev.execute(args, run_uip=fake_run, run_pack=fake_pack)

    assert review_seen
    assert review_seen[0][2] == [
        ["login", "status", "--output", "json"],
        ["login", "tenant", "list", "--output", "json"],
    ]


def test_discover_dev_robot_packer_finds_standard_candidate_after_wrong_version(monkeypatch, tmp_path):
    wrong = tmp_path / "wrong" / "UiRobot.exe"
    right = tmp_path / "right" / "UiRobot.exe"
    wrong.parent.mkdir()
    right.parent.mkdir()
    wrong.write_text("", encoding="utf-8")
    right.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        publish_dev,
        "_dev_robot_packer_candidates",
        lambda: [
            publish_dev._PackerCandidate(wrong, "standard install"),
            publish_dev._PackerCandidate(right, "portable 23.10"),
        ],
    )
    monkeypatch.setattr(
        publish_dev,
        "_uirobot_version",
        lambda path: "UiRobot 25.10.1" if path == wrong else "UiRobot 23.10.8",
    )

    assert publish_dev.discover_dev_robot_packer() == right


def test_discover_dev_robot_packer_fails_for_explicit_wrong_version(monkeypatch, tmp_path):
    wrong = tmp_path / "UiRobot.exe"
    wrong.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        publish_dev,
        "_dev_robot_packer_candidates",
        lambda: [
            publish_dev._PackerCandidate(
                wrong,
                publish_dev.DEV_ROBOT_PACKER_ENV_VAR,
                explicit=True,
            ),
        ],
    )
    monkeypatch.setattr(publish_dev, "_uirobot_version", lambda path: "UiRobot 25.10.1")

    with pytest.raises(RuntimeError, match="not a Studio/Robot 23.10 packer"):
        publish_dev.discover_dev_robot_packer()


def test_default_dev_robot_packer_candidates_include_standard_windows_installs(monkeypatch, tmp_path):
    local_app_data = tmp_path / "LocalAppData"
    program_files = tmp_path / "ProgramFiles"
    monkeypatch.delenv(publish_dev.DEV_ROBOT_PACKER_ENV_VAR, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("ProgramFiles", str(program_files))
    monkeypatch.delenv("ProgramW6432", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)
    monkeypatch.setattr(publish_dev.shutil, "which", lambda name: None)

    candidates = publish_dev._default_dev_robot_packer_candidates()

    assert local_app_data / "Programs" / "UiPath" / "Studio" / "UiRobot.exe" in candidates
    assert program_files / "UiPath" / "Studio" / "UiRobot.exe" in candidates


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
    pack_calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_calls.append((project_json, pack_dir, version, timeout))
        assert project_json == project / "project.json"
        generated_uiproj = json.loads((project / "project.uiproj").read_text())
        assert generated_uiproj == {
            "Name": "InvoiceProcessing",
            "ProjectType": "Process",
            "Description": "",
            "MainFile": "Main.xaml",
        }
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(pack_dir / "InvoiceProcessing.1.2.4.nupkg")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    plan = publish_dev.execute(
        args,
        run_uip=fake_run,
        run_pack=fake_pack,
        run_review=_review_ok,
    )

    assert plan.next_version == "1.2.4"
    assert pack_calls == [
        (project / "project.json", tmp_path / "out" / "pack", "1.2.4", 600),
    ]
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
    pack_calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_calls.append((project_json, pack_dir, version, timeout))
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
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(pack_dir / "InvoiceProcessing.1.2.4.nupkg")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    publish_dev.execute(
        args,
        run_uip=fake_run,
        run_pack=fake_pack,
        run_review=_review_ok,
    )

    assert pack_calls == [
        (project / "project.json", tmp_path / "out" / "pack", "1.2.4", 600),
    ]


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
