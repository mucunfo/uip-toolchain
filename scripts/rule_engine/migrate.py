"""Legacy/Windows-Legacy → Windows migration orchestrator.

Wraps UiPath Activity Migrator CLI (closed-source binário oficial GA em Studio
v25.10) com pre-scan + post-fix do engine de regras Sicoob.

Pipeline:
  1. Pre-scan (read-only): engine review no projeto-fonte. Reporta findings
     que podem bloquear migração. NÃO modifica fonte.
  2. Activity Migrator: invoca `<binary> upgrade -p <in> -o <out>`. Faz
     dependency resolution real (NuGet feed) + activity shape change
     (Click classic → modern, etc.) — partes que regex puro não consegue.
  3. Post-fix: engine `fix --apply` no projeto migrado. Aplica regras Sicoob
     (naming, structural, W-* enforcement) que Migrator não cobre.
  4. Final review: relatório consolidado.

Activity Migrator NÃO é instalado por default. Resolve binário via:
  - Flag `--migrator-path`
  - Env var `UIPATH_ACTIVITY_MIGRATOR`
  - PATH (`uipath-activity-migrator`)
  - Studio install dir
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import json as _json


_MIGRATOR_BIN_NAMES = (
    "UiPath.Upgrade.exe",
    "UiPath.Upgrade",
    "uipath-activity-migrator.exe",
    "uipath-activity-migrator",
    "UiPath.ActivityMigrator.exe",
)


def find_migrator(explicit: str | None) -> Path | None:
    """Resolve Activity Migrator binary. Order: explicit → env → PATH → Studio."""
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return p if p.is_file() else None

    env = os.environ.get("UIPATH_ACTIVITY_MIGRATOR")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_file():
            return p

    for name in _MIGRATOR_BIN_NAMES:
        which = shutil.which(name)
        if which:
            return Path(which).resolve()

    search_roots = [
        Path("C:/Tools/UiPathActivityMigrator"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "UiPath",
        Path(os.environ.get("PROGRAMFILES", "")) / "UiPath" / "Studio",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "UiPath" / "Studio",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for name in _MIGRATOR_BIN_NAMES:
            direct = root / name
            if direct.is_file():
                return direct.resolve()
            for hit in root.rglob(name):
                return hit.resolve()
    return None


def _read_target_framework(project_root: Path) -> str | None:
    pj = project_root / "project.json"
    if not pj.is_file():
        return None
    try:
        data = _json.loads(pj.read_text(encoding="utf-8-sig"))
    except _json.JSONDecodeError:
        return None
    return data.get("targetFramework")


def cmd_migrate_windows(args) -> int:
    """Subcommand entry point. Returns engine exit code."""
    from .cli import (
        EXIT_OK, EXIT_ERROR, EXIT_INTERNAL,
        _cmd_review, _cmd_fix, _load_rules_or_die,
    )

    src = Path(args.path).expanduser().resolve()
    if not src.is_dir():
        print(f"[INTERNAL] projeto não encontrado: {src}", file=sys.stderr)
        return EXIT_INTERNAL

    tf = _read_target_framework(src)
    if tf is None:
        print(f"[INTERNAL] project.json ausente ou inválido em {src}", file=sys.stderr)
        return EXIT_INTERNAL
    if tf == "Windows":
        print(f"[SKIP] {src.name}: já está em targetFramework=Windows")
        return EXIT_OK
    if tf not in ("Legacy", "Windows-Legacy"):
        print(f"[INTERNAL] targetFramework desconhecido: {tf!r} (esperado Legacy/Windows-Legacy)", file=sys.stderr)
        return EXIT_INTERNAL

    out = (
        Path(args.out).expanduser().resolve() if args.out
        else src.parent / f"{src.name}_Migrated"
    )

    print(f"# === migrate-windows ===")
    print(f"# source : {src}")
    print(f"# target : {out}")
    print(f"# tf     : {tf}\n")

    # ---- Phase 1: pre-scan (read-only) ----------------------------------
    print("## [1/4] Pre-scan engine (read-only)")
    pre_args = type("A", (), {})()
    pre_args.path = str(src)
    pre_args.rules_file = args.rules_file
    pre_args.format = "text"
    pre_args.multi_project = False
    pre_args.verbose = False
    pre_rc = _cmd_review(pre_args)
    print(f"# pre-scan exit={pre_rc}\n")

    if args.skip_migrator:
        print("# --skip-migrator: parando após pre-scan.")
        return pre_rc

    # ---- Phase 2: Activity Migrator -------------------------------------
    print("## [2/4] UiPath Activity Migrator")
    migrator = find_migrator(args.migrator_path)
    if migrator is None:
        print("[INTERNAL] Activity Migrator binary não encontrado. Instale via:", file=sys.stderr)
        print("  - Studio v25.10+: já incluso. Procure em %LOCALAPPDATA%\\UiPath\\Studio\\", file=sys.stderr)
        print("  - Standalone: download em forum.uipath.com/t/uipath-activity-migrator-is-generally-available/", file=sys.stderr)
        print("  - Setar env var UIPATH_ACTIVITY_MIGRATOR=<full path>", file=sys.stderr)
        print("  - Ou passar --migrator-path <full path>", file=sys.stderr)
        return EXIT_INTERNAL
    print(f"# binary : {migrator}")

    if out.exists() and not args.force:
        print(f"[INTERNAL] output existe: {out}. Use --force pra sobrescrever.", file=sys.stderr)
        return EXIT_INTERNAL
    if out.exists() and args.force:
        print(f"# --force: removendo {out}")
        shutil.rmtree(out)

    subcommand = "analyze" if getattr(args, "analyze_only", False) else "upgrade"
    cmd = [str(migrator), subcommand, "-p", str(src)]
    if subcommand == "upgrade":
        cmd.extend(["--output-path", str(out)])
    if getattr(args, "ignore_missing_dependencies", False):
        cmd.append("--ignore-missing-dependencies")
    extra = (args.migrator_args or "").split()
    cmd.extend(extra)
    print(f"# cmd    : {' '.join(cmd)}\n")

    if args.dry_run:
        print("# --dry-run: pulando invocação Migrator.")
        return EXIT_OK

    try:
        proc = subprocess.run(cmd, check=False, capture_output=False)
    except FileNotFoundError as e:
        print(f"[INTERNAL] falha ao executar Migrator: {e}", file=sys.stderr)
        return EXIT_INTERNAL
    print(f"\n# migrator exit={proc.returncode}\n")
    if proc.returncode != 0:
        print("[ERROR] Activity Migrator falhou. Engine post-fix abortado.", file=sys.stderr)
        return EXIT_ERROR

    if not out.is_dir():
        print(f"[INTERNAL] output {out} não criado pelo Migrator.", file=sys.stderr)
        return EXIT_INTERNAL

    new_tf = _read_target_framework(out)
    if new_tf != "Windows":
        print(f"[ERROR] output targetFramework={new_tf!r}, esperado 'Windows'.", file=sys.stderr)
        return EXIT_ERROR

    # ---- Phase 3: post-fix engine ---------------------------------------
    print("## [3/4] Post-fix engine (deterministic)")
    if args.skip_post:
        print("# --skip-post: pulando.\n")
    else:
        post_args = type("A", (), {})()
        post_args.path = str(out)
        post_args.rules_file = args.rules_file
        post_args.apply = True
        post_args.rules = ""
        post_args.include_class = "deterministic"
        post_rc = _cmd_fix(post_args)
        print(f"# post-fix exit={post_rc}\n")

    # ---- Phase 4: final review ------------------------------------------
    print("## [4/4] Review final")
    final_args = type("A", (), {})()
    final_args.path = str(out)
    final_args.rules_file = args.rules_file
    final_args.format = "text"
    final_args.multi_project = False
    final_args.verbose = False
    return _cmd_review(final_args)
