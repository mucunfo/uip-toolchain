"""One-shot publisher for UiPath projects to RPA_Desenvolvimento."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .official_uip import OfficialUipResult, _official_uip_subprocess_env, run_official_uip
from .project_view import PUBLISH_SKIP_DIRS, iter_project_json_files
from .publish_dev import (
    DEV_TENANT,
    EXIT_ERROR,
    EXIT_INTERNAL,
    EXIT_OK,
    VALID_BUMPS,
    PublishPlan,
    RunUip,
    _project_name,
    build_parser as build_single_parser,
    ensure_login,
    execute as execute_one,
)


DEFAULT_DONE_ROOT = (
    Path.home() / "OneDrive - Sicoob" / "Projects" / "3. done"
)


@dataclass(frozen=True)
class ProjectCandidate:
    index: int
    root: Path
    folder_name: str
    project_name: str


@dataclass(frozen=True)
class BatchItemResult:
    candidate: ProjectCandidate
    ok: bool
    plan: PublishPlan | None = None
    error: str | None = None
    commit_status: str | None = None
    commit_error: str | None = None


def discover_projects(root: Path) -> list[ProjectCandidate]:
    if not root.is_dir():
        raise ValueError(f"folder not found: {root}")
    project_jsons = list(
        iter_project_json_files(root, extra_skip_dirs=PUBLISH_SKIP_DIRS)
    )

    candidates: list[ProjectCandidate] = []
    for project_json in sorted(project_jsons, key=lambda p: str(p.parent.relative_to(root)).lower()):
        project_root = project_json.parent
        try:
            project_name = _project_name(project_root)
        except ValueError as exc:
            project_name = f"(invalid project.json: {exc})"
        rel = project_root.relative_to(root)
        folder_name = root.name if str(rel) == "." else str(rel)
        candidates.append(
            ProjectCandidate(
                index=len(candidates) + 1,
                root=project_root.resolve(),
                folder_name=folder_name,
                project_name=project_name,
            )
        )
    return candidates


def parse_selection(text: str, *, max_index: int) -> list[int]:
    value = text.strip().lower()
    if value in {"all", "todos", "*"}:
        return list(range(1, max_index + 1))
    if not value:
        raise ValueError("empty selection")

    selected: set[int] = set()
    for part in value.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = [piece.strip() for piece in token.split("-", 1)]
            start = int(start_text)
            end = int(end_text)
            if start > end:
                start, end = end, start
            selected.update(range(start, end + 1))
        else:
            selected.add(int(token))

    invalid = sorted(i for i in selected if i < 1 or i > max_index)
    if invalid:
        raise ValueError(f"selection out of range: {', '.join(str(i) for i in invalid)}")
    return sorted(selected)


def choose_projects(
    candidates: list[ProjectCandidate],
    *,
    input_func: Callable[[str], str] = input,
) -> list[ProjectCandidate]:
    if not candidates:
        raise ValueError("no project.json files found in the selected folder")

    print("\nProjetos encontrados:")
    for candidate in candidates:
        print(
            f"  {candidate.index:>2}. {candidate.folder_name} "
            f"[project: {candidate.project_name}]"
        )

    while True:
        raw = input_func("\nSelecione repos para subir (ex: 1,3,5-8 ou all): ")
        try:
            indexes = parse_selection(raw, max_index=len(candidates))
            if indexes:
                by_index = {candidate.index: candidate for candidate in candidates}
                return [by_index[index] for index in indexes]
        except (ValueError, TypeError) as exc:
            print(f"Selecao invalida: {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ccs-uip-publish",
        description=(
            "Publish selected UiPath projects to RPA_Desenvolvimento and "
            "download the handoff nupkgs."
        ),
    )
    parser.add_argument("bump", choices=VALID_BUMPS)
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help=f"Folder to scan recursively. Default: {DEFAULT_DONE_ROOT}",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Compatibility alias for path.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Folder where downloaded .nupkg files are written directly. "
             "Default: <root>/.publish-dev-handoff",
    )
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Select every discovered project without prompting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show selected projects and auth/folder configuration.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip final confirmation after the multi-select prompt.",
    )
    parser.add_argument(
        "--commit-message",
        default=None,
        help="After a successful publish, commit all current changes in the "
             "project Git repository using this message. Requires --commit-branch.",
    )
    parser.add_argument(
        "--commit-branch",
        default=None,
        help="Expected current Git branch for --commit-message. The command validates "
             "the branch and does not switch branches.",
    )
    return parser


def _resolve_root(args: argparse.Namespace) -> Path:
    if args.path and args.root:
        raise ValueError("pass either positional path or --root, not both")
    return Path(args.path or args.root or DEFAULT_DONE_ROOT).resolve()


def _single_args(
    *,
    candidate: ProjectCandidate,
    batch_args: argparse.Namespace,
    out_dir: Path,
    work_root: Path,
) -> argparse.Namespace:
    argv = [
        str(candidate.root),
        batch_args.bump,
        "--dev-tenant",
        DEV_TENANT,
        "--out-dir",
        str(work_root / candidate.folder_name),
        "--download-dir",
        str(out_dir),
        "--timeout",
        str(batch_args.timeout),
    ]
    return build_single_parser().parse_args(argv)


def _list_dotnet_sdks(dotnet: str, env: dict[str, str]) -> tuple[int, list[str], str]:
    proc = subprocess.run(
        [dotnet, "--list-sdks"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
        env=env,
    )
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
    sdk_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return proc.returncode, sdk_lines, output


def _sdk_major_from_line(line: str) -> int | None:
    version = line.strip().split(maxsplit=1)[0] if line.strip() else ""
    if not version:
        return None
    try:
        return int(version.split(".", 1)[0])
    except ValueError:
        return None


def _has_required_pack_sdk(sdk_lines: list[str]) -> bool:
    return any(
        major is not None and major >= 8
        for major in (_sdk_major_from_line(line) for line in sdk_lines)
    )


def _run_git(git_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(git_root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _git_output_or_error(proc: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())


def _git_root(project_root: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"project is not inside a Git repository: {project_root}. "
            f"{_git_output_or_error(proc)}"
        )
    return Path(proc.stdout.strip()).resolve()


def _current_branch(git_root: Path) -> str:
    proc = _run_git(git_root, ["branch", "--show-current"])
    if proc.returncode != 0:
        raise RuntimeError(f"could not read current Git branch: {_git_output_or_error(proc)}")
    branch = proc.stdout.strip()
    if not branch:
        raise RuntimeError(f"Git repository is detached: {git_root}")
    return branch


def commit_publish_changes(
    plan: PublishPlan,
    *,
    message: str,
    expected_branch: str,
) -> str:
    git_root = _git_root(plan.project_root)
    branch = _current_branch(git_root)
    if branch != expected_branch:
        raise RuntimeError(
            f"current branch is '{branch}', expected '{expected_branch}' in {git_root}"
        )

    proc = _run_git(git_root, ["add", "-A"])
    if proc.returncode != 0:
        raise RuntimeError(f"git add failed: {_git_output_or_error(proc)}")

    proc = _run_git(git_root, ["diff", "--cached", "--quiet"])
    if proc.returncode == 0:
        return f"SKIP no staged changes on {branch}"
    if proc.returncode not in {0, 1}:
        raise RuntimeError(f"git diff --cached failed: {_git_output_or_error(proc)}")

    proc = _run_git(git_root, ["commit", "-m", message])
    if proc.returncode != 0:
        raise RuntimeError(f"git commit failed: {_git_output_or_error(proc)}")

    commit_hash = _run_git(git_root, ["rev-parse", "--short", "HEAD"])
    if commit_hash.returncode != 0:
        raise RuntimeError(f"could not read commit hash: {_git_output_or_error(commit_hash)}")
    return f"COMMIT {commit_hash.stdout.strip()} on {branch}"


def preflight_commit_branch(
    selected: list[ProjectCandidate],
    *,
    expected_branch: str,
) -> None:
    for candidate in selected:
        git_root = _git_root(candidate.root)
        branch = _current_branch(git_root)
        if branch != expected_branch:
            raise RuntimeError(
                f"{candidate.folder_name}: current branch is '{branch}', "
                f"expected '{expected_branch}' in {git_root}"
            )


def ensure_dotnet_sdk_for_official_pack() -> None:
    env = _official_uip_subprocess_env()
    dotnet = shutil.which("dotnet", path=env.get("PATH", ""))
    if dotnet is None:
        raise RuntimeError(
            ".NET SDK 8+ not found. Official `uip rpa pack` restores a net8.0 "
            "temporary project before generating the .nupkg. Install .NET SDK 8 "
            "or run tools\\install-dotnet-sdk-portable.cmd before publishing."
        )

    returncode, sdk_lines, output = _list_dotnet_sdks(dotnet, env)
    if returncode != 0 or not sdk_lines:
        raise RuntimeError(
            "`dotnet --list-sdks` did not return an installed SDK. Official "
            "`uip rpa pack` requires .NET SDK 8+ for its net8.0 temporary "
            f"restore project. Output: {output or '(empty)'}"
        )

    if not _has_required_pack_sdk(sdk_lines):
        found = "; ".join(sdk_lines)
        raise RuntimeError(
            "Official `uip rpa pack` requires .NET SDK 8+ because the current "
            f"RPA tool restores a net8.0 temporary project. Found SDK(s): {found}. "
            "Install .NET SDK 8 or run tools\\install-dotnet-sdk-portable.cmd "
            "before publishing."
        )


def execute(
    args: argparse.Namespace,
    *,
    run_uip: RunUip | None = None,
    input_func: Callable[[str], str] = input,
    check_environment: bool = True,
) -> list[BatchItemResult]:
    if args.commit_branch and not args.commit_message:
        raise ValueError("--commit-branch requires --commit-message")
    if args.commit_message and not args.commit_branch:
        raise ValueError("--commit-message requires --commit-branch")

    root = _resolve_root(args)
    candidates = discover_projects(root)
    selected = candidates if args.all else choose_projects(candidates, input_func=input_func)

    print("\nSelecionados:")
    for candidate in selected:
        print(f"  - {candidate.folder_name} [project: {candidate.project_name}]")
    print(f"\nBump: {args.bump}")
    print(f"RPA DEV: {DEV_TENANT}", flush=True)

    if args.dry_run:
        return [
            BatchItemResult(candidate=candidate, ok=True)
            for candidate in selected
        ]

    if check_environment:
        ensure_dotnet_sdk_for_official_pack()

    if args.commit_message:
        preflight_commit_branch(selected, expected_branch=args.commit_branch)

    if not args.yes:
        confirm = input_func("\nConfirmar upload/download desses repos? [y/N]: ")
        if confirm.strip().lower() not in {"y", "yes", "s", "sim"}:
            raise RuntimeError("batch cancelled by user")

    timeout = int(args.timeout)

    def _default_run_uip(command: list[str]) -> OfficialUipResult:
        return run_official_uip(command, timeout=timeout)

    runner = run_uip or _default_run_uip
    ensure_login(runner, dev_tenant=DEV_TENANT)

    out_dir = (
        Path(args.out_dir).resolve()
        if args.out_dir
        else root / ".publish-dev-handoff"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    work_root = Path(tempfile.mkdtemp(prefix="ccs-uip-publish-"))
    results: list[BatchItemResult] = []
    try:
        for candidate in selected:
            print(f"\n[{candidate.index}/{len(candidates)}] {candidate.folder_name}")
            try:
                plan = execute_one(
                    _single_args(
                        candidate=candidate,
                        batch_args=args,
                        out_dir=out_dir,
                        work_root=work_root,
                    ),
                    run_uip=runner,
                    ensure_auth=False,
                )
                print(f"  OK {plan.current_version} -> {plan.next_version}")
                print(f"  nupkg: {plan.downloaded_nupkg}")
                commit_status = None
                if args.commit_message:
                    commit_status = commit_publish_changes(
                        plan,
                        message=args.commit_message,
                        expected_branch=args.commit_branch,
                    )
                    print(f"  {commit_status}")
                results.append(
                    BatchItemResult(
                        candidate=candidate,
                        ok=True,
                        plan=plan,
                        commit_status=commit_status,
                    )
                )
            except Exception as exc:
                print(f"  FAIL {exc}")
                results.append(
                    BatchItemResult(
                        candidate=candidate,
                        ok=False,
                        error=str(exc),
                    )
                )
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    return results


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        results = execute(args)
    except KeyboardInterrupt:
        return EXIT_ERROR
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    ok = [result for result in results if result.ok]
    failed = [result for result in results if not result.ok]
    print("\nResumo:")
    print(f"  OK: {len(ok)}")
    print(f"  FAIL: {len(failed)}")
    for result in failed:
        print(f"  - {result.candidate.folder_name}: {result.error}")
    return EXIT_OK if not failed else EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
