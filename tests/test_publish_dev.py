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


def _write_nupkg(
    path: Path,
    *,
    tfm: str = "net6.0-windows7.0",
    include_project_json: bool = True,
    include_content_project_json: bool = False,
    include_git_metadata: bool = False,
    system_activities_version: str = "[23.10.11]",
) -> None:
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
            "UiPath.System.Activities": system_activities_version,
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
                f'      <group targetFramework="{tfm}" />',
                "    </dependencies>",
                "  </metadata>",
                "</package>",
            ]),
        )
        if include_project_json:
            archive.writestr(
                f"lib/{tfm}/project.json",
                json.dumps(descriptor),
            )
        if include_content_project_json:
            archive.writestr(
                "content/project.json",
                json.dumps(descriptor),
            )
        archive.writestr("content/Main.xaml", "<Activity />")
        archive.writestr(f"lib/{tfm}/{package_id}.dll", b"")
        if include_git_metadata:
            archive.writestr("content/.git/HEAD", "ref: refs/heads/main\n")


def _copy_uploaded_download(command: list[str], uploaded: Path | None) -> Path:
    assert uploaded is not None
    destination = Path(command[command.index("--destination") + 1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(uploaded.read_bytes())
    return destination


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
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            uploaded_nupkg = Path(command[3])
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = _copy_uploaded_download(command, uploaded_nupkg)
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
    assert plan.downloaded_nupkg.read_bytes() == uploaded_nupkg.read_bytes()
    assert calls[0] == [
        "login", "status", "--output", "json",
    ]
    assert calls[1] == [
        "login", "tenant", "list", "--output", "json",
    ]
    assert calls[2] == [
        "login", "tenant", "set", "RPA_Desenvolvimento", "--output", "json",
    ]
    assert pack_calls == [
        (project / "project.json", tmp_path / "out" / "pack", "1.0.1", 600),
    ]
    assert calls[3][0:4] == [
        "or",
        "packages",
        "upload",
        str(tmp_path / "out" / "pack" / "InvoiceProcessing.1.0.1.nupkg"),
    ]
    assert "--tenant" not in calls[3]
    assert calls[4][0:4] == ["or", "packages", "download", "InvoiceProcessing:1.0.1"]
    assert "--tenant" not in calls[4]
    assert calls[4][calls[4].index("--destination") + 1] == str(
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
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
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


def test_validate_blocks_mixed_package_missing_net45_project_json(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    with zipfile.ZipFile(nupkg, "w") as archive:
        archive.writestr(
            "InvoiceProcessing.nuspec",
            "\n".join([
                '<?xml version="1.0" encoding="utf-8"?>',
                '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">',
                "  <metadata>",
                "    <id>InvoiceProcessing</id>",
                "    <version>1.0.1</version>",
                "    <dependencies>",
                '      <group targetFramework="net45" />',
                '      <group targetFramework="net6.0-windows7.0" />',
                "    </dependencies>",
                "  </metadata>",
                "</package>",
            ]),
        )
        archive.writestr(
            "lib/net6.0-windows7.0/project.json",
            json.dumps({"name": "InvoiceProcessing", "projectVersion": "1.0.1"}),
        )
        archive.writestr("lib/net6.0-windows7.0/InvoiceProcessing.dll", b"")
        archive.writestr("lib/net45/InvoiceProcessing.dll", b"")

    with pytest.raises(RuntimeError, match=r"lib/net45/project\.json"):
        publish_dev.validate_dev_robot_package_compatibility(nupkg)


def test_validate_blocks_mixed_package_with_legacy_tfm(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    descriptor = {
        "name": "InvoiceProcessing",
        "projectVersion": "1.0.1",
        "targetFramework": "Windows",
        "designOptions": {"outputType": "Process"},
        "main": "Main.xaml",
        "entryPoints": [{"filePath": "Main.xaml"}],
    }
    with zipfile.ZipFile(nupkg, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr(
            "InvoiceProcessing.nuspec",
            "\n".join([
                '<?xml version="1.0" encoding="utf-8"?>',
                '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">',
                "  <metadata>",
                "    <id>InvoiceProcessing</id>",
                "    <version>1.0.1</version>",
                "    <dependencies>",
                '      <group targetFramework="net45" />',
                '      <group targetFramework="net6.0-windows7.0" />',
                "    </dependencies>",
                "  </metadata>",
                "</package>",
            ]),
        )
        for tfm in ("net45", "net6.0-windows7.0"):
            archive.writestr(f"lib/{tfm}/project.json", json.dumps(descriptor))
            archive.writestr(f"lib/{tfm}/InvoiceProcessing.dll", b"")

    with pytest.raises(RuntimeError, match="not compatible with the DEV Robot net6"):
        publish_dev.validate_dev_robot_package_compatibility(nupkg)


def test_execute_repairs_content_project_json_into_lib_before_upload(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
    (project / "project.json").write_text(
        json.dumps({"name": "InvoiceProcessing", "projectVersion": "1.0.0"}),
        encoding="utf-8",
    )
    calls = []
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            uploaded = Path(command[3])
            uploaded_nupkg = uploaded
            with zipfile.ZipFile(uploaded) as archive:
                names = set(archive.namelist())
                assert "content/project.json" in names
                assert "lib/net6.0-windows7.0/project.json" in names
                assert archive.read("lib/net6.0-windows7.0/project.json") == archive.read(
                    "content/project.json"
                )
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = _copy_uploaded_download(command, uploaded_nupkg)
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(
            pack_dir / "InvoiceProcessing.1.0.1.nupkg",
            include_project_json=False,
            include_content_project_json=True,
        )

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

    assert any(command[:3] == ["or", "packages", "upload"] for command in calls)


def test_execute_blocks_source_descriptor_drift_before_upload(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
    (project / "project.json").write_text(
        json.dumps({
            "name": "InvoiceProcessing",
            "projectVersion": "1.0.0",
            "dependencies": {
                "UiPath.System.Activities": "[23.10.11]",
            },
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
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            raise AssertionError("upload should not be called")
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(
            pack_dir / "InvoiceProcessing.1.0.1.nupkg",
            system_activities_version="[99.0.0]",
        )

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    with pytest.raises(RuntimeError, match="HANDOFF-SOURCE-DESCRIPTOR-MISMATCH"):
        publish_dev.execute(
            args,
            run_uip=fake_run,
            run_pack=fake_pack,
            run_review=_review_ok,
        )

    assert not any(command[:3] == ["or", "packages", "upload"] for command in calls)


def test_execute_removes_git_metadata_from_nupkg_before_upload(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
    (project / "project.json").write_text(
        json.dumps({"name": "InvoiceProcessing", "projectVersion": "1.0.0"}),
        encoding="utf-8",
    )
    calls = []
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            uploaded_nupkg = Path(command[3])
            with zipfile.ZipFile(uploaded_nupkg) as archive:
                assert "content/.git/HEAD" not in archive.namelist()
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = _copy_uploaded_download(command, uploaded_nupkg)
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(
            pack_dir / "InvoiceProcessing.1.0.1.nupkg",
            include_git_metadata=True,
        )

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

    with zipfile.ZipFile(plan.downloaded_nupkg) as archive:
        assert "content/.git/HEAD" not in archive.namelist()
    assert any(command[:3] == ["or", "packages", "upload"] for command in calls)


def test_execute_blocks_when_downloaded_package_hash_differs(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.uiproj").write_text("{}", encoding="utf-8")
    (project / "project.json").write_text(
        json.dumps({"name": "InvoiceProcessing", "projectVersion": "1.0.0"}),
        encoding="utf-8",
    )
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            uploaded_nupkg = Path(command[3])
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = _copy_uploaded_download(command, uploaded_nupkg)
            with zipfile.ZipFile(destination, "a") as archive:
                archive.writestr("content/OrchestratorChanged.txt", "changed")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    def fake_pack(project_json, pack_dir, version, timeout):
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_nupkg(pack_dir / "InvoiceProcessing.1.0.1.nupkg")

    args = publish_dev.build_parser().parse_args([
        str(project),
        "patch",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    with pytest.raises(RuntimeError, match="does not match uploaded package bytes"):
        publish_dev.execute(
            args,
            run_uip=fake_run,
            run_pack=fake_pack,
            run_review=_review_ok,
        )


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
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
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
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Message": "not logged in"}, returncode=1, result="Failure")
        if command[:2] == ["login", "--interactive"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            uploaded_nupkg = Path(command[3])
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = _copy_uploaded_download(command, uploaded_nupkg)
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
    assert calls[3] == ["login", "tenant", "set", "RPA_Desenvolvimento", "--output", "json"]


def test_ensure_login_blocks_robot_session_without_dev_tenant():
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"AuthSource": "Robot"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "Default"}])
        if command[:2] == ["login", "which"]:
            return _result(
                {"Message": "No credentials file found"},
                returncode=1,
                result="Failure",
            )
        raise AssertionError(command)

    with pytest.raises(RuntimeError) as excinfo:
        publish_dev.ensure_login(fake_run, dev_tenant="RPA_Desenvolvimento")

    message = str(excinfo.value)
    assert "cannot see required tenant(s): RPA_Desenvolvimento" in message
    assert "Available tenants: Default" in message
    assert "`uip login which` did not return reusable CLI credentials" in message
    assert calls == [
        ["login", "status", "--output", "json"],
        ["login", "tenant", "list", "--output", "json"],
        ["login", "which", "--output", "json"],
    ]


def test_ensure_login_blocks_when_dev_tenant_cannot_be_selected():
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result(
                {"Message": "tenant set failed"},
                returncode=1,
                result="Failure",
            )
        if command[:2] == ["login", "which"]:
            return _result({"Credential": "stored"})
        raise AssertionError(command)

    with pytest.raises(RuntimeError) as excinfo:
        publish_dev.ensure_login(fake_run, dev_tenant="RPA_Desenvolvimento")

    message = str(excinfo.value)
    assert "`uip login tenant set RPA_Desenvolvimento` failed" in message
    assert "`uip login which` returned an active CLI credential" in message
    assert calls == [
        ["login", "status", "--output", "json"],
        ["login", "tenant", "list", "--output", "json"],
        ["login", "tenant", "set", "RPA_Desenvolvimento", "--output", "json"],
        ["login", "which", "--output", "json"],
    ]


def test_publish_ccs_validation_uses_orchestrator_library_versions(tmp_path):
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
        assert command[:3] == ["resource", "libraries", "versions"]
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
            "resource", "libraries", "versions", "CCS_Controle",
            "--limit", "1000",
            "--output", "json",
        ],
        [
            "resource", "libraries", "versions", "CCS_SipagDirect",
            "--limit", "1000",
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
        assert command[:4] == ["resource", "libraries", "versions", "CCS_SipagNet"]
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
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            uploaded_nupkg = Path(command[3])
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = _copy_uploaded_download(command, uploaded_nupkg)
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
        ["login", "tenant", "set", "RPA_Desenvolvimento", "--output", "json"],
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
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            uploaded_nupkg = Path(command[3])
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = _copy_uploaded_download(command, uploaded_nupkg)
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
    uploaded_nupkg = None

    def fake_run(command):
        nonlocal uploaded_nupkg
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "upload"]:
            uploaded_nupkg = Path(command[3])
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = _copy_uploaded_download(command, uploaded_nupkg)
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
        _write_nupkg(
            pack_dir / "InvoiceProcessing.1.2.4.nupkg",
            system_activities_version="[25.10.1]",
        )

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
