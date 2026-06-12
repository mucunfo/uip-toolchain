"""Publish a bumped RPA package to DEV and export the uploaded nupkg.

This command intentionally stays separate from ``ccs-uip``. The main CCS
command is a local quality gate; this module performs authenticated tenant
operations through the official UiPath CLI.
"""
from __future__ import annotations

import argparse
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree as ET

from .official_uip import (
    OfficialUipResult,
    official_failure_text,
    run_official_uip,
)
from .publish_readiness import (
    _load_project_json,
    _project_name,
    _project_version,
    prepare_project_for_official_pack,
    scrub_pack_incompatible_assembly_references,
)


DEV_TENANT = "RPA_Desenvolvimento"
VALID_BUMPS = ("major", "minor", "patch")
EXIT_OK = 0
EXIT_ERROR = 2
EXIT_INTERNAL = 10
DEV_ROBOT_PACKER_ENV_VAR = "UIP_TOOLCHAIN_DEV_ROBOT_PACKER"
DEV_ROBOT_COMPATIBLE_TFMS = frozenset({
    "net6.0-windows",
    "net6.0-windows7.0",
})
DEV_ROBOT_PACKER_VERSION_RE = re.compile(r"\b23\.10\.")
CCS_LATEST_PIN_RULE_ID = "D-1q-CCS-AUTO"


@dataclass(frozen=True)
class PublishPlan:
    project_root: Path
    package_key: str
    dev_tenant: str
    current_version: str
    next_version: str
    work_dir: Path
    pack_dir: Path
    downloaded_nupkg: Path
    changed_files: tuple[Path, ...] = ()


@dataclass(frozen=True)
class _PackerCandidate:
    path: Path
    source: str
    explicit: bool = False


RunUip = Callable[[list[str]], OfficialUipResult]
RunPack = Callable[[Path, Path, str, int], None]
RunReview = Callable[[Path], None]


_SEMVER_RE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)(?:\s*)$")


def bump_version(version: str, bump: str) -> str:
    match = _SEMVER_RE.match(version)
    if not match:
        raise ValueError(
            f"active version '{version}' is not plain SemVer X.Y.Z; "
            "cannot apply automatic major/minor/patch bump"
        )
    major, minor, patch = (int(part) for part in match.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"invalid bump '{bump}', expected one of: {', '.join(VALID_BUMPS)}")


def _envelope_data(result: OfficialUipResult) -> Any:
    if result.envelope is None:
        raise RuntimeError(
            "official uip did not return a JSON envelope. Output:\n"
            f"{official_failure_text(result)}"
        )
    if result.returncode != 0 or not result.envelope.ok:
        raise RuntimeError(official_failure_text(result) or "official uip command failed")
    return result.envelope.data


def _uip_success(result: OfficialUipResult) -> bool:
    return (
        result.returncode == 0
        and result.envelope is not None
        and result.envelope.ok
    )


def _records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("Items", "items", "Value", "value", "Results", "results", "Data", "data"):
            child = data.get(key)
            if isinstance(child, list):
                return [item for item in child if isinstance(item, dict)]
        return [data]
    return []


def _first_str(record: dict[str, Any], *names: str) -> str | None:
    lowered = {str(k).lower(): v for k, v in record.items()}
    for name in names:
        value = record.get(name)
        if value is None:
            value = lowered.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _tenant_names(data: Any) -> set[str]:
    names: set[str] = set()
    for record in _records(data):
        name = _first_str(record, "TenantName", "Name", "Tenant", "TenantNameOrId")
        if name:
            names.add(name)
    return names


def _strip_dependency_version(value: Any) -> str:
    match = re.match(r"^\[?\s*([^,\]\s]+)\s*(?:,\s*[^\]]+)?\]?$", str(value))
    return match.group(1) if match else str(value).strip()


def _iter_values(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_values(child)


def _extract_package_versions(data: Any) -> list[str]:
    versions: set[str] = set()
    version_key_re = re.compile(r"^(?:package)?version$", re.IGNORECASE)
    semver_re = re.compile(r"\b\d+\.\d+\.\d+(?:[-+][A-Za-z0-9_.+-]+)?\b")

    for item in _iter_values(data):
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if not version_key_re.match(str(key)):
                continue
            if isinstance(value, str):
                match = semver_re.search(value)
                if match:
                    versions.add(match.group(0))

    if isinstance(data, str):
        match = semver_re.search(data)
        if match:
            versions.add(match.group(0))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                match = semver_re.search(item)
                if match:
                    versions.add(match.group(0))

    from .heuristics.ccs_latest_pin import _parse_semver

    return sorted(versions, key=_parse_semver)


def _remote_library_versions(
    run_uip: RunUip,
    *,
    package: str,
    dev_tenant: str,
) -> list[str]:
    result = run_uip([
        "resource", "libraries", "versions", package,
        "--tenant", dev_tenant,
        "--limit", "1000",
        "--output", "json",
    ])
    data = _envelope_data(result)
    return _extract_package_versions(data)


def validate_ccs_packages_against_orchestrator(
    project_root: Path,
    *,
    run_uip: RunUip,
    dev_tenant: str,
) -> list["Finding"]:
    """Validate CCS package pins against the authenticated Orchestrator feed.

    Publish is a tenant-mutating online operation, so local `.nupkgs` must not
    decide package availability. The remote feed is the source of truth here.
    """
    from ._types import Finding, Severity
    from .heuristics.ccs_latest_pin import _parse_semver, _scan_project_ccs_assemblies

    data = _load_project_json(project_root)
    deps = data.get("dependencies")
    if not isinstance(deps, dict):
        return []

    required: dict[str, str | None] = {
        str(pkg): _strip_dependency_version(version)
        for pkg, version in deps.items()
        if str(pkg).lower().startswith("ccs_")
    }

    referenced = _scan_project_ccs_assemblies(project_root)
    deps_lower = {pkg.lower() for pkg in required}
    for pkg in referenced:
        if pkg.lower() not in deps_lower:
            required[pkg] = None

    findings: list[Finding] = []
    for pkg in sorted(required, key=str.lower):
        declared = required[pkg]
        try:
            versions = _remote_library_versions(
                run_uip,
                package=pkg,
                dev_tenant=dev_tenant,
            )
        except Exception as exc:
            findings.append(Finding(
                rule_id=CCS_LATEST_PIN_RULE_ID,
                severity=Severity.ERROR,
                category="publish_remote_feed",
                file=str(project_root / "project.json"),
                line=1,
                message=(
                    "CCS_* deve ser validado no Orchestrator durante publish: "
                    f"nao foi possivel consultar {pkg} em {dev_tenant} via "
                    f"`uip resource libraries versions`. Erro: {exc}. "
                    "Nao ha fallback local para .nupkgs no publish."
                ),
            ))
            continue

        if not versions:
            findings.append(Finding(
                rule_id=CCS_LATEST_PIN_RULE_ID,
                severity=Severity.ERROR,
                category="publish_remote_feed",
                file=str(project_root / "project.json"),
                line=1,
                message=(
                    "CCS_* deve existir no Orchestrator durante publish: "
                    f"library {pkg} nao possui versoes disponiveis em "
                    f"{dev_tenant}. Nao ha fallback local para .nupkgs no "
                    "publish."
                ),
            ))
            continue

        latest = max(versions, key=_parse_semver)
        if declared is None:
            source = referenced.get(pkg)
            try:
                source_label = str(source.relative_to(project_root)) if source else "XAML"
            except ValueError:
                source_label = str(source)
            findings.append(Finding(
                rule_id=CCS_LATEST_PIN_RULE_ID,
                severity=Severity.ERROR,
                category="publish_remote_feed",
                file=str(project_root / "project.json"),
                line=1,
                message=(
                    f"XAML referencia assembly '{pkg}' em {source_label}, "
                    "mas project.json::dependencies nao declara o pacote. "
                    f"Versao mais recente no Orchestrator {dev_tenant}: {latest}."
                ),
            ))
            continue

        if declared not in versions:
            findings.append(Finding(
                rule_id=CCS_LATEST_PIN_RULE_ID,
                severity=Severity.ERROR,
                category="publish_remote_feed",
                file=str(project_root / "project.json"),
                line=1,
                message=(
                    f"project.json declara {pkg}=[{declared}], mas essa versao "
                    f"nao existe no Orchestrator {dev_tenant}. Versoes "
                    f"disponiveis: {', '.join(versions)}. Nao ha fallback local "
                    "para .nupkgs no publish."
                ),
            ))
            continue

        if declared != latest:
            findings.append(Finding(
                rule_id=CCS_LATEST_PIN_RULE_ID,
                severity=Severity.ERROR,
                category="publish_remote_feed",
                file=str(project_root / "project.json"),
                line=1,
                message=(
                    f"project.json declara {pkg}=[{declared}], mas a versao "
                    f"mais recente no Orchestrator {dev_tenant} e {latest}."
                ),
            ))

    return findings


def ensure_login(
    run_uip: RunUip,
    *,
    dev_tenant: str,
) -> None:
    status = run_uip(["login", "status", "--output", "json"])
    if not _uip_success(status):
        print("[LOGIN] no valid UiPath CLI session; starting interactive login.", file=sys.stderr)
        _run_checked(run_uip, ["login", "--interactive", "--output", "json"])

    try:
        tenants_data = _run_checked(run_uip, ["login", "tenant", "list", "--output", "json"])
    except RuntimeError:
        print("[LOGIN] stored session could not list tenants; refreshing login.", file=sys.stderr)
        _run_checked(run_uip, ["login", "--interactive", "--output", "json"])
        tenants_data = _run_checked(run_uip, ["login", "tenant", "list", "--output", "json"])

    tenants = _tenant_names(tenants_data)
    required = {dev_tenant}
    missing = sorted(required - tenants)
    if missing:
        available = ", ".join(sorted(tenants)) if tenants else "(none returned)"
        raise RuntimeError(
            "logged-in UiPath account cannot see required tenant(s): "
            f"{', '.join(missing)}. Available tenants: {available}"
        )

def _find_nupkg(pack_dir: Path, package_key: str, version: str) -> Path:
    expected = pack_dir / f"{package_key}.{version}.nupkg"
    if expected.is_file():
        return expected
    matches = sorted(pack_dir.glob("*.nupkg"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(matches) == 1:
        return matches[0]
    if matches:
        names = ", ".join(p.name for p in matches[:5])
        raise RuntimeError(
            f"could not identify generated package {expected.name}; found: {names}"
        )
    raise RuntimeError(f"UiRobot pack did not create a .nupkg in {pack_dir}")


def _append_candidate(
    candidates: list[_PackerCandidate],
    seen: set[str],
    path: Path,
    *,
    source: str,
    explicit: bool = False,
) -> None:
    key = str(path).lower()
    if key in seen:
        return
    seen.add(key)
    candidates.append(_PackerCandidate(path=path, source=source, explicit=explicit))


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value) if value else None


def _dev_robot_packer_candidates() -> list[_PackerCandidate]:
    candidates: list[_PackerCandidate] = []
    seen: set[str] = set()

    explicit = os.environ.get(DEV_ROBOT_PACKER_ENV_VAR)
    if explicit:
        _append_candidate(
            candidates,
            seen,
            Path(explicit),
            source=DEV_ROBOT_PACKER_ENV_VAR,
            explicit=True,
        )

    _append_candidate(
        candidates,
        seen,
        Path.home() / "Documents" / "UiPathStudio23x" / "UiPath" / "Studio" / "UiRobot.exe",
        source="portable 23.10",
    )

    local_app_data = _env_path("LOCALAPPDATA")
    if local_app_data:
        _append_candidate(
            candidates,
            seen,
            local_app_data / "Programs" / "UiPath" / "Studio" / "UiRobot.exe",
            source="%LOCALAPPDATA% standard install",
        )
        _append_candidate(
            candidates,
            seen,
            local_app_data / "UiPath" / "Studio" / "UiRobot.exe",
            source="%LOCALAPPDATA% UiPath install",
        )
        ui_path_root = local_app_data / "UiPath"
        if ui_path_root.is_dir():
            for path in sorted(ui_path_root.glob("app-*/UiRobot.exe")):
                _append_candidate(
                    candidates,
                    seen,
                    path,
                    source="%LOCALAPPDATA% UiPath app-* install",
                )

    for env_name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        root = _env_path(env_name)
        if root:
            _append_candidate(
                candidates,
                seen,
                root / "UiPath" / "Studio" / "UiRobot.exe",
                source=f"%{env_name}% standard install",
            )

    on_path = shutil.which("UiRobot.exe")
    if on_path:
        _append_candidate(
            candidates,
            seen,
            Path(on_path),
            source="PATH",
        )

    return candidates


def _default_dev_robot_packer_candidates() -> list[Path]:
    return [candidate.path for candidate in _dev_robot_packer_candidates()]


def _uirobot_version(packer: Path) -> str:
    proc = subprocess.run(
        [str(packer), "version"],
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        timeout=30,
        check=False,
    )
    output = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())
    if proc.returncode != 0:
        raise RuntimeError(
            f"could not read UiRobot version from {packer}. Output:\n{output or '(empty)'}"
        )
    return output


def discover_dev_robot_packer() -> Path:
    searched: list[str] = []
    rejected: list[str] = []

    for candidate in _dev_robot_packer_candidates():
        searched.append(f"{candidate.path} ({candidate.source})")
        if not candidate.path.is_file():
            if candidate.explicit:
                raise RuntimeError(
                    f"{DEV_ROBOT_PACKER_ENV_VAR} points to a missing UiRobot.exe: "
                    f"{candidate.path}"
                )
            continue
        try:
            version = _uirobot_version(candidate.path)
        except RuntimeError as exc:
            if candidate.explicit:
                raise
            rejected.append(f"{candidate.path} ({candidate.source}): {exc}")
            continue
        if DEV_ROBOT_PACKER_VERSION_RE.search(version):
            return candidate.path
        message = (
            f"{candidate.path} ({candidate.source}) is not a Studio/Robot 23.10 packer. "
            f"Version output: {version}."
        )
        if candidate.explicit:
            raise RuntimeError(
                f"{message} Set {DEV_ROBOT_PACKER_ENV_VAR} to a UiRobot.exe "
                "from Studio/Robot 23.10."
            )
        rejected.append(message)

    searched_text = ", ".join(searched)
    rejected_text = ""
    if rejected:
        rejected_text = " Existing non-compatible candidates: " + " | ".join(rejected)
    raise RuntimeError(
        "Studio/Robot 23.10 UiRobot.exe packer not found. "
        f"Set {DEV_ROBOT_PACKER_ENV_VAR} to a UiRobot.exe from Studio/Robot 23.10. "
        f"Searched: {searched_text}.{rejected_text}"
    )


def run_dev_robot_pack(
    project_json: Path,
    pack_dir: Path,
    version: str,
    timeout: int,
) -> None:
    packer = discover_dev_robot_packer()
    argv = [
        str(packer),
        "pack",
        str(project_json),
        "-o",
        str(pack_dir),
        "-v",
        version,
    ]
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        timeout=timeout,
        check=False,
    )
    output = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())
    if proc.returncode != 0:
        raise RuntimeError(
            "UiRobot 23.10 pack failed. Command: "
            f"{' '.join(argv)}\nOutput:\n{output or '(empty)'}"
        )
    if not any(pack_dir.glob("*.nupkg")):
        raise RuntimeError(
            "UiRobot 23.10 pack completed without a .nupkg. Command: "
            f"{' '.join(argv)}\nOutput:\n{output or '(empty)'}"
        )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _nupkg_target_frameworks(nupkg: Path) -> list[str]:
    frameworks: set[str] = set()
    try:
        with zipfile.ZipFile(nupkg) as archive:
            for name in archive.namelist():
                parts = name.replace("\\", "/").split("/")
                if len(parts) >= 3 and parts[0] == "lib" and parts[1]:
                    frameworks.add(parts[1])

            for name in archive.namelist():
                if not name.endswith(".nuspec"):
                    continue
                root = ET.fromstring(archive.read(name))
                for element in root.iter():
                    if _local_name(element.tag) == "group":
                        target = element.attrib.get("targetFramework")
                        if target:
                            frameworks.add(target)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"generated package is not a valid .nupkg: {nupkg}") from exc
    except ET.ParseError as exc:
        raise RuntimeError(f"generated package has an invalid .nuspec: {nupkg}") from exc

    return sorted(frameworks)


def validate_dev_robot_package_compatibility(nupkg: Path) -> None:
    frameworks = _nupkg_target_frameworks(nupkg)
    if any(framework in DEV_ROBOT_COMPATIBLE_TFMS for framework in frameworks):
        return

    actual = ", ".join(frameworks) if frameworks else "(none found)"
    expected = ", ".join(sorted(DEV_ROBOT_COMPATIBLE_TFMS))
    raise RuntimeError(
        "generated package is not compatible with the DEV Robot net6 runtime. "
        f"Package target framework(s): {actual}. Expected one of: {expected}. "
        "Do not upload this package to DEV; repack it with a UiPath Studio/Robot "
        "23.10-compatible packer or upgrade the target Robot before publishing."
    )


def run_publish_review_gate(
    project_root: Path,
    *,
    run_uip: RunUip | None = None,
    dev_tenant: str = DEV_TENANT,
) -> None:
    from ._types import Severity
    from .cli import (
        DEFAULT_RULES_FILE,
        DETECTOR_REGISTRY,
        FIXER_REGISTRY,
        _apply_sicoob_lib_overrides,
        _load_rules_or_die,
    )
    from .runner import Runner

    rules = _load_rules_or_die(str(DEFAULT_RULES_FILE))
    runner = Runner(rules=rules, detectors=DETECTOR_REGISTRY, fixers=FIXER_REGISTRY)
    result = runner.run(project_root)
    _apply_sicoob_lib_overrides(result, verbose=False)
    # D-1q's normal detector is intentionally local/offline and reads
    # `.nupkgs`. Publish is online and authenticated, so replace that local
    # source-of-truth with the Orchestrator feed used by upload/download.
    for finding in result.findings:
        if finding.rule_id == CCS_LATEST_PIN_RULE_ID:
            finding.suppressed = True
    remote_runner = run_uip
    if remote_runner is None:
        remote_runner = lambda command: run_official_uip(command, timeout=180)
    result.findings.extend(
        validate_ccs_packages_against_orchestrator(
            project_root,
            run_uip=remote_runner,
            dev_tenant=dev_tenant,
        )
    )

    if result.internal_errors:
        details = "\n".join(f"  - {error}" for error in result.internal_errors[:10])
        raise RuntimeError(
            "pre-publish review failed with internal errors; package was not built.\n"
            f"{details}"
        )

    blockers = [
        finding
        for finding in result.findings
        if not finding.suppressed
        and finding.severity in (Severity.ERROR, Severity.HALT)
    ]
    if not blockers:
        return

    lines = []
    for finding in blockers[:12]:
        rel_file = Path(finding.file)
        try:
            rel_file = rel_file.relative_to(project_root)
        except ValueError:
            pass
        lines.append(
            f"  - {finding.rule_id} {rel_file}:{finding.line}: {finding.message}"
        )
    if len(blockers) > len(lines):
        lines.append(f"  - ... plus {len(blockers) - len(lines)} more blocker(s)")
    details = "\n".join(lines)
    raise RuntimeError(
        "pre-publish review found blocking ERROR/HALT findings; package was not built.\n"
        f"Summary: errors={result.error_count}, halts={result.halt_count}.\n"
        f"{details}"
    )


def _default_work_dir(project_root: Path, package_key: str, version: str) -> Path:
    safe_pkg = re.sub(r"[^A-Za-z0-9_.-]+", "_", package_key)
    return project_root / ".tmp" / "publish-dev" / f"{safe_pkg}.{version}"


def _write_project_version(project_root: Path, version: str) -> Path:
    project_json = project_root / "project.json"
    data = _load_project_json(project_root)
    data["projectVersion"] = version
    project_json.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return project_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ccs-uip-publish-project",
        description=(
            "Read project.json projectVersion, bump major/minor/patch, pack "
            "the project, upload to RPA_Desenvolvimento, then download the "
            "uploaded .nupkg for handoff."
        ),
    )
    parser.add_argument("project", help="UiPath project root containing project.json")
    parser.add_argument("bump", choices=VALID_BUMPS, help="Required automatic version bump")
    parser.add_argument("--dev-tenant", default=DEV_TENANT)
    parser.add_argument(
        "--package-key",
        default=None,
        help="Package key/id. Default: project.json name.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for pack output and downloaded handoff nupkg. "
             "Default: <project>/.tmp/publish-dev/<package>.<version>",
    )
    parser.add_argument(
        "--download-dir",
        default=None,
        help="Directory where the uploaded .nupkg is downloaded. "
             "Default: <out-dir>/download",
    )
    parser.add_argument("--timeout", type=int, default=600)
    return parser


def _run_checked(run_uip: RunUip, args: list[str]) -> Any:
    result = run_uip(args)
    return _envelope_data(result)


def execute(
    args: argparse.Namespace,
    *,
    run_uip: RunUip | None = None,
    run_pack: RunPack | None = None,
    run_review: RunReview | None = None,
    ensure_auth: bool = True,
) -> PublishPlan:
    project_root = Path(args.project).resolve()
    package_key = args.package_key or _project_name(project_root)
    current_version = _project_version(project_root)
    timeout = int(args.timeout)

    def _default_run_uip(command: list[str]) -> OfficialUipResult:
        return run_official_uip(command, timeout=timeout)

    runner = run_uip or _default_run_uip
    pack_runner = run_pack or run_dev_robot_pack
    if run_review is None:
        def review_runner(project: Path) -> None:
            run_publish_review_gate(
                project,
                run_uip=runner,
                dev_tenant=args.dev_tenant,
            )
    else:
        review_runner = run_review

    if ensure_auth and run_review is None:
        ensure_login(runner, dev_tenant=args.dev_tenant)

    review_runner(project_root)

    if ensure_auth and run_review is not None:
        ensure_login(runner, dev_tenant=args.dev_tenant)

    next_version = bump_version(current_version, args.bump)
    project_json = project_root / "project.json"
    original_project_json = project_json.read_bytes()

    work_dir = (
        Path(args.out_dir).resolve()
        if args.out_dir
        else _default_work_dir(project_root, package_key, next_version)
    )
    if work_dir.exists():
        shutil.rmtree(work_dir)
    pack_dir = work_dir / "pack"
    download_dir = Path(args.download_dir).resolve() if args.download_dir else work_dir / "download"
    pack_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)

    changed_files: list[Path] = []
    try:
        _write_project_version(project_root, next_version)
        if project_json.read_bytes() != original_project_json:
            changed_files.append(project_json)

        preparation = prepare_project_for_official_pack(project_root)
        if preparation.descriptor_changed:
            print(f"[PACK] synced project descriptor: {preparation.descriptor}", file=sys.stderr)
            changed_files.append(preparation.descriptor)

        if preparation.scrubbed_xamls:
            print(
                "[PACK] removed stale headless-pack AssemblyReference lines: "
                f"{len(preparation.scrubbed_xamls)} file(s)",
                file=sys.stderr,
            )
            changed_files.extend(preparation.scrubbed_xamls)

        pack_runner(project_json, pack_dir, next_version, timeout)

        packed_nupkg = _find_nupkg(pack_dir, package_key, next_version)
        validate_dev_robot_package_compatibility(packed_nupkg)

        _run_checked(
            runner,
            [
                "or", "packages", "upload", str(packed_nupkg),
                "--tenant", args.dev_tenant,
                "--output", "json",
            ],
        )

        downloaded_nupkg = download_dir / packed_nupkg.name
        if downloaded_nupkg.exists():
            raise RuntimeError(f"download target already exists: {downloaded_nupkg}")
        _run_checked(
            runner,
            [
                "or", "packages", "download", f"{package_key}:{next_version}",
                "--destination", str(downloaded_nupkg),
                "--tenant", args.dev_tenant,
                "--output", "json",
            ],
        )
        if not downloaded_nupkg.is_file():
            raise RuntimeError(
                f"download command completed but file was not found: {downloaded_nupkg}"
            )
    except Exception:
        project_json.write_bytes(original_project_json)
        raise

    return PublishPlan(
        project_root=project_root,
        package_key=package_key,
        dev_tenant=args.dev_tenant,
        current_version=current_version,
        next_version=next_version,
        work_dir=work_dir,
        pack_dir=pack_dir,
        downloaded_nupkg=downloaded_nupkg,
        changed_files=tuple(dict.fromkeys(path.resolve() for path in changed_files)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        plan = execute(args)
    except KeyboardInterrupt:
        return EXIT_ERROR
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    print("Publish DEV/export OK")
    print(f"  package: {plan.package_key}")
    print(f"  version: {plan.current_version} -> {plan.next_version}")
    print(f"  uploaded tenant: {plan.dev_tenant}")
    print(f"  handoff nupkg: {plan.downloaded_nupkg}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
