"""Publish a bumped RPA package to DEV and export the uploaded nupkg.

This command intentionally stays separate from ``ccs-uip``. The main CCS
command is a local quality gate; this module performs authenticated tenant
operations through the official UiPath CLI.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .official_uip import (
    OfficialUipResult,
    official_failure_text,
    run_official_uip,
)
from .publish_readiness import (
    PACK_INCOMPATIBLE_STALE_ASSEMBLY_REFERENCES,
    _load_project_json,
    _project_name,
    _project_version,
    is_packable_project,
    prepare_project_for_official_pack,
    scrub_pack_incompatible_assembly_references,
    sync_project_uiproj,
)


DEV_TENANT = "RPA_Desenvolvimento"
VALID_BUMPS = ("major", "minor", "patch")
EXIT_OK = 0
EXIT_ERROR = 2
EXIT_INTERNAL = 10


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


RunUip = Callable[[list[str]], OfficialUipResult]


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
    raise RuntimeError(f"uip rpa pack did not create a .nupkg in {pack_dir}")


def _default_work_dir(project_root: Path, package_key: str, version: str) -> Path:
    safe_pkg = re.sub(r"[^A-Za-z0-9_.-]+", "_", package_key)
    return project_root / ".tmp" / "publish-dev" / f"{safe_pkg}.{version}"


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


def _pack_project(
    run_uip: RunUip,
    *,
    project_root: Path,
    pack_dir: Path,
    next_version: str,
) -> None:
    preparation = prepare_project_for_official_pack(project_root)
    if preparation.descriptor_changed:
        print(f"[PACK] synced project descriptor: {preparation.descriptor}", file=sys.stderr)

    if preparation.scrubbed_xamls:
        print(
            "[PACK] removed stale headless-pack AssemblyReference lines: "
            f"{len(preparation.scrubbed_xamls)} file(s)",
            file=sys.stderr,
        )

    modern_result = run_uip(
        [
            "rpa", "pack", str(project_root), str(pack_dir),
            "--package-version", next_version,
            "--skip-analyze",
            "--output", "json",
        ],
    )
    if _uip_success(modern_result):
        return

    _envelope_data(modern_result)


def execute(
    args: argparse.Namespace,
    *,
    run_uip: RunUip | None = None,
    ensure_auth: bool = True,
) -> PublishPlan:
    project_root = Path(args.project).resolve()
    package_key = args.package_key or _project_name(project_root)
    current_version = _project_version(project_root)
    timeout = int(args.timeout)

    def _default_run_uip(command: list[str]) -> OfficialUipResult:
        return run_official_uip(command, timeout=timeout)

    runner = run_uip or _default_run_uip
    if ensure_auth:
        ensure_login(runner, dev_tenant=args.dev_tenant)

    next_version = bump_version(current_version, args.bump)

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

    _pack_project(
        runner,
        project_root=project_root,
        pack_dir=pack_dir,
        next_version=next_version,
    )
    packed_nupkg = _find_nupkg(pack_dir, package_key, next_version)

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

    return PublishPlan(
        project_root=project_root,
        package_key=package_key,
        dev_tenant=args.dev_tenant,
        current_version=current_version,
        next_version=next_version,
        work_dir=work_dir,
        pack_dir=pack_dir,
        downloaded_nupkg=downloaded_nupkg,
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
