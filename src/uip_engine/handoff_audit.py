"""Audit generated DEV handoff packages against source UiPath projects."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .nupkg_audit import (
    ERROR,
    WARN,
    NupkgAuditResult,
    audit_nupkg,
    collect_nupkgs,
    format_audit_result,
)
from .publish_dev import bump_version
from .publish_done import discover_projects
from .publish_readiness import _project_version


@dataclass(frozen=True)
class ExpectedHandoffPackage:
    folder_name: str
    project_root: Path
    package_id: str
    current_version: str
    expected_version: str

    @property
    def file_name(self) -> str:
        return f"{self.package_id}.{self.expected_version}.nupkg"

    def to_dict(self) -> dict[str, Any]:
        return {
            "folder_name": self.folder_name,
            "project_root": str(self.project_root),
            "package_id": self.package_id,
            "current_version": self.current_version,
            "expected_version": self.expected_version,
            "file_name": self.file_name,
        }


@dataclass(frozen=True)
class HandoffAuditIssue:
    severity: str
    code: str
    message: str
    path: Path | None = None
    folder_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.path is not None:
            payload["path"] = str(self.path)
        if self.folder_name is not None:
            payload["folder_name"] = self.folder_name
        return payload


@dataclass(frozen=True)
class HandoffPackageAudit:
    expected: ExpectedHandoffPackage
    path: Path | None
    package_audit: NupkgAuditResult | None = None

    @property
    def ok(self) -> bool:
        return self.path is not None and self.package_audit is not None and self.package_audit.ok

    @property
    def warn_count(self) -> int:
        return self.package_audit.warn_count if self.package_audit is not None else 0

    @property
    def error_count(self) -> int:
        return self.package_audit.error_count if self.package_audit is not None else 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected": self.expected.to_dict(),
            "path": str(self.path) if self.path is not None else None,
            "ok": self.ok,
            "audit": self.package_audit.to_dict() if self.package_audit is not None else None,
        }


@dataclass(frozen=True)
class HandoffAuditResult:
    source_root: Path
    handoff_paths: tuple[Path, ...]
    bump: str
    expected: tuple[ExpectedHandoffPackage, ...]
    packages: tuple[HandoffPackageAudit, ...]
    unexpected: tuple[Path, ...]
    issues: tuple[HandoffAuditIssue, ...]

    @property
    def error_count(self) -> int:
        own_errors = sum(1 for issue in self.issues if issue.severity == ERROR)
        package_errors = sum(pkg.package_audit.error_count for pkg in self.packages if pkg.package_audit)
        return own_errors + package_errors

    @property
    def warn_count(self) -> int:
        own_warnings = sum(1 for issue in self.issues if issue.severity == WARN)
        package_warnings = sum(pkg.warn_count for pkg in self.packages)
        return own_warnings + package_warnings

    @property
    def ok(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_root": str(self.source_root),
            "handoff_paths": [str(path) for path in self.handoff_paths],
            "bump": self.bump,
            "summary": {
                "expected": len(self.expected),
                "passed": sum(1 for package in self.packages if package.ok),
                "failed": sum(1 for package in self.packages if not package.ok),
                "unexpected": len(self.unexpected),
                "errors": self.error_count,
                "warnings": self.warn_count,
            },
            "expected": [expected.to_dict() for expected in self.expected],
            "packages": [package.to_dict() for package in self.packages],
            "unexpected": [str(path) for path in self.unexpected],
            "issues": [issue.to_dict() for issue in self.issues],
        }


def audit_publish_handoff(
    source_root: Path,
    handoff_paths: list[Path],
    *,
    bump: str,
    recursive: bool = False,
) -> HandoffAuditResult:
    root = Path(source_root).resolve()
    paths = tuple(Path(path).resolve() for path in handoff_paths)
    candidates = discover_projects(root)
    expected = tuple(
        ExpectedHandoffPackage(
            folder_name=candidate.folder_name,
            project_root=candidate.root,
            package_id=candidate.project_name,
            current_version=_project_version(candidate.root),
            expected_version=bump_version(_project_version(candidate.root), bump),
        )
        for candidate in candidates
    )

    nupkgs = collect_nupkgs(list(paths), recursive=recursive)
    by_file_name: dict[str, list[Path]] = {}
    for nupkg in nupkgs:
        by_file_name.setdefault(nupkg.name.lower(), []).append(nupkg)

    expected_names = {item.file_name.lower() for item in expected}
    issues: list[HandoffAuditIssue] = []
    packages: list[HandoffPackageAudit] = []

    for item in expected:
        matches = by_file_name.get(item.file_name.lower(), [])
        if not matches:
            issues.append(HandoffAuditIssue(
                ERROR,
                "HANDOFF-MISSING-PACKAGE",
                f"missing expected handoff package {item.file_name}",
                folder_name=item.folder_name,
            ))
            packages.append(HandoffPackageAudit(expected=item, path=None, package_audit=None))
            continue
        if len(matches) > 1:
            issues.append(HandoffAuditIssue(
                ERROR,
                "HANDOFF-DUPLICATE-PACKAGE",
                f"expected package {item.file_name} appears {len(matches)} times",
                path=matches[0],
                folder_name=item.folder_name,
            ))
        package_audit = audit_nupkg(
            matches[0],
            expected_id=item.package_id,
            expected_version=item.expected_version,
            require_dev_compatible=True,
        )
        packages.append(HandoffPackageAudit(
            expected=item,
            path=matches[0],
            package_audit=package_audit,
        ))

    unexpected = tuple(
        sorted(
            (nupkg for nupkg in nupkgs if nupkg.name.lower() not in expected_names),
            key=lambda path: str(path).lower(),
        )
    )
    for nupkg in unexpected:
        issues.append(HandoffAuditIssue(
            ERROR,
            "HANDOFF-UNEXPECTED-PACKAGE",
            f"unexpected handoff package {nupkg.name}",
            path=nupkg,
        ))

    if not expected:
        issues.append(HandoffAuditIssue(
            ERROR,
            "HANDOFF-NO-PROJECTS",
            f"no project.json files found under {root}",
        ))
    if not nupkgs:
        issues.append(HandoffAuditIssue(
            ERROR,
            "HANDOFF-NO-NUPKGS",
            "no .nupkg files found in the provided handoff path(s)",
        ))

    return HandoffAuditResult(
        source_root=root,
        handoff_paths=paths,
        bump=bump,
        expected=expected,
        packages=tuple(packages),
        unexpected=unexpected,
        issues=tuple(issues),
    )


def format_handoff_audit(result: HandoffAuditResult) -> str:
    passed = sum(1 for package in result.packages if package.ok)
    failed = sum(1 for package in result.packages if not package.ok)
    lines = [
        (
            f"HANDOFF audit: {passed}/{len(result.expected)} expected packages passed, "
            f"failed={failed}, unexpected={len(result.unexpected)}, "
            f"errors={result.error_count}, warnings={result.warn_count}"
        ),
        f"  source : {result.source_root}",
        f"  handoff: {', '.join(str(path) for path in result.handoff_paths)}",
        f"  bump   : {result.bump}",
    ]
    for issue in result.issues:
        detail = f" [{issue.path}]" if issue.path is not None else ""
        if issue.folder_name:
            detail += f" [{issue.folder_name}]"
        lines.append(f"  - {issue.severity} {issue.code}{detail}: {issue.message}")

    for package in result.packages:
        expected = package.expected
        status = "PASS" if package.ok else "FAIL"
        path_text = str(package.path) if package.path is not None else "(missing)"
        lines.append(
            f"\n{status} {expected.folder_name}: "
            f"{expected.package_id} {expected.current_version} -> "
            f"{expected.expected_version}"
        )
        lines.append(f"  file: {path_text}")
        if package.package_audit is not None:
            lines.append(format_audit_result(package.package_audit))

    return "\n".join(lines)


def handoff_audit_to_json(result: HandoffAuditResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
