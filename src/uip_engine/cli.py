"""CLI entry point — review, fix, list, validate, render-md."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Disable .pyc bytecode caching engine-wide. Stale .pyc causou false positive
# J-6 (cache leu versão velha do detector json_checks após edits).
# Sem cache → impossível ler versão obsoleta.
sys.dont_write_bytecode = True

# Sweep existing __pycache__ DIRS dentro do pacote uip_engine — invalida
# caches escritos por runs anteriores ANTES desse flag entrar em vigor.
def _sweep_pycache() -> None:
    import shutil
    pkg_root = Path(__file__).resolve().parent
    for cache_dir in pkg_root.rglob("__pycache__"):
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
        except Exception:
            pass

_sweep_pycache()

# sys.path injection: ensures rules.yaml python detectors referenced as
# `uip_engine.heuristics.<mod>` resolve in all invocation modes
# (console_script `ccs-uip`, `python -m uip_engine.cli`, hooks subprocess).
# After src/ reorg (2026-05-26), parents[2] = `.uip-toolchain/` and
# the package lives at `src/uip_engine/`. Adding repo root to sys.path
# is harmless and provides resilience for environments where the
# editable install link is stale or missing.
_engine_root_for_compat = Path(__file__).resolve().parents[2]
if str(_engine_root_for_compat) not in sys.path:
    sys.path.insert(0, str(_engine_root_for_compat))

# Force UTF-8 stdout so PT-BR + acentos + emoji safe under Windows charmap.
# reconfigure() (3.7+) muta wrapper existente em vez de criar novo — evita
# double-wrap GC fechar buffer original (causava "I/O operation on closed file"
# quando subcommand chamava import diferido pós wrap).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except Exception:
            pass

from .loader import load_rules, SchemaError
from .runner import Runner
from .detectors import REGISTRY as DETECTOR_REGISTRY
from .fixers import REGISTRY as FIXER_REGISTRY
from .safety import apply_with_gate
from .classify import get_apply_class, VALID_CLASSES
from ._types import Severity, ValidationResult


DEFAULT_RULES_FILE = Path(__file__).resolve().parents[2] / "rules.yaml"

# Sentinel marker em NuGet.config gerado por engine (pack-gate, eventualmente
# outros gates). Permite detecção idempotente de orphan config remanescente
# de runs crashed (SIGKILL entre create e finally). Se outro processo
# encontra NuGet.config com esse marker no projeto, sabe que foi engine-temp
# e pode remover safely. Config pré-existente de dev NUNCA carrega marker
# (idempotência preserva config committed).
_TEMP_NUGET_CONFIG_SENTINEL = "engine-temp-nuget-config (.uip-toolchain)"

_PUBLISH_READINESS_PRECONDITION_RULES = frozenset({
    "J-9",
    "W-40",
    "A-19d",
})


# Exit codes
EXIT_OK = 0
EXIT_WARN = 1
EXIT_ERROR = 2
EXIT_HALT = 3
EXIT_INTERNAL = 10


def _iter_analyzer_snapshot_paths(project_root: Path):
    """Files that analyzer-gate rollback must be able to restore.

    The gate used to snapshot only XAMLs. That was insufficient because the
    deterministic fix loop can also mutate project metadata (project.json,
    .project/design.json, .gitignore, project.uiproj). A package/project change
    can introduce Studio load errors while the XAML bytes are innocent; rollback
    must restore the whole analyzer-relevant surface, not just workflows.
    """
    import os as _os
    from .project_view import filter_walk_dirs

    snapshot_names = {
        ".gitignore",
        "NuGet.config",
        "project.json",
        "project.uiproj",
    }
    snapshot_suffixes = {
        ".xaml",
        ".json",
        ".uiproj",
        ".config",
    }

    for root, dirs, files in _os.walk(project_root):
        filter_walk_dirs(dirs)
        root_path = Path(root)
        for name in files:
            path = root_path / name
            if name in snapshot_names or path.suffix in snapshot_suffixes:
                yield path


def _is_project_metadata_snapshot_path(path: Path, project_root: Path) -> bool:
    """Project metadata must not be blanket-rolled back by XAML analyzer fallback.

    Dependency pins and project manifests are fixed by separate deterministic
    gates. A project-level analyzer error with no FilePath should not undo those
    fixes; otherwise the next phase diagnoses stale dependencies again instead
    of the real remaining blocker.
    """
    try:
        rel_parts = path.resolve().relative_to(project_root.resolve()).parts
    except (OSError, ValueError):
        rel_parts = path.parts

    rel_lower = tuple(p.lower() for p in rel_parts)
    name = path.name.lower()
    if name in {
        "project.json",
        "project.uiproj",
        "packagebindingsmetadata.json",
    }:
        return True
    return bool(rel_lower and rel_lower[0] == ".project")


def _is_analyzer_metadata_or_cli_infra_issue(issue) -> bool:
    """True for analyzer regressions that should not roll back XAML bytes.

    Official `uip rpa analyze` can fail after dependency graph changes with
    project-level infrastructure errors such as missing assemblies. Those are
    restore/dependency diagnostics, not proof that deterministic XAML fixes
    introduced a workflow regression. A full-snapshot XAML rollback in that
    situation recreates hundreds of mechanical blockers (W-19, W-4, etc.) and
    hides the real package graph issue.
    """
    file_name = Path(getattr(issue, "file", "") or "").name.lower()
    code = (getattr(issue, "error_code", "") or "").upper()
    description = (getattr(issue, "description", "") or "").lower()

    if file_name not in {"project.json", "project.uiproj"}:
        return False
    if code in {
        "CLI_ASSEMBLY_MISSING",
        "CLI_PROJECT_FORMAT",
        "CLI_REQUIRED_PACKAGE_MISSING",
    }:
        return True
    return (
        "cannot load assembly" in description
        or "não foi possível carregar assembly" in description
        or "nao foi possivel carregar assembly" in description
        or "project path and pack configuration" in description
    )


_TEXT_EXPRESSION_IMPL_BLOCK_RE = re.compile(
    r"<TextExpression\.(?P<kind>ReferencesForImplementation|NamespacesForImplementation)>"
    r".*?"
    r"</TextExpression\.(?P=kind)>",
    re.DOTALL,
)


def _is_reference_namespace_only_delta(before: bytes, after: bytes) -> bool:
    """True when a XAML delta only touches expression refs/imports.

    FULL-SNAPSHOT rollback is a last resort for analyzer errors without a
    usable FilePath. W-11/ENV fixes live in TextExpression refs/imports and are
    intentionally low risk; rolling them back recreates deterministic blockers
    across many files while hiding the actual analyzer regression.
    """
    if before == after:
        return False
    try:
        before_text = before.decode("utf-8-sig", errors="strict")
        after_text = after.decode("utf-8-sig", errors="strict")
    except UnicodeError:
        return False

    stripped_before = _TEXT_EXPRESSION_IMPL_BLOCK_RE.sub(
        "<TextExpression.__CCS_IMPL_BLOCK__ />",
        before_text,
    )
    stripped_after = _TEXT_EXPRESSION_IMPL_BLOCK_RE.sub(
        "<TextExpression.__CCS_IMPL_BLOCK__ />",
        after_text,
    )
    return stripped_before == stripped_after


def _rollback_bytes_preserving_refs_namespaces(
    before: bytes,
    current: bytes,
) -> bytes:
    """Return pre-loop XAML bytes with current refs/import blocks preserved."""
    if before == current:
        return before
    try:
        before_text = before.decode("utf-8-sig", errors="strict")
        current_text = current.decode("utf-8-sig", errors="strict")
    except UnicodeError:
        return before

    current_blocks = {
        m.group("kind"): m.group(0)
        for m in _TEXT_EXPRESSION_IMPL_BLOCK_RE.finditer(current_text)
    }
    if not current_blocks:
        return before

    changed = False

    def repl(match: re.Match) -> str:
        nonlocal changed
        kind = match.group("kind")
        current_block = current_blocks.get(kind)
        if current_block and current_block != match.group(0):
            changed = True
            return current_block
        return match.group(0)

    merged = _TEXT_EXPRESSION_IMPL_BLOCK_RE.sub(repl, before_text)
    if not changed:
        return before
    encoding = "utf-8-sig" if before.startswith(b"\xef\xbb\xbf") else "utf-8"
    return merged.encode(encoding)


_PROPERTY_ELEMENT_ATTR_RE = re.compile(
    r'<[A-Za-z_][\w]*:[A-Za-z_][\w]*\.[A-Za-z_][\w]*'
    r'(?:\s+[A-Za-z_][\w:]*="[^"]*")+\s*>'
)


def _property_element_attribute_snippet(path: Path) -> str | None:
    """Best-effort locator for Studio's NonemptyPropertyElement ATTRIBUTE error."""
    try:
        content = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    m = _PROPERTY_ELEMENT_ATTR_RE.search(content)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(0))[:220]


_INVOKE_WORKFLOW_BLOCK_RE = re.compile(
    r'(?P<opening><(?P<prefix>[A-Za-z_]\w*):InvokeWorkflowFile(?=[\s/>])'
    r'(?P<attrs>[^>]*)>)'
    r'(?P<body>.*?)'
    r'(?P<closing></(?P=prefix):InvokeWorkflowFile>)',
    re.DOTALL,
)


def _line_for_offset(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _invoke_workflow_arguments_conflict_snippets(
    project_root: Path,
    pre_loop_bytes: dict[Path, bytes],
) -> list[tuple[Path, int, str]]:
    """Best-effort locator for hidden InvokeWorkflowFile Arguments duplicates."""
    out: list[tuple[Path, int, str]] = []
    for path in _iter_analyzer_snapshot_paths(project_root):
        if path.suffix.lower() != ".xaml" or not path.exists():
            continue
        try:
            current = path.read_bytes()
        except OSError:
            continue
        try:
            content = current.decode("utf-8-sig", errors="replace")
        except Exception:
            continue
        for m in _INVOKE_WORKFLOW_BLOCK_RE.finditer(content):
            opening = m.group("opening")
            attrs = m.group("attrs")
            body = m.group("body")
            prefix = m.group("prefix")
            prop_re = re.compile(
                rf'<{re.escape(prefix)}:InvokeWorkflowFile\.Arguments(?=[\s/>])'
            )
            prop_count = len(prop_re.findall(body))
            has_attr = bool(re.search(r'\bArguments\s*=', attrs))
            has_var = bool(re.search(r'\bArgumentsVariable\s*=', attrs))
            if prop_count > 1:
                reason = f"property-elements={prop_count}"
            elif prop_count and has_attr:
                reason = "inline Arguments attr + property element"
            elif prop_count and has_var:
                reason = "ArgumentsVariable attr + property element"
            else:
                continue
            snippet = re.sub(r"\s+", " ", opening)[:220]
            out.append((path, _line_for_offset(content, m.start()), f"{reason}: {snippet}"))
    return out


def _has_property_element_with_attribute(path: Path) -> bool:
    return _property_element_attribute_snippet(path) is not None


def _cleanup_pre_migration_backups(project_root: Path) -> list[Path]:
    """Remove `<project>_BeforeMigration_<timestamp>` siblings após PASS.

    PHASE 0 Activity Migrator cria backup `_BeforeMigration_<YYYYMMDD-HHMMSS>`
    pre-swap (migrate.py:380). Backup serve só como rollback manual emergência
    — se engine completou pipeline com PASS, backup é dead weight (~50-200MB
    por projeto, acumula em batch runs).

    Auto-clean DISPARA somente em PASS/PASS-WITH-NOTES final (não em FAIL —
    user pode querer rollback nesses casos).

    Opt-out via env `UIP_TOOLCHAIN_KEEP_BACKUP=1` (debug / paranoid mode).

    Returns lista de paths removidos.

    Windows-safe rmtree: .git/refs/ + packed-refs são readonly → rmtree padrão
    falha. Handler chmod +w + retry (mesma técnica de migrate.py).
    """
    import os as _os_cl
    if _os_cl.environ.get("UIP_TOOLCHAIN_KEEP_BACKUP", "").strip() in ("1", "true", "yes"):
        return []

    import re as _re_cl
    import shutil as _shutil_cl
    import stat as _stat_cl

    parent = project_root.parent
    name = project_root.name
    # Pattern: <name>_BeforeMigration_YYYYMMDD-HHMMSS
    pat = _re_cl.compile(
        _re_cl.escape(name) + r"_BeforeMigration_\d{8}-\d{6}$"
    )
    removed: list[Path] = []
    if not parent.is_dir():
        return removed

    def _force_writable(func, path, exc_info):
        try:
            _os_cl.chmod(path, _stat_cl.S_IWRITE)
            func(path)
        except (OSError, PermissionError):
            pass

    for sibling in parent.iterdir():
        if not sibling.is_dir():
            continue
        if not pat.match(sibling.name):
            continue
        try:
            # Python 3.12+ uses onexc; older Python uses onerror.
            try:
                _shutil_cl.rmtree(sibling, onexc=_force_writable)
            except TypeError:
                _shutil_cl.rmtree(
                    sibling,
                    onerror=lambda f, p, e: _force_writable(f, p, e),
                )
            removed.append(sibling)
        except OSError as e:
            print(
                f"[BACKUP-CLEAN] cannot remove {sibling.name}: {e}",
                file=sys.stderr,
            )
    return removed


def _cleanup_orphan_temp_nuget_config(project_root: Path) -> bool:
    """Detect + remove orphan NuGet.config left by crashed engine run.

    Pack-gate cria NuGet.config temp + cleanup em finally. Em crash hard
    (SIGKILL, machine reboot, OneDrive sync race) finally não roda → orphan
    fica no projeto. Próximo `uip` run detecta via sentinel + remove ANTES
    de qualquer phase. Garante zero rastro de feed local Sicoob no projeto
    mesmo em crash path.

    Idempotente: NuGet.config sem sentinel (dev committed) = preserva.
    Retorna True se removeu orphan, False se nada a fazer.
    """
    cfg = project_root / "NuGet.config"
    if not cfg.is_file():
        return False
    try:
        content = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if _TEMP_NUGET_CONFIG_SENTINEL not in content:
        return False
    try:
        cfg.unlink()
        return True
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return EXIT_OK

    if args.command == "review":
        return _cmd_review(args)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "list":
        return _cmd_list(args)
    if args.command == "docs":
        return _cmd_docs(args)
    if args.command == "fix":
        return _cmd_fix(args)
    if args.command == "phase-out":
        return _cmd_phase_out(args)
    if args.command == "migrate-windows":
        from .migrate import cmd_migrate_windows
        return cmd_migrate_windows(args)
    if args.command == "stats":
        return _cmd_stats(args)
    if args.command == "all":
        return _cmd_all(args)
    if args.command == "pre-migrate-check":
        return _cmd_pre_migrate_check(args)
    if args.command == "pack-scrub":
        return _cmd_pack_scrub(args)
    if args.command == "migrate-check":
        return _cmd_migrate_check(args)
    if args.command == "install-skills":
        from .agent_skills import ensure_ccs_agent_skills
        records = ensure_ccs_agent_skills(verbose=True)
        changed = sum(1 for record in records if record.changed)
        print(f"CCS skills OK: {len(records)} checked, {changed} changed")
        return EXIT_OK
    if args.command == "doctor-uipath-cli":
        return _cmd_doctor_uipath_cli(args)

    parser.print_help()
    return EXIT_OK


def ccs_uip_main(argv: list[str] | None = None) -> int:
    """God command entry-point — injeta subcommand 'all' implícito.

    `ccs-uip <project> [flags]` ≡ `rule-engine all <project> [flags]`. Existe pra
    eliminar dependência de alias PowerShell em profile.ps1 (não carrega em
    `-NoProfile` shells, hooks, agents, CI).

    Interface pública intencionalmente mínima:
        `ccs-uip <project_path>`
        `ccs-uip <project_path> --apply-contextual`

    Subcommands atômicos continuam existindo só pelo entrypoint interno:
        `python -m uip_engine.cli <subcmd> ...`
    """
    argv = argv if argv is not None else sys.argv[1:]
    internal_subcommands = {
        "review", "fix", "list", "validate", "docs", "stats", "all",
        "migrate-windows", "phase-out",
        # Phase 7 (2026-05): new standalone subcommands.
        "pre-migrate-check", "pack-scrub", "migrate-check",
        "install-skills",
        "doctor-uipath-cli",
    }
    if argv and argv[0] in internal_subcommands:
        print(
            f"[ERROR] `ccs-uip {argv[0]}` não é interface pública.\n"
            f"Use `ccs-uip <project_path> [--apply-contextual]`.\n"
            f"Para debug interno: `python -m uip_engine.cli {argv[0]} ...`.",
            file=sys.stderr,
        )
        return EXIT_ERROR
    if argv and argv[0] in ("-h", "--help"):
        print(
            "ccs-uip — god command UiPath rules engine\n"
            "\n"
            "USAGE:\n"
            "  ccs-uip <project_path> [--apply-contextual]\n"
            "      Pipeline completo (migration probe → deterministic fix →\n"
            "      external gates → contextual report). FAIL só para\n"
            "      qualquer ERROR/HALT ativo.\n"
            "      --apply-contextual: modo assistido por IA para aplicar fixes\n"
            "      contextuais (default: lista como PASS-WITH-NOTES, sem aplicar).\n"
            "\n"
            "INTERFACE PÚBLICA: só `ccs-uip <project_path>` e\n"
            "`ccs-uip <project_path> --apply-contextual`.\n"
            "Debug interno: `python -m uip_engine.cli <subcommand> ...`.\n"
        )
        return EXIT_OK
    if not argv:
        return ccs_uip_main(["--help"])
    from .agent_skills import ensure_ccs_agent_skills
    ensure_ccs_agent_skills(verbose=True)
    import os as _os
    if _os.environ.get("UIP_TOOLCHAIN_SKIP_DOCTOR", "").lower() not in {"1", "true", "yes"}:
        doctor_rc = _cmd_doctor_uipath_cli(type("A", (), {})())
        if doctor_rc != EXIT_OK:
            print(
                "[ERROR] toolchain doctor failed; fix local UiPath CLI/migrator "
                "readiness or set UIP_TOOLCHAIN_SKIP_DOCTOR=1 for controlled tests.",
                file=sys.stderr,
            )
            return doctor_rc
    return main(["all"] + argv)


# Backwards-compatible Python symbol for old imports. The public console
# script intentionally no longer exports `uip`.
uip_main = ccs_uip_main


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rule-engine")
    sub = p.add_subparsers(dest="command")

    rev = sub.add_parser("review", help="Review project against rules")
    rev.add_argument("path", help="Project root or workspace path")
    rev.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE))
    rev.add_argument("--format", choices=["text", "json"], default="text")
    rev.add_argument("--multi-project", action="store_true")
    rev.add_argument("--verbose", action="store_true")
    rev.add_argument("--telemetry", action="store_true",
                     help="Append findings counts to .tmp/telemetry/<date>.jsonl")
    # NOTE: --no-analyzer-gate flag mantido só p/ back-compat. Review é o
    # canonical pre-publish gate: a engine decide os gates externos. Flag emite
    # warning e é ignorada (não desliga gate).
    rev.add_argument("--no-analyzer-gate", action="store_true",
                     help="DEPRECATED. review controla analyzer/pack gates "
                          "(pre-publish gate canonical, sem opt-out). Flag emite "
                          "warning e é ignorada — mantida só por backwards-compat.")
    rev.add_argument("--analyzer-gate-timeout", type=int, default=180,
                     help="Timeout analyzer gate em segundos (default 180). "
                          "Usa `uip rpa analyze`.")
    rev.add_argument("--pack-gate-timeout", type=int, default=600,
                     help="Timeout pack gate em segundos (default 600). "
                          "Usa `uip rpa pack` como dry-run.")
    rev.add_argument("--restore-gate-timeout", dest="nuget_gate_timeout",
                     type=int, default=300,
                     help="Timeout `uip rpa restore` em segundos (default 300).")
    rev.add_argument("--build-gate-timeout", type=int, default=180,
                     help="Timeout `uip rpa build --skip-analyze` em segundos "
                          "(default 180).")
    st = sub.add_parser("stats", help="Aggregate telemetry: top rules + trends")
    st.add_argument("--since", default="30d",
                    help="Window: <N>d (days), <N>h (hours), or 'all'. Default 30d")
    st.add_argument("--top", type=int, default=20,
                    help="Top N rules to show (default 20)")
    st.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE))

    val = sub.add_parser("validate", help="Validate rules.yaml schema")
    val.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE))

    lst = sub.add_parser("list", help="List loaded rules")
    lst.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE))
    lst.add_argument("--by-category", action="store_true")
    lst.add_argument("--by-class", action="store_true",
                     help="Group rules por apply_class (deterministic/contextual/structural)")

    docs = sub.add_parser("docs", help="Gera catálogo derivado de regras (markdown)")
    docs.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE))
    docs.add_argument("--llm-only", action="store_true",
                      help="Só rules LLM-dep (apply_class != deterministic)")
    docs.add_argument("--out", default=None,
                      help="Path destino. Default stdout.")

    fx = sub.add_parser("fix", help="Apply fix.mechanical for findings (default dry-run)")
    fx.add_argument("path", help="Project root path")
    fx.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE))
    fx.add_argument("--apply", action="store_true",
                    help="Write changes (default: dry-run)")
    fx.add_argument("--rules", default="",
                    help="Comma-separated rule IDs to filter")
    fx.add_argument("--include-class", default="deterministic",
                    help="Apply-class(es) a aplicar: deterministic (default), "
                         "contextual, structural, all, ou comma-separated. "
                         "Default deterministic = só fixes mecânicos seguros.")
    fx.add_argument("--no-analyzer-gate", action="store_true",
                    help="Desliga analyzer gate oficial (`uip rpa analyze`) — default ON. "
                         "Default behavior: roda baseline pré-fix + diff "
                         "pós-fix. Reporta erros INTRODUZIDOS pelos fixes "
                         "(diff-based: pré-existentes ignorados).")

    po = sub.add_parser("phase-out", help="Universalize windows-only rules")
    po.add_argument("scope", choices=["windows-only"])
    po.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE))
    po.add_argument("--apply", action="store_true",
                    help="Write changes to rules.yaml (default: dry-run)")

    mw = sub.add_parser(
        "migrate-windows",
        help="Migra projeto Legacy/Windows-Legacy → Windows via Activity Migrator CLI + engine pre/post"
    )
    mw.add_argument("path", help="Projeto Legacy/Windows-Legacy a migrar")
    mw.add_argument("--out", default=None,
                    help="Output dir (default: <input>_Migrated)")
    mw.add_argument("--migrator-path", default=None,
                    help="Path explícito ao Activity Migrator binary "
                         "(senão lê env UIPATH_ACTIVITY_MIGRATOR ou PATH)")
    mw.add_argument("--migrator-args", default="",
                    help="Args extras forwardados ao Activity Migrator")
    mw.add_argument("--ignore-missing-dependencies", action="store_true",
                    help="Forward `--ignore-missing-dependencies` ao Migrator. "
                         "Útil sem VPN/feed privado (ccs_* etc viram warnings).")
    mw.add_argument("--analyze-only", action="store_true",
                    help="Roda `analyze` em vez de `upgrade` (read-only, "
                         "gera SARIF). Pula post-fix.")
    mw.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE))
    mw.add_argument("--skip-migrator", action="store_true",
                    help="Só pre-scan, não invoca Migrator")
    mw.add_argument("--skip-post", action="store_true",
                    help="Pula engine fix --apply pós-Migrator")
    mw.add_argument("--force", action="store_true",
                    help="Sobrescreve --out se já existir")
    mw.add_argument("--dry-run", action="store_true",
                    help="Mostra plano, não executa Migrator")

    # Phase 2 (2026-05): pre-migrate-check subcommand. Offline clone do
    # MigratedPackageVersionResolver — reproduz §6 do dossier Stream E.
    # Surfaces drift PRE Activity Migrator pra evitar surprise post-migrate.
    pmc = sub.add_parser(
        "pre-migrate-check",
        help="Offline pre-check pin drift PRE Activity Migrator (reproduz "
             "MigratedPackageVersionResolver.GetRecommendedVersion §6).",
    )
    pmc.add_argument("path", help="Project root path (must contain project.json)")
    pmc.add_argument(
        "--target-framework",
        default="net6.0-windows7.0",
        help="TFM target post-migrate (default net6.0-windows7.0).",
    )
    pmc.add_argument(
        "--cache-dir",
        default=str(Path(__file__).resolve().parents[2] / ".tmp" / "nuget_cache"),
        help="NuGet response cache dir (default .uip-toolchain/.tmp/nuget_cache/).",
    )
    pmc.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    pmc.add_argument(
        "--include-prerelease",
        action="store_true",
        help="Include -prerelease versions (default off; matches Studio).",
    )
    # Phase 2.1 (2026-05): local .nupkgs/ folder fallback. Source-of-truth para
    # pacotes proprietarios CCS_* (Sicoob) que nao existem em nuget.org public.
    pmc.add_argument(
        "--local-nupkgs",
        default=r"C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs",
        help="Pasta local .nupkgs/ usada como source-of-truth offline para "
             "pacotes proprietarios CCS_* (Sicoob). Pass '' (empty) para "
             "desabilitar e usar apenas NuGet public.",
    )

    # Phase 4 (2026-05): pack-scrub subcommand. Remove <repository> leak do
    # .nuspec dentro de um .nupkg published. Stream E dossier §05.
    ps = sub.add_parser(
        "pack-scrub",
        help="Remove <repository> leak do .nuspec dentro de um .nupkg "
             "post-publish (Stream E dossier §05)",
    )
    ps.add_argument("nupkg", help="Path ao .nupkg")
    ps.add_argument("-o", "--output", default=None,
                    help="Output path; default = inplace (atomic replace)")
    ps.add_argument("--inspect-only", action="store_true",
                    help="Só inspect, não modifica (alias: --dry-run)")
    ps.add_argument("--dry-run", action="store_true", dest="inspect_only",
                    help=argparse.SUPPRESS)
    ps.add_argument("--sign-cert", default=None,
                    help="Se setado, invoca `nuget sign` post-scrub com este "
                         "cert thumbprint (SHA-1/SHA-256). Requer nuget no PATH.")
    ps.add_argument("--timestamper",
                    default="http://timestamp.digicert.com",
                    help="RFC 3161 timestamp server (usado só se --sign-cert)")

    # Phase 5 (2026-05): migrate-check subcommand (advisory, opt-in).
    # Reflection-driven Activity Migrator probe — surfaces what GA Migrator
    # would do, sem mutar projeto.
    mc = sub.add_parser(
        "migrate-check",
        help="Reflection-driven Activity Migrator probe (Stream E §04). "
             "Surfaces what the GA 'Migrate to Windows' would do, sem mutar.",
    )
    mc.add_argument("project", help="Path ao project root ou project.json")
    mc.add_argument("--dry-run", action="store_true", default=True,
                    help="DEFAULT True — apenas advisory, não muta XAML")
    mc.add_argument("--dll", default=None,
                    help="Override UiPath.UIAutomationNext.Migration.dll path")
    mc.add_argument("--format", choices=["json", "text"], default="text",
                    help="Output format (default text)")
    mc.add_argument("--timeout", type=int, default=300,
                    help="Timeout (s) para migrator_headless subprocess (default 300)")

    al = sub.add_parser(
        "all",
        help="GOD COMMAND — pipeline completo: migration probe + "
             "deterministic auto-fix + external gates + contextual "
             "report. FAIL para qualquer ERROR/HALT.",
    )
    al.add_argument("path", help="Project root path")
    al.add_argument("--apply-contextual", action="store_true",
                    help="Modo assistido por IA: aplica fixes contextuais "
                         "(default: reporta em PASS-WITH-NOTES, sem aplicar).")
    # Escape hatches internos (NÃO documentados no `uip --help`). Acessíveis
    # via env vars; tests invocam direto via `_ns(...)`. Mantidos pra debug
    # interno e back-compat de invocações programáticas — NÃO são interface
    # pública. Interface pública = `ccs-uip <path> [--apply-contextual]` só.
    #
    # Configuração runtime via env:
    #   UIP_TOOLCHAIN_SKIP_MIGRATION=1   → pula PHASE 0 (Migrator)
    #   UIP_TOOLCHAIN_NO_SWAP=1          → não swap após Migrator success
    #   UIP_TOOLCHAIN_WATCH=1            → loop interativo aguardando mtime
    #   UIP_TOOLCHAIN_WATCH_INTERVAL=<f> → cadence poll watch (segundos)
    #   UIP_TOOLCHAIN_MAX_ITERS=<n>      → limite iters loop (0 = ilimitado)
    #   UIP_TOOLCHAIN_RULES_FILE=<path>        → override rules.yaml

    sub.add_parser(
        "install-skills",
        help="Install/update CCS-managed agent skills globally for Codex and Claude",
    )
    sub.add_parser(
        "doctor-uipath-cli",
        help="Check official UiPath CLI host, rpa-tool, Node, and .NET readiness",
    )

    return p


def _load_rules_or_die(path: str) -> list:
    try:
        rules = load_rules(
            Path(path),
            registered_detectors=set(DETECTOR_REGISTRY.keys()),
            registered_fixers=set(FIXER_REGISTRY.keys()),
        )
        from .rule_quality import validate_rule_quality
        quality_errors = validate_rule_quality(rules)
        if quality_errors:
            print("[RULE-QUALITY] enterprise rule quality failed:", file=sys.stderr)
            for err in quality_errors:
                print(f"  - {err}", file=sys.stderr)
            sys.exit(EXIT_INTERNAL)
        return rules
    except SchemaError as e:
        print(f"[INTERNAL] schema error: {e}", file=sys.stderr)
        sys.exit(EXIT_INTERNAL)
    except Exception as e:
        print(f"[INTERNAL] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(EXIT_INTERNAL)


def _cmd_review(args) -> int:
    """review = canonical pre-publish gate.

    Ordem de gates:
      1. runner.run(args.path)              # rules Sicoob (engine local)
      2. _apply_sicoob_lib_overrides(...)   # downgrade lib-contract findings
      3. publish-readiness preconditions    # J-9/W-40/A-19d
      4. _run_official_restore_gate(...)    # uip rpa restore (official)
      5. _inject_analyzer_findings(...)     # uip rpa analyze
      6. _run_official_build_gate(...)      # uip rpa build
      7. _run_pack_gate(...)                # uip rpa pack
      8. relatório final + exit code

    Sem opt-out CLI. Se review passa, projeto é publish-safe.

    Env opt-out (tests apenas):
      UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES=1 → pula gates externos
      restore/analyze/build/pack. Não é meant for production — apenas test harness.
    """
    import os as _os
    rules = _load_rules_or_die(args.rules_file)
    runner = Runner(rules=rules, detectors=DETECTOR_REGISTRY, fixers=FIXER_REGISTRY)
    result = runner.run(args.path)

    # Sicoob lib-contract overrides: downgrade findings que casam (rule, ident).
    # Aplicado ANTES do analyzer gate p/ que count INFO consolidado fique correto.
    _apply_sicoob_lib_overrides(result, verbose=getattr(args, "verbose", False))
    publish_preconditions_blocked = _has_publish_readiness_precondition_errors(result)

    # Back-compat: --no-analyzer-gate deprecado. Warning + ignore.
    if getattr(args, "no_analyzer_gate", False):
        print("[WARNING] --no-analyzer-gate is deprecated and ignored; "
              "review controls analyzer/pack gates.", file=sys.stderr)

    external_gates_disabled = (
        _os.environ.get("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", "").strip()
        in ("1", "true", "yes")
    )

    if publish_preconditions_blocked and getattr(args, "verbose", False):
        print("[review] publish-readiness precondition failed; "
              "skipping external UiPath gates.", file=sys.stderr)

    if not external_gates_disabled and not publish_preconditions_blocked:
        verbose = getattr(args, "verbose", False)
        project_root = Path(args.path).resolve()
        restore_handled, restore_blocked = _run_official_restore_gate(
            result,
            project_root,
            timeout=getattr(args, "nuget_gate_timeout", 300),
            verbose=verbose,
        )

        # P1 (2026-05): gates externos paralelos via ThreadPoolExecutor.
        # Cada gate é uma invocação subprocess externa independente
        # (uip rpa analyze/build/pack) — sem shared state mutável
        # além de `result.add(...)` (list.append é GIL-atomic em CPython).
        from concurrent.futures import ThreadPoolExecutor, as_completed
        gates = []
        if not restore_blocked:
            gates.extend([
                (
                    "analyzer-gate",
                    lambda: _inject_analyzer_findings(
                        result, args.path,
                        timeout=getattr(args, "analyzer_gate_timeout", 180),
                        verbose=verbose,
                    ),
                ),
                (
                    "build-gate",
                    lambda: _run_official_build_gate(
                        result, args.path,
                        timeout=getattr(args, "build_gate_timeout", 180),
                        verbose=verbose,
                    ),
                ),
                (
                    "pack-gate",
                    lambda: _run_pack_gate(
                        result, args.path,
                        timeout=getattr(args, "pack_gate_timeout", 600),
                        verbose=verbose,
                    ),
                ),
            ])
        elif verbose:
            print("[review] restore gate blocked analyzer/pack gates.",
                  file=sys.stderr)
        if gates:
            with ThreadPoolExecutor(max_workers=len(gates)) as ex:
                future_to_name = {ex.submit(fn): name for name, fn in gates}
                for fut in as_completed(future_to_name):
                    name = future_to_name[fut]
                    try:
                        fut.result()
                        if verbose:
                            print(f"[{name}] complete", file=sys.stderr)
                    except Exception as e:
                        # Gate failure não derruba review — emit finding diagnóstico.
                        result.add_internal_error(
                            f"{name} raised {type(e).__name__}: {e}"
                        )
                        print(f"[{name}] FAILED: {type(e).__name__}: {e}",
                              file=sys.stderr)
    elif external_gates_disabled and getattr(args, "verbose", False):
        print("[review] UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES set — "
              "skipping restore/analyze/build/pack gates.", file=sys.stderr)

    rule_index = {r.id: r for r in rules}
    if args.format == "json":
        _emit_json(result, args.path, rule_index)
    else:
        _emit_text(result, args.path, rule_index)

    if getattr(args, "telemetry", False):
        try:
            _write_telemetry(result, args.path)
        except Exception as e:
            print(f"[telemetry] {type(e).__name__}: {e}", file=sys.stderr)

    if result.internal_errors:
        return EXIT_INTERNAL
    sev = result.max_severity()
    if sev is None:
        return EXIT_OK
    if sev == Severity.HALT:
        return EXIT_HALT
    if sev == Severity.ERROR:
        return EXIT_ERROR
    return EXIT_WARN


def _has_publish_readiness_precondition_errors(result) -> bool:
    for finding in getattr(result, "findings", []):
        if getattr(finding, "suppressed", False):
            continue
        if finding.rule_id not in _PUBLISH_READINESS_PRECONDITION_RULES:
            continue
        if finding.severity in (Severity.ERROR, Severity.HALT):
            return True
    return False


_ANALYZER_SEVERITY_MAP = {
    "Error": Severity.ERROR,
    "Warning": Severity.WARN,
    "Info": Severity.INFO,
}

# UiPath rule codes que sao politica aceita Sicoob (A-3 credential propagation
# REFramework). Downgrade pra INFO + category "uipath_sicoob_policy" para nao
# bloquear gate em padroes legitimos. NAO eh mass-suppress — eh policy override
# explicita declarada na engine, alinhada com CLAUDE.md.
_ANALYZER_SICOOB_POLICY = {
    "ST-SEC-007": "A-3 credential propagation — SecureString arg legitimo no chain.",
    "ST-SEC-008": "A-3 credential propagation — SecureString circula entre workflows REFramework.",
    "ST-SEC-009": "A-3 credential propagation — SecureString->String necessario p/ header Bearer/Basic.",
    "ST-NMG-009": "N-1/N-2 Sicoob — DataTable variavel usa prefixo 'vDTab', nao 'dt_'.",
    "ST-NMG-011": "N-2 Sicoob — DataTable argumento usa prefixo 'in_DTab'/'io_DTab'/'out_DTab', nao 'dt_'.",
    "ST-NMG-008": "Duplicata de Sicoob N-8 (mesma regra, >30 chars). N-8 governa.",
    "ST-NMG-016": "Duplicata de N-8 (max length arg). N-8/lib-contract governam.",
    # Adicionados 2026-05-19 (aprovado pelo usuario) — Sicoob convention prevalece.
    "ST-NMG-005": "Duplicata de Sicoob U-4 (variavel definida >1x). U-4 governa.",
    "ST-MRD-002": "Duplicata de Sicoob N-17 (DisplayName descritivo). N-17 governa global.",
    "ST-DBP-007": "Duplicata de Sicoob A-5 (decomposicao modular por conceito). A-5 governa.",
    "ST-MRD-009": "Duplicata de Sicoob CX-2 (nesting depth). CX-2 governa thresholds.",
    "ST-USG-009": "Duplicata de Sicoob U-1 (variavel declarada nao usada). U-1 governa.",
    "TA-DBP-002": "Duplicata de Sicoob TCC-1 (Test Case coverage). TCC-1 governa.",
    "UI-ANA-017": "Duplicata de Sicoob API-1 (ContinueOnError em verbos nao-idempotentes). API-1 governa.",
    "ST-USG-034": "Sicoob nao usa Automation Hub — exigencia nao aplicavel.",
    "UI-USG-011": "Sisbr UI: idx= necessario p/ identificar elementos em datatables (UI-3 ByInstance + UI-2 Simulate atenuam volatilidade do idx).",
}

# Whitelist por escopo de path. Testes Sicoob nao precisam seguir convencoes
# de production: DisplayName padrao OK (mocks), variaveis curtas OK (vTI_A
# = Test Item A), LogMessage nao obrigatoria (test runner separado).
# Format: {rule_code: (path_substrings_tuple, reason)}.
_ANALYZER_TEST_SCOPE_WHITELIST = {
    # ST-MRD-002 e ST-NMG-008 removidos daqui — agora em GLOBAL policy
    # (Sicoob N-17 / N-8 governam globalmente, nao só em Tests/).
    "ST-NMG-004": (("\\Tests\\", "/Tests/"),
                   "Tests/* — DisplayName duplicado aceito em test setups."),
    "ST-USG-020": (("\\Tests\\", "/Tests/"),
                   "Tests/* — Log nao usada OK em test runners (assert/mock)."),
    "ST-NMG-001": (("\\Tests\\", "/Tests/"),
                   "Tests/* — naming variado aceito em fixtures."),
    "ST-ANA-009": (("\\Tests\\", "/Tests/"),
                   "Tests/* — containers colapsados OK (UI design-time)."),
}

# Framework/* + Main.xaml = REFramework template. CLAUDE.md A-4: nao modificar
# SetTransactionStatus/InitAllApplications + protecao geral REFramework.
# Whitelist rules que sao caracteristicas legitimas do template.
_ANALYZER_FRAMEWORK_SCOPE_WHITELIST = {
    "ST-NMG-004": (("\\Framework\\", "/Framework/"),
                   "Framework/* — REFramework template; A-4 protected, DisplayName dups intencionais."),
    "ST-MRD-002": (("\\Framework\\", "/Framework/"),
                   "Framework/* — REFramework template; DisplayName default em activities de boilerplate."),
    "ST-AMG-001": (("\\Framework\\", "/Framework/", "\\Main.xaml", "/Main.xaml"),
                   "REFramework template — BusinessRuleException classica e padrao do framework Sicoob."),
    "UI-PRR-004": (("\\Framework\\", "/Framework/"),
                   "Framework/* — delays hardcoded de template REFramework (TakeScreenshot/SetTxStatus)."),
    "ST-MRD-007": (("\\Framework\\", "/Framework/"),
                   "Framework/* — REFramework state machine naturalmente aninha >3."),
}

# Engine Sicoob findings que sao overrides legitimos por contrato de lib externa.
# Match por (rule_id, identifier_substring). Findings sao downgraded para INFO
# com nota explicativa. Diferente de policy whitelist UiPath (ANALYZER_SICOOB_POLICY)
# que e por rule_id inteiro — aqui eh por arg/var ESPECIFICO. Match exato no message.
_SICOOB_LIB_CONTRACT_OVERRIDES = [
    # CCS_Controle 1.1.0 obriga 'Atualiza' (presente 3sg) — engine N-13 quer infinitivo
    ("N-13", "in_BlAtualizaProcessamentoFim", "CCS_Controle 1.1.0 contract: lib exige 'Atualiza' (nao 'Atualizar')."),
    ("N-13", "in_BlAtualizaProcessamentoInicio", "CCS_Controle 1.1.0 contract: lib exige 'Atualiza' (nao 'Atualizar')."),
    # Mesmo arg estoura 30 chars (32) — contrato nao permite encurtar
    ("N-8", "in_BlAtualizaProcessamentoInicio", "CCS_Controle 1.1.0 contract: nome fixo da lib, 32 chars."),
]


def _official_uip_enabled() -> bool:
    import os as _os
    return _os.environ.get("UIP_TOOLCHAIN_USE_OFFICIAL_UIP", "1").strip().lower() not in (
        "0", "false", "no", "legacy",
    )


def _write_official_nuget_config(base_dir: Path) -> Path | None:
    from .official_uip import write_official_nuget_config

    return write_official_nuget_config(base_dir)


def _apply_sicoob_lib_overrides(result, verbose: bool = False) -> int:
    """Downgrade findings que casam (rule_id, identifier) em LIB_CONTRACT_OVERRIDES.

    Override = INFO + category="sicoob_lib_contract" + nota anexada. Aplica-se
    a findings Sicoob (rule_id sem prefixo UIPATH:). Returns count of overrides.
    """
    if not _SICOOB_LIB_CONTRACT_OVERRIDES:
        return 0
    count = 0
    for f in result.findings:
        if f.rule_id.startswith("UIPATH:"):
            continue
        for rid, identifier, note in _SICOOB_LIB_CONTRACT_OVERRIDES:
            if f.rule_id != rid:
                continue
            if identifier not in f.message:
                continue
            f.severity = Severity.INFO
            f.category = "sicoob_lib_contract"
            f.message = f"{f.message} | OVERRIDE: {note}"
            count += 1
            break
    if verbose and count:
        print(f"[lib-contract-override] {count} findings downgraded.", file=sys.stderr)
    return count


def _add_analyzer_record_finding(result, raw: dict, *, source: str = "analyzer") -> bool:
    """Convert one analyzer record into a CCS Finding."""
    from ._types import Finding

    sev_str = raw.get("ErrorSeverity") or ""
    sev = _ANALYZER_SEVERITY_MAP.get(sev_str)
    if sev is None:
        sev = _ANALYZER_SEVERITY_MAP.get(str(sev_str).title())
    if sev is None:
        sev = Severity.ERROR
    code = raw.get("ErrorCode") or "LOAD"
    fp = raw.get("FilePath") or ""
    item = raw.get("Item") or ""
    act = raw.get("ActivityDisplayName") or ""
    desc = (raw.get("Description") or "").strip()
    category = "uipath"
    policy_note = _ANALYZER_SICOOB_POLICY.get(code)
    if policy_note is not None:
        sev = Severity.INFO
        category = "uipath_sicoob_policy"
        desc = f"{desc} | POLICY-ACEITA: {policy_note}"
    else:
        scope = _ANALYZER_TEST_SCOPE_WHITELIST.get(code)
        if scope is not None:
            substrs, scope_note = scope
            if any(s in fp for s in substrs):
                sev = Severity.INFO
                category = "uipath_test_scope"
                desc = f"{desc} | SCOPE-WHITELIST: {scope_note}"
        fw_scope = _ANALYZER_FRAMEWORK_SCOPE_WHITELIST.get(code)
        if fw_scope is not None and category == "uipath":
            substrs, scope_note = fw_scope
            if any(s in fp for s in substrs):
                sev = Severity.INFO
                category = "uipath_framework_scope"
                desc = f"{desc} | FRAMEWORK-WHITELIST: {scope_note}"
    msg_parts = [desc or f"{source} reported {code}"]
    if item:
        msg_parts.append(f"[{item}]")
    if act:
        msg_parts.append(f"@{act}")
    result.add(Finding(
        rule_id=f"UIPATH:{code}",
        severity=sev,
        category=category,
        file=fp or "(project)",
        line=0,
        message=" ".join(msg_parts),
    ))
    return category != "uipath"


def _add_official_uip_diagnostic(result, diagnostic, *, source: str) -> None:
    """Convert an official CLI compatibility/failure diagnostic into a finding."""
    from ._types import Finding

    sev = Severity.ERROR
    if str(getattr(diagnostic, "severity", "")).lower() == "warning":
        sev = Severity.WARN
    result.add(Finding(
        rule_id=f"UIPATH:{diagnostic.code}",
        severity=sev,
        category="breaking" if sev == Severity.ERROR else "metadata",
        file=getattr(diagnostic, "file", "project.json") or "project.json",
        line=0,
        message=f"[{source}] {diagnostic.message}",
    ))


def _check_official_uip_compatibility(result, official: Path, *, source: str) -> bool:
    """Return True when official CLI is compatible enough to run the gate."""
    from .official_uip import compatibility_diagnostic, get_official_uip_version

    diagnostic = compatibility_diagnostic(get_official_uip_version(str(official)))
    if diagnostic is None:
        return True
    _add_official_uip_diagnostic(result, diagnostic, source=source)
    return str(diagnostic.severity).lower() != "error"


def _run_official_restore_gate(result, project_root: Path, timeout: int,
                               verbose: bool) -> tuple[bool, bool]:
    """Run official `uip rpa restore` before analyze/pack.

    Returns `(handled, blocked)`: handled means official CLI was available and
    attempted/diagnosed; blocked means findings were added that should stop
    later official analyzer/pack gates for this review run.
    """
    import tempfile
    import shutil as _shutil
    from ._types import Finding
    from .official_uip import (
        diagnose_official_uip_failure,
        discover_official_uip,
        official_failure_text,
        run_official_uip,
    )

    if not _official_uip_enabled():
        return False, False
    official = discover_official_uip()
    if official is None:
        return False, False
    if not _check_official_uip_compatibility(result, official, source="RESTORE-GATE"):
        return True, True

    engine_root = Path(__file__).resolve().parents[2]
    base_tmp = engine_root / ".tmp" / "official_uip_restore"
    base_tmp.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(dir=str(base_tmp), prefix="restore_"))
    outdir = tmpdir / "deps"
    try:
        nuget_config = _write_official_nuget_config(tmpdir)
        args = ["rpa", "restore", str(project_root), str(outdir), "--output", "json"]
        if nuget_config is not None:
            args.extend(["--nuget-sources-config-path", str(nuget_config)])
        if verbose:
            print(f"[RESTORE-GATE] running official uip rpa restore via {official}",
                  file=sys.stderr)
        try:
            res = run_official_uip(args, timeout=timeout, uip_path=official)
        except Exception as exc:
            result.add(Finding(
                rule_id="UIPATH:RESTORE_HALT",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=f"[RESTORE-GATE] official uip rpa restore failed: "
                        f"{type(exc).__name__}: {exc}",
            ))
            print(f"[RESTORE-GATE] official uip rpa restore failed: {exc}",
                  file=sys.stderr)
            return True, True

        if res.returncode == 0:
            if verbose:
                print("[RESTORE-GATE] official uip rpa restore OK", file=sys.stderr)
            return True, False

        diagnostics = diagnose_official_uip_failure(
            official_failure_text(res),
            "rpa restore",
        )
        for diagnostic in diagnostics:
            _add_official_uip_diagnostic(result, diagnostic, source="RESTORE-GATE")
        if not diagnostics:
            msg = ""
            if res.envelope is not None:
                msg = res.envelope.message or res.envelope.instructions or ""
            if not msg:
                msg = (res.stderr or res.stdout).strip().splitlines()[-1:] or [""]
                msg = msg[0]
            result.add(Finding(
                rule_id="UIPATH:RESTORE_HALT",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=f"[RESTORE-GATE] official uip rpa restore exit "
                        f"{res.returncode}: {str(msg)[:400]}",
            ))
        return True, True
    finally:
        _shutil.rmtree(tmpdir, ignore_errors=True)


def _cmd_doctor_uipath_cli(args) -> int:
    """Check local official UiPath CLI readiness for CCS external gates."""
    import os as _os
    import shutil as _shutil
    import subprocess
    from .official_uip import (
        compatibility_diagnostic,
        discover_official_uip,
        get_official_uip_version,
        parse_uip_envelope,
        run_official_uip,
    )
    from .migrate import find_migrator

    errors: list[str] = []
    warnings: list[str] = []

    official = discover_official_uip()
    if official is None:
        errors.append("official `uip` not found. Install @uipath/cli or set UIPATH_UIP_CLI.")
        print("official uip: NOT FOUND")
        return EXIT_ERROR

    print(f"official uip: {official}")
    version = get_official_uip_version(str(official))
    if version is None:
        warnings.append("could not read `uip --version`")
        print("uip version: UNKNOWN")
    else:
        print(f"uip version: {version.raw}")
    diag = compatibility_diagnostic(version)
    if diag is not None:
        target = errors if str(diag.severity).lower() == "error" else warnings
        target.append(diag.message)

    try:
        tools = run_official_uip(
            ["tools", "list", "--output", "json"],
            timeout=60,
            uip_path=official,
        )
    except Exception as exc:
        errors.append(f"`uip tools list` failed: {type(exc).__name__}: {exc}")
        tools = None
    if tools is not None:
        envelope = tools.envelope or parse_uip_envelope(tools.stdout)
        rpa_tool = None
        if envelope is not None and isinstance(envelope.data, list):
            for item in envelope.data:
                if isinstance(item, dict) and item.get("commandPrefix") == "rpa":
                    rpa_tool = item
                    break
        if rpa_tool is None:
            errors.append("rpa-tool not installed; run `uip tools update`.")
            print("rpa-tool: NOT FOUND")
        else:
            print(f"rpa-tool: {rpa_tool.get('version')}")

    node = _shutil.which("node")
    if node:
        try:
            proc = subprocess.run(
                [node, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False,
            )
            node_version = (proc.stdout or proc.stderr).strip()
            print(f"node: {node_version} ({node})")
            major = int(node_version.lstrip("v").split(".", 1)[0])
            if major < 18:
                errors.append(f"Node.js {node_version} is below official CLI requirement >=18.")
        except Exception as exc:
            warnings.append(f"could not read node version: {type(exc).__name__}: {exc}")
    else:
        errors.append("node not found on PATH; official UiPath CLI requires Node.js >=18.")
        print("node: NOT FOUND")

    dotnet = None
    explicit_dotnet_root = _os.environ.get("UIP_TOOLCHAIN_DOTNET_ROOT")
    if explicit_dotnet_root:
        explicit_dotnet = Path(explicit_dotnet_root) / "dotnet.exe"
        if explicit_dotnet.is_file():
            dotnet = str(explicit_dotnet)
    if dotnet is None:
        home_dotnet = Path.home() / ".dotnet" / "dotnet.exe"
        if home_dotnet.is_file():
            dotnet = str(home_dotnet)
    if dotnet is None:
        dotnet = _shutil.which("dotnet")
    if dotnet:
        try:
            version_proc = subprocess.run(
                [dotnet, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False,
            )
            sdk_proc = subprocess.run(
                [dotnet, "--list-sdks"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False,
            )
            dotnet_version = (version_proc.stdout or version_proc.stderr).strip()
            sdk_lines = [line.strip() for line in sdk_proc.stdout.splitlines() if line.strip()]
            print(f"dotnet: {dotnet_version} ({dotnet})")
            if sdk_lines:
                print("dotnet SDKs: " + "; ".join(sdk_lines))
            has_sdk8 = any(
                (match is not None and int(match.group(1)) >= 8)
                for match in (re.match(r"^\s*(\d+)\.", line) for line in sdk_lines)
            )
            if sdk_proc.returncode != 0 or not sdk_lines:
                errors.append(
                    ".NET SDK not listed by `dotnet --list-sdks`; official `uip rpa pack` "
                    "requires .NET SDK 8+."
                )
            elif not has_sdk8:
                errors.append(
                    ".NET SDK 8+ not found; official `uip rpa pack` restores a net8.0 "
                    "temporary project even when the UiPath Studio project targets Windows/.NET 6."
                )
        except Exception as exc:
            warnings.append(f"could not read dotnet version: {type(exc).__name__}: {exc}")
    else:
        errors.append(
            ".NET SDK 8+ not found on PATH or ~/.dotnet; official `uip rpa pack` cannot run."
        )
        print("dotnet: NOT FOUND")

    migrator = find_migrator(None)
    if migrator is None:
        errors.append(
            "UiPath Activity Migrator not found. Provide tools/UiPathActivityMigrator, "
            "vendor/UiPathActivityMigrator, or UIPATH_ACTIVITY_MIGRATOR."
        )
        print("activity migrator: NOT FOUND")
    else:
        try:
            stat = migrator.stat()
            print(
                f"activity migrator: {migrator} "
                f"({round(stat.st_size / 1024 / 1024, 1)} MB)"
            )
        except OSError:
            print(f"activity migrator: {migrator}")

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    return EXIT_ERROR if errors else EXIT_OK


def _inject_official_analyzer_findings(result, project_root: Path, timeout: int,
                                       verbose: bool) -> bool:
    """Run official `uip rpa analyze`. Returns True when official CLI handled it."""
    import os as _os
    import tempfile
    import shutil as _shutil
    from ._types import Finding
    from .official_uip import (
        discover_official_uip,
        iter_analyzer_records,
        run_official_uip,
    )

    if not _official_uip_enabled():
        return False
    official = discover_official_uip()
    if official is None:
        return False
    if not _check_official_uip_compatibility(result, official, source="analyzer-gate"):
        return True

    engine_root = Path(__file__).resolve().parents[2]
    base_tmp = engine_root / ".tmp" / "official_uip_analyze"
    base_tmp.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(dir=str(base_tmp), prefix="analyze_"))
    try:
        nuget_config = _write_official_nuget_config(tmpdir)
        detailed_log = tmpdir / "analyze.log"
        args = [
            "rpa", "analyze", str(project_root),
            "--output", "json",
            "--detailed-log-path", str(detailed_log),
        ]
        if nuget_config is not None:
            args.extend(["--nuget-sources-config-path", str(nuget_config)])
        governance = _os.environ.get("UIPATH_GOVERNANCE_FILE_PATH")
        if governance:
            args.extend(["--governance-file-path", governance])
            gtype = _os.environ.get("UIPATH_GOVERNANCE_FILE_TYPE")
            if gtype:
                args.extend(["--governance-file-type", gtype])
        if verbose:
            print(f"[analyzer-gate] running official uip rpa analyze via {official}",
                  file=sys.stderr)
        try:
            res = run_official_uip(args, timeout=timeout, uip_path=official)
        except Exception as exc:
            result.add(Finding(
                rule_id="UIPATH:ANALYZE_HALT",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=f"[analyzer-gate] official uip rpa analyze failed: "
                        f"{type(exc).__name__}: {exc}",
            ))
            print(f"[analyzer-gate] official uip rpa analyze failed: {exc}",
                  file=sys.stderr)
            return True

        injected = 0
        downgraded = 0
        for raw in iter_analyzer_records(res.envelope):
            if _add_analyzer_record_finding(result, raw, source="uip rpa analyze"):
                downgraded += 1
            injected += 1

        if res.returncode != 0 and injected == 0:
            from .official_uip import diagnose_official_uip_failure, official_failure_text

            diagnostics = diagnose_official_uip_failure(
                official_failure_text(res),
                "rpa analyze",
            )
            for diagnostic in diagnostics:
                _add_official_uip_diagnostic(result, diagnostic, source="analyzer-gate")
            if diagnostics:
                injected += len(diagnostics)
        if res.returncode != 0 and injected == 0:
            msg = ""
            if res.envelope is not None:
                msg = res.envelope.message or res.envelope.instructions or ""
            if not msg:
                msg = (res.stderr or res.stdout).strip().splitlines()[-1:] or [""]
                msg = msg[0]
            result.add(Finding(
                rule_id="UIPATH:ANALYZE_HALT",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=f"[analyzer-gate] official uip rpa analyze exit "
                        f"{res.returncode}: {str(msg)[:400]}",
            ))
            injected += 1
        if verbose:
            print(f"[analyzer-gate] official uip injected {injected} findings "
                  f"({downgraded} downgraded; exit {res.returncode}).",
                  file=sys.stderr)
        return True
    finally:
        _shutil.rmtree(tmpdir, ignore_errors=True)


def _inject_analyzer_findings(result, project_path: str, timeout: int = 180,
                              verbose: bool = False) -> None:
    """Run official `uip rpa analyze` and inject findings into result.

    Legacy `UiPath.Studio.CommandLine.exe analyze` fallback was removed from
    the modern validation path. If official `uip` is unavailable, review must
    fail instead of silently validating against a different toolchain.
    """
    from ._types import Finding

    project_root = Path(project_path).resolve()
    project_json = project_root / "project.json"
    if not project_json.is_file():
        if verbose:
            print(f"[analyzer-gate] no project.json at {project_root} — skipped.",
                  file=sys.stderr)
        return

    if _inject_official_analyzer_findings(result, project_root, timeout, verbose):
        return

    result.add(Finding(
        rule_id="UIPATH:CLI_NOT_FOUND",
        severity=Severity.ERROR,
        category="breaking",
        file="project.json",
        line=0,
        message=(
            "[analyzer-gate] official `uip` CLI not found or disabled. Install "
            "the current UiPath CLI, run `uip tools update`, or set "
            "UIPATH_UIP_CLI. Legacy Studio CommandLine fallback is no longer "
            "part of the modern validation path."
        ),
    ))
    print("[analyzer-gate] official uip unavailable; gate failed.",
          file=sys.stderr)


# Pattern p/ extrair file path + line de erros do `uip rpa pack`.
# A CLI emite "Path/To/File.xaml: BC30002: msg" e variantes
# "Path/To/File.xaml(123,45): BC30002: msg".
_PACK_FILE_LINE_RE = None  # lazy

# Frases-âncora que indicam erro em pack/publish (PT-BR + EN).
_PACK_ERROR_ANCHORS = (
    "O projeto tem erros de validação",
    "Project has validation errors",
    "ERROR(S)",
    "Errors:",
    "[Error]",
    "Erro:",
    "Não foi possível publicar",
    "Failed to publish",
    "Failed to package",
)


def _run_official_pack_gate(result, project_root: Path, timeout: int,
                            verbose: bool) -> bool:
    """Run official `uip rpa pack`. Returns True when official CLI handled it."""
    import tempfile
    import shutil as _shutil
    from ._types import Finding
    from .official_uip import discover_official_uip, iter_analyzer_records, run_official_uip
    from .project_view import PUBLISH_SKIP_DIRS
    from .publish_readiness import prepare_project_for_official_pack

    if not _official_uip_enabled():
        return False
    official = discover_official_uip()
    if official is None:
        return False
    if not _check_official_uip_compatibility(result, official, source="PACK-GATE"):
        return True

    engine_root = Path(__file__).resolve().parents[2]
    base_tmp = engine_root / ".tmp" / "official_uip_pack"
    base_tmp.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(dir=str(base_tmp), prefix="pack_"))
    work_project = tmpdir / "project"
    outdir = tmpdir / "out"
    outdir.mkdir(parents=True, exist_ok=True)
    project_json = project_root / "project.json"
    project_json_pre_bytes = project_json.read_bytes() if project_json.is_file() else None
    try:
        try:
            _shutil.copytree(
                project_root,
                work_project,
                ignore=_shutil.ignore_patterns(*sorted(PUBLISH_SKIP_DIRS)),
            )
            preparation = prepare_project_for_official_pack(work_project)
        except Exception as exc:
            result.add(Finding(
                rule_id="UIPATH:PACK_PREP",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=(
                    f"[PACK-GATE] official pack preparation failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            ))
            return True
        nuget_config = _write_official_nuget_config(tmpdir)
        detailed_log = tmpdir / "pack.log"
        args = [
            "rpa", "pack", str(work_project), str(outdir),
            "--skip-analyze",
            "--output", "json",
            "--detailed-log-path", str(detailed_log),
        ]
        if nuget_config is not None:
            args.extend(["--nuget-sources-config-path", str(nuget_config)])
        if verbose:
            print(
                f"[PACK-GATE] running official uip rpa pack via {official} "
                f"(descriptor_changed={preparation.descriptor_changed}, "
                f"scrubbed={len(preparation.scrubbed_xamls)})",
                file=sys.stderr,
            )
        try:
            res = run_official_uip(args, timeout=timeout, uip_path=official)
        except Exception as exc:
            result.add(Finding(
                rule_id="UIPATH:PACK_HALT",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=f"[PACK-GATE] official uip rpa pack failed: "
                        f"{type(exc).__name__}: {exc}",
            ))
            print(f"[PACK-GATE] official uip rpa pack failed: {exc}",
                  file=sys.stderr)
            return True

        injected = 0
        for raw in iter_analyzer_records(res.envelope):
            _add_analyzer_record_finding(result, raw, source="uip rpa pack")
            injected += 1

        output = "\n".join(
            part for part in (
                res.stdout,
                res.stderr,
                res.envelope.message if res.envelope is not None else "",
                res.envelope.instructions if res.envelope is not None else "",
            )
            if part
        )
        injected += _parse_pack_output_and_inject(result, output, project_root)

        if res.returncode != 0 and injected == 0:
            from .official_uip import diagnose_official_uip_failure, official_failure_text

            diagnostics = diagnose_official_uip_failure(
                official_failure_text(res),
                "rpa pack",
            )
            for diagnostic in diagnostics:
                _add_official_uip_diagnostic(result, diagnostic, source="PACK-GATE")
            if diagnostics:
                injected += len(diagnostics)
        if res.returncode != 0 and injected == 0:
            fallback_msg = ""
            for line in reversed(output.splitlines()):
                s = line.strip()
                if s:
                    fallback_msg = s
                    break
            result.add(Finding(
                rule_id="UIPATH:PACK",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=f"official uip rpa pack returned exit {res.returncode}. "
                        f"Last line: {fallback_msg[:300]}",
            ))
            injected += 1
        if verbose:
            print(f"[PACK-GATE] official uip injected {injected} findings "
                  f"(exit {res.returncode}).", file=sys.stderr)
        return True
    finally:
        if project_json_pre_bytes is not None:
            try:
                if project_json.read_bytes() != project_json_pre_bytes:
                    project_json.write_bytes(project_json_pre_bytes)
                    if verbose:
                        print("[PACK-GATE] restored project.json "
                              "(official uip rpa pack mutou source — revertido)",
                              file=sys.stderr)
            except OSError as exc:
                if verbose:
                    print(f"[PACK-GATE] cannot restore project.json: {exc}",
                          file=sys.stderr)
        _shutil.rmtree(tmpdir, ignore_errors=True)



def _run_pack_gate(result, project_path: str, timeout: int = 600,
                   verbose: bool = False) -> None:
    """Run the official publish dry-run gate via `uip rpa pack`.

    Legacy `UiPath.Studio.CommandLine.exe publish` fallback was intentionally
    removed: the current toolchain treats official `uip` as the source of
    truth for restore/analyze/build/pack. Legacy migration remains isolated in
    `migrate-windows`.
    """
    project_root = Path(project_path).resolve()
    project_json = project_root / "project.json"
    if not project_json.is_file():
        if verbose:
            print(f"[PACK-GATE] no project.json at {project_root}; skipped.",
                  file=sys.stderr)
        return

    if _run_official_pack_gate(result, project_root, timeout, verbose):
        return

    result.add(Finding(
        rule_id="UIPATH:CLI_NOT_FOUND",
        severity=Severity.ERROR,
        category="breaking",
        file="project.json",
        line=0,
        message=(
            "[PACK-GATE] official `uip` CLI not found or disabled. Install the "
            "current UiPath CLI, run `uip tools update`, or set UIPATH_UIP_CLI. "
            "Legacy Studio CommandLine fallback is no longer part of the "
            "modern validation path."
        ),
    ))
    print("[PACK-GATE] official uip unavailable; gate failed.", file=sys.stderr)


def _run_official_build_gate(result, project_path: str, timeout: int = 180,
                             verbose: bool = False) -> None:
    """Run the official compile gate via `uip rpa build`.

    The official CLI is the source of truth for project-level compile
    diagnostics; `pack --skip-analyze` remains the packaging dry-run gate.
    """
    import tempfile
    import shutil as _shutil
    from .official_uip import (
        diagnose_official_uip_failure,
        discover_official_uip,
        iter_analyzer_records,
        official_failure_text,
        run_official_uip,
    )

    project_root = Path(project_path).resolve()
    if not (project_root / "project.json").is_file():
        if verbose:
            print(f"[BUILD-GATE] no project.json at {project_root}; skipped.",
                  file=sys.stderr)
        return

    official = discover_official_uip()
    if official is None:
        result.add(Finding(
            rule_id="UIPATH:CLI_NOT_FOUND",
            severity=Severity.ERROR,
            category="breaking",
            file="project.json",
            line=0,
            message=(
                "[BUILD-GATE] official `uip` CLI not found. Install the current "
                "UiPath CLI, run `uip tools update`, or set UIPATH_UIP_CLI."
            ),
        ))
        print("[BUILD-GATE] official uip unavailable; gate failed.", file=sys.stderr)
        return
    if not _check_official_uip_compatibility(result, official, source="BUILD-GATE"):
        return

    engine_root = Path(__file__).resolve().parents[2]
    base_tmp = engine_root / ".tmp" / "official_uip_build"
    base_tmp.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(dir=str(base_tmp), prefix="build_"))
    try:
        nuget_config = _write_official_nuget_config(tmpdir)
        detailed_log = tmpdir / "build.log"
        args = [
            "rpa", "build", str(project_root),
            "--skip-analyze",
            "--output", "json",
            "--detailed-log-path", str(detailed_log),
        ]
        if nuget_config is not None:
            args.extend(["--nuget-sources-config-path", str(nuget_config)])
        import os as _os
        governance = _os.environ.get("UIPATH_GOVERNANCE_FILE_PATH")
        if governance:
            args.extend(["--governance-file-path", governance])
            gtype = _os.environ.get("UIPATH_GOVERNANCE_FILE_TYPE")
            if gtype:
                args.extend(["--governance-file-type", gtype])
        if verbose:
            print(f"[BUILD-GATE] running official uip rpa build via {official}",
                  file=sys.stderr)
        try:
            res = run_official_uip(args, timeout=timeout, uip_path=official)
        except Exception as exc:
            result.add(Finding(
                rule_id="UIPATH:BUILD_HALT",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=f"[BUILD-GATE] official uip rpa build failed: "
                        f"{type(exc).__name__}: {exc}",
            ))
            print(f"[BUILD-GATE] official uip rpa build failed: {exc}",
                  file=sys.stderr)
            return

        injected = 0
        for raw in iter_analyzer_records(res.envelope):
            _add_analyzer_record_finding(result, raw, source="uip rpa build")
            injected += 1

        try:
            detailed_log_text = detailed_log.read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            detailed_log_text = ""
        output = "\n".join(
            part for part in (
                official_failure_text(res),
                detailed_log_text,
            )
            if part
        )
        injected += _parse_pack_output_and_inject(result, output, project_root)

        if res.returncode != 0 and injected == 0:
            diagnostics = diagnose_official_uip_failure(output, "rpa build")
            for diagnostic in diagnostics:
                _add_official_uip_diagnostic(result, diagnostic, source="BUILD-GATE")
            injected += len(diagnostics)
        if res.returncode != 0 and injected == 0:
            fallback_msg = ""
            for line in reversed(output.splitlines()):
                s = line.strip()
                if s:
                    fallback_msg = s
                    break
            result.add(Finding(
                rule_id="UIPATH:BUILD",
                severity=Severity.ERROR,
                category="breaking",
                file="project.json",
                line=0,
                message=f"official uip rpa build returned exit {res.returncode}. "
                        f"Last line: {fallback_msg[:300]}",
            ))
            injected += 1
        if verbose:
            print(f"[BUILD-GATE] official uip injected {injected} findings "
                  f"(exit {res.returncode}).", file=sys.stderr)
    finally:
        _shutil.rmtree(tmpdir, ignore_errors=True)

def _parse_pack_output_and_inject(result, output: str, project_root: Path) -> int:
    """Parse `uip rpa pack` stdout/stderr, emit UIPATH:PACK findings.

    Captura:
      - Linhas `<relpath>.xaml: BC<NNNN>: <msg>` (VB compile errors).
      - Linhas `<relpath>.xaml(<line>,<col>): BC<NNNN>: <msg>` (com posição).
      - Linhas após anchors `Errors:` / `[Error]` / "O projeto tem erros".
      - Errors gerais (sem file context) viram findings em `project.json`.

    Dedup por (file, error_code, msg[:100]).

    Retorna count de findings injetados.
    """
    import re
    from ._types import Finding

    # Pattern 1: "<path>.xaml: BC<NNNN>: <msg>" or "<path>.xaml(line,col): BC<NNNN>: <msg>"
    file_err_re = re.compile(
        r"^(?P<file>[^\s:][^:]*\.xaml)"
        r"(?:\((?P<line>\d+),(?P<col>\d+)\))?"
        r":\s*(?P<code>BC\d{4,5}|[A-Z]{2,5}\d{2,5})"
        r":\s*(?P<msg>.+?)\s*$",
        re.MULTILINE,
    )

    injected = 0
    seen: set[tuple[str, str, str]] = set()

    for m in file_err_re.finditer(output):
        rel_file = m.group("file").strip()
        line = int(m.group("line") or 0)
        code = m.group("code")
        msg = m.group("msg").strip()
        key = (rel_file, code, msg[:100])
        if key in seen:
            continue
        seen.add(key)
        # Resolve to absolute path if possible.
        abs_file = project_root / rel_file
        file_for_finding = str(abs_file) if abs_file.is_file() else rel_file
        result.add(Finding(
            rule_id="UIPATH:PACK",
            severity=Severity.ERROR,
            category="breaking",
            file=file_for_finding,
            line=line,
            message=f"{code}: {msg}",
        ))
        injected += 1

    # Linha-âncora final "O projeto tem erros de validação..." vira finding
    # geral se nada mais foi capturado — confirma que houve falha overall.
    has_anchor = any(a in output for a in _PACK_ERROR_ANCHORS)
    if has_anchor and injected == 0:
        # Look for the actual anchor msg.
        for anchor in _PACK_ERROR_ANCHORS:
            if anchor in output:
                # Capture line containing the anchor.
                for line in output.splitlines():
                    if anchor in line:
                        msg = line.strip()
                        key = ("project.json", "PACK", msg[:100])
                        if key in seen:
                            continue
                        seen.add(key)
                        result.add(Finding(
                            rule_id="UIPATH:PACK",
                            severity=Severity.ERROR,
                            category="breaking",
                            file="project.json",
                            line=0,
                            message=msg[:400],
                        ))
                        injected += 1
                        break
                break

    return injected


_TELEMETRY_DIR = Path(__file__).resolve().parents[2] / ".tmp" / "telemetry"


def _write_telemetry(result, project_path: str) -> None:
    """Append findings to .tmp/telemetry/<YYYY-MM-DD>.jsonl, one record per rule.

    Schema: {ts, project, rule_id, severity, count, suppressed_count}
    Aggregated counts (not raw findings) — keeps file size bounded.
    """
    from collections import Counter
    from datetime import datetime, timezone

    _TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    out = _TELEMETRY_DIR / f"{today}.jsonl"

    findings = result.findings
    by_rule = Counter()
    suppressed = Counter()
    for f in findings:
        if getattr(f, "suppressed", False):
            suppressed[(f.rule_id, Severity(f.severity).name)] += 1
        else:
            by_rule[(f.rule_id, Severity(f.severity).name)] += 1

    ts = datetime.now(timezone.utc).isoformat()
    project_short = Path(project_path).resolve().name
    rows = []
    keys = set(by_rule) | set(suppressed)
    for rid, sev in sorted(keys):
        rows.append({
            "ts": ts,
            "project": project_short,
            "rule_id": rid,
            "severity": sev,
            "count": by_rule.get((rid, sev), 0),
            "suppressed_count": suppressed.get((rid, sev), 0),
        })

    with out.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _parse_window(window: str):
    """Parse '30d' / '24h' / 'all' → datetime cutoff (UTC) or None for 'all'."""
    from datetime import datetime, timezone, timedelta
    w = window.strip().lower()
    if w == "all":
        return None
    if w.endswith("d"):
        n = int(w[:-1])
        return datetime.now(timezone.utc) - timedelta(days=n)
    if w.endswith("h"):
        n = int(w[:-1])
        return datetime.now(timezone.utc) - timedelta(hours=n)
    raise ValueError(f"invalid window: {window}")


def _cmd_stats(args) -> int:
    """Aggregate telemetry JSONL files, print markdown report."""
    from collections import defaultdict
    from datetime import datetime

    if not _TELEMETRY_DIR.exists():
        print(f"[stats] no telemetry data in {_TELEMETRY_DIR}")
        print("[stats] run `cli review --telemetry` to populate")
        return EXIT_OK

    cutoff = _parse_window(args.since)
    files = sorted(_TELEMETRY_DIR.glob("*.jsonl"))
    if not files:
        print(f"[stats] {_TELEMETRY_DIR} is empty")
        return EXIT_OK

    rules_by_id = {}
    try:
        rules = _load_rules_or_die(args.rules_file)
        rules_by_id = {r.id: r for r in rules}
    except Exception:
        pass

    counts = defaultdict(lambda: {"count": 0, "suppressed": 0, "projects": set(), "severities": set()})
    runs_per_project = defaultdict(int)
    parsed_records = 0
    for fp in files:
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if cutoff is not None:
                try:
                    ts = datetime.fromisoformat(row["ts"])
                    if ts < cutoff:
                        continue
                except Exception:
                    continue
            parsed_records += 1
            rid = row.get("rule_id", "")
            entry = counts[rid]
            entry["count"] += row.get("count", 0)
            entry["suppressed"] += row.get("suppressed_count", 0)
            entry["projects"].add(row.get("project", "?"))
            entry["severities"].add(row.get("severity", "?"))
            runs_per_project[row.get("project", "?")] += 1

    if not counts:
        print(f"[stats] no records in window={args.since}")
        return EXIT_OK

    sorted_counts = sorted(counts.items(), key=lambda kv: -kv[1]["count"])
    total_findings = sum(v["count"] for v in counts.values())
    rule_ids_total = len(rules_by_id) or "?"

    print(f"# Telemetry stats — window={args.since}")
    print("")
    print(f"- Records aggregated: {parsed_records}")
    print(f"- Total findings: {total_findings}")
    print(f"- Distinct rules triggered: {len(counts)}/{rule_ids_total}")
    print(f"- Distinct projects: {len(runs_per_project)}")
    print("")
    print(f"## Top {args.top} rules by findings")
    print("")
    print("| Rank | Rule | Sev | Title | Count | Suppressed | Projects |")
    print("|---|---|---|---|---|---|---|")
    for i, (rid, info) in enumerate(sorted_counts[:args.top], 1):
        title = rules_by_id.get(rid).title if rid in rules_by_id else "?"
        sev = "/".join(sorted(info["severities"]))
        title_short = title[:50] + ("..." if len(title) > 50 else "")
        print(f"| {i} | {rid} | {sev} | {title_short} | {info['count']} | {info['suppressed']} | {len(info['projects'])} |")

    # Rules never triggered (candidates for deprecation review)
    untriggered = sorted(set(rules_by_id) - set(counts))
    if untriggered and rules_by_id:
        print("")
        print(f"## Rules never triggered ({len(untriggered)} of {len(rules_by_id)})")
        print("")
        print("Candidates for review (may indicate dead rules or rare conditions):")
        for rid in untriggered[:30]:
            print(f"- {rid}: {rules_by_id[rid].title[:80]}")
        if len(untriggered) > 30:
            print(f"- ... +{len(untriggered)-30} more")

    return EXIT_OK


def _cmd_validate(args) -> int:
    try:
        rules = _load_rules_or_die(args.rules_file)
        print(f"OK — {len(rules)} regras válidas em {args.rules_file}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        print(f"[INTERNAL] {e}", file=sys.stderr)
        return EXIT_INTERNAL


def _cmd_list(args) -> int:
    rules = _load_rules_or_die(args.rules_file)
    if args.by_class:
        from collections import defaultdict
        groups = defaultdict(list)
        for r in rules:
            groups[get_apply_class(r)].append(r)
        for cls in ("deterministic", "contextual", "structural"):
            rs = groups.get(cls, [])
            print(f"\n## apply_class={cls} ({len(rs)})")
            for r in sorted(rs, key=lambda x: x.id):
                print(f"  {r.id} [{Severity(r.severity).name}] [{r.category}] {r.title}")
    elif args.by_category:
        from collections import defaultdict
        groups = defaultdict(list)
        for r in rules:
            groups[r.category].append(r)
        for cat, rs in sorted(groups.items()):
            print(f"\n## {cat} ({len(rs)})")
            for r in sorted(rs, key=lambda x: x.id):
                print(f"  {r.id} [{Severity(r.severity).name}] [{r.category}] {r.title} (apply_class={get_apply_class(r)})")
    else:
        for r in sorted(rules, key=lambda x: x.id):
            print(f"{r.id} [{Severity(r.severity).name}] [{r.category}] [{get_apply_class(r)}] {r.title}")
    return EXIT_OK


def _cmd_docs(args) -> int:
    rules = _load_rules_or_die(args.rules_file)
    from collections import defaultdict

    def _fl(text):
        if not text:
            return None
        for ln in text.splitlines():
            s = ln.strip()
            if s:
                return s
        return None

    if args.llm_only:
        rules = [r for r in rules if get_apply_class(r) != "deterministic"]

    by_pref: dict[str, list] = defaultdict(list)
    for r in rules:
        by_pref[r.id.split("-", 1)[0]].append(r)

    out_lines: list[str] = []
    title = "LLM-dependent rules" if args.llm_only else "Rules catalog"
    out_lines.append(f"# {title}")
    out_lines.append("")
    out_lines.append(f"Generated from `rules.yaml` ({len(rules)} rules). Não editar à mão.")
    out_lines.append("")
    for pref in sorted(by_pref):
        rs = sorted(by_pref[pref], key=lambda r: r.id)
        out_lines.append(f"## {pref} ({len(rs)})")
        out_lines.append("")
        for r in rs:
            sev = Severity(r.severity).name
            cls = get_apply_class(r)
            why = _fl(r.description) or ""
            prose = _fl((r.fix or {}).get("prose")) if r.fix else None
            out_lines.append(f"### `{r.id}` [{sev}] {r.title}")
            out_lines.append(f"- **class:** {cls}  |  **target:** {r.target}  |  **category:** {r.category}")
            if why:
                out_lines.append(f"- **why:** {why}")
            if prose:
                out_lines.append(f"- **fix:** {prose}")
            out_lines.append("")

    rendered = "\n".join(out_lines)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
        print(f"Wrote {args.out} ({len(rules)} rules)")
    else:
        print(rendered)
    return EXIT_OK


def _cmd_fix(args) -> int:
    rules = _load_rules_or_die(args.rules_file)
    runner = Runner(rules=rules, detectors=DETECTOR_REGISTRY, fixers=FIXER_REGISTRY)

    filter_rules = {x.strip() for x in args.rules.split(",") if x.strip()}

    project_root = Path(args.path).resolve()
    if (project_root / "project.json").exists():
        pass
    else:
        from .context import ProjectContext
        pc = ProjectContext.find_root(project_root)
        if pc is not None:
            project_root = pc.root

    applied = would_fix = no_op = no_fix = blocked = 0
    regressions = cascade_regressions = vb_regressions = 0
    dry_run = not args.apply
    label = "would-fix" if dry_run else "fix"

    if not dry_run and (not filter_rules or "J-9" in filter_rules):
        try:
            from .publish_readiness import project_uiproj_needs_sync, sync_project_uiproj
            needs_sync, reason = project_uiproj_needs_sync(project_root)
            if needs_sync:
                descriptor, changed = sync_project_uiproj(project_root)
                if changed:
                    print(
                        "# pre-fix official-pack descriptor synced: "
                        f"{descriptor} ({reason})"
                    )
        except Exception as e:
            if getattr(args, "verbose", False):
                print(
                    "# pre-fix official-pack descriptor sync skipped: "
                    f"{type(e).__name__}: {e}",
                    file=sys.stderr,
                )

    # Apply-class filter: default = só `deterministic`. Flag --include-class=X
    # estende. --include-class=all opt-in todas (use com cuidado).
    raw_classes = (getattr(args, "include_class", None) or "deterministic").split(",")
    raw_classes = [c.strip() for c in raw_classes if c.strip()]
    if "all" in raw_classes:
        included_classes = frozenset(VALID_CLASSES)
    else:
        unknown = [c for c in raw_classes if c not in VALID_CLASSES]
        if unknown:
            print(f"ERROR: --include-class valor desconhecido: {unknown}. Válidos: {VALID_CLASSES} ou 'all'.")
            return EXIT_INTERNAL
        included_classes = frozenset(raw_classes)
    if not dry_run:
        print(f"# include_classes={sorted(included_classes)}")

    # Analyzer gate baseline. Roda uma única vez ANTES de qualquer fix iter e
    # captura set de issues pré-existentes. Diff vs post-loop dá erros
    # introduzidos. Default-on em fix --apply; use --no-analyzer-gate apenas em
    # debug controlado.
    analyzer_baseline = None
    analyzer_gate_enabled = (not getattr(args, "no_analyzer_gate", False)) and not dry_run
    # F28: pre-loop bytes snapshot p/ rollback se Layer 2 reportar new errors.
    pre_loop_bytes: dict = {}
    if analyzer_gate_enabled:
        from .analyzer import run_analyzer, load_cached_baseline, save_cached_baseline
        from .official_uip import discover_official_uip
        official_uip_path = discover_official_uip() if _official_uip_enabled() else None
        if official_uip_path is None:
            print("# analyzer-gate: official uip não encontrado. "
                  "Defina UIPATH_UIP_CLI. Skipping baseline.")
        else:
            # Cache lookup (F27): re-runs consecutivos reaproveitam baseline
            # oficial quando a assinatura do projeto/engine/CLI não mudou.
            analyzer_baseline = load_cached_baseline(project_root)
            if analyzer_baseline is not None:
                print(f"# analyzer-gate: baseline cache HIT "
                      f"({len(analyzer_baseline)} issues). Skipping baseline run.")
            else:
                print("# analyzer-gate: baseline run via official uip rpa analyze...")
                analyzer_baseline = run_analyzer(project_root)
                if analyzer_baseline is None:
                    print("# analyzer-gate: baseline failed/timeout. Skipping gate.")
                else:
                    save_cached_baseline(project_root, analyzer_baseline)
            if analyzer_baseline is not None:
                base_err = sum(1 for i in analyzer_baseline if i.severity == "Error")
                base_warn = sum(1 for i in analyzer_baseline if i.severity == "Warning")
                print(f"# analyzer-gate: baseline = {len(analyzer_baseline)} issues "
                      f"({base_err} errors, {base_warn} warnings). Pré-existentes "
                      "serão ignoradas no diff final.")
                # F28/F40: snapshot pre-loop analyzer-relevant files p/
                # rollback potencial. Inclui XAML + metadata de projeto porque
                # package/project.json changes podem introduzir load errors.
                for x in _iter_analyzer_snapshot_paths(project_root):
                    try:
                        pre_loop_bytes[x.resolve()] = x.read_bytes()
                    except OSError:
                        pass

    rules_by_id = {r.id: r for r in rules}

    # Dedup logger pra fix loop. Mesmo finding (kind, rule_id, file) repete em
    # múltiplas iterações do fixpoint — gera log spam (milhares de linhas
    # idênticas inviabiliza monitor/grep). Primeira ocorrência printa
    # inline; subsequentes contabilizam pra summary final.
    from collections import Counter as _Counter
    class _FixLogger:
        def __init__(self) -> None:
            self._seen: set[tuple[str, str, str]] = set()
            self._counts: _Counter = _Counter()
        def log(self, kind: str, rule_id: str, file: str, msg: str) -> None:
            key = (kind, rule_id, file)
            self._counts[key] += 1
            if key not in self._seen:
                self._seen.add(key)
                print(msg)
        def emit_summary(self) -> None:
            dupes = [(k, c) for k, c in self._counts.items() if c > 1]
            if not dupes:
                return
            dupes.sort(key=lambda x: -x[1])
            print(f"\n# Eventos repetidos no fix loop (top 30 de {len(dupes)}):")
            for (kind, rule_id, file), count in dupes[:30]:
                base = file.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
                print(f"  [{kind}] [{rule_id}] {base}: ×{count}")
            if len(dupes) > 30:
                print(f"  ... +{len(dupes)-30} more repeated events")
    _fix_log = _FixLogger()

    # F35: per-file rollback + retomar loop. Analyzer-gate regression em file F
    # vira F frozen (skip nos retries seguintes do fix loop), re-roda fixpoint
    # + analyzer-gate até gate limpo OU retries exauridos. Estado residual
    # propaga pra PHASE 2 — não aborta pipeline em EXIT_INTERNAL.
    ANALYZER_GATE_MAX_RETRIES = 3
    frozen_files: set = set()
    analyzer_retry = 0

    # Idempotência: alguns detectores (N-6/N-7) emitem 1 finding por (tag, attr).
    # Pattern do segundo finding fica stale após primeiro fix mutar tag.
    # Loop detect→apply até `applied=0` numa iteração (fixpoint). Dry-run roda
    # 1 iteração só (não escreve). Max 20 iters como safety bound.
    # F35: outer loop = analyzer-gate retry. Inner = fixpoint deterministic.
    MAX_ITERATIONS = 20
    iteration = 0

    while True:  # outer: analyzer-gate retry
        # --- Inner: fixpoint ---
        while True:
            iteration += 1
            if iteration > MAX_ITERATIONS:
                print(f"\nWARN: fixpoint não convergiu em {MAX_ITERATIONS} iterações. Abortando loop.")
                break

            result = runner.run(args.path)

            _apply_sicoob_lib_overrides(result, verbose=getattr(args, "verbose", False))

            seen_keys: set[tuple[str, str]] = set()
            iter_applied = 0
            iter_would_fix = 0
            iter_blocked = 0
            iter_no_fix = 0
            iter_no_op = 0
            iter_regressions = 0
            iter_vb_regressions = 0
            iter_cascade_regressions = 0
            for f in result.findings:
                if f.suppressed:
                    continue
                if filter_rules and f.rule_id not in filter_rules:
                    continue
                # F35: skip files frozen por analyzer-gate em retry anterior.
                # Mantemos arquivo em estado pré-loop pra preservar absence de
                # regression (ex.: ST-SEC-008 SecureString scope cascade).
                try:
                    if Path(f.file).resolve() in frozen_files:
                        continue
                except (OSError, ValueError):
                    pass
                if not f.fix_mechanical:
                    iter_no_fix += 1
                    continue
                rule = rules_by_id.get(f.rule_id)
                if rule:
                    rule_class = get_apply_class(rule)
                    if rule_class not in included_classes:
                        iter_blocked += 1
                        if not dry_run:
                            _fix_log.log(
                                f"BLOCKED apply_class={rule_class}", f.rule_id, f.file,
                                f"  [BLOCKED apply_class={rule_class}] [{f.rule_id}] {f.file}: revisar manualmente (ver fix.prose).",
                            )
                        continue
                mech_type = f.fix_mechanical.get("type")
                fixer = FIXER_REGISTRY.get(mech_type)
                if fixer is None:
                    _fix_log.log(
                        "SKIP", f.rule_id, f.file,
                        f"  [SKIP] [{f.rule_id}] {f.file}: fixer '{mech_type}' não registrado",
                    )
                    continue

                # Per-spec deduplication: same file + rule + fix spec = same fix
                # applied multiple times = idempotent. Different specs (per-finding
                # mechanical from heuristics) must each run.
                if mech_type in {"regex_replace", "delete_element", "rename_attribute"}:
                    spec_key = repr(sorted(f.fix_mechanical.items()))
                    key = (f.file, f.rule_id, spec_key)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                import inspect
                sig = inspect.signature(fixer)
                fixer_kwargs: dict = {}
                if "project_root" in sig.parameters:
                    fixer_kwargs["project_root"] = project_root

                ar = apply_with_gate(
                    fixer,
                    Path(f.file),
                    f.fix_mechanical,
                    dry_run=dry_run,
                    project_root=project_root,
                    fixer_kwargs=fixer_kwargs,
                )

                if ar.status == "error":
                    _fix_log.log(
                        "SKIP-ERR", f.rule_id, f.file,
                        f"  [SKIP] [{f.rule_id}] {f.file}: {ar.error}",
                    )
                    continue
                if ar.status == "regression":
                    iter_regressions += 1
                    _fix_log.log(
                        "REGRESSION", f.rule_id, f.file,
                        f"  [REGRESSION rolled back] [{f.rule_id}] {ar.error}",
                    )
                    continue
                if ar.status == "regression-vb":
                    iter_vb_regressions += 1
                    _fix_log.log(
                        "REGRESSION-VB", f.rule_id, f.file,
                        f"  [REGRESSION-VB rolled back] [{f.rule_id}] {ar.error}",
                    )
                    continue
                if ar.status == "regression-cascade":
                    iter_cascade_regressions += 1
                    _fix_log.log(
                        "REGRESSION-CASCADE", f.rule_id, f.file,
                        f"  [REGRESSION cascade rolled back] [{f.rule_id}] {f.file}: {ar.error}",
                    )
                    continue
                if ar.status == "regression-cascade-vb":
                    iter_cascade_regressions += 1
                    _fix_log.log(
                        "REGRESSION-CASCADE-VB", f.rule_id, f.file,
                        f"  [REGRESSION cascade-VB rolled back] [{f.rule_id}] {f.file}: {ar.error}",
                    )
                    continue
                if ar.changed:
                    if dry_run:
                        iter_would_fix += 1
                    else:
                        iter_applied += 1
                    _fix_log.log(
                        label, f.rule_id, f.file,
                        f"  [{label}] [{f.rule_id}] {f.file}",
                    )
                else:
                    iter_no_op += 1

            applied += iter_applied
            would_fix += iter_would_fix
            no_op += iter_no_op
            no_fix = iter_no_fix     # último iter (não acumula)
            blocked = iter_blocked   # último iter
            regressions += iter_regressions
            vb_regressions += iter_vb_regressions
            cascade_regressions += iter_cascade_regressions

            # Convergência:
            # - dry_run: 1 iteração (não escreve, repetir mostra mesmas findings).
            # - apply: parar quando applied=0 nessa iteração (fixpoint).
            if dry_run:
                break
            if iter_applied == 0:
                break
            print(f"  [iter {iteration}] applied={iter_applied}, re-detecting...")

        # --- Analyzer-gate (apply mode + baseline disponível) ---
        if dry_run or analyzer_baseline is None or applied == 0:
            break  # nada pra gate, sai do outer

        from .fixers import (
            sanitize_invoke_arguments_dictionary_placeholders,
            sanitize_invoke_arguments_variable_conflicts,
        )
        sanitized_files, sanitized_attrs = sanitize_invoke_arguments_variable_conflicts(
            project_root
        )
        if sanitized_attrs:
            print(
                "# pre-analyzer sanitize: W-34 stripped "
                f"{sanitized_attrs} ArgumentsVariable placeholders "
                f"em {sanitized_files} XAMLs"
            )
            applied += sanitized_files
        dict_files, dict_placeholders = (
            sanitize_invoke_arguments_dictionary_placeholders(project_root)
        )
        if dict_placeholders:
            print(
                "# pre-analyzer sanitize: W-34 stripped "
                f"{dict_placeholders} empty Arguments dictionaries "
                f"em {dict_files} XAMLs"
            )
            applied += dict_files

        from .analyzer import run_analyzer, diff_new_issues, format_issue
        retry_tag = (
            f" (retry {analyzer_retry}/{ANALYZER_GATE_MAX_RETRIES})"
            if analyzer_retry > 0 else ""
        )
        runner_label = "official uip rpa analyze"
        print(f"\n# analyzer-gate: post-fix re-run via {runner_label}{retry_tag}...")
        analyzer_post = run_analyzer(project_root)
        if analyzer_post is None:
            print("# analyzer-gate: post run failed/timeout. Diff incomplete.")
            break

        new_issues = diff_new_issues(analyzer_baseline, analyzer_post)
        resolved = analyzer_baseline - analyzer_post
        # F38 (2026-05-21): analyzer-gate ignora errors policy-aceitos Sicoob
        # (ST-SEC-008 SecureString chain, etc.). Antes filtro só usava RAW
        # severity Studio analyzer — _ANALYZER_SICOOB_POLICY downgrade só
        # aplicava em review formatting (line 696-731). Resultado: gate
        # rolava back fixes ESCANDO-se em policy-aceitos como se fossem
        # regressões reais. Aplica policy filter aqui pra consistência.
        new_errs = [
            i for i in new_issues
            if i.severity == "Error"
            and i.error_code not in _ANALYZER_SICOOB_POLICY
        ]
        # Surface policy-suppressed "errors" as INFO-level diagnostics (não
        # bloqueia gate). Auditoria visível.
        policy_suppressed_errs = [
            i for i in new_issues
            if i.severity == "Error"
            and i.error_code in _ANALYZER_SICOOB_POLICY
        ]
        new_warns = [i for i in new_issues if i.severity == "Warning"]
        resolved_count = len(resolved)
        print(
            f"# analyzer-gate: {len(new_issues)} new issues "
            f"({len(new_errs)} errors, {len(new_warns)} warnings) | "
            f"{resolved_count} resolved"
        )

        if policy_suppressed_errs:
            print(
                f"\n[ANALYZER POLICY-SUPPRESSED] {len(policy_suppressed_errs)} "
                f"errors aceitos por _ANALYZER_SICOOB_POLICY (não causam rollback):"
            )
            for i in policy_suppressed_errs[:10]:
                policy_note = _ANALYZER_SICOOB_POLICY.get(i.error_code, "")
                print(f"  ~ {format_issue(i)[:160]} | {policy_note[:80]}")
            if len(policy_suppressed_errs) > 10:
                print(f"  ... +{len(policy_suppressed_errs)-10} more")
        if not new_errs:
            # Gate limpo. Warns são informativas.
            if new_warns:
                print("\n[ANALYZER WARN] Warnings introduzidas (sem block):")
                for i in new_warns[:10]:
                    print(f"  ~ {format_issue(i)[:200]}")
                if len(new_warns) > 10:
                    print(f"  ... +{len(new_warns)-10} more")
            break

        # New errors → rollback per-file + freeze + retry.
        print("\n[ANALYZER REGRESSION] Errors INTRODUZIDOS pelos fixes:")
        for i in new_errs[:30]:
            print(f"  ! {format_issue(i)[:200]}")
        if len(new_errs) > 30:
            print(f"  ... +{len(new_errs)-30} more")

        invoke_args_error = any(
            "InvokeWorkflowFile" in i.description and "Arguments" in i.description
            for i in new_errs
        )
        if invoke_args_error:
            from .fixers import (
                sanitize_invoke_arguments_dictionary_placeholders,
                sanitize_invoke_arguments_variable_conflicts,
            )
            sanitized_files, sanitized_attrs = sanitize_invoke_arguments_variable_conflicts(
                project_root
            )
            dict_files, dict_placeholders = (
                sanitize_invoke_arguments_dictionary_placeholders(project_root)
            )
            if sanitized_attrs or dict_placeholders:
                print(
                    "\n[ANALYZER RECOVERY] W-34 stripped "
                    f"{sanitized_attrs} ArgumentsVariable placeholders "
                    f"em {sanitized_files} XAMLs; "
                    f"{dict_placeholders} empty Arguments dictionaries "
                    f"em {dict_files} XAMLs; revalidando antes do rollback..."
                )
                analyzer_recovered = run_analyzer(project_root, analyzer_cli_path)
                if analyzer_recovered is None:
                    print("# analyzer-gate: recovery run failed/timeout. Mantendo rollback path.")
                else:
                    recovered_new = diff_new_issues(
                        analyzer_baseline, analyzer_recovered
                    )
                    recovered_errs = [
                        i for i in recovered_new
                        if i.severity == "Error"
                        and i.error_code not in _ANALYZER_SICOOB_POLICY
                    ]
                    recovered_warns = [
                        i for i in recovered_new if i.severity == "Warning"
                    ]
                    print(
                        "# analyzer-gate: recovery = "
                        f"{len(recovered_new)} new issues "
                        f"({len(recovered_errs)} errors, "
                        f"{len(recovered_warns)} warnings)"
                    )
                    if not recovered_errs:
                        if recovered_warns:
                            print(
                                "\n[ANALYZER WARN] Warnings introduzidas "
                                "após recovery (sem block):"
                            )
                            for i in recovered_warns[:10]:
                                print(f"  ~ {format_issue(i)[:200]}")
                            if len(recovered_warns) > 10:
                                print(f"  ... +{len(recovered_warns)-10} more")
                        break

            candidates = _invoke_workflow_arguments_conflict_snippets(
                project_root, pre_loop_bytes
            )
            if candidates:
                print("\n[ANALYZER DIAG] InvokeWorkflowFile Arguments candidates:")
                for path, line, snippet in candidates[:30]:
                    print(f"  ? {path.name}:{line} — {snippet[:220]}")
                if len(candidates) > 30:
                    print(f"  ... +{len(candidates)-30} more")
            else:
                print("\n[ANALYZER DIAG] nenhum candidato InvokeWorkflowFile Arguments encontrado.")

        err_files = {i.file for i in new_errs if i.file}
        rolled_back_paths: list = []
        rollback_failed: list = []
        # GRANULAR rollback: pra cada XAML no snapshot cujo basename apareça em
        # err_files, restaura bytes pré-loop.
        for path, pre_bytes in pre_loop_bytes.items():
            if path.name not in err_files:
                continue
            if path.resolve() in frozen_files:
                continue  # já rollback'd em retry anterior
            if _is_project_metadata_snapshot_path(path, project_root):
                print(
                    "# analyzer-gate: preservando metadata em rollback "
                    f"granular: {path.name}"
                )
                continue
            try:
                current_bytes = path.read_bytes() if path.exists() else b""
                if path.suffix.lower() == ".xaml":
                    rollback_bytes = _rollback_bytes_preserving_refs_namespaces(
                        pre_bytes,
                        current_bytes,
                    )
                    if rollback_bytes != pre_bytes:
                        print(
                            "# analyzer-gate: rollback preservou refs/imports "
                            f"em {path.name}"
                        )
                else:
                    rollback_bytes = pre_bytes
                path.write_bytes(rollback_bytes)
                rolled_back_paths.append(path)
            except OSError as e:
                rollback_failed.append((path.name, str(e)))

        # Studio sometimes reports XAML parser regressions as
        # FilePath=System.Activities.Xaml with a path-redacted Description.
        # When the signature is the known property-element ATTRIBUTE error,
        # locate changed XAMLs that still contain property-elements with attrs
        # and rollback only those files instead of falling back to all files.
        attr_parse_error = any(
            "ATTRIBUTE" in i.description
            or "NonemptyPropertyElement" in i.description
            for i in new_errs
        )
        if not rolled_back_paths and attr_parse_error:
            for path, pre_bytes in pre_loop_bytes.items():
                if path.suffix.lower() != ".xaml":
                    continue
                if path.resolve() in frozen_files:
                    continue
                try:
                    if path.exists() and path.read_bytes() != pre_bytes:
                        snippet = _property_element_attribute_snippet(path)
                        if snippet:
                            print(
                                "# analyzer-gate: ATTRIBUTE rollback candidate "
                                f"{path.name}: {snippet}"
                            )
                            rollback_bytes = (
                                _rollback_bytes_preserving_refs_namespaces(
                                    pre_bytes,
                                    path.read_bytes(),
                                )
                            )
                            if rollback_bytes != pre_bytes:
                                print(
                                    "# analyzer-gate: rollback preservou "
                                    f"refs/imports em {path.name}"
                                )
                            path.write_bytes(rollback_bytes)
                            rolled_back_paths.append(path)
                except OSError as e:
                    rollback_failed.append((path.name, str(e)))

        metadata_or_cli_infra_only = (
            bool(new_errs)
            and all(_is_analyzer_metadata_or_cli_infra_issue(i) for i in new_errs)
        )

        # FULL-SNAPSHOT fallback: granular rollback falhou (err_files vazio
        # ou todos basenames ausentes do snapshot — típico de analyzer-error
        # project-level sem FilePath, ex.: "Não foi possível realizar análise
        # do projeto"). Engine NUNCA pode deixar XAML/config pior que estado
        # pré-fix loop. Project metadata is intentionally excluded here:
        # dependency pins and manifests are governed by restore/pack gates and
        # rolling them back would hide the real remaining dependency diagnosis.
        # Regression test: pilot contestacao-de-compras (5/27) — granular
        # rollback nunca disparou pq err_files = {""} (FilePath vazio).
        if not rolled_back_paths and metadata_or_cli_infra_only:
            print(
                "# analyzer-gate: erro metadata/infra-only da CLI oficial; "
                "sem FULL-SNAPSHOT rollback de XAML. Diagnóstico segue para "
                "PHASE 2."
            )
            break

        if not rolled_back_paths and new_errs:
            print(
                "# analyzer-gate: granular rollback inexequível "
                "(err_files sem match no snapshot). "
                "Iniciando FULL-SNAPSHOT rollback de XAMLs divergentes..."
            )
            for path, pre_bytes in pre_loop_bytes.items():
                if path.resolve() in frozen_files:
                    continue
                if _is_project_metadata_snapshot_path(path, project_root):
                    continue
                try:
                    if not path.exists():
                        path.write_bytes(pre_bytes)
                        rolled_back_paths.append(path)
                        continue
                    current_bytes = path.read_bytes()
                    if current_bytes == pre_bytes:
                        continue
                    if (
                        path.suffix.lower() == ".xaml"
                        and _is_reference_namespace_only_delta(
                            pre_bytes, current_bytes
                        )
                    ):
                        print(
                            "# analyzer-gate: preservando refs/imports "
                            f"em rollback amplo: {path.name}"
                        )
                        continue
                    rollback_bytes = (
                        _rollback_bytes_preserving_refs_namespaces(
                            pre_bytes,
                            current_bytes,
                        )
                        if path.suffix.lower() == ".xaml"
                        else pre_bytes
                    )
                    if rollback_bytes != pre_bytes:
                        print(
                            "# analyzer-gate: rollback preservou refs/imports "
                            f"em {path.name}"
                        )
                    path.write_bytes(rollback_bytes)
                    rolled_back_paths.append(path)
                except OSError as e:
                    rollback_failed.append((path.name, str(e)))
            for path in _iter_analyzer_snapshot_paths(project_root):
                try:
                    resolved = path.resolve()
                except OSError:
                    continue
                if resolved in pre_loop_bytes or resolved in frozen_files:
                    continue
                if _is_project_metadata_snapshot_path(path, project_root):
                    continue
                try:
                    path.unlink()
                    rolled_back_paths.append(path)
                except OSError as e:
                    rollback_failed.append((path.name, str(e)))

        if rolled_back_paths:
            print(
                f"\n[ANALYZER ROLLBACK] {len(rolled_back_paths)} files "
                f"revertidos pra estado pré-loop (freeze ativo):"
            )
            for p in rolled_back_paths:
                print(f"  ~ {p.name}")
        if rollback_failed:
            print(f"[ANALYZER ROLLBACK FAILED] {len(rollback_failed)} files:")
            for name, err in rollback_failed[:5]:
                print(f"  ! {name}: {err}")

        if not rolled_back_paths:
            # Snapshot vazio (analyzer baseline não rodou OU projeto sem XAML
            # no momento do snapshot). Não há estado pré-loop pra restaurar.
            print(
                "# analyzer-gate: rollback impossível (snapshot vazio). "
                "Estado residual: ver PHASE 2."
            )
            break

        frozen_files.update(p.resolve() for p in rolled_back_paths)
        analyzer_retry += 1
        if analyzer_retry > ANALYZER_GATE_MAX_RETRIES:
            print(
                f"\n[ANALYZER GATE] retries exauridos "
                f"({ANALYZER_GATE_MAX_RETRIES}). {len(frozen_files)} file(s) "
                f"frozen — findings remanescentes vão pra PHASE 2."
            )
            break

        print(
            f"# analyzer-gate: retomando fix loop "
            f"(frozen={len(frozen_files)}, retry "
            f"{analyzer_retry}/{ANALYZER_GATE_MAX_RETRIES})"
        )

    _fix_log.emit_summary()
    print(
        f"\nSUMMARY ({iteration} iter, classes={sorted(included_classes)}): "
        f"applied={applied} would-fix={would_fix} no-op={no_op} "
        f"no-mechanical-fix={no_fix} blocked-other-class={blocked} "
        f"regressions-rolled-back={regressions} regressions-vb={vb_regressions} "
        f"regressions-cascade={cascade_regressions}"
    )
    if frozen_files:
        print(
            f"# analyzer-gate frozen files ({len(frozen_files)}): "
            f"findings restantes nesses arquivos serão reportados em PHASE 2."
        )
        for p in sorted(frozen_files, key=lambda x: x.name):
            print(f"  ~ {p.name}")
    if dry_run and would_fix > 0:
        print("Re-run with --apply to write changes.")

    return EXIT_OK


def _cmd_phase_out(args) -> int:
    if args.scope != "windows-only":
        return EXIT_INTERNAL

    UNIVERSALIZE = {"W-3", "W-10", "W-12", "W-16", "W-17"}

    rules_file = Path(args.rules_file)
    content = rules_file.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    import re
    id_pattern = re.compile(r'^\s*-\s+id:\s+([A-Z][A-Z0-9]*-\w+)\s*$')
    target_pattern = re.compile(r'^(\s+)target:\s+windows\s*$')

    changes: list[tuple[int, str, str]] = []
    current_rule = None
    for i, line in enumerate(lines):
        m = id_pattern.match(line)
        if m:
            current_rule = m.group(1)
            continue
        if current_rule in UNIVERSALIZE:
            tm = target_pattern.match(line)
            if tm:
                indent = tm.group(1)
                new_line = f"{indent}target: all\n"
                changes.append((i, line, new_line))
                current_rule = None  # done with this rule

    if not changes:
        print("Nada para universalizar — todas regras alvo já são target: all ou ausentes.")
        return EXIT_OK

    print(f"Phase-out windows-only — {len(changes)} regra(s) universalizam:")
    for idx, old, new in changes:
        print(f"  line {idx+1}: {old.rstrip()} → {new.rstrip()}")

    if not args.apply:
        print("\nDry-run. Re-run with --apply para aplicar.")
        return EXIT_OK

    new_lines = list(lines)
    for idx, _, new in changes:
        new_lines[idx] = new
    rules_file.write_text("".join(new_lines), encoding="utf-8")
    print(f"\nAplicado em {rules_file}")
    return EXIT_OK


def _first_line(text: str | None) -> str | None:
    if not text:
        return None
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s
    return None


def _emit_text(result: ValidationResult, path: str, rule_index: dict | None = None) -> None:
    rule_index = rule_index or {}
    if result.internal_errors:
        for e in result.internal_errors:
            print(f"[INTERNAL] {e}", file=sys.stderr)

    by_file: dict[str, list] = {}
    for f in result.findings:
        if f.suppressed:
            continue
        by_file.setdefault(f.file, []).append(f)

    for file_, fs in sorted(by_file.items()):
        print(f"\n=== {file_} ===")
        for f in sorted(fs, key=lambda x: -x.severity.value):
            sev = Severity(f.severity).name
            print(f"  [{sev}] [{f.rule_id}] linha {f.line}: {f.message}")
            rule = rule_index.get(f.rule_id)
            why = _first_line(getattr(rule, "description", None)) if rule else None
            fix_text = _first_line(f.fix_prose) or why
            if why:
                print(f"      why: {why}")
            if fix_text and fix_text != why:
                print(f"      fix: {fix_text}")

    print(f"\nSUMMARY: errors={result.error_count} "
          f"warnings={result.warn_count} "
          f"info={result.info_count} "
          f"halts={result.halt_count}")


def _emit_json(result: ValidationResult, path: str, rule_index: dict | None = None) -> None:
    rule_index = rule_index or {}
    out = {
        "summary": {
            "errors": result.error_count,
            "warnings": result.warn_count,
            "info": result.info_count,
            "halts": result.halt_count,
            "files_scanned": len({f.file for f in result.findings}),
            "internal_errors": len(result.internal_errors),
        },
        "internal_errors": result.internal_errors,
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": Severity(f.severity).name,
                "category": f.category,
                "file": f.file,
                "line": f.line,
                "message": f.message,
                "description": getattr(rule_index.get(f.rule_id), "description", None),
                "suppressed": f.suppressed,
                "fix": {
                    "mechanical_available": f.fix_mechanical is not None,
                    "prose": f.fix_prose,
                },
            }
            for f in result.findings
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


def _ns(**kwargs) -> argparse.Namespace:
    """Build argparse.Namespace pra passar ao sub-handler."""
    return argparse.Namespace(**kwargs)


def _read_target_framework(project_root: Path) -> str | None:
    pj = project_root / "project.json"
    if not pj.is_file():
        return None
    try:
        data = json.loads(pj.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return data.get("targetFramework")


def _run_review_quiet(project: Path, rules_file: str) -> tuple[int, "ValidationResult"]:
    """Roda _cmd_review captura stdout; retorna (exit_code, ValidationResult)."""
    from .runner import Runner as _Runner
    rules = _load_rules_or_die(rules_file)
    runner = _Runner(rules=rules, detectors=DETECTOR_REGISTRY, fixers=FIXER_REGISTRY)
    result = runner.run(str(project))
    _apply_sicoob_lib_overrides(result, verbose=False)
    publish_preconditions_blocked = _has_publish_readiness_precondition_errors(result)

    import os as _os
    external_gates_disabled = (
        _os.environ.get("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", "").strip()
        in ("1", "true", "yes")
    )
    if not external_gates_disabled and not publish_preconditions_blocked:
        _inject_analyzer_findings(result, str(project), timeout=180, verbose=False)
        _run_official_build_gate(result, str(project), timeout=180, verbose=False)
        _run_pack_gate(result, str(project), timeout=600, verbose=False)

    if result.internal_errors:
        return EXIT_INTERNAL, result
    sev = result.max_severity()
    if sev is None:
        return EXIT_OK, result
    if sev == Severity.HALT:
        return EXIT_HALT, result
    if sev == Severity.ERROR:
        return EXIT_ERROR, result
    return EXIT_WARN, result


def _phase0_migration(project: Path, rules_file: str,
                      no_swap_after_migration: bool = False) -> dict:
    """Phase 0 — migration probe.

    Returns dict: {ran: bool, target_framework: str, status: str}.
    Se targetFramework != Windows, invoca cmd_migrate_windows in-place
    (output = project, preserva original via .Migrated sibling).
    """
    tf = _read_target_framework(project)
    if tf == "Windows":
        return {"ran": False, "target_framework": tf, "status": "skip"}
    if tf is None:
        return {"ran": False, "target_framework": None, "status": "skip (no project.json)"}
    if tf not in ("Legacy", "Windows-Legacy"):
        return {"ran": False, "target_framework": tf, "status": f"skip (unknown tf={tf!r})"}

    from .migrate import cmd_migrate_windows
    import os as _os_mig
    no_swap = no_swap_after_migration or (
        _os_mig.environ.get("UIP_TOOLCHAIN_NO_SWAP", "").strip()
        in ("1", "true", "yes")
    )
    mw_args = _ns(
        path=str(project),
        out=None,
        migrator_path=None,
        migrator_args="",
        ignore_missing_dependencies=False,
        analyze_only=False,
        rules_file=rules_file,
        skip_migrator=False,
        skip_post=False,
        force=True,
        dry_run=False,
        no_swap_after_migration=no_swap,
    )
    rc = cmd_migrate_windows(mw_args)
    return {"ran": True, "target_framework": tf, "status": f"migrated (exit={rc})"}


def _phase1_deterministic(project: Path, rules_file: str) -> dict:
    """Phase 1 — auto-apply deterministic fixes. Reusa _cmd_fix com --apply."""
    fx_args = _ns(
        path=str(project),
        rules_file=rules_file,
        apply=True,
        rules="",
        include_class="deterministic",
        no_analyzer_gate=False,
        verbose=False,
    )
    rc = _cmd_fix(fx_args)
    return {"exit": rc}


def _phase3_contextual_apply(project: Path, rules_file: str) -> dict:
    """Phase 3 (opt-in) — aplica contextual fixes quando --apply-contextual."""
    fx_args = _ns(
        path=str(project),
        rules_file=rules_file,
        apply=True,
        rules="",
        include_class="contextual",
        no_analyzer_gate=False,
        verbose=False,
    )
    rc = _cmd_fix(fx_args)
    return {"exit": rc}


# F37: Pipeline-integrity rule_ids — gate-injected findings que indicam o
# engine NÃO conseguiu validar o projeto (preflight check failed, analyzer
# hung, pack hung). `apply_class` continua útil para orientar fix/display,
# mas o contrato de pronto é mais simples: qualquer ERROR não suprimido
# bloqueia deploy. Achado manual/contextual com severity ERROR não é nota
# deploy-safe; é revisão obrigatória.
_GATE_INTEGRITY_BLOCKING_RULES = frozenset({
    "UIPATH:PREFLIGHT",       # official uip not found / project.json missing
    "UIPATH:ANALYZE_HALT",    # uip rpa analyze failed/timeout
    "UIPATH:PACK_HALT",       # uip rpa pack failed/timeout
    "UIPATH:CLI_REQUIRED_PACKAGE_MISSING",  # dependência obrigatória ausente
})


def _effective_apply_class(finding, rule_index) -> str:
    """Returns effective apply_class PER-FINDING (não per-rule).

    F37: engine só bloqueia PASS pelo que prometeu auto-fixar
    mecanicamente. Honesto:

      - Rule conhecida + class=deterministic + finding.fix_mechanical
        presente → 'deterministic' (engine sabe fixar; se ainda ERROR é
        bug do fixer ou safety pipeline rolled back).
      - Rule conhecida + class=deterministic + fix_mechanical=None →
        'contextual' (detector achou problema mas safety guard preveniu
        injeção de fix mecânico — ex: F36 CCS-1 SecureString case;
        usuário decide manualmente via Studio UI seguindo fix.prose).
      - Rule conhecida + class=contextual/structural → mantém (manual
        review já era a expectativa).
      - Rule desconhecida (gate-injected) + rule_id em
        _GATE_INTEGRITY_BLOCKING_RULES → 'deterministic' (pipeline integrity).
      - Rule desconhecida + outro UIPATH:*/NU* → 'contextual' (Studio
        analyzer reportou; user investiga).
    """
    rule = rule_index.get(finding.rule_id)
    if rule is None:
        if finding.rule_id in _GATE_INTEGRITY_BLOCKING_RULES:
            return "deterministic"
        return "contextual"
    rule_cls = get_apply_class(rule)
    if rule_cls == "deterministic" and not finding.fix_mechanical:
        return "contextual"
    return rule_cls


def _classify_contextual_pending(result, rule_index) -> list:
    """Filtra findings que precisam decisão humana — effective_class ∈
    {contextual, structural}, sem incluir ERROR/HALT.

    ERROR contextual/structural continua exigindo decisão humana, mas agora
    bloqueia "pronto" por severidade. PASS_WITH_NOTES fica reservado para
    WARN/INFO residuais.

    F37: inclui também findings com effective_class downgrade — rules
    deterministic cujo fixer skipou (safety guard) E gate-injected findings
    de Studio analyzer (UIPATH:LOAD/ST-*/PACK). Display reflete status real
    pra usuário (precisa ação manual).
    """
    pending = []
    for f in result.findings:
        if f.suppressed:
            continue
        if f.severity in (Severity.ERROR, Severity.HALT):
            continue
        cls = _effective_apply_class(f, rule_index)
        if cls in ("contextual", "structural"):
            pending.append(f)
    return pending


def _is_blocking_error(finding, rule_index) -> bool:
    """Qualquer ERROR ativo bloqueia PASS.

    `apply_class` decide como tratar o fix; não decide segurança de deploy.
    """
    return finding.severity == Severity.ERROR and not finding.suppressed


def _classify_deploy_blockers(result, rule_index) -> list:
    """Findings que bloqueiam deploy no contrato público `ccs-uip <path>`.

    ERROR e HALT sempre bloqueiam. WARN/INFO contextuais seguem como notas.
    """
    blockers = []
    for f in result.findings:
        if f.suppressed:
            continue
        if f.severity == Severity.HALT or _is_blocking_error(f, rule_index):
            blockers.append(f)
    return blockers


def _print_uip_header(project: Path, iter_no: int) -> None:
    print(f"\n[ccs-uip] {project.name} — iter {iter_no}")
    print("=" * (8 + len(project.name) + 12))


def _print_phase(name: str, summary: str) -> None:
    print(f"PHASE {name:30s} {summary}")


def _print_status(status: str, *, project: Path, apply_contextual: bool) -> None:
    print()
    if status == "PASS":
        print("[PASS] projeto done.")
    elif status == "PASS_WITH_NOTES":
        if apply_contextual:
            print("[PASS-WITH-NOTES] contextual aplicado, findings remanescentes "
                  "WARN/INFO exigem decisão manual.")
        else:
            print("[PASS-WITH-NOTES] sem ERROR/HALT. Contextual findings "
                  "WARN/INFO são informacionais.")
            print(f"  Opt-in fix: ccs-uip {project} --apply-contextual")
    elif status == "FAIL":
        print("[FAIL] deploy blockers residuais.")


def _print_findings_table(findings: list, *, max_rows: int = 10, header: str) -> None:
    if not findings:
        return
    print(f"\n{header} (top {min(max_rows, len(findings))} de {len(findings)}):")
    for f in findings[:max_rows]:
        file_short = Path(f.file).name
        msg = f.message[:120]
        print(f"  [{f.rule_id:10s}] {file_short}:{f.line} — {msg}")
        if f.fix_prose:
            prose_line = f.fix_prose.strip().splitlines()[0][:120]
            print(f"               → {prose_line}")


def _cmd_all(args) -> int:
    """GOD COMMAND — pipeline 0→4 loop até PASS.

    Flow:
      iter 1+:
        PHASE 0 migration probe (Activity Migrator se tf != Windows)
        PHASE 1 deterministic fix auto-apply
        PHASE 2 gates Layer 2/3/5 via _run_review_quiet (review canonical)
        PHASE 3 contextual handling (dry-run | apply se --apply-contextual)
        PHASE 4 decide PASS / PASS_WITH_NOTES / FAIL

      PASS            → exit 0 (clean)
      PASS_WITH_NOTES → exit 0 (contextual findings WARN/INFO;
                        opt-in --apply-contextual aplica fixes manuais)
      FAIL            → exit 2 (default — blocker: deterministic ERROR ou HALT).
                        Com --watch: loop com watch.wait_for_change aguardando
                        edições (modo Studio dev).
    """
    from .watch import wait_for_change
    from .engine_status import EngineStatus

    project = Path(args.path).expanduser().resolve()
    if not project.is_dir():
        # Aceita também project.json direto
        if project.is_file() and project.name == "project.json":
            project = project.parent
        else:
            print(f"[INTERNAL] projeto não encontrado: {project}", file=sys.stderr)
            return EXIT_INTERNAL

    # Boot-time orphan cleanup: NuGet.config com sentinel = leftover de run
    # crashed (SIGKILL entre create no pack-gate e finally cleanup). Remove
    # ANTES de qualquer phase pra garantir zero rastro de feed local Sicoob
    # no projeto em estado consistente.
    if _cleanup_orphan_temp_nuget_config(project):
        print(f"[BOOT] orphan engine-temp NuGet.config removed from {project.name}",
              file=sys.stderr)

    # Interface pública = `ccs-uip <path> [--apply-contextual]`. Demais settings
    # são intrínsecos: defaults internos sobreescritos só via env vars
    # (escape hatches debug) ou via `_ns(...)` direto (tests).
    import os as _os_all
    rules_file = (
        getattr(args, "rules_file", None)
        or _os_all.environ.get("UIP_TOOLCHAIN_RULES_FILE")
        or str(DEFAULT_RULES_FILE)
    )
    rules = _load_rules_or_die(rules_file)
    rule_index = {r.id: r for r in rules}
    apply_ctx = bool(getattr(args, "apply_contextual", False))
    # Default = no_watch (modo CI/agentic). Opt-in interativo via env
    # UIP_TOOLCHAIN_WATCH=1 ou kwarg `watch=True` em `_ns(...)` (tests).
    watch_enabled = bool(getattr(args, "watch", False)) or (
        _os_all.environ.get("UIP_TOOLCHAIN_WATCH", "").strip()
        in ("1", "true", "yes")
    )
    no_watch = not watch_enabled
    interval = float(
        getattr(args, "watch_interval", None)
        or _os_all.environ.get("UIP_TOOLCHAIN_WATCH_INTERVAL", 2.0)
    )
    max_iters_raw = (
        getattr(args, "max_iters", None)
        or _os_all.environ.get("UIP_TOOLCHAIN_MAX_ITERS", 0)
    )
    max_iters = int(max_iters_raw) if max_iters_raw else 0

    estatus = EngineStatus(project)

    iter_no = 0
    while True:
        iter_no += 1
        estatus.begin_iter(iter_no)
        if max_iters and iter_no > max_iters:
            print(f"\n[ABORT] max-iters={max_iters} atingido sem PASS.")
            estatus.finalize("FAIL_MAX_ITERS")
            return EXIT_ERROR

        _print_uip_header(project, iter_no)

        # ---- PHASE 0: migration probe ----
        import os as _os
        skip_mig = bool(getattr(args, "skip_migration", False)) or (
            _os.environ.get("UIP_TOOLCHAIN_SKIP_MIGRATION", "").strip()
            in ("1", "true", "yes")
        )
        estatus.begin_phase("phase0_migration")
        if skip_mig:
            p0 = {"ran": False, "status": "skipped (--skip-migration)"}
            _print_phase("0  migration", p0["status"])
            estatus.end_phase("skipped", reason="user_opt_out")
        else:
            p0 = _phase0_migration(
                project, rules_file,
                no_swap_after_migration=bool(
                    getattr(args, "no_swap_after_migration", False)
                ),
            )
            _print_phase("0  migration", p0["status"])
            estatus.end_phase("ok", probe_status=p0.get("status"))

        # ---- PHASE 1: deterministic auto-fix ----
        estatus.begin_phase("phase1_deterministic")
        p1 = _phase1_deterministic(project, rules_file)
        _print_phase("1  deterministic", f"fix exit={p1['exit']}")
        estatus.end_phase("ok" if p1["exit"] == 0 else "fail", fix_exit=p1["exit"])

        # ---- PHASE 3 (apply mode): contextual auto-apply ANTES do review final ----
        if apply_ctx:
            estatus.begin_phase("phase3a_contextual_apply")
            p3a = _phase3_contextual_apply(project, rules_file)
            _print_phase("3a contextual-apply", f"fix exit={p3a['exit']}")
            estatus.end_phase("ok" if p3a["exit"] == 0 else "fail", fix_exit=p3a["exit"])

        # ---- PHASE 2+4: review final com Layer 2/3/5 + classify ----
        estatus.begin_phase("phase2_review")
        rc, result = _run_review_quiet(project, rules_file)

        # `errors` (display) = total bruto. `errors_blocking` (PASS gate) =
        # qualquer ERROR ativo. `apply_class` orienta fix/display, não segurança
        # de deploy.
        errors = sum(1 for f in result.findings
                     if f.severity == Severity.ERROR and not f.suppressed)
        errors_blocking = sum(1 for f in result.findings
                              if _is_blocking_error(f, rule_index))
        warns = sum(1 for f in result.findings
                    if f.severity == Severity.WARN and not f.suppressed)
        infos = sum(1 for f in result.findings
                    if f.severity == Severity.INFO and not f.suppressed)
        halts = sum(1 for f in result.findings
                    if f.severity == Severity.HALT and not f.suppressed)
        ctx_errs = errors - errors_blocking
        _print_phase(
            "2  gates+review",
            f"errors={errors} (blocking={errors_blocking}, contextual={ctx_errs}) "
            f"warns={warns} info={infos} halts={halts}",
        )
        estatus.end_phase(
            "fail" if errors_blocking > 0 or halts > 0 else "ok",
            errors=errors, errors_blocking=errors_blocking,
            warns=warns, infos=infos, halts=halts,
        )

        estatus.begin_phase("phase3_contextual")
        contextual_pending = _classify_contextual_pending(result, rule_index)
        if apply_ctx:
            _print_phase("3b contextual-residual", f"{len(contextual_pending)} findings")
        else:
            _print_phase("3  contextual (dry-run)", f"{len(contextual_pending)} findings PENDING")
        estatus.end_phase("ok", pending=len(contextual_pending),
                          apply_mode=apply_ctx)

        # ---- PHASE 4: decisão ----
        # Blocker = qualquer ERROR ativo ou HALT. Contextual WARN/INFO viram
        # PASS_WITH_NOTES. `--apply-contextual` pode reduzir notas, mas deploy
        # nunca depende de aceitar ERROR manual como pronto.
        if errors_blocking > 0 or halts > 0:
            status = "FAIL"
        elif contextual_pending:
            status = "PASS_WITH_NOTES"
        else:
            status = "PASS"

        # ---- Display findings relevantes ----
        if status == "FAIL":
            blocking = _classify_deploy_blockers(result, rule_index)
            _print_findings_table(blocking, max_rows=10,
                                  header="Deploy blockers (mecânicos/pipeline)")
        elif status == "PASS_WITH_NOTES" and not apply_ctx:
            _print_findings_table(contextual_pending, max_rows=20,
                                  header="Contextual findings (informacional — decisão humana)")

        _print_status(status, project=project, apply_contextual=apply_ctx)

        if status in ("PASS", "PASS_WITH_NOTES"):
            # Auto-clean `_BeforeMigration_*` backups quando engine completou
            # com PASS ou PASS_WITH_NOTES. Backup serve só como rollback manual;
            # engine concluiu pipeline com sucesso (sem blockers) → backup é
            # dead weight (50-200MB). Opt-out: UIP_TOOLCHAIN_KEEP_BACKUP=1.
            removed_backups = _cleanup_pre_migration_backups(project)
            for b in removed_backups:
                print(f"[BACKUP-CLEAN] removed {b.name}", file=sys.stderr)
            estatus.finalize(status)
            return EXIT_OK

        # FAIL → loop com watch ou abort
        if no_watch:
            estatus.finalize("FAIL")
            return EXIT_ERROR

        print(f"\n[WAITING] aguarda edições em {project.name} (Ctrl-C aborta)...")
        try:
            changed = wait_for_change(project, interval_s=interval)
        except KeyboardInterrupt:
            print("\n[ABORT] interrupted by user.")
            estatus.finalize("ABORTED")
            return EXIT_ERROR
        names = sorted({Path(p).name for p in changed})[:5]
        print(f"[CHANGE] {len(changed)} file(s) modified ({', '.join(names)}{'...' if len(changed) > 5 else ''}) — retrying...\n")


def _cmd_pre_migrate_check(args) -> int:
    """Phase 2 (2026-05): Run MigratedPackageVersionResolver offline clone.

    Exit codes:
        0 = todas SAME           => safe to invoke Activity Migrator
        1 = qualquer UPDATED     => predicted pin drift target; engine flags
                                    D-1*/D-PINALERT post-migrate
        2 = qualquer UNRESOLVED  => blocker; missing pkg/version (cannot
                                    safely migrate)
        3 = infra error          => NuGet unreachable AND no cache (caller
                                    should retry with VPN/proxy)
    """
    from .migrate_resolver import (
        ResolutionAction,
        check_project,
    )

    project_root = Path(args.path).resolve()
    project_json = project_root / "project.json"
    if not project_json.exists():
        print(f"[pre-migrate-check] project.json not found: {project_json}",
              file=sys.stderr)
        return EXIT_HALT

    cache_dir = Path(args.cache_dir) if args.cache_dir else None

    # Phase 2.1: pasta .nupkgs/ local. Empty string => disable (remote-only).
    local_nupkgs_raw = getattr(args, "local_nupkgs", None)
    local_nupkgs_folder: Path | None = None
    if local_nupkgs_raw:
        candidate = Path(local_nupkgs_raw)
        if candidate.exists() and candidate.is_dir():
            local_nupkgs_folder = candidate
        else:
            print(
                f"[pre-migrate-check] --local-nupkgs {candidate} not a directory; "
                f"falling back to remote-only.",
                file=sys.stderr,
            )

    try:
        results = check_project(
            project_json,
            target_framework=args.target_framework,
            cache_dir=cache_dir,
            include_prerelease=args.include_prerelease,
            local_nupkgs_folder=local_nupkgs_folder,
        )
    except Exception as exc:  # pragma: no cover — final safety net
        print(f"[pre-migrate-check] internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    summary = {
        "same":       sum(1 for r in results if r.action == ResolutionAction.SAME),
        "updated":    sum(1 for r in results if r.action == ResolutionAction.UPDATED),
        "unresolved": sum(1 for r in results if r.action == ResolutionAction.UNRESOLVED),
        "total":      len(results),
    }

    if args.format == "json":
        payload = {
            "project_json": str(project_json),
            "target_framework": args.target_framework,
            "summary": summary,
            "results": [r.to_dict() for r in results],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"pre-migrate-check :: {project_json}")
        print(f"target_framework  :: {args.target_framework}")
        print(f"summary           :: {summary}")
        for r in results:
            mark = {"Same": "OK", "Updated": "DRIFT", "Unresolved": "MISS"}[r.action.value]
            print(f"  [{mark:5}] {r.package_id} : {r.current_version} -> "
                  f"{r.recommended_version}  ({r.reason})")

    # Exit policy: blocker (UNRESOLVED) > drift (UPDATED) > clean (SAME).
    # All UNRESOLVED with no candidates = treat as infra error (3) only
    # when count == 0 across the board (likely NuGet down). Mixed
    # UNRESOLVED + SAME/UPDATED = real per-package gap, still exit 2.
    if summary["unresolved"] == summary["total"] and summary["total"] > 0:
        # Tutto unresolved & every result reason looks like "fetch failed":
        all_fetch_fail = all(
            "fetch failed" in r.reason.lower() or "unreachable" in r.reason.lower()
            for r in results
        )
        if all_fetch_fail:
            print("[pre-migrate-check] all NuGet fetches failed — "
                  "treating as infra error (exit 3).", file=sys.stderr)
            return EXIT_HALT
    if summary["unresolved"] > 0:
        return EXIT_ERROR
    if summary["updated"] > 0:
        return EXIT_WARN
    return EXIT_OK


def _cmd_pack_scrub(args) -> int:
    """Phase 4 (2026-05): scrub <repository> leak from .nuspec inside .nupkg.

    Exit codes:
        0 = scrub OK / dry-run / no-change (idempotente)
        1 = sign falhou pós scrub OK
        2 = arquivo não existe / IO fail
        10 = exception interna
    """
    from .pack_scrubber import scrub_repository, sign, inspect

    target = Path(args.nupkg)
    if not target.exists():
        print(f"ERROR: {target} not found", file=sys.stderr)
        return EXIT_ERROR

    inspect_only = getattr(args, "inspect_only", False)

    try:
        info_before = inspect(target)
        out = Path(args.output) if args.output else None
        info_after = scrub_repository(
            target, output_path=out, dry_run=inspect_only
        )
    except Exception as exc:  # pragma: no cover — final safety net
        print(f"[pack-scrub] internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    scrubbed = (
        info_before.repository_url is not None
        and info_after.repository_url is None
    )
    final_path = out if out else target
    tag = "DRY-RUN" if inspect_only else ("SCRUBBED" if scrubbed else "NO-CHANGE")
    print(f"[{tag}] {final_path}")
    print(f"  before.repository_url: {info_before.repository_url or '(none)'}")
    print(f"  after.repository_url : {info_after.repository_url or '(none)'}")

    # Optional signing post-scrub.
    if args.sign_cert and not inspect_only:
        ok, msg = sign(
            final_path,
            cert_fingerprint=args.sign_cert,
            timestamper=args.timestamper,
        )
        print(f"[SIGN {'OK' if ok else 'FAIL'}] {msg}")
        if not ok:
            return EXIT_WARN
    return EXIT_OK


def _cmd_migrate_check(args) -> int:
    """Phase 5 (2026-05): advisory Activity Migrator probe (opt-in).

    Exit codes:
        0 = sem findings, host resolvable, dry-run completo
        1 = findings emitidos (advisory; nunca causa HALT)
        2 = path inválido / project não existe
        (nunca 3 HALT — migrate-check é advisory only)
    """
    from .migrator_headless import run_migrate, run_probe

    project_root = Path(args.project)
    if project_root.is_file():
        project_root = project_root.parent
    if not project_root.exists():
        print(f"ERROR: {project_root} not found", file=sys.stderr)
        return EXIT_ERROR

    # Probe first — fail-fast if Migration DLL inacessível. Probe é cheap
    # (~30s) e isola erros de infra dos findings reais.
    probe_code, probe_payload = run_probe(timeout=30, dll_override=args.dll)
    if probe_code != 0:
        if args.format == "json":
            print(json.dumps({"probe": probe_payload}, indent=2))
        else:
            print(f"[PROBE FAIL] Migration host unavailable. "
                  f"Code={probe_code}. See JSON dump for details.")
            print(json.dumps(probe_payload, indent=2))
        return EXIT_WARN  # advisory; nunca HALT pelo migrate-check

    code, findings = run_migrate(
        project_root, dry_run=args.dry_run, timeout=args.timeout,
        dll_override=args.dll,
    )
    if args.format == "json":
        # Inline serialization — Finding dataclass via asdict; severity Enum
        # vira int (compat com outros JSON outputs do engine).
        payload = {
            "exit_code": code,
            "total": len(findings),
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": int(f.severity),
                    "severity_name": f.severity.name,
                    "category": f.category,
                    "file": f.file,
                    "line": f.line,
                    "message": f.message,
                }
                for f in findings
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for f in findings:
            print(f"[{f.severity.name}] {f.rule_id} {f.file}: {f.message}")
        print(f"\nTotal findings: {len(findings)} (exit={code})")
    # Advisory exit: never HALT, never FAIL pipeline solely on migrator_headless.
    return EXIT_WARN if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
