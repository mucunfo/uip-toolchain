"""Synchronize Orchestrator process versions with published package handoff."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .nupkg_audit import ERROR, WARN, audit_nupkg, collect_nupkgs, format_audit_result
from .official_uip import OfficialUipResult, official_failure_text
from .publish_dev import DEV_TENANT, RunUip, _envelope_data, _first_str, _records, ensure_login


@dataclass(frozen=True)
class SyncIssue:
    severity: str
    code: str
    subject: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.severity.upper() == ERROR

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "subject": self.subject,
            "message": self.message,
        }


@dataclass(frozen=True)
class SyncTarget:
    package_id: str
    package_version: str
    process_key: str
    current_version: str | None
    folder_path: str | None
    folder_key: str | None
    process_name: str | None
    nupkg_path: Path
    updated: bool = False
    already_current: bool = False

    @property
    def subject(self) -> str:
        return f"{self.package_id}@{self.package_version}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "packageId": self.package_id,
            "packageVersion": self.package_version,
            "processKey": self.process_key,
            "currentVersion": self.current_version,
            "folderPath": self.folder_path,
            "folderKey": self.folder_key,
            "processName": self.process_name,
            "nupkgPath": str(self.nupkg_path),
            "updated": self.updated,
            "alreadyCurrent": self.already_current,
        }


@dataclass(frozen=True)
class SyncResult:
    tenant: str
    handoff_paths: tuple[Path, ...]
    executed: bool
    targets: tuple[SyncTarget, ...] = field(default_factory=tuple)
    issues: tuple[SyncIssue, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not any(issue.is_error for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.is_error)

    @property
    def warn_count(self) -> int:
        return sum(1 for issue in self.issues if not issue.is_error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant": self.tenant,
            "handoffPaths": [str(path) for path in self.handoff_paths],
            "executed": self.executed,
            "summary": {
                "targets": len(self.targets),
                "updated": sum(1 for target in self.targets if target.updated),
                "alreadyCurrent": sum(1 for target in self.targets if target.already_current),
                "errors": self.error_count,
                "warnings": self.warn_count,
                "ok": self.ok,
            },
            "targets": [target.to_dict() for target in self.targets],
            "issues": [issue.to_dict() for issue in self.issues],
        }


def sync_orchestrator_process_versions(
    handoff_paths: list[Path],
    *,
    run_uip: RunUip,
    tenant: str = DEV_TENANT,
    recursive: bool = False,
    execute: bool = False,
    allow_multiple: bool = False,
) -> SyncResult:
    paths = tuple(Path(path).resolve() for path in handoff_paths)
    ensure_login(run_uip, dev_tenant=tenant)

    issues: list[SyncIssue] = []
    targets: list[SyncTarget] = []
    nupkgs = collect_nupkgs(list(paths), recursive=recursive)
    if not nupkgs:
        issues.append(_error(
            "SYNC-NO-NUPKGS",
            ", ".join(str(path) for path in paths),
            "no .nupkg files found in the provided handoff path(s)",
        ))

    seen_packages: set[tuple[str, str]] = set()
    for nupkg in nupkgs:
        package_audit = audit_nupkg(nupkg, require_dev_compatible=True)
        if not package_audit.ok:
            issues.append(_error(
                "SYNC-PACKAGE-AUDIT",
                str(nupkg),
                format_audit_result(package_audit, errors_only=True),
            ))
            continue
        package_id = package_audit.package_id
        package_version = package_audit.version
        if not package_id or not package_version:
            issues.append(_error(
                "SYNC-PACKAGE-ID",
                str(nupkg),
                "package id/version could not be read from .nupkg",
            ))
            continue
        package_key = (package_id.lower(), package_version)
        if package_key in seen_packages:
            issues.append(_error(
                "SYNC-DUPLICATE-PACKAGE",
                str(nupkg),
                f"duplicate package/version in handoff set: {package_id}.{package_version}",
            ))
            continue
        seen_packages.add(package_key)

        candidates, candidate_issues = _find_process_targets(
            package_id=package_id,
            package_version=package_version,
            nupkg=nupkg,
            run_uip=run_uip,
        )
        issues.extend(candidate_issues)
        if len(candidates) > 1 and not allow_multiple:
            detail = "; ".join(
                f"{candidate.process_key} {candidate.folder_path or candidate.folder_key or '(no folder)'}"
                for candidate in candidates
            )
            issues.append(_error(
                "SYNC-PROCESS-AMBIGUOUS",
                f"{package_id}@{package_version}",
                (
                    "multiple processes match this package; pass --allow-multiple "
                    f"only if every match should be updated: {detail}"
                ),
            ))
            continue
        targets.extend(candidates)

    if issues:
        return SyncResult(
            tenant=tenant,
            handoff_paths=paths,
            executed=execute,
            targets=tuple(targets),
            issues=tuple(issues),
        )

    if not execute:
        return SyncResult(
            tenant=tenant,
            handoff_paths=paths,
            executed=False,
            targets=tuple(targets),
            issues=(_warn(
                "SYNC-DRY-RUN",
                ", ".join(target.subject for target in targets) or "(none)",
                "process versions were not changed; pass --execute to update Orchestrator",
            ),),
        )

    updated_targets: list[SyncTarget] = []
    for target in targets:
        if target.current_version == target.package_version:
            updated_targets.append(_replace_target(
                target,
                already_current=True,
            ))
            continue
        update_issue = _update_process_version(target, run_uip)
        if update_issue:
            issues.append(update_issue)
            updated_targets.append(target)
            continue
        verified, verify_issue = _verify_process_version(target, run_uip)
        if verify_issue:
            issues.append(verify_issue)
        updated_targets.append(_replace_target(
            target,
            updated=verified,
            current_version=target.package_version if verified else target.current_version,
        ))

    return SyncResult(
        tenant=tenant,
        handoff_paths=paths,
        executed=True,
        targets=tuple(updated_targets),
        issues=tuple(issues),
    )


def format_sync_result(result: SyncResult) -> str:
    if result.executed:
        status = "OK" if result.ok else "FAIL"
    else:
        status = "DRY-RUN" if result.ok or result.warn_count else "FAIL"
    lines = [
        (
            f"ORCHESTRATOR sync: {status}; tenant={result.tenant}; "
            f"targets={len(result.targets)}; "
            f"updated={sum(1 for target in result.targets if target.updated)}; "
            f"alreadyCurrent={sum(1 for target in result.targets if target.already_current)}; "
            f"errors={result.error_count}; warnings={result.warn_count}"
        )
    ]
    for target in result.targets:
        folder = target.folder_path or target.folder_key or "(folder missing)"
        action = "already-current" if target.already_current else ("updated" if target.updated else "planned")
        lines.append(
            f"  - {action} {target.subject}: process={target.process_key} "
            f"from={target.current_version or '(missing)'} folder={folder}"
        )
    for issue in result.issues:
        lines.append(
            f"  - {issue.severity} {issue.code} {issue.subject}: {issue.message}"
        )
    return "\n".join(lines)


def sync_result_to_json(result: SyncResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def _find_process_targets(
    *,
    package_id: str,
    package_version: str,
    nupkg: Path,
    run_uip: RunUip,
) -> tuple[list[SyncTarget], list[SyncIssue]]:
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
            "SYNC-PROCESS-LIST",
            f"{package_id}@{package_version}",
            f"could not list Orchestrator processes: {exc}",
        )]

    targets: list[SyncTarget] = []
    for record in _records(data):
        if not _record_matches_package(record, package_id):
            continue
        process_key = _first_str(record, "Key", "ReleaseKey", "ProcessGuid")
        if not process_key:
            return [], [_error(
                "SYNC-PROCESS-KEY",
                f"{package_id}@{package_version}",
                "matching process does not expose a process GUID key",
            )]
        folder_path = _first_str(record, "FolderPath", "OrganizationUnitFullyQualifiedName")
        folder_key = _first_str(record, "FolderKey", "OrganizationUnitKey")
        if not folder_path and not folder_key:
            return [], [_error(
                "SYNC-PROCESS-FOLDER",
                f"{package_id}@{package_version}",
                f"matching process {process_key} does not expose folder path/key",
            )]
        targets.append(SyncTarget(
            package_id=package_id,
            package_version=package_version,
            process_key=process_key,
            current_version=_first_str(
                record,
                "ProcessVersion",
                "PackageVersion",
                "Version",
                "ReleaseVersion",
            ),
            folder_path=folder_path,
            folder_key=folder_key,
            process_name=_first_str(record, "Name", "ReleaseName", "ProcessName"),
            nupkg_path=nupkg,
        ))

    if not targets:
        return [], [_error(
            "SYNC-PROCESS-MISSING",
            f"{package_id}@{package_version}",
            "no Orchestrator process found for this package id",
        )]
    return targets, []


def _update_process_version(target: SyncTarget, run_uip: RunUip) -> SyncIssue | None:
    command = [
        "or", "processes", "update-version", target.process_key,
        "--package-version", target.package_version,
        "--output", "json",
    ]
    if target.folder_key:
        command.extend(["--folder-key", target.folder_key])
    elif target.folder_path:
        command.extend(["--folder-path", target.folder_path])
    result: OfficialUipResult = run_uip(command)
    if result.returncode != 0 or result.envelope is None or not result.envelope.ok:
        return _error(
            "SYNC-UPDATE-FAILED",
            target.subject,
            official_failure_text(result) or "uip or processes update-version failed",
        )
    return None


def _verify_process_version(target: SyncTarget, run_uip: RunUip) -> tuple[bool, SyncIssue | None]:
    try:
        data = _run_checked(run_uip, [
            "or", "processes", "get",
            target.process_key,
            "--all-fields",
            "--output", "json",
        ])
    except Exception as exc:
        return False, _error(
            "SYNC-VERIFY-FAILED",
            target.subject,
            f"could not verify updated process version: {exc}",
        )
    records = _records(data)
    if not records:
        return False, _error(
            "SYNC-VERIFY-MISSING",
            target.subject,
            "process get returned no record after update",
        )
    actual = _first_str(
        records[0],
        "ProcessVersion",
        "PackageVersion",
        "Version",
        "ReleaseVersion",
    )
    if actual != target.package_version:
        return False, _error(
            "SYNC-VERIFY-VERSION",
            target.subject,
            f"process version after update is {actual or '(missing)'}",
        )
    return True, None


def _replace_target(
    target: SyncTarget,
    *,
    updated: bool | None = None,
    already_current: bool | None = None,
    current_version: str | None = None,
) -> SyncTarget:
    return SyncTarget(
        package_id=target.package_id,
        package_version=target.package_version,
        process_key=target.process_key,
        current_version=current_version if current_version is not None else target.current_version,
        folder_path=target.folder_path,
        folder_key=target.folder_key,
        process_name=target.process_name,
        nupkg_path=target.nupkg_path,
        updated=target.updated if updated is None else updated,
        already_current=target.already_current if already_current is None else already_current,
    )


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


def _error(code: str, subject: str, message: str) -> SyncIssue:
    return SyncIssue(severity=ERROR, code=code, subject=subject, message=message)


def _warn(code: str, subject: str, message: str) -> SyncIssue:
    return SyncIssue(severity=WARN, code=code, subject=subject, message=message)
