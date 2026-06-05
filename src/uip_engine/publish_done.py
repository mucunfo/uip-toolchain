"""One-shot publisher for UiPath projects to RPA_Desenvolvimento."""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .official_uip import OfficialUipResult, run_official_uip
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


def discover_projects(root: Path) -> list[ProjectCandidate]:
    if not root.is_dir():
        raise ValueError(f"folder not found: {root}")
    skip_dirs = {".git", ".tmp", ".publish-dev-handoff", "bin", "obj", "node_modules"}
    project_jsons: list[Path] = []
    for current_text, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        if "project.json" in files:
            current = Path(current_text)
            project_jsons.append(current / "project.json")

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
        help="Batch output folder. Default: <root>/.publish-dev-handoff",
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
) -> argparse.Namespace:
    argv = [
        str(candidate.root),
        batch_args.bump,
        "--dev-tenant",
        DEV_TENANT,
        "--out-dir",
        str(out_dir / candidate.folder_name),
        "--timeout",
        str(batch_args.timeout),
    ]
    return build_single_parser().parse_args(argv)


def execute(
    args: argparse.Namespace,
    *,
    run_uip: RunUip | None = None,
    input_func: Callable[[str], str] = input,
) -> list[BatchItemResult]:
    root = _resolve_root(args)
    candidates = discover_projects(root)
    selected = candidates if args.all else choose_projects(candidates, input_func=input_func)

    print("\nSelecionados:")
    for candidate in selected:
        print(f"  - {candidate.folder_name} [project: {candidate.project_name}]")
    print(f"\nBump: {args.bump}")
    print(f"RPA DEV: {DEV_TENANT}")

    if args.dry_run:
        return [
            BatchItemResult(candidate=candidate, ok=True)
            for candidate in selected
        ]

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

    results: list[BatchItemResult] = []
    for candidate in selected:
        print(f"\n[{candidate.index}/{len(candidates)}] {candidate.folder_name}")
        try:
            plan = execute_one(
                _single_args(candidate=candidate, batch_args=args, out_dir=out_dir),
                run_uip=runner,
                ensure_auth=False,
            )
            print(f"  OK {plan.current_version} -> {plan.next_version}")
            print(f"  nupkg: {plan.downloaded_nupkg}")
            results.append(
                BatchItemResult(
                    candidate=candidate,
                    ok=True,
                    plan=plan,
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
