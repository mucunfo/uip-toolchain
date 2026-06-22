import json
import re
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path

import pytest

from uip_engine import cli
from uip_engine import nupkg_audit as nupkg_audit_module
from uip_engine.handoff_audit import ExpectedHandoffPackage, _audit_source_descriptor_match
from uip_engine.nupkg_audit import audit_nupkg, scrub_nupkg_packaging_artifacts


ROOT = Path(__file__).resolve().parent.parent


def _issue_codes(path: Path, prefixes: tuple[str, ...]) -> set[str]:
    pattern = r'"((?:' + "|".join(re.escape(prefix) for prefix in prefixes) + r')-[A-Z0-9-]+)"'
    return set(re.findall(pattern, path.read_text(encoding="utf-8")))


def _project_descriptor(
    package_id: str,
    version: str,
    *,
    ccs_controle_version: str = "[1.1.0]",
    entry_points: list[dict] | None = None,
) -> dict:
    if entry_points is None:
        entry_points = [{
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
        }]
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
        "entryPoints": entry_points,
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
    entry_points: list[dict] | None = None,
    descriptor_overrides: dict | None = None,
    extra_members: dict[str, str | bytes] | None = None,
) -> None:
    stem = path.name.removesuffix(".nupkg")
    package_id, major, minor, patch = stem.rsplit(".", 3)
    version = ".".join([major, minor, patch])
    descriptor = _project_descriptor(
        package_id,
        version,
        ccs_controle_version=ccs_controle_version,
        entry_points=entry_points,
    )
    if descriptor_overrides:
        descriptor.update(descriptor_overrides)
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
        for member, payload in (extra_members or {}).items():
            archive.writestr(member, payload)


def _write_project(
    root: Path,
    folder: str,
    name: str,
    version: str = "1.0.0",
    *,
    ccs_controle_version: str = "[1.1.0]",
    entry_points: list[dict] | None = None,
) -> Path:
    project = root / folder
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps(
            _project_descriptor(
                name,
                version,
                ccs_controle_version=ccs_controle_version,
                entry_points=entry_points,
            )
        ),
        encoding="utf-8",
    )
    return project


def _write_matrix_nupkg(
    path: Path,
    *,
    include_content_types: bool = True,
    include_nuspec: bool = True,
    nuspec_xml: str | None = None,
    nuspec_id: str | None = None,
    nuspec_version: str | None = None,
    nuspec_frameworks: tuple[str, ...] = ("net6.0-windows7.0",),
    lib_frameworks: tuple[str, ...] = ("net6.0-windows7.0",),
    descriptor: dict | list | str | None = None,
    content_descriptor: dict | list | str | None = None,
    include_lib_project_json: bool = True,
    include_content_project_json: bool = True,
    include_runtime_dll: bool = True,
    include_main: bool = True,
    dependencies_xml: str = "",
    duplicate_main: bool = False,
    extra_members: dict[str, str | bytes] | None = None,
) -> None:
    try:
        stem = path.name.removesuffix(".nupkg")
        package_id, major, minor, patch = stem.rsplit(".", 3)
        version = ".".join([major, minor, patch])
    except ValueError:
        package_id = "InvoiceProcessing"
        version = "1.0.1"
    descriptor_payload = descriptor
    if descriptor_payload is None:
        descriptor_payload = _project_descriptor(package_id, version)
    content_payload = descriptor_payload if content_descriptor is None else content_descriptor

    def _json_bytes(payload) -> str:
        if isinstance(payload, str):
            return payload
        return json.dumps(payload)

    with zipfile.ZipFile(path, "w") as archive:
        if include_content_types:
            archive.writestr("[Content_Types].xml", "<Types />")
        if include_nuspec:
            if nuspec_xml is None:
                groups = "\n".join(
                    f'      <group targetFramework="{framework}" />'
                    for framework in nuspec_frameworks
                )
                nuspec_xml = "\n".join([
                    '<?xml version="1.0" encoding="utf-8"?>',
                    '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">',
                    "  <metadata>",
                    f"    <id>{nuspec_id if nuspec_id is not None else package_id}</id>",
                    f"    <version>{nuspec_version if nuspec_version is not None else version}</version>",
                    "    <dependencies>",
                    groups,
                    dependencies_xml,
                    "    </dependencies>",
                    "  </metadata>",
                    "</package>",
                ])
            archive.writestr(f"{package_id}.nuspec", nuspec_xml)
        if include_main:
            archive.writestr("content/Main.xaml", "<Activity />")
            if duplicate_main:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr("content/Main.xaml", "<Activity />")
        if include_content_project_json:
            archive.writestr("content/project.json", _json_bytes(content_payload))
        for framework in lib_frameworks:
            if include_lib_project_json:
                archive.writestr(f"lib/{framework}/project.json", _json_bytes(descriptor_payload))
            if include_runtime_dll:
                archive.writestr(f"lib/{framework}/{package_id}.dll", b"")
        for member, payload in (extra_members or {}).items():
            archive.writestr(member, payload)


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


@pytest.mark.parametrize(
    ("scenario", "expected_code"),
    [
        ("missing_file", "NUPKG-MISSING"),
        ("bad_filename", "NUPKG-FILENAME"),
        ("invalid_zip", "ZIP-INVALID"),
        ("missing_content_types", "NUPKG-CONTENT-TYPES"),
        ("duplicate_member", "ZIP-DUPLICATE-MEMBER"),
        ("missing_nuspec", "NUSPEC-COUNT"),
        ("invalid_nuspec_xml", "NUSPEC-XML"),
        ("missing_nuspec_metadata", "NUSPEC-METADATA"),
        ("missing_nuspec_id", "NUSPEC-ID"),
        ("missing_nuspec_version", "NUSPEC-VERSION"),
        ("missing_nuspec_dependency_version", "NUSPEC-DEPENDENCY-VERSION"),
        ("filename_id_mismatch", "NUPKG-ID-MISMATCH"),
        ("filename_version_mismatch", "NUPKG-VERSION-MISMATCH"),
        ("filename_expected_id_mismatch", "NUPKG-EXPECTED-ID"),
        ("filename_expected_version_mismatch", "NUPKG-EXPECTED-VERSION"),
        ("expected_id_mismatch", "NUSPEC-EXPECTED-ID"),
        ("expected_version_mismatch", "NUSPEC-EXPECTED-VERSION"),
        ("no_lib", "NUPKG-NO-LIB"),
        ("no_nuspec_tfm", "NUSPEC-NO-TFM"),
        ("tfm_not_declared_in_nuspec", "TFM-NUSPEC-MISSING"),
        ("tfm_declared_missing_lib", "TFM-LIB-MISSING"),
        ("dev_incompatible_tfm", "TFM-DEV-INCOMPATIBLE"),
        ("runtime_dll_missing", "RUNTIME-DLL"),
    ],
)
def test_audit_nupkg_blocks_container_nuspec_tfm_and_runtime_matrix(
    tmp_path,
    scenario,
    expected_code,
):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    expected_id = None
    expected_version = None
    if scenario == "missing_file":
        pass
    elif scenario == "bad_filename":
        nupkg = tmp_path / "bad.nupkg"
        _write_matrix_nupkg(nupkg)
    elif scenario == "invalid_zip":
        nupkg.write_text("not a zip", encoding="utf-8")
    elif scenario == "missing_content_types":
        _write_matrix_nupkg(nupkg, include_content_types=False)
    elif scenario == "duplicate_member":
        _write_matrix_nupkg(nupkg, duplicate_main=True)
    elif scenario == "missing_nuspec":
        _write_matrix_nupkg(nupkg, include_nuspec=False)
    elif scenario == "invalid_nuspec_xml":
        _write_matrix_nupkg(nupkg, nuspec_xml="<package")
    elif scenario == "missing_nuspec_metadata":
        _write_matrix_nupkg(nupkg, nuspec_xml="<package />")
    elif scenario == "missing_nuspec_id":
        _write_matrix_nupkg(
            nupkg,
            nuspec_xml=(
                "<package><metadata><version>1.0.1</version></metadata></package>"
            ),
        )
    elif scenario == "missing_nuspec_version":
        _write_matrix_nupkg(
            nupkg,
            nuspec_xml=(
                "<package><metadata><id>InvoiceProcessing</id></metadata></package>"
            ),
        )
    elif scenario == "missing_nuspec_dependency_version":
        _write_matrix_nupkg(
            nupkg,
            dependencies_xml='      <dependency id="UiPath.System.Activities" />',
        )
    elif scenario == "filename_id_mismatch":
        _write_matrix_nupkg(nupkg, nuspec_id="OtherPackage")
    elif scenario == "filename_version_mismatch":
        _write_matrix_nupkg(nupkg, nuspec_version="9.9.9")
    elif scenario == "filename_expected_id_mismatch":
        expected_id = "OtherPackage"
        _write_matrix_nupkg(nupkg)
    elif scenario == "filename_expected_version_mismatch":
        expected_version = "9.9.9"
        _write_matrix_nupkg(nupkg)
    elif scenario == "expected_id_mismatch":
        expected_id = "OtherPackage"
        _write_matrix_nupkg(nupkg)
    elif scenario == "expected_version_mismatch":
        expected_version = "9.9.9"
        _write_matrix_nupkg(nupkg)
    elif scenario == "no_lib":
        _write_matrix_nupkg(nupkg, lib_frameworks=())
    elif scenario == "no_nuspec_tfm":
        _write_matrix_nupkg(nupkg, nuspec_frameworks=())
    elif scenario == "tfm_not_declared_in_nuspec":
        _write_matrix_nupkg(nupkg, nuspec_frameworks=("net8.0-windows7.0",))
    elif scenario == "tfm_declared_missing_lib":
        _write_matrix_nupkg(nupkg, lib_frameworks=("net8.0-windows7.0",))
    elif scenario == "dev_incompatible_tfm":
        _write_matrix_nupkg(
            nupkg,
            lib_frameworks=("net8.0-windows7.0",),
            nuspec_frameworks=("net8.0-windows7.0",),
        )
    elif scenario == "runtime_dll_missing":
        _write_matrix_nupkg(nupkg, include_runtime_dll=False)

    result = audit_nupkg(nupkg, expected_id=expected_id, expected_version=expected_version)

    assert any(issue.code == expected_code for issue in result.issues)


def test_audit_nupkg_reports_zip_corrupt_member(tmp_path, monkeypatch):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    _write_matrix_nupkg(nupkg)
    real_zip_file = zipfile.ZipFile

    class CorruptZipFile:
        def __init__(self, *args, **kwargs):
            self._archive = real_zip_file(*args, **kwargs)

        def __enter__(self):
            self._archive.__enter__()
            return self

        def __exit__(self, *args):
            return self._archive.__exit__(*args)

        def testzip(self):
            return "content/Main.xaml"

        def namelist(self):
            return self._archive.namelist()

        def read(self, *args, **kwargs):
            return self._archive.read(*args, **kwargs)

    monkeypatch.setattr(nupkg_audit_module.zipfile, "ZipFile", CorruptZipFile)

    result = audit_nupkg(nupkg)

    assert any(issue.code == "ZIP-CORRUPT-MEMBER" for issue in result.issues)


def test_audit_nupkg_reports_zip_io_error(tmp_path, monkeypatch):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    _write_matrix_nupkg(nupkg)

    def raise_os_error(*args, **kwargs):
        raise OSError("package locked")

    monkeypatch.setattr(nupkg_audit_module.zipfile, "ZipFile", raise_os_error)

    result = audit_nupkg(nupkg)

    assert any(issue.code == "NUPKG-IO" for issue in result.issues)


@pytest.mark.parametrize(
    ("scenario", "expected_code"),
    [
        ("project_json_parse", "PROJECT-JSON-PARSE"),
        ("project_json_root", "PROJECT-JSON-ROOT"),
        ("descriptor_drift", "PROJECT-JSON-DESCRIPTOR-DRIFT"),
        ("project_name_missing", "PROJECT-NAME"),
        ("project_name_mismatch", "PROJECT-NAME-MISMATCH"),
        ("project_version_missing", "PROJECT-VERSION"),
        ("project_version_mismatch", "PROJECT-VERSION-MISMATCH"),
        ("target_framework", "PROJECT-TARGET-FRAMEWORK"),
        ("output_type", "PROJECT-OUTPUT-TYPE"),
        ("main_missing", "PROJECT-MAIN"),
        ("main_file_missing", "PROJECT-MAIN-FILE"),
        ("entrypoints_missing", "PROJECT-ENTRYPOINTS"),
        ("entrypoint_not_object", "PROJECT-ENTRYPOINT"),
        ("entrypoint_filepath_missing", "PROJECT-ENTRYPOINT-FILEPATH"),
        ("entrypoint_file_missing", "PROJECT-ENTRYPOINT-FILE"),
        ("dependency_version_empty", "PROJECT-DEPENDENCY-VERSION"),
        ("ccs_dependency_not_exact", "PROJECT-DEPENDENCY-PIN"),
        ("dependencies_not_object", "PROJECT-DEPENDENCIES"),
    ],
)
def test_audit_nupkg_blocks_project_descriptor_matrix(tmp_path, scenario, expected_code):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    descriptor = _project_descriptor("InvoiceProcessing", "1.0.1")
    kwargs = {}
    if scenario == "project_json_parse":
        kwargs["descriptor"] = "{not-json"
    elif scenario == "project_json_root":
        kwargs["descriptor"] = ["not", "object"]
    elif scenario == "descriptor_drift":
        content_descriptor = dict(descriptor)
        content_descriptor["projectVersion"] = "9.9.9"
        kwargs["content_descriptor"] = content_descriptor
    elif scenario == "project_name_missing":
        descriptor.pop("name")
    elif scenario == "project_name_mismatch":
        descriptor["name"] = "OtherPackage"
    elif scenario == "project_version_missing":
        descriptor.pop("projectVersion")
    elif scenario == "project_version_mismatch":
        descriptor["projectVersion"] = "9.9.9"
    elif scenario == "target_framework":
        descriptor["targetFramework"] = "WindowsLegacy"
    elif scenario == "output_type":
        descriptor["designOptions"] = {"outputType": "Library"}
    elif scenario == "main_missing":
        descriptor.pop("main")
    elif scenario == "main_file_missing":
        descriptor["main"] = "Missing.xaml"
    elif scenario == "entrypoints_missing":
        descriptor["entryPoints"] = []
    elif scenario == "entrypoint_not_object":
        descriptor["entryPoints"] = ["Main.xaml"]
    elif scenario == "entrypoint_filepath_missing":
        descriptor["entryPoints"] = [{"uniqueId": "missing-filepath"}]
    elif scenario == "entrypoint_file_missing":
        descriptor["entryPoints"] = [{"filePath": "Missing.xaml"}]
    elif scenario == "dependency_version_empty":
        descriptor["dependencies"] = {"UiPath.System.Activities": ""}
    elif scenario == "ccs_dependency_not_exact":
        descriptor["dependencies"] = {"CCS_Controle": "1.1.0"}
    elif scenario == "dependencies_not_object":
        descriptor["dependencies"] = []
    kwargs["descriptor"] = kwargs.get("descriptor", descriptor)

    _write_matrix_nupkg(nupkg, **kwargs)

    result = audit_nupkg(nupkg)

    assert any(issue.code == expected_code for issue in result.issues)


def test_audit_nupkg_warns_for_non_ccs_dependency_not_exact(tmp_path):
    nupkg = tmp_path / "InvoiceProcessing.1.0.1.nupkg"
    descriptor = _project_descriptor("InvoiceProcessing", "1.0.1")
    descriptor["dependencies"] = {"UiPath.System.Activities": "23.10.11"}
    _write_matrix_nupkg(nupkg, descriptor=descriptor)

    result = audit_nupkg(nupkg)

    assert result.ok
    assert any(
        issue.code == "PROJECT-DEPENDENCY-PIN" and issue.severity == "WARN"
        for issue in result.issues
    )


def _run_handoff_audit(source: Path, *handoff_paths: Path):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "uip_engine.cli",
            "audit-publish-handoff",
            "patch",
            str(source),
            *(str(path) for path in handoff_paths),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_cli_audit_publish_handoff_blocks_empty_source_and_empty_handoff(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()

    proc = _run_handoff_audit(source, handoff)

    assert proc.returncode == cli.EXIT_ERROR
    assert "HANDOFF-NO-PROJECTS" in proc.stdout
    assert "HANDOFF-NO-NUPKGS" in proc.stdout


def test_cli_audit_publish_handoff_blocks_duplicate_expected_package(tmp_path):
    source = tmp_path / "source"
    handoff_a = tmp_path / "handoff-a"
    handoff_b = tmp_path / "handoff-b"
    source.mkdir()
    handoff_a.mkdir()
    handoff_b.mkdir()
    _write_project(source, "RepoA", "ProjectA")
    _write_process_nupkg(handoff_a / "ProjectA.1.0.1.nupkg")
    _write_process_nupkg(handoff_b / "ProjectA.1.0.1.nupkg")

    proc = _run_handoff_audit(source, handoff_a, handoff_b)

    assert proc.returncode == cli.EXIT_ERROR
    assert "HANDOFF-DUPLICATE-PACKAGE" in proc.stdout


def test_source_descriptor_match_reports_unreadable_source_project_json(tmp_path):
    project = _write_project(tmp_path, "RepoA", "ProjectA")
    (project / "project.json").write_text("{not-json", encoding="utf-8")
    nupkg = tmp_path / "ProjectA.1.0.1.nupkg"
    _write_process_nupkg(nupkg)
    expected = ExpectedHandoffPackage(
        folder_name="RepoA",
        project_root=project,
        package_id="ProjectA",
        current_version="1.0.0",
        expected_version="1.0.1",
    )

    issues = _audit_source_descriptor_match(nupkg, expected)

    assert any(issue.code == "HANDOFF-SOURCE-DESCRIPTOR" for issue in issues)


def test_source_descriptor_match_reports_unreadable_package_project_json(tmp_path):
    project = _write_project(tmp_path, "RepoA", "ProjectA")
    nupkg = tmp_path / "ProjectA.1.0.1.nupkg"
    _write_matrix_nupkg(
        nupkg,
        include_lib_project_json=False,
        include_content_project_json=False,
    )
    expected = ExpectedHandoffPackage(
        folder_name="RepoA",
        project_root=project,
        package_id="ProjectA",
        current_version="1.0.0",
        expected_version="1.0.1",
    )

    issues = _audit_source_descriptor_match(nupkg, expected)

    assert any(issue.code == "HANDOFF-PACKAGE-DESCRIPTOR" for issue in issues)


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


def test_cli_audit_publish_handoff_accepts_canonicalized_optional_entrypoints(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(source, "RepoA", "ProjectA")
    _write_process_nupkg(
        handoff / "ProjectA.1.0.1.nupkg",
        entry_points=[{"filePath": "Main.xaml"}],
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

    assert proc.returncode == cli.EXIT_OK
    assert "HANDOFF audit: 1/1 expected packages passed" in proc.stdout


def test_cli_audit_publish_handoff_treats_null_entrypoint_input_as_optional(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(
        source,
        "RepoA",
        "ProjectA",
        entry_points=[{
            "filePath": "Main.xaml",
            "input": None,
            "output": [],
        }],
    )
    _write_process_nupkg(
        handoff / "ProjectA.1.0.1.nupkg",
        entry_points=[{"filePath": "Main.xaml"}],
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

    assert proc.returncode == cli.EXIT_OK
    assert "HANDOFF audit: 1/1 expected packages passed" in proc.stdout


def test_cli_audit_publish_handoff_accepts_canonicalized_optional_argument_metadata(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(source, "RepoA", "ProjectA")
    _write_process_nupkg(
        handoff / "ProjectA.1.0.1.nupkg",
        descriptor_overrides={
            "arguments": {
                "input": [{
                    "name": "in_RequiredTicket",
                    "type": "System.String",
                }],
                "output": [],
            }
        },
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

    assert proc.returncode == cli.EXIT_OK
    assert "HANDOFF audit: 1/1 expected packages passed" in proc.stdout


def test_cli_audit_publish_handoff_blocks_missing_optional_argument_input(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(source, "RepoA", "ProjectA")
    _write_process_nupkg(
        handoff / "ProjectA.1.0.1.nupkg",
        descriptor_overrides={"arguments": {"input": [], "output": []}},
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
    assert "arguments.input" in proc.stdout


def test_cli_audit_publish_handoff_blocks_missing_required_argument_input(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    project = _write_project(source, "RepoA", "ProjectA")
    descriptor = _project_descriptor("ProjectA", "1.0.0")
    descriptor["arguments"] = {
        "input": [{
            "name": "in_RequiredTicket",
            "type": "System.String",
            "required": True,
            "hasDefault": False,
        }],
        "output": [],
    }
    (project / "project.json").write_text(json.dumps(descriptor), encoding="utf-8")
    _write_process_nupkg(
        handoff / "ProjectA.1.0.1.nupkg",
        descriptor_overrides={"arguments": {"input": [], "output": []}},
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
    assert "arguments.input" in proc.stdout


def test_cli_audit_publish_handoff_blocks_missing_required_entrypoint_input(tmp_path):
    source = tmp_path / "source"
    handoff = tmp_path / "handoff"
    source.mkdir()
    handoff.mkdir()
    _write_project(
        source,
        "RepoA",
        "ProjectA",
        entry_points=[{
            "filePath": "Main.xaml",
            "uniqueId": "11111111-1111-1111-1111-111111111111",
            "input": [{
                "name": "in_RequiredTicket",
                "type": "System.String",
                "required": True,
                "hasDefault": False,
            }],
            "output": [],
        }],
    )
    _write_process_nupkg(
        handoff / "ProjectA.1.0.1.nupkg",
        entry_points=[{"filePath": "Main.xaml"}],
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
    assert "entryPoints" in proc.stdout


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


def test_nupkg_audit_issue_codes_have_named_test_coverage():
    prefixes = (
        "NUPKG",
        "ZIP",
        "PKG",
        "NUSPEC",
        "TFM",
        "UIPATH",
        "PROJECT",
        "RUNTIME",
    )
    source_codes = _issue_codes(ROOT / "src" / "uip_engine" / "nupkg_audit.py", prefixes)
    test_codes = _issue_codes(Path(__file__), prefixes)

    assert source_codes - test_codes == set()


def test_handoff_audit_issue_codes_have_named_test_coverage():
    source_codes = _issue_codes(ROOT / "src" / "uip_engine" / "handoff_audit.py", ("HANDOFF",))
    test_codes = _issue_codes(Path(__file__), ("HANDOFF",))

    assert source_codes - test_codes == set()
