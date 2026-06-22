"""Audit generated DEV handoff packages against source UiPath projects."""
from __future__ import annotations

import json
import zipfile
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
        if package_audit.ok:
            issues.extend(_audit_source_descriptor_match(matches[0], item))
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


_DESCRIPTOR_COMPARE_KEYS = (
    "name",
    "projectVersion",
    "main",
    "targetFramework",
    "expressionLanguage",
    "schemaVersion",
    "studioVersion",
    "dependencies",
    "runtimeOptions",
    "designOptions",
    "arguments",
    "entryPoints",
    "isTemplate",
)


def _audit_source_descriptor_match(
    nupkg: Path,
    expected: ExpectedHandoffPackage,
) -> list[HandoffAuditIssue]:
    try:
        source_descriptor = json.loads(
            (expected.project_root / "project.json").read_text(encoding="utf-8-sig")
        )
    except Exception as exc:
        return [HandoffAuditIssue(
            ERROR,
            "HANDOFF-SOURCE-DESCRIPTOR",
            f"could not read source project.json: {exc}",
            path=expected.project_root / "project.json",
            folder_name=expected.folder_name,
        )]
    if not isinstance(source_descriptor, dict):
        return [HandoffAuditIssue(
            ERROR,
            "HANDOFF-SOURCE-DESCRIPTOR",
            "source project.json root must be an object",
            path=expected.project_root / "project.json",
            folder_name=expected.folder_name,
        )]

    source_descriptor = dict(source_descriptor)
    source_descriptor["projectVersion"] = expected.expected_version

    try:
        package_member, package_descriptor = _read_primary_package_descriptor(nupkg)
    except Exception as exc:
        return [HandoffAuditIssue(
            ERROR,
            "HANDOFF-PACKAGE-DESCRIPTOR",
            f"could not read package project.json descriptor: {exc}",
            path=nupkg,
            folder_name=expected.folder_name,
        )]

    expected_view = _descriptor_compare_view(source_descriptor)
    actual_view = _descriptor_compare_view(package_descriptor)
    diffs = _diff_descriptor_values(expected_view, actual_view)
    if not diffs:
        return []
    preview = ", ".join(diffs[:12])
    if len(diffs) > 12:
        preview += f", +{len(diffs) - 12} more"
    return [HandoffAuditIssue(
        ERROR,
        "HANDOFF-SOURCE-DESCRIPTOR-MISMATCH",
        (
            f"package descriptor {package_member} does not match source "
            f"project.json after version bump; changed fields: {preview}"
        ),
        path=nupkg,
        folder_name=expected.folder_name,
    )]


def _read_primary_package_descriptor(nupkg: Path) -> tuple[str, dict[str, Any]]:
    with zipfile.ZipFile(nupkg) as archive:
        names = [
            (name.replace("\\", "/").lstrip("/"), name)
            for name in archive.namelist()
        ]
        lib_descriptors = sorted(
            (normalized, original)
            for normalized, original in names
            if normalized.lower().startswith("lib/")
            and normalized.lower().endswith("/project.json")
        )
        candidates = [item for item in lib_descriptors]
        lower_to_original = {normalized.lower(): (normalized, original) for normalized, original in names}
        if not candidates and "content/project.json" in lower_to_original:
            candidates = [lower_to_original["content/project.json"]]
        if not candidates:
            raise ValueError("no lib/<tfm>/project.json descriptor found")
        member, original_member = candidates[0]
        descriptor = json.loads(archive.read(original_member).decode("utf-8-sig"))
    if not isinstance(descriptor, dict):
        raise ValueError(f"{member} root must be an object")
    return member, descriptor


def _descriptor_compare_view(descriptor: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _normalize_descriptor_value(key, descriptor.get(key))
        for key in _DESCRIPTOR_COMPARE_KEYS
        if key in descriptor
    }


def _normalize_descriptor_value(key: str, value: Any) -> Any:
    if key == "arguments":
        return _normalize_arguments(value)
    if key == "entryPoints":
        return _normalize_entry_points(value)
    if key == "dependencies":
        return _normalize_dependencies(value)
    return _normalize_json_value(value)


def _normalize_dependencies(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    return {
        str(name): _normalize_dependency_version(version)
        for name, version in sorted(value.items(), key=lambda item: str(item[0]).lower())
    }


def _normalize_dependency_version(value: Any) -> str:
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    return text


def _normalize_arguments(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    normalized: dict[str, Any] = {}
    input_items = value.get("input")
    if isinstance(input_items, list):
        normalized["input"] = sorted(
            (
                _normalize_argument_contract(item)
                for item in input_items
                if isinstance(item, dict)
            ),
            key=lambda item: item.get("name") or "",
        )
    output_items = value.get("output")
    if isinstance(output_items, list):
        normalized["output"] = sorted(
            (_normalize_argument(item) for item in output_items if isinstance(item, dict)),
            key=lambda item: item.get("name") or "",
        )
    return normalized


def _normalize_argument_contract(value: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "name": _string_or_none(value.get("name")),
        "type": _normalize_type_name(value.get("type")),
    }
    if _is_truthy(value.get("required")):
        normalized["required"] = True
    return normalized


def _normalize_entry_points(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    entries: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        input_items = item.get("input")
        if not isinstance(input_items, list):
            input_items = []
        required_inputs = sorted(
            (
                _normalize_argument(arg)
                for arg in input_items
                if isinstance(arg, dict) and _is_truthy(arg.get("required"))
            ),
            key=lambda arg: arg.get("name") or "",
        )
        entry = {
            "filePath": _normalize_entry_point_path(item.get("filePath")),
        }
        if required_inputs:
            entry["requiredInput"] = required_inputs
        entries.append(entry)
    return sorted(entries, key=lambda item: item.get("filePath") or "")


def _normalize_argument(value: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "name": _string_or_none(value.get("name")),
        "type": _normalize_type_name(value.get("type")),
    }
    for key in ("required", "hasDefault"):
        if key in value:
            normalized[key] = value.get(key)
    return normalized


def _normalize_type_name(value: Any) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    return text.split(",", 1)[0].strip()


def _normalize_entry_point_path(value: Any) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    return text.replace("\\", "/").lstrip("/")


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _normalize_json_value(child)
            for key, child in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    return value


def _diff_descriptor_values(expected: Any, actual: Any, prefix: str = "") -> list[str]:
    if expected == actual:
        return []
    label = prefix or "descriptor"
    if isinstance(expected, dict) and isinstance(actual, dict):
        diffs: list[str] = []
        # The source project is the contract. Packer-added fields are tolerated,
        # but every field declared by the source must survive unchanged.
        for key in sorted(expected):
            child_prefix = f"{label}.{key}" if prefix else str(key)
            diffs.extend(_diff_descriptor_values(
                expected.get(key),
                actual.get(key),
                child_prefix,
            ))
        return diffs
    return [label]


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
