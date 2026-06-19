"""Build Orchestrator readiness/smoke manifests from published packages."""
from __future__ import annotations

import json
import re
import html
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .nupkg_audit import ERROR, audit_nupkg, collect_nupkgs, format_audit_result
from .official_uip import OfficialUipResult, official_failure_text
from .publish_dev import DEV_TENANT, RunUip, _envelope_data, _first_str, _records, ensure_login


@dataclass(frozen=True)
class ManifestIssue:
    severity: str
    code: str
    subject: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.severity.upper() == "ERROR"

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "subject": self.subject,
            "message": self.message,
        }


@dataclass(frozen=True)
class ManifestEntry:
    package_id: str
    package_version: str
    process_key: str
    folder_path: str | None
    folder_key: str | None
    runtime_type: str
    process_name: str | None
    nupkg_path: Path
    target_framework: str | None = None
    entry_point_path: str | None = None
    required_resources: tuple[dict[str, str], ...] = field(default_factory=tuple)
    runtime_resource_hints: tuple[dict[str, str], ...] = field(default_factory=tuple)
    required_input_arguments: tuple[str, ...] = field(default_factory=tuple)

    def to_manifest_item(self) -> dict[str, Any]:
        item = {
            "packageId": self.package_id,
            "packageVersion": self.package_version,
            "processKey": self.process_key,
            "runtimeType": self.runtime_type,
        }
        if self.folder_path:
            item["folderPath"] = self.folder_path
        if self.folder_key:
            item["folderKey"] = self.folder_key
        if self.process_name:
            item["processName"] = self.process_name
        if self.target_framework:
            item["targetFramework"] = self.target_framework
        if self.entry_point_path:
            item["entryPointPath"] = self.entry_point_path
        if self.required_resources:
            item["requiredResources"] = list(self.required_resources)
        if self.runtime_resource_hints:
            item["runtimeResourceHints"] = list(self.runtime_resource_hints)
        if self.required_input_arguments:
            item["requiredInputArguments"] = list(self.required_input_arguments)
        return item

    def to_dict(self) -> dict[str, Any]:
        payload = self.to_manifest_item()
        payload["nupkgPath"] = str(self.nupkg_path)
        return payload


@dataclass(frozen=True)
class ManifestBuildResult:
    tenant: str
    handoff_paths: tuple[Path, ...]
    output_path: Path | None
    entries: tuple[ManifestEntry, ...] = field(default_factory=tuple)
    issues: tuple[ManifestIssue, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not any(issue.is_error for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.is_error)

    @property
    def warn_count(self) -> int:
        return sum(1 for issue in self.issues if not issue.is_error)

    @property
    def manifest(self) -> dict[str, Any]:
        return {
            "tenant": self.tenant,
            "items": [entry.to_manifest_item() for entry in self.entries],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant": self.tenant,
            "handoffPaths": [str(path) for path in self.handoff_paths],
            "outputPath": str(self.output_path) if self.output_path else None,
            "summary": {
                "entries": len(self.entries),
                "errors": self.error_count,
                "warnings": self.warn_count,
                "ok": self.ok,
            },
            "entries": [entry.to_dict() for entry in self.entries],
            "issues": [issue.to_dict() for issue in self.issues],
            "manifest": self.manifest,
        }


def build_orchestrator_manifest(
    handoff_paths: list[Path],
    *,
    run_uip: RunUip,
    tenant: str = DEV_TENANT,
    recursive: bool = False,
    runtime_type: str = "Unattended",
    allow_multiple: bool = False,
    output_path: Path | None = None,
    source_root: Path | None = None,
) -> ManifestBuildResult:
    paths = tuple(Path(path).resolve() for path in handoff_paths)
    source_index = _source_project_index(source_root) if source_root else {}
    ensure_login(run_uip, dev_tenant=tenant)

    issues: list[ManifestIssue] = []
    entries: list[ManifestEntry] = []
    nupkgs = collect_nupkgs(list(paths), recursive=recursive)
    if not nupkgs:
        issues.append(_error(
            "MANIFEST-NO-NUPKGS",
            ", ".join(str(path) for path in paths),
            "no .nupkg files found in the provided handoff path(s)",
        ))

    seen_packages: set[tuple[str, str]] = set()
    for nupkg in nupkgs:
        package_audit = audit_nupkg(nupkg, require_dev_compatible=True)
        if not package_audit.ok:
            issues.append(_error(
                "MANIFEST-PACKAGE-AUDIT",
                str(nupkg),
                format_audit_result(package_audit, errors_only=True),
            ))
            continue
        package_id = package_audit.package_id
        package_version = package_audit.version
        if not package_id or not package_version:
            issues.append(_error(
                "MANIFEST-PACKAGE-ID",
                str(nupkg),
                "package id/version could not be read from .nupkg",
            ))
            continue
        package_key = (package_id.lower(), package_version)
        if package_key in seen_packages:
            issues.append(_error(
                "MANIFEST-DUPLICATE-PACKAGE",
                str(nupkg),
                f"duplicate package/version in handoff set: {package_id}.{package_version}",
            ))
            continue
        seen_packages.add(package_key)
        runtime_contract, contract_issues = _package_runtime_contract(
            nupkg,
            package_id=package_id,
            package_version=package_version,
        )
        issues.extend(contract_issues)

        matches, match_issues = _resolve_processes(
            package_id=package_id,
            package_version=package_version,
            nupkg=nupkg,
            run_uip=run_uip,
            runtime_type=runtime_type,
            target_framework=runtime_contract["targetFramework"],
            entry_point_path=runtime_contract["entryPointPath"],
        )
        issues.extend(match_issues)
        if len(matches) > 1 and not allow_multiple:
            issue_detail = "; ".join(
                f"{match.process_key} {match.folder_path or match.folder_key or '(no folder)'}"
                for match in matches
            )
            issues.append(_error(
                "MANIFEST-PROCESS-AMBIGUOUS",
                f"{package_id}@{package_version}",
                (
                    "multiple processes are bound to this package/version; pass "
                    f"--allow-multiple only if every match should be smoked: {issue_detail}"
                ),
            ))
            continue
        matches, source_issues = _with_source_resources(
            matches,
            package_id=package_id,
            source_index=source_index,
            source_root=source_root,
        )
        issues.extend(source_issues)
        entries.extend(matches)

    result = ManifestBuildResult(
        tenant=tenant,
        handoff_paths=paths,
        output_path=output_path,
        entries=tuple(entries),
        issues=tuple(issues),
    )
    if output_path is not None and result.ok:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result.manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return result


def format_manifest_build(result: ManifestBuildResult) -> str:
    status = "OK" if result.ok else "FAIL"
    lines = [
        (
            f"ORCHESTRATOR manifest: {status}; tenant={result.tenant}; "
            f"entries={len(result.entries)}; errors={result.error_count}; "
            f"warnings={result.warn_count}"
        )
    ]
    if result.output_path:
        lines.append(f"  output: {result.output_path}")
    for entry in result.entries:
        folder = entry.folder_path or entry.folder_key or "(folder missing)"
        lines.append(
            f"  - {entry.package_id}@{entry.package_version}: "
            f"process={entry.process_key} folder={folder} runtime={entry.runtime_type}"
        )
    for issue in result.issues:
        lines.append(
            f"  - {issue.severity} {issue.code} {issue.subject}: {issue.message}"
        )
    if result.ok and not result.output_path:
        lines.append(json.dumps(result.manifest, indent=2, ensure_ascii=False))
    return "\n".join(lines)


def manifest_build_to_json(result: ManifestBuildResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def _with_source_resources(
    matches: list[ManifestEntry],
    *,
    package_id: str,
    source_index: dict[str, Path],
    source_root: Path | None,
) -> tuple[list[ManifestEntry], list[ManifestIssue]]:
    if source_root is None:
        return matches, []
    project_path = source_index.get(_normalize(package_id))
    if project_path is None:
        return matches, [_warn(
            "MANIFEST-SOURCE-MISSING",
            package_id,
            (
                f"source root {source_root} did not contain a project.json "
                f"matching package id {package_id}; runtime resources were not inferred"
            ),
        )]

    required_resources, hints = _infer_runtime_resources_from_source(project_path)
    required_input_arguments = _infer_required_input_arguments(project_path)
    issues: list[ManifestIssue] = []
    if not required_resources and hints:
        issues.append(_warn(
            "MANIFEST-BOOTSTRAP-ASSET-UNKNOWN",
            package_id,
            (
                f"source project {project_path} uses dynamic runtime resource keys, "
                "but no ArquivoConfiguracao_* bootstrap asset literal was found"
            ),
        ))
    if hints:
        keys = ", ".join(sorted({hint["configKey"] for hint in hints})[:12])
        issues.append(_warn(
            "MANIFEST-DYNAMIC-RESOURCE-KEYS",
            package_id,
            (
                "source uses runtime resource names from configuration keys; "
                f"validate the real config values through requiredResources: {keys}"
            ),
        ))
    enriched = [
        ManifestEntry(
            package_id=entry.package_id,
            package_version=entry.package_version,
            process_key=entry.process_key,
            folder_path=entry.folder_path,
            folder_key=entry.folder_key,
            runtime_type=entry.runtime_type,
            process_name=entry.process_name,
            nupkg_path=entry.nupkg_path,
            target_framework=entry.target_framework,
            entry_point_path=entry.entry_point_path,
            required_resources=required_resources,
            runtime_resource_hints=hints,
            required_input_arguments=required_input_arguments,
        )
        for entry in matches
    ]
    return enriched, issues


def _source_project_index(source_root: Path) -> dict[str, Path]:
    root = Path(source_root).resolve()
    index: dict[str, Path] = {}
    for project_json in sorted(root.rglob("project.json")):
        try:
            payload = json.loads(project_json.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        names = [
            payload.get("name"),
            payload.get("projectName"),
            project_json.parent.name,
        ]
        for name in names:
            if isinstance(name, str) and name.strip():
                index.setdefault(_normalize(name), project_json.parent)
    return index


def _infer_runtime_resources_from_source(
    project_path: Path,
) -> tuple[tuple[dict[str, str], ...], tuple[dict[str, str], ...]]:
    text = _source_xaml_text(project_path)
    required_resources = tuple(
        {
            "type": "asset",
            "name": asset_name,
            "valueType": "Text",
            "source": "source:ArquivoConfiguracao",
        }
        for asset_name in sorted(set(_bootstrap_config_assets(text)))
    )
    hints = tuple(
        {
            "type": resource_type,
            "configKey": key,
            "source": "source:Config",
        }
        for resource_type, key in sorted(_dynamic_resource_keys(text))
    )
    return required_resources, hints


def _infer_required_input_arguments(project_path: Path) -> tuple[str, ...]:
    project_json = project_path / "project.json"
    try:
        payload = json.loads(project_json.read_text(encoding="utf-8-sig"))
    except Exception:
        return ()
    inputs = (payload.get("arguments") or {}).get("input")
    if not isinstance(inputs, list):
        return ()
    required: list[str] = []
    for item in inputs:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip() and item.get("required") is True:
            required.append(name.strip())
    return tuple(sorted(dict.fromkeys(required)))


def _package_runtime_contract(
    nupkg: Path,
    *,
    package_id: str,
    package_version: str,
) -> tuple[dict[str, str | None], list[ManifestIssue]]:
    descriptors: list[dict[str, Any]] = []
    issues: list[ManifestIssue] = []
    try:
        with zipfile.ZipFile(nupkg) as archive:
            for name in archive.namelist():
                normalized = name.replace("\\", "/")
                if not normalized.startswith("lib/") or not normalized.endswith("/project.json"):
                    continue
                try:
                    descriptors.append(json.loads(archive.read(name).decode("utf-8-sig")))
                except Exception as exc:
                    issues.append(_error(
                        "MANIFEST-RUNTIME-DESCRIPTOR",
                        f"{package_id}@{package_version}",
                        f"could not parse {name}: {exc}",
                    ))
    except Exception as exc:
        return (
            {"targetFramework": None, "entryPointPath": None},
            [_error(
                "MANIFEST-RUNTIME-DESCRIPTOR",
                f"{package_id}@{package_version}",
                f"could not open package to inspect runtime descriptor: {exc}",
            )],
        )

    if not descriptors:
        return (
            {"targetFramework": None, "entryPointPath": None},
            [_error(
                "MANIFEST-RUNTIME-DESCRIPTOR",
                f"{package_id}@{package_version}",
                "package contains no lib/<tfm>/project.json runtime descriptor",
            )],
        )

    target_frameworks = {
        value.strip()
        for descriptor in descriptors
        for value in [_string_or_none(descriptor.get("targetFramework"))]
        if value
    }
    entry_points = {
        value.strip().replace("\\", "/")
        for descriptor in descriptors
        for value in [_descriptor_entry_point(descriptor)]
        if value
    }
    if len(target_frameworks) > 1:
        issues.append(_error(
            "MANIFEST-RUNTIME-DESCRIPTOR",
            f"{package_id}@{package_version}",
            f"runtime descriptors disagree on targetFramework: {sorted(target_frameworks)}",
        ))
    if len(entry_points) > 1:
        issues.append(_error(
            "MANIFEST-RUNTIME-DESCRIPTOR",
            f"{package_id}@{package_version}",
            f"runtime descriptors disagree on entry point: {sorted(entry_points)}",
        ))
    return {
        "targetFramework": next(iter(target_frameworks), None),
        "entryPointPath": next(iter(entry_points), None),
    }, issues


def _descriptor_entry_point(descriptor: dict[str, Any]) -> str | None:
    main = _string_or_none(descriptor.get("main"))
    if main:
        return main
    entry_points = descriptor.get("entryPoints")
    if isinstance(entry_points, list):
        for entry in entry_points:
            if not isinstance(entry, dict):
                continue
            file_path = _string_or_none(entry.get("filePath") or entry.get("path"))
            if file_path:
                return file_path
    return None


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _source_xaml_text(project_path: Path) -> str:
    chunks: list[str] = []
    for xaml in sorted(project_path.rglob("*.xaml")):
        try:
            chunks.append(xaml.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(chunks)


def _bootstrap_config_assets(text: str) -> list[str]:
    decoded = html.unescape(text)
    return re.findall(r"\bArquivoConfiguracao_[A-Za-z0-9_]+\b", decoded)


def _dynamic_resource_keys(text: str) -> set[tuple[str, str]]:
    decoded = html.unescape(text)
    resources: set[tuple[str, str]] = set()
    for line in decoded.splitlines():
        if "Config(" not in line:
            continue
        for key in re.findall(r'(?:in_)?Config\("([^"]+)"\)', line):
            if _line_uses_config_as_credential(line):
                resources.add(("credential", key))
            elif _line_uses_config_as_queue(line):
                resources.add(("queue", key))
            elif _line_uses_config_as_bucket(line):
                resources.add(("bucket", key))
            elif _line_uses_config_as_calendar(line):
                resources.add(("calendar", key))
            elif _line_uses_config_as_asset(line):
                resources.add(("asset", key))
    return resources


def _line_uses_config_as_credential(line: str) -> bool:
    return (
        ("GetRobotCredential" in line and "AssetName=" in line)
        or ("SetCredential" in line and "CredentialName=" in line)
    )


def _line_uses_config_as_queue(line: str) -> bool:
    return (
        "QueueName=" in line
        or "QueueType=" in line
        or "QueueDefinitionName=" in line
    )


def _line_uses_config_as_bucket(line: str) -> bool:
    return "BucketName=" in line or "BucketKey=" in line or "StorageBucket" in line


def _line_uses_config_as_calendar(line: str) -> bool:
    return "OrchestratorHttpRequest" in line and "/odata/Calendars" in line


def _line_uses_config_as_asset(line: str) -> bool:
    return "GetRobotAsset" in line and "AssetName=" in line


def _resolve_processes(
    *,
    package_id: str,
    package_version: str,
    nupkg: Path,
    run_uip: RunUip,
    runtime_type: str,
    target_framework: str | None,
    entry_point_path: str | None,
) -> tuple[list[ManifestEntry], list[ManifestIssue]]:
    try:
        data = _run_checked(run_uip, [
            "or", "processes", "list",
            "--all-folders",
            "--name", package_id,
            "--all-fields",
            "--limit", "1000",
            "--output", "json",
        ])
    except Exception as exc:
        return [], [_error(
            "MANIFEST-PROCESS-LIST",
            f"{package_id}@{package_version}",
            f"could not list Orchestrator processes: {exc}",
        )]

    candidates = _records(data)
    matches: list[ManifestEntry] = []
    version_mismatches: list[str] = []
    for record in candidates:
        if not _record_matches_package(record, package_id):
            continue
        actual_version = _first_str(
            record,
            "ProcessVersion",
            "PackageVersion",
            "Version",
            "ReleaseVersion",
        )
        actual_name = _first_str(record, "Name", "ReleaseName", "ProcessName")
        process_key = _first_str(record, "Key", "ReleaseKey", "ProcessKey")
        folder_path = _first_str(record, "FolderPath", "OrganizationUnitFullyQualifiedName")
        folder_key = _first_str(record, "FolderKey", "OrganizationUnitKey")
        if actual_version != package_version:
            version_mismatches.append(
                f"{actual_name or process_key or '(unknown)'}={actual_version or '(missing)'}"
            )
            continue
        if not process_key:
            return [], [_error(
                "MANIFEST-PROCESS-KEY",
                f"{package_id}@{package_version}",
                "matching process does not expose a process GUID key",
            )]
        if not folder_path and not folder_key:
            return [], [_error(
                "MANIFEST-PROCESS-FOLDER",
                f"{package_id}@{package_version}",
                f"matching process {process_key} does not expose folder path/key",
            )]
        matches.append(ManifestEntry(
            package_id=package_id,
            package_version=package_version,
            process_key=process_key,
            folder_path=folder_path,
            folder_key=folder_key,
            runtime_type=runtime_type,
            process_name=actual_name,
            nupkg_path=nupkg,
            target_framework=target_framework,
            entry_point_path=entry_point_path,
        ))

    if matches:
        return matches, []
    if version_mismatches:
        return [], [_error(
            "MANIFEST-PROCESS-VERSION-NOT-BOUND",
            f"{package_id}@{package_version}",
            (
                "processes were found for the package, but none are bound to "
                f"the handoff version. Seen: {', '.join(version_mismatches[:10])}"
            ),
        )]
    return [], [_error(
        "MANIFEST-PROCESS-MISSING",
        f"{package_id}@{package_version}",
        "no Orchestrator process found for this package id/version",
    )]


def _record_matches_package(record: dict[str, Any], package_id: str) -> bool:
    expected = _normalize(package_id)
    values = [
        _first_str(record, "PackageName", "PackageId", "PackageIdentifier", "ProcessKey"),
        _first_str(record, "Name", "ReleaseName", "ProcessName"),
    ]
    return any(value and _normalize(value) == expected for value in values)


def _run_checked(run_uip: RunUip, command: list[str]) -> Any:
    result: OfficialUipResult = run_uip(command)
    try:
        return _envelope_data(result)
    except Exception as exc:
        detail = official_failure_text(result).strip()
        if detail:
            raise RuntimeError(detail) from exc
        raise


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _error(code: str, subject: str, message: str) -> ManifestIssue:
    return ManifestIssue(severity=ERROR, code=code, subject=subject, message=message)


def _warn(code: str, subject: str, message: str) -> ManifestIssue:
    return ManifestIssue(severity="WARN", code=code, subject=subject, message=message)
