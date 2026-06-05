"""Publish a bumped RPA package to DEV and export the uploaded nupkg.

This command intentionally stays separate from ``ccs-uip``. The main CCS
command is a local quality gate; this module performs authenticated tenant
operations through the official UiPath CLI.
"""
from __future__ import annotations

import argparse
import json
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


PROD_TENANT = "Producao"
DEV_TENANT = "RPA_Desenvolvimento"
VALID_BUMPS = ("major", "minor", "patch")

EXIT_OK = 0
EXIT_ERROR = 2
EXIT_INTERNAL = 10


@dataclass(frozen=True)
class ActiveProcess:
    key: str | None
    name: str
    package_key: str
    version: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class PublishPlan:
    project_root: Path
    package_key: str
    process_name: str
    prod_tenant: str
    dev_tenant: str
    prod_folder_path: str | None
    prod_folder_key: str | None
    current_version: str
    next_version: str
    work_dir: Path
    pack_dir: Path
    downloaded_nupkg: Path


RunUip = Callable[[list[str]], OfficialUipResult]


def _load_project_json(project_root: Path) -> dict[str, Any]:
    project_json = project_root / "project.json"
    if not project_json.is_file():
        raise ValueError(f"project.json not found at {project_json}")
    try:
        data = json.loads(project_json.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid project.json: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("project.json root must be an object")
    return data


def _project_name(project_root: Path) -> str:
    data = _load_project_json(project_root)
    name = data.get("name") or data.get("projectName")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("project.json must define a non-empty 'name'")
    return name.strip()


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
    prod_tenant: str,
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
    required = {prod_tenant, dev_tenant}
    missing = sorted(required - tenants)
    if missing:
        available = ", ".join(sorted(tenants)) if tenants else "(none returned)"
        raise RuntimeError(
            "logged-in UiPath account cannot see required tenant(s): "
            f"{', '.join(missing)}. Available tenants: {available}"
        )


def _record_to_process(record: dict[str, Any]) -> ActiveProcess | None:
    name = _first_str(record, "Name", "ProcessName", "DisplayName")
    package_key = _first_str(record, "PackageKey", "PackageId", "PackageName", "ProcessKey")
    version = _first_str(record, "Version", "PackageVersion", "ProcessVersion")
    if not name or not version:
        return None
    return ActiveProcess(
        key=_first_str(record, "Key", "ProcessKey", "Id"),
        name=name,
        package_key=package_key or name,
        version=version,
        raw=record,
    )


def select_active_process(
    records: list[dict[str, Any]],
    *,
    process_name: str,
    package_key: str,
) -> ActiveProcess:
    processes = [p for p in (_record_to_process(record) for record in records) if p]
    exact_name = [p for p in processes if p.name.lower() == process_name.lower()]
    if len(exact_name) == 1:
        return exact_name[0]
    exact_package = [p for p in processes if p.package_key.lower() == package_key.lower()]
    if len(exact_package) == 1:
        return exact_package[0]
    if len(exact_name) > 1 or len(exact_package) > 1:
        raise RuntimeError(
            "more than one production process matched. Pass --process-name "
            "or narrow the folder."
        )
    if len(processes) == 1:
        return processes[0]
    raise RuntimeError(
        f"no active production process matched name '{process_name}' "
        f"or package '{package_key}'"
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
        prog="ccs-uip-publish-dev",
        description=(
            "Read the active production process version, bump major/minor/patch, "
            "pack the project, upload to RPA_Desenvolvimento, then download the "
            "uploaded .nupkg for handoff."
        ),
    )
    parser.add_argument("project", help="UiPath project root containing project.json")
    parser.add_argument("bump", choices=VALID_BUMPS, help="Required automatic version bump")
    parser.add_argument("--prod-tenant", default=PROD_TENANT)
    parser.add_argument("--dev-tenant", default=DEV_TENANT)
    folder = parser.add_mutually_exclusive_group(required=True)
    folder.add_argument("--prod-folder-path", default=None)
    folder.add_argument("--prod-folder-key", default=None)
    parser.add_argument(
        "--package-key",
        default=None,
        help="Package key/id. Default: project.json name.",
    )
    parser.add_argument(
        "--process-name",
        default=None,
        help="Production process/release name. Default: package key.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for pack output and downloaded handoff nupkg. "
             "Default: <project>/.tmp/publish-dev/<package>.<version>",
    )
    parser.add_argument("--timeout", type=int, default=600)
    return parser


def _run_checked(run_uip: RunUip, args: list[str]) -> Any:
    result = run_uip(args)
    return _envelope_data(result)


def execute(args: argparse.Namespace, *, run_uip: RunUip | None = None) -> PublishPlan:
    project_root = Path(args.project).resolve()
    package_key = args.package_key or _project_name(project_root)
    process_name = args.process_name or package_key
    timeout = int(args.timeout)

    def _default_run_uip(command: list[str]) -> OfficialUipResult:
        return run_official_uip(command, timeout=timeout)

    runner = run_uip or _default_run_uip
    ensure_login(runner, prod_tenant=args.prod_tenant, dev_tenant=args.dev_tenant)

    process_cmd = [
        "or", "processes", "list",
        "--tenant", args.prod_tenant,
        "--name", process_name,
        "--output", "json",
    ]
    if args.prod_folder_path:
        process_cmd.extend(["--folder-path", args.prod_folder_path])
    else:
        process_cmd.extend(["--folder-key", args.prod_folder_key])

    prod_records = _records(_run_checked(runner, process_cmd))
    active = select_active_process(
        prod_records,
        process_name=process_name,
        package_key=package_key,
    )
    next_version = bump_version(active.version, args.bump)

    work_dir = (
        Path(args.out_dir).resolve()
        if args.out_dir
        else _default_work_dir(project_root, package_key, next_version)
    )
    if work_dir.exists():
        shutil.rmtree(work_dir)
    pack_dir = work_dir / "pack"
    download_dir = work_dir / "download"
    pack_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)

    _run_checked(
        runner,
        [
            "rpa", "pack", str(project_root), str(pack_dir),
            "--output-type", "Process",
            "--package-version", next_version,
            "--output", "json",
        ],
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
        downloaded_nupkg.unlink()
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
        process_name=process_name,
        prod_tenant=args.prod_tenant,
        dev_tenant=args.dev_tenant,
        prod_folder_path=args.prod_folder_path,
        prod_folder_key=args.prod_folder_key,
        current_version=active.version,
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
    print(f"  production tenant: {plan.prod_tenant}")
    if plan.prod_folder_path:
        print(f"  production folder: {plan.prod_folder_path}")
    else:
        print(f"  production folder key: {plan.prod_folder_key}")
    print(f"  version: {plan.current_version} -> {plan.next_version}")
    print(f"  uploaded tenant: {plan.dev_tenant}")
    print(f"  handoff nupkg: {plan.downloaded_nupkg}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
