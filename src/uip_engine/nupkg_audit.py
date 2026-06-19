"""Read-only audit for UiPath ``.nupkg`` process packages."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ERROR = "ERROR"
WARN = "WARN"

DEFAULT_DEV_COMPATIBLE_TFMS = frozenset({
    "net6.0-windows",
    "net6.0-windows7.0",
})

_FILENAME_RE = re.compile(
    r"^(?P<id>.+)\.(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z][0-9A-Za-z_.-]*)?)\.nupkg$",
    re.IGNORECASE,
)

_EXACT_DEP_RE = re.compile(r"^\[\s*[^,\]\s]+\s*\]$")

_BLOCKED_MEMBER_EXACT = frozenset({
    ".git",
    "content/.git",
    "content/.tmp",
    "content/.local",
    "content/.publish-dev-handoff",
    "content/.pytest_cache",
    "content/__pycache__",
})

_BLOCKED_MEMBER_PREFIXES = tuple(f"{name}/" for name in sorted(_BLOCKED_MEMBER_EXACT))


@dataclass(frozen=True)
class NupkgAuditIssue:
    severity: str
    code: str
    message: str
    member: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.member is not None:
            payload["member"] = self.member
        return payload


@dataclass(frozen=True)
class NupkgAuditResult:
    path: Path
    sha256: str | None
    package_id: str | None
    version: str | None
    filename_id: str | None
    filename_version: str | None
    lib_frameworks: tuple[str, ...]
    nuspec_frameworks: tuple[str, ...]
    project_json_frameworks: tuple[str, ...]
    issues: tuple[NupkgAuditIssue, ...]

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == ERROR)

    @property
    def warn_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == WARN)

    @property
    def ok(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "package_id": self.package_id,
            "version": self.version,
            "filename_id": self.filename_id,
            "filename_version": self.filename_version,
            "lib_frameworks": list(self.lib_frameworks),
            "nuspec_frameworks": list(self.nuspec_frameworks),
            "project_json_frameworks": list(self.project_json_frameworks),
            "ok": self.ok,
            "errors": self.error_count,
            "warnings": self.warn_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_blocked_packaging_artifact_member(member_name: str) -> bool:
    normalized = _normalize_member(member_name).lower()
    return normalized in _BLOCKED_MEMBER_EXACT or normalized.startswith(_BLOCKED_MEMBER_PREFIXES)


def scrub_nupkg_packaging_artifacts(nupkg: Path) -> list[str]:
    """Remove source-control/build artifacts from a package, preserving all other entries."""
    removed: list[str] = []
    temp = nupkg.with_name(f"{nupkg.name}.tmp")
    if temp.exists():
        temp.unlink()

    try:
        with zipfile.ZipFile(nupkg) as source:
            entries = source.infolist()
            with zipfile.ZipFile(
                temp,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True,
            ) as target:
                for entry in entries:
                    if is_blocked_packaging_artifact_member(entry.filename):
                        removed.append(entry.filename)
                        continue
                    target.writestr(entry, source.read(entry.filename))
    except Exception:
        if temp.exists():
            temp.unlink()
        raise

    if removed:
        temp.replace(nupkg)
    else:
        temp.unlink()
    return removed


def audit_nupkg(
    nupkg: Path,
    *,
    expected_id: str | None = None,
    expected_version: str | None = None,
    require_dev_compatible: bool = True,
    compatible_tfms: frozenset[str] = DEFAULT_DEV_COMPATIBLE_TFMS,
) -> NupkgAuditResult:
    path = Path(nupkg)
    issues: list[NupkgAuditIssue] = []
    package_id: str | None = None
    version: str | None = None
    filename_id: str | None = None
    filename_version: str | None = None
    lib_frameworks: set[str] = set()
    nuspec_frameworks: set[str] = set()
    project_json_frameworks: set[str] = set()
    sha256: str | None = None

    match = _FILENAME_RE.match(path.name)
    if match:
        filename_id = match.group("id")
        filename_version = match.group("version")
    else:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUPKG-FILENAME",
            "file name must be <package-id>.<semver>.nupkg",
        ))

    if expected_id and filename_id and filename_id != expected_id:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUPKG-EXPECTED-ID",
            f"file package id is {filename_id}, expected {expected_id}",
        ))
    if expected_version and filename_version and filename_version != expected_version:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUPKG-EXPECTED-VERSION",
            f"file package version is {filename_version}, expected {expected_version}",
        ))

    if not path.is_file():
        issues.append(NupkgAuditIssue(ERROR, "NUPKG-MISSING", "package file not found"))
        return _result(
            path,
            sha256,
            package_id,
            version,
            filename_id,
            filename_version,
            lib_frameworks,
            nuspec_frameworks,
            project_json_frameworks,
            issues,
        )

    sha256 = sha256_file(path)

    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "ZIP-CORRUPT-MEMBER",
                    f"zip CRC check failed for {bad_member}",
                    bad_member,
                ))

            names = [_normalize_member(name) for name in archive.namelist()]
            lower_to_original: dict[str, str] = {}
            duplicates: list[str] = []
            for original in names:
                lowered = original.lower()
                if lowered in lower_to_original:
                    duplicates.append(original)
                else:
                    lower_to_original[lowered] = original

            if duplicates:
                examples = ", ".join(duplicates[:5])
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "ZIP-DUPLICATE-MEMBER",
                    f"package contains duplicate member names; examples: {examples}",
                ))

            if "[content_types].xml" not in lower_to_original:
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "NUPKG-CONTENT-TYPES",
                    "package is missing [Content_Types].xml",
                ))

            blocked = [name for name in names if is_blocked_packaging_artifact_member(name)]
            if blocked:
                examples = ", ".join(blocked[:5])
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "PKG-BUILD-ARTIFACTS",
                    f"package contains source-control/build artifacts ({len(blocked)} member(s)); "
                    f"examples: {examples}",
                    blocked[0],
                ))

            nuspec_names = [
                name for name in names
                if name.lower().endswith(".nuspec") and "/" not in name
            ]
            if len(nuspec_names) != 1:
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "NUSPEC-COUNT",
                    f"package must contain exactly one root .nuspec; found {len(nuspec_names)}",
                ))
            else:
                package_id, version = _audit_nuspec(
                    archive,
                    nuspec_names[0],
                    issues,
                    nuspec_frameworks,
                )

            for name in names:
                parts = name.split("/")
                if len(parts) >= 3 and parts[0].lower() == "lib" and parts[1]:
                    framework = parts[1]
                    lib_frameworks.add(framework)
                    if parts[2].lower() == "project.json":
                        project_json_frameworks.add(framework)

            _audit_package_identity(
                issues,
                package_id=package_id,
                version=version,
                filename_id=filename_id,
                filename_version=filename_version,
                expected_id=expected_id,
                expected_version=expected_version,
            )
            _audit_frameworks(
                issues,
                lib_frameworks=lib_frameworks,
                nuspec_frameworks=nuspec_frameworks,
                project_json_frameworks=project_json_frameworks,
                require_dev_compatible=require_dev_compatible,
                compatible_tfms=compatible_tfms,
            )
            _audit_project_json_descriptors(
                archive,
                names,
                issues,
                package_id=package_id,
                version=version,
                project_json_frameworks=project_json_frameworks,
            )
            _audit_runtime_files(
                names,
                issues,
                package_id=package_id,
                lib_frameworks=lib_frameworks,
            )
    except zipfile.BadZipFile:
        issues.append(NupkgAuditIssue(ERROR, "ZIP-INVALID", "file is not a valid zip/.nupkg"))
    except OSError as exc:
        issues.append(NupkgAuditIssue(ERROR, "NUPKG-IO", f"could not read package: {exc}"))

    return _result(
        path,
        sha256,
        package_id,
        version,
        filename_id,
        filename_version,
        lib_frameworks,
        nuspec_frameworks,
        project_json_frameworks,
        issues,
    )


def collect_nupkgs(paths: list[Path], *, recursive: bool = False) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            pattern = "**/*.nupkg" if recursive else "*.nupkg"
            found.extend(sorted(path.glob(pattern)))
        else:
            found.append(path)
    return sorted(dict.fromkeys(found))


def format_audit_result(result: NupkgAuditResult, *, errors_only: bool = False) -> str:
    status = "PASS" if result.ok else "FAIL"
    package = result.package_id or result.filename_id or result.path.stem
    version = result.version or result.filename_version or "(unknown)"
    lines = [
        f"{status} {result.path}",
        f"  package: {package} {version}",
        f"  sha256 : {result.sha256 or '(unavailable)'}",
        f"  tfms   : {', '.join(result.lib_frameworks) if result.lib_frameworks else '(none)'}",
    ]
    selected = [
        issue for issue in result.issues
        if not errors_only or issue.severity == ERROR
    ]
    for issue in selected:
        member = f" [{issue.member}]" if issue.member else ""
        lines.append(f"  - {issue.severity} {issue.code}{member}: {issue.message}")
    return "\n".join(lines)


def format_audit_summary(results: list[NupkgAuditResult]) -> str:
    total = len(results)
    failed = sum(1 for result in results if not result.ok)
    warnings = sum(result.warn_count for result in results)
    lines = [
        f"NUPKG audit: {total - failed}/{total} passed, failed={failed}, warnings={warnings}",
    ]
    for result in results:
        lines.append(format_audit_result(result))
    return "\n\n".join(lines)


def raise_for_audit_errors(result: NupkgAuditResult, *, context: str) -> None:
    if result.ok:
        return
    raise RuntimeError(f"{context}\n{format_audit_result(result, errors_only=True)}")


def _result(
    path: Path,
    sha256: str | None,
    package_id: str | None,
    version: str | None,
    filename_id: str | None,
    filename_version: str | None,
    lib_frameworks: set[str],
    nuspec_frameworks: set[str],
    project_json_frameworks: set[str],
    issues: list[NupkgAuditIssue],
) -> NupkgAuditResult:
    return NupkgAuditResult(
        path=path,
        sha256=sha256,
        package_id=package_id,
        version=version,
        filename_id=filename_id,
        filename_version=filename_version,
        lib_frameworks=tuple(sorted(lib_frameworks)),
        nuspec_frameworks=tuple(sorted(nuspec_frameworks)),
        project_json_frameworks=tuple(sorted(project_json_frameworks)),
        issues=tuple(issues),
    )


def _normalize_member(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, child_name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == child_name and child.text and child.text.strip():
            return child.text.strip()
    return None


def _audit_nuspec(
    archive: zipfile.ZipFile,
    nuspec_name: str,
    issues: list[NupkgAuditIssue],
    frameworks: set[str],
) -> tuple[str | None, str | None]:
    try:
        root = ET.fromstring(archive.read(nuspec_name))
    except ET.ParseError as exc:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUSPEC-XML",
            f"nuspec is not valid XML: {exc}",
            nuspec_name,
        ))
        return None, None

    metadata = None
    for element in root.iter():
        if _local_name(element.tag) == "metadata":
            metadata = element
            break
    if metadata is None:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUSPEC-METADATA",
            "nuspec is missing <metadata>",
            nuspec_name,
        ))
        return None, None

    package_id = _child_text(metadata, "id")
    version = _child_text(metadata, "version")
    if not package_id:
        issues.append(NupkgAuditIssue(ERROR, "NUSPEC-ID", "nuspec is missing package id", nuspec_name))
    if not version:
        issues.append(NupkgAuditIssue(ERROR, "NUSPEC-VERSION", "nuspec is missing version", nuspec_name))

    for element in root.iter():
        if _local_name(element.tag) == "group":
            target = element.attrib.get("targetFramework")
            if target:
                frameworks.add(target)
        if _local_name(element.tag) == "dependency":
            dep_id = element.attrib.get("id", "").strip()
            dep_version = element.attrib.get("version", "").strip()
            if dep_id and not dep_version:
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "NUSPEC-DEPENDENCY-VERSION",
                    f"nuspec dependency {dep_id} is missing a version",
                    nuspec_name,
                ))

    return package_id, version


def _audit_package_identity(
    issues: list[NupkgAuditIssue],
    *,
    package_id: str | None,
    version: str | None,
    filename_id: str | None,
    filename_version: str | None,
    expected_id: str | None,
    expected_version: str | None,
) -> None:
    if package_id and filename_id and package_id != filename_id:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUPKG-ID-MISMATCH",
            f"filename package id is {filename_id}, nuspec id is {package_id}",
        ))
    if version and filename_version and version != filename_version:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUPKG-VERSION-MISMATCH",
            f"filename version is {filename_version}, nuspec version is {version}",
        ))
    if expected_id and package_id and package_id != expected_id:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUSPEC-EXPECTED-ID",
            f"nuspec package id is {package_id}, expected {expected_id}",
        ))
    if expected_version and version and version != expected_version:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUSPEC-EXPECTED-VERSION",
            f"nuspec version is {version}, expected {expected_version}",
        ))


def _audit_frameworks(
    issues: list[NupkgAuditIssue],
    *,
    lib_frameworks: set[str],
    nuspec_frameworks: set[str],
    project_json_frameworks: set[str],
    require_dev_compatible: bool,
    compatible_tfms: frozenset[str],
) -> None:
    if not lib_frameworks:
        issues.append(NupkgAuditIssue(ERROR, "NUPKG-NO-LIB", "package has no lib/<tfm>/ entries"))
    if not nuspec_frameworks:
        issues.append(NupkgAuditIssue(
            ERROR,
            "NUSPEC-NO-TFM",
            "nuspec has no dependency group targetFramework",
        ))

    missing_in_nuspec = sorted(lib_frameworks - nuspec_frameworks)
    if missing_in_nuspec:
        issues.append(NupkgAuditIssue(
            ERROR,
            "TFM-NUSPEC-MISSING",
            "lib target framework(s) missing from nuspec dependency groups: "
            + ", ".join(missing_in_nuspec),
        ))

    missing_in_lib = sorted(nuspec_frameworks - lib_frameworks)
    if missing_in_lib:
        issues.append(NupkgAuditIssue(
            ERROR,
            "TFM-LIB-MISSING",
            "nuspec target framework(s) missing from lib folders: "
            + ", ".join(missing_in_lib),
        ))

    descriptor_missing = sorted(lib_frameworks - project_json_frameworks)
    if descriptor_missing:
        issues.append(NupkgAuditIssue(
            ERROR,
            "UIPATH-RUNTIME-DESCRIPTOR",
            "missing UiPath runtime descriptor(s): "
            + ", ".join(f"lib/{framework}/project.json" for framework in descriptor_missing),
        ))

    if require_dev_compatible:
        unsupported = sorted(framework for framework in lib_frameworks if framework not in compatible_tfms)
        if unsupported:
            issues.append(NupkgAuditIssue(
                ERROR,
                "TFM-DEV-INCOMPATIBLE",
                "target framework(s) are not compatible with DEV Robot net6 runtime: "
                + ", ".join(unsupported),
            ))


def _audit_project_json_descriptors(
    archive: zipfile.ZipFile,
    names: list[str],
    issues: list[NupkgAuditIssue],
    *,
    package_id: str | None,
    version: str | None,
    project_json_frameworks: set[str],
) -> None:
    lower_to_original = {name.lower(): name for name in names}
    descriptor_members = [
        f"lib/{framework}/project.json" for framework in sorted(project_json_frameworks)
    ]
    content_member = lower_to_original.get("content/project.json")
    if content_member:
        descriptor_members.append(content_member)

    descriptors: dict[str, dict[str, Any]] = {}
    require_workflow_content = any(name.lower().endswith(".xaml") for name in names)
    for member in descriptor_members:
        original_member = lower_to_original.get(member.lower(), member)
        try:
            loaded = json.loads(archive.read(original_member).decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            issues.append(NupkgAuditIssue(
                ERROR,
                "PROJECT-JSON-PARSE",
                f"project.json is not valid JSON: {exc}",
                original_member,
            ))
            continue
        if not isinstance(loaded, dict):
            issues.append(NupkgAuditIssue(
                ERROR,
                "PROJECT-JSON-ROOT",
                "project.json root must be an object",
                original_member,
            ))
            continue
        descriptors[original_member] = loaded
        _audit_single_project_descriptor(
            loaded,
            issues,
            member=original_member,
            package_id=package_id,
            version=version,
            names=names,
            require_workflow_content=require_workflow_content,
        )

    if len(descriptors) >= 2:
        first_member, first_payload = next(iter(descriptors.items()))
        first_canonical = _canonical_json(first_payload)
        for member, payload in list(descriptors.items())[1:]:
            if _canonical_json(payload) != first_canonical:
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "PROJECT-JSON-DESCRIPTOR-DRIFT",
                    f"{member} differs from {first_member}",
                    member,
                ))


def _audit_single_project_descriptor(
    project: dict[str, Any],
    issues: list[NupkgAuditIssue],
    *,
    member: str,
    package_id: str | None,
    version: str | None,
    names: list[str],
    require_workflow_content: bool,
) -> None:
    project_name = project.get("name") or project.get("projectName")
    if not isinstance(project_name, str) or not project_name.strip():
        issues.append(NupkgAuditIssue(ERROR, "PROJECT-NAME", "project.json is missing name", member))
    elif package_id and project_name.strip() != package_id:
        issues.append(NupkgAuditIssue(
            ERROR,
            "PROJECT-NAME-MISMATCH",
            f"project.json name is {project_name.strip()}, nuspec id is {package_id}",
            member,
        ))

    project_version = project.get("projectVersion")
    if not isinstance(project_version, str) or not project_version.strip():
        issues.append(NupkgAuditIssue(
            ERROR,
            "PROJECT-VERSION",
            "project.json is missing projectVersion",
            member,
        ))
    elif version and project_version.strip() != version:
        issues.append(NupkgAuditIssue(
            ERROR,
            "PROJECT-VERSION-MISMATCH",
            f"project.json projectVersion is {project_version.strip()}, nuspec version is {version}",
            member,
        ))

    target_framework = project.get("targetFramework")
    if target_framework != "Windows":
        issues.append(NupkgAuditIssue(
            ERROR,
            "PROJECT-TARGET-FRAMEWORK",
            f"project.json targetFramework must be Windows; found {target_framework!r}",
            member,
        ))

    design_options = project.get("designOptions")
    output_type = design_options.get("outputType") if isinstance(design_options, dict) else None
    if output_type != "Process":
        issues.append(NupkgAuditIssue(
            ERROR,
            "PROJECT-OUTPUT-TYPE",
            f"project.json designOptions.outputType must be Process; found {output_type!r}",
            member,
        ))

    main = project.get("main")
    if not isinstance(main, str) or not main.strip():
        issues.append(NupkgAuditIssue(ERROR, "PROJECT-MAIN", "project.json is missing main", member))
    elif require_workflow_content:
        _audit_content_file_exists(names, issues, main.strip(), source_member=member, code="PROJECT-MAIN-FILE")

    entry_points = project.get("entryPoints")
    if not isinstance(entry_points, list) or not entry_points:
        issues.append(NupkgAuditIssue(
            ERROR,
            "PROJECT-ENTRYPOINTS",
            "project.json entryPoints must be a non-empty list",
            member,
        ))
    else:
        for index, entry in enumerate(entry_points):
            if not isinstance(entry, dict):
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "PROJECT-ENTRYPOINT",
                    f"entryPoints[{index}] must be an object",
                    member,
                ))
                continue
            file_path = entry.get("filePath")
            if not isinstance(file_path, str) or not file_path.strip():
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "PROJECT-ENTRYPOINT-FILEPATH",
                    f"entryPoints[{index}].filePath is missing",
                    member,
                ))
                continue
            if require_workflow_content:
                _audit_content_file_exists(
                    names,
                    issues,
                    file_path.strip(),
                    source_member=member,
                    code="PROJECT-ENTRYPOINT-FILE",
                )

    dependencies = project.get("dependencies")
    if isinstance(dependencies, dict):
        for dep_name, dep_version in sorted(dependencies.items()):
            if not isinstance(dep_version, str) or not dep_version.strip():
                issues.append(NupkgAuditIssue(
                    ERROR,
                    "PROJECT-DEPENDENCY-VERSION",
                    f"dependency {dep_name} has an empty or non-string version",
                    member,
                ))
                continue
            if not _EXACT_DEP_RE.match(dep_version.strip()):
                severity = ERROR if str(dep_name).startswith("CCS_") else WARN
                issues.append(NupkgAuditIssue(
                    severity,
                    "PROJECT-DEPENDENCY-PIN",
                    f"dependency {dep_name} is not an exact [version] pin: {dep_version}",
                    member,
                ))
    elif dependencies is not None:
        issues.append(NupkgAuditIssue(
            ERROR,
            "PROJECT-DEPENDENCIES",
            "project.json dependencies must be an object when present",
            member,
        ))


def _audit_runtime_files(
    names: list[str],
    issues: list[NupkgAuditIssue],
    *,
    package_id: str | None,
    lib_frameworks: set[str],
) -> None:
    if not package_id:
        return
    lower_names = {name.lower() for name in names}
    for framework in sorted(lib_frameworks):
        dll_member = f"lib/{framework}/{package_id}.dll"
        if dll_member.lower() not in lower_names:
            issues.append(NupkgAuditIssue(
                ERROR,
                "RUNTIME-DLL",
                f"package is missing runtime assembly {dll_member}",
                dll_member,
            ))


def _audit_content_file_exists(
    names: list[str],
    issues: list[NupkgAuditIssue],
    file_path: str,
    *,
    source_member: str,
    code: str,
) -> None:
    normalized = _normalize_member(file_path)
    lower_names = {name.lower() for name in names}
    candidates = [
        normalized,
        f"content/{normalized}",
    ]
    if not any(candidate.lower() in lower_names for candidate in candidates):
        issues.append(NupkgAuditIssue(
            ERROR,
            code,
            f"referenced workflow file is missing from package content: {file_path}",
            source_member,
        ))


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
