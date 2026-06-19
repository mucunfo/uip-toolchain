import json
import subprocess
import sys
import zipfile
from pathlib import Path

from uip_engine import cli
from uip_engine.nupkg_audit import audit_nupkg, scrub_nupkg_packaging_artifacts


ROOT = Path(__file__).resolve().parent.parent


def _project_descriptor(
    package_id: str,
    version: str,
    *,
    ccs_controle_version: str = "[1.1.0]",
) -> dict:
    return {
        "name": package_id,
        "projectVersion": version,
        "targetFramework": "Windows",
        "expressionLanguage": "VisualBasic",
        "schemaVersion": "4.0",
        "studioVersion": "23.10.13",
        "main": "Main.xaml",
        "runtimeOptions": {
            "isAttended": False,
            "requiresUserInteraction": True,
            "executionType": "Workflow",
        },
        "designOptions": {
            "outputType": "Process",
            "modernBehavior": True,
            "libraryOptions": {"includeOriginalXaml": False, "privateWorkflows": []},
        },
        "arguments": {
            "input": [{
                "name": "in_RequiredTicket",
                "type": "System.String",
                "required": False,
                "hasDefault": False,
            }],
            "output": [],
        },
        "entryPoints": [{
            "filePath": "Main.xaml",
            "uniqueId": "11111111-1111-1111-1111-111111111111",
            "input": [{
                "name": "in_RequiredTicket",
                "type": (
                    "System.String, System.Private.CoreLib, Version=6.0.0.0, "
                    "Culture=neutral, PublicKeyToken=7cec85d7bea7798e"
                ),
                "required": False,
                "hasDefault": False,
            }],
            "output": [],
        }],
        "dependencies": {
            "CCS_Controle": ccs_controle_version,
            "UiPath.System.Activities": "[23.10.11]",
        },
        "isTemplate": False,
    }


def _write_process_nupkg(
    path: Path,
    *,
    include_lib_project_json: bool = True,
    include_git_metadata: bool = False,
    include_workflow_content: bool = True,
    ccs_controle_version: str = "[1.1.0]",
) -> None:
    stem = path.name.removesuffix(".nupkg")
    package_id, major, minor, patch = stem.rsplit(".", 3)
    version = ".".join([major, minor, patch])
    descriptor = _project_descriptor(
        package_id,
        version,
        ccs_controle_version=ccs_controle_version,
    )
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
        if include_lib_project_json:
            archive.writestr(
                "lib/net6.0-windows7.0/project.json",
                json.dumps(descriptor),
        )
        archive.writestr("content/project.json", json.dumps(descriptor))
        if include_workflow_content:
            archive.writestr("content/Main.xaml", "<Activity />")
        archive.writestr(f"lib/net6.0-windows7.0/{package_id}.dll", b"")
        if include_git_metadata:
            archive.writestr("content/.git/HEAD", "ref: refs/heads/main\n")


def _write_project(
    root: Path,
    folder: str,
    name: str,
    version: str = "1.0.0",
    *,
    ccs_controle_version: str = "[1.1.0]",
) -> Path:
    project = root / folder
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps(
            _project_descriptor(
                name,
                version,
                ccs_controle_version=ccs_controle_version,
            )
        ),
        encoding="utf-8",
    )
    return project


def test_audit_accepts_valid_process_package(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    _write_process_nupkg(nupkg)

    result = audit_nupkg(nupkg)

    assert result.ok
    assert result.package_id == "InvoiceProcessing"
    assert result.version == "1.0.1"
    assert result.lib_frameworks == ("net6.0-windows7.0",)


def test_audit_accepts_compiled_package_without_xaml_content(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    _write_process_nupkg(nupkg, include_workflow_content=False)

    result = audit_nupkg(nupkg)

    assert result.ok


def test_audit_flags_missing_runtime_project_json(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    _write_process_nupkg(nupkg, include_lib_project_json=False)

    result = audit_nupkg(nupkg)

    assert not result.ok
    assert any(issue.code == "UIPATH-RUNTIME-DESCRIPTOR" for issue in result.issues)


def test_audit_flags_and_scrubs_git_metadata(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    _write_process_nupkg(nupkg, include_git_metadata=True)

    result = audit_nupkg(nupkg)
    assert not result.ok
    assert any(issue.code == "PKG-BUILD-ARTIFACTS" for issue in result.issues)

    removed = scrub_nupkg_packaging_artifacts(nupkg)

    assert removed == ["content/.git/HEAD"]
    assert audit_nupkg(nupkg).ok


def test_cli_audit_nupkg_reports_failures(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    _write_process_nupkg(nupkg, include_lib_project_json=False)

    proc = subprocess.run(
        [sys.executable, "-m", "uip_engine.cli", "audit-nupkg", str(nupkg)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == cli.EXIT_ERROR
    assert "UIPATH-RUNTIME-DESCRIPTOR" in proc.stdout


def test_cli_audit_publish_handoff_accepts_expected_package_set(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(source, "RepoA", "ProjectA")
    _write_project(source, "RepoB", "ProjectB")
    _write_process_nupkg(handoff / "ProjectA.1.0.1.nupkg")
    _write_process_nupkg(handoff / "ProjectB.1.0.1.nupkg")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "uip_engine.cli",
            "audit-publish-handoff",
            "patch",
            str(source),
            str(handoff),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == cli.EXIT_OK
    assert "HANDOFF audit: 2/2 expected packages passed" in proc.stdout


def test_cli_audit_publish_handoff_flags_source_descriptor_mismatch(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(source, "RepoA", "ProjectA", ccs_controle_version="[1.1.0]")
    _write_process_nupkg(
        handoff / "ProjectA.1.0.1.nupkg",
        ccs_controle_version="[9.9.9]",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "uip_engine.cli",
            "audit-publish-handoff",
            "patch",
            str(source),
            str(handoff),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == cli.EXIT_ERROR
    assert "HANDOFF-SOURCE-DESCRIPTOR-MISMATCH" in proc.stdout
    assert "dependencies" in proc.stdout


def test_cli_audit_publish_handoff_flags_wrong_version_as_missing_and_unexpected(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(source, "RepoA", "ProjectA")
    _write_process_nupkg(handoff / "ProjectA.1.0.2.nupkg")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "uip_engine.cli",
            "audit-publish-handoff",
            "patch",
            str(source),
            str(handoff),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == cli.EXIT_ERROR
    assert "HANDOFF-MISSING-PACKAGE" in proc.stdout
    assert "ProjectA.1.0.1.nupkg" in proc.stdout
    assert "HANDOFF-UNEXPECTED-PACKAGE" in proc.stdout
    assert "ProjectA.1.0.2.nupkg" in proc.stdout


def test_cli_audit_publish_handoff_flags_invalid_matching_package(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(source, "RepoA", "ProjectA")
    _write_process_nupkg(
        handoff / "ProjectA.1.0.1.nupkg",
        include_lib_project_json=False,
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "uip_engine.cli",
            "audit-publish-handoff",
            "patch",
            str(source),
            str(handoff),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == cli.EXIT_ERROR
    assert "UIPATH-RUNTIME-DESCRIPTOR" in proc.stdout
