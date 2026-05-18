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


# `.nupkgs/` Sicoob: source-of-truth local pra CCS_*. Path configurável via
# env UIPATH_CCS_NUPKGS_DIR; default fixo pra workspace Sicoob padrão.
_DEFAULT_CCS_NUPKGS = Path(
    "C:/Users/lisan/OneDrive - Sicoob/Projects/.nupkgs"
)


def _align_ccs_deps_to_local_nupkgs(project_root: Path) -> int:
    """Pre-Migrator step: realinha `dependencies.CCS_*` em project.json com
    versões dos `.nupkgs` locais Sicoob.

    Why:
      Activity Migrator `RestoreStep` exige resolver TODAS as deps via feed.
      Quando project.json pin CCS_* versão antiga (já phase-out'ada do feed),
      RestoreStep falha mas Migrator exits 0 sem criar `_Migrated/` output
      → engine não progride. Sem essa correção, projetos Legacy travam para
      sempre.

    How:
      Lê `<dir>/CCS_<Name>.<X.Y.Z>.nupkg`, captura versão pelo nome do arquivo
      (semver simples) e regrava dependencies CCS_* em project.json. Preserva
      style do pin: `[X.Y.Z]` (exato) vs `X.Y.Z` (range).

      Override: env `UIPATH_CCS_NUPKGS_DIR=<path>` muda fonte. Quando dir
      não existe ou sem .nupkgs casando padrão CCS_*, retorna 0 (no-op).

    Returns:
      Número de deps atualizadas (0 se nada mudar).
    """
    import re as _re
    nupkgs_env = os.environ.get("UIPATH_CCS_NUPKGS_DIR")
    nupkgs_dir = Path(nupkgs_env).expanduser() if nupkgs_env else _DEFAULT_CCS_NUPKGS
    if not nupkgs_dir.is_dir():
        return 0

    # `<Name>.<Version>.nupkg` onde Version é `<digits>.<digits>.<digits>` (semver
    # simples — sem pre-release/build pra CCS Sicoob). Múltiplas versões do
    # mesmo Name: pega a maior (semver tuple sort).
    pkg_re = _re.compile(r"^(?P<name>CCS_[A-Za-z]+)\.(?P<ver>\d+\.\d+\.\d+)\.nupkg$")
    candidates: dict[str, list[tuple[int, int, int]]] = {}
    for f in nupkgs_dir.glob("*.nupkg"):
        m = pkg_re.match(f.name)
        if m:
            ver_tuple = tuple(int(x) for x in m.group("ver").split("."))
            candidates.setdefault(m.group("name"), []).append(ver_tuple)
    if not candidates:
        return 0
    local_versions = {
        name: ".".join(str(x) for x in max(versions))
        for name, versions in candidates.items()
    }

    pj_path = project_root / "project.json"
    if not pj_path.is_file():
        return 0

    try:
        pj = _json.loads(pj_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0

    deps = pj.get("dependencies")
    if not isinstance(deps, dict):
        return 0

    updated = 0
    for pkg, new_ver in local_versions.items():
        if pkg not in deps:
            continue
        old = str(deps[pkg])
        # Preserva pin style: `[X]` exato vs `X` range vs `[X,Y]` complexo.
        # Complex (vírgula) deixa intacto — escopo é só pin simples Sicoob.
        if "," in old:
            continue
        if old.startswith("[") and old.endswith("]"):
            new = f"[{new_ver}]"
        else:
            new = new_ver
        if old != new:
            deps[pkg] = new
            updated += 1
            print(f"# CCS align: {pkg} {old} → {new}")

    if updated > 0:
        pj["dependencies"] = deps
        try:
            pj_path.write_text(
                _json.dumps(pj, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            print(f"# CCS align: WRITE FAIL {e}", file=sys.stderr)
            return 0
    return updated


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

    # ---- Phase 1.5: align CCS_* deps with local .nupkgs (Sicoob SoT) ----
    # Migrator RestoreStep falha quando project.json pede CCS_* versions que
    # não existem mais em feeds (libs Sicoob upgrade'aram, versões antigas
    # foram phase-out'adas). `.nupkgs/` local é source-of-truth Sicoob; lê
    # filename pra capturar versão atual e atualiza project.json antes de
    # invocar Migrator. Sem alignment, Migrator silent-fail (exit 0 sem
    # criar output dir). D-1* rules (target=windows) NÃO ajudam aqui pois
    # projeto ainda é Legacy.
    aligned = _align_ccs_deps_to_local_nupkgs(src)
    if aligned > 0:
        print(f"# CCS align: {aligned} deps atualizadas pra versões em .nupkgs/\n")

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
        # Windows: .git/ tem files readonly (refs/, packed-refs). rmtree padrão
        # falha com PermissionError. onexc handler chmod +w + retry — pattern
        # padrão pra deletar trees git no Windows.
        import stat as _stat
        def _force_writable(func, path, exc_info):
            try:
                os.chmod(path, _stat.S_IWRITE)
                func(path)
            except (OSError, PermissionError):
                pass
        try:
            shutil.rmtree(out, onexc=_force_writable)
        except TypeError:
            # Python < 3.12 não tem onexc; fallback onerror (deprecated).
            shutil.rmtree(out, onerror=lambda f, p, e: _force_writable(f, p, e))

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

    # Activity Migrator binary IS uipcli (Studio.CommandLine) — mesmo profile
    # de hang (cloud heartbeat / license check). Usa guard com timeout duro
    # 1800s (Migrator pode levar 5-15min legitimamente em projetos grandes)
    # + halt detection 120s (sem CPU = pendurou).
    # Override env: UIPATH_MIGRATOR_TIMEOUT_SEC, UIPATH_MIGRATOR_HALT_WINDOW_SEC.
    import os as _os
    from .uipcli_runner import run_uipcli_guarded
    mig_timeout = int(_os.environ.get("UIPATH_MIGRATOR_TIMEOUT_SEC", "1800"))
    mig_halt = int(_os.environ.get("UIPATH_MIGRATOR_HALT_WINDOW_SEC", "120"))
    try:
        res = run_uipcli_guarded(
            cmd,
            timeout_sec=mig_timeout,
            halt_window_sec=mig_halt,
        )
    except FileNotFoundError as e:
        print(f"[INTERNAL] falha ao executar Migrator: {e}", file=sys.stderr)
        return EXIT_INTERNAL

    # Replay Migrator stdout/stderr (capture_output=False viraria pass-through;
    # com guard precisamos imprimir explicitamente).
    if res.stdout:
        print(res.stdout, end="" if res.stdout.endswith("\n") else "\n")
    if res.stderr:
        print(res.stderr, end="" if res.stderr.endswith("\n") else "\n", file=sys.stderr)

    if not res.completed:
        print(f"\n[ERROR] Activity Migrator {res.as_diagnostic()}", file=sys.stderr)
        return EXIT_ERROR
    print(f"\n# migrator exit={res.returncode} (duration {res.duration_sec:.1f}s)\n")
    if res.returncode != 0:
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
    final_rc = _cmd_review(final_args)

    # ---- Phase 5: swap source ↔ _Migrated -------------------------------
    # Sem swap, source segue tf=Legacy e proximos `uip` re-disparam Migrator
    # eternamente (loop não-progressivo). Critério atomic swap:
    #   - Migrator exit=0
    #   - out/project.json tem tf=Windows (já validado linha 330)
    #   - Sem HALT findings no _Migrated/ (errors são esperados — são o
    #     trabalho post-migration. Halt = projeto não pode rodar.)
    # Default: swap ON. Opt-out: --no-swap-after-migration ou
    # UIPATH_RULES_NO_SWAP=1.
    no_swap = bool(getattr(args, "no_swap_after_migration", False)) or (
        os.environ.get("UIPATH_RULES_NO_SWAP", "").strip() in ("1", "true", "yes")
    )
    if no_swap:
        print("# swap: --no-swap-after-migration — _Migrated/ preservado, source intacto.")
        return final_rc

    # Final review já validou halts via _cmd_review. Aqui usamos exit code:
    # EXIT_HALT=3 indica HALT. Outros (0/1/2) liberam swap.
    if final_rc == 3:
        print("# swap: _Migrated/ tem HALTs — NÃO swapping. Resolva HALTs manualmente.")
        return final_rc

    # Atomic-ish swap (Windows rename é atomic intra-volume).
    import time as _time
    timestamp = _time.strftime("%Y%m%d-%H%M%S")
    backup = src.parent / f"{src.name}_BeforeMigration_{timestamp}"
    if backup.exists():
        print(f"# swap: backup target já existe {backup.name}; abortando swap.",
              file=sys.stderr)
        return final_rc

    print(f"\n## [5/5] Swap source ↔ _Migrated")
    print(f"# {src.name} → {backup.name}")
    try:
        os.rename(src, backup)
    except OSError as e:
        print(f"[ERROR] swap step 1 failed (rename source→backup): {e}",
              file=sys.stderr)
        return EXIT_ERROR
    print(f"# {out.name} → {src.name}")
    try:
        os.rename(out, src)
    except OSError as e:
        # Rollback step 1 pra evitar source em estado fantasma.
        print(f"[ERROR] swap step 2 failed (rename _Migrated→source): {e}",
              file=sys.stderr)
        try:
            os.rename(backup, src)
            print(f"# rollback: {backup.name} → {src.name}", file=sys.stderr)
        except OSError as e2:
            print(f"[CRITICAL] rollback FAILED: {e2}. Source em "
                  f"{backup.name}, _Migrated em {out.name}.",
                  file=sys.stderr)
        return EXIT_ERROR

    print(f"# swap OK. Source agora tf=Windows. Original preservado em {backup.name}.")
    return final_rc
