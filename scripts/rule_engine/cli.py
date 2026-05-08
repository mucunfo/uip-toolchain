"""CLI entry point — review, fix, list, validate, render-md."""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# Disable .pyc bytecode caching engine-wide. Stale .pyc causou false positive
# J-6 (cache leu versão velha do detector json_checks após edits).
# Sem cache → impossível ler versão obsoleta.
sys.dont_write_bytecode = True

# Sweep existing __pycache__ DIRS dentro do pacote rule_engine — invalida
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


# Exit codes
EXIT_OK = 0
EXIT_WARN = 1
EXIT_ERROR = 2
EXIT_HALT = 3
EXIT_INTERNAL = 10


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

    parser.print_help()
    return EXIT_OK


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
                    help="Desliga Studio Analyzer gate (uipcli) — default ON. "
                         "Default behavior: roda baseline pré-fix + diff "
                         "pós-fix. Reporta erros INTRODUZIDOS pelos fixes "
                         "(diff-based: pré-existentes ignorados). Skip "
                         "automaticamente se uipcli não encontrado (graceful).")

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

    return p


def _load_rules_or_die(path: str) -> list:
    try:
        return load_rules(
            Path(path),
            registered_detectors=set(DETECTOR_REGISTRY.keys()),
            registered_fixers=set(FIXER_REGISTRY.keys()),
        )
    except SchemaError as e:
        print(f"[INTERNAL] schema error: {e}", file=sys.stderr)
        sys.exit(EXIT_INTERNAL)
    except Exception as e:
        print(f"[INTERNAL] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(EXIT_INTERNAL)


def _cmd_review(args) -> int:
    rules = _load_rules_or_die(args.rules_file)
    runner = Runner(rules=rules, detectors=DETECTOR_REGISTRY, fixers=FIXER_REGISTRY)
    result = runner.run(args.path)

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
    from datetime import datetime, timezone

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
    print(f"")
    print(f"- Records aggregated: {parsed_records}")
    print(f"- Total findings: {total_findings}")
    print(f"- Distinct rules triggered: {len(counts)}/{rule_ids_total}")
    print(f"- Distinct projects: {len(runs_per_project)}")
    print(f"")
    print(f"## Top {args.top} rules by findings")
    print(f"")
    print(f"| Rank | Rule | Sev | Title | Count | Suppressed | Projects |")
    print(f"|---|---|---|---|---|---|---|")
    for i, (rid, info) in enumerate(sorted_counts[:args.top], 1):
        title = rules_by_id.get(rid).title if rid in rules_by_id else "?"
        sev = "/".join(sorted(info["severities"]))
        title_short = title[:50] + ("..." if len(title) > 50 else "")
        print(f"| {i} | {rid} | {sev} | {title_short} | {info['count']} | {info['suppressed']} | {len(info['projects'])} |")

    # Rules never triggered (candidates for deprecation review)
    untriggered = sorted(set(rules_by_id) - set(counts))
    if untriggered and rules_by_id:
        print(f"")
        print(f"## Rules never triggered ({len(untriggered)} of {len(rules_by_id)})")
        print(f"")
        print(f"Candidates for review (may indicate dead rules or rare conditions):")
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

    # Analyzer gate baseline (opt-in via --analyzer-gate). Roda uma única vez
    # ANTES de qualquer fix iter, captura set de issues pré-existentes. Diff
    # vs post-loop dá erros introduzidos. Caro (10-30s) — só rodar quando
    # explicitamente requested.
    analyzer_baseline = None
    analyzer_cli_path = None
    analyzer_gate_enabled = (not getattr(args, "no_analyzer_gate", False)) and not dry_run
    # F28: pre-loop bytes snapshot p/ rollback se Layer 2 reportar new errors.
    pre_loop_bytes: dict = {}
    if analyzer_gate_enabled:
        from .analyzer import (discover_uipcli, run_analyzer,
                                load_cached_baseline, save_cached_baseline)
        analyzer_cli_path = discover_uipcli()
        if analyzer_cli_path is None:
            print("# analyzer-gate: uipcli não encontrado. Defina UIPATH_STUDIO_CLI ou "
                  "instale UiPath Studio. Skipping gate.")
        else:
            # Cache lookup (F27): re-run consecutivos paga só uipcli post-diff.
            analyzer_baseline = load_cached_baseline(project_root)
            if analyzer_baseline is not None:
                print(f"# analyzer-gate: baseline cache HIT "
                      f"({len(analyzer_baseline)} issues). Skipping baseline run.")
            else:
                print(f"# analyzer-gate: baseline run via {analyzer_cli_path.name}...")
                analyzer_baseline = run_analyzer(project_root, analyzer_cli_path)
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
                # F28: snapshot pre-loop XAML bytes p/ rollback potencial.
                for x in project_root.rglob("*.xaml"):
                    try:
                        pre_loop_bytes[x.resolve()] = x.read_bytes()
                    except OSError:
                        pass

    rules_by_id = {r.id: r for r in rules}

    # Idempotência: alguns detectores (N-6/N-7) emitem 1 finding por (tag, attr).
    # Pattern do segundo finding fica stale após primeiro fix mutar tag.
    # Loop detect→apply até `applied=0` numa iteração (fixpoint). Dry-run roda
    # 1 iteração só (não escreve). Max 20 iters como safety bound.
    MAX_ITERATIONS = 20
    iteration = 0
    while True:
        iteration += 1
        if iteration > MAX_ITERATIONS:
            print(f"\nWARN: fixpoint não convergiu em {MAX_ITERATIONS} iterações. Abortando loop.")
            break

        result = runner.run(args.path)
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
            if not f.fix_mechanical:
                iter_no_fix += 1
                continue
            rule = rules_by_id.get(f.rule_id)
            if rule:
                rule_class = get_apply_class(rule)
                if rule_class not in included_classes:
                    iter_blocked += 1
                    if not dry_run:
                        print(f"  [BLOCKED apply_class={rule_class}] [{f.rule_id}] {f.file}: revisar manualmente (ver fix.prose).")
                    continue
            mech_type = f.fix_mechanical.get("type")
            fixer = FIXER_REGISTRY.get(mech_type)
            if fixer is None:
                print(f"  [SKIP] [{f.rule_id}] {f.file}: fixer '{mech_type}' não registrado")
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
                print(f"  [SKIP] [{f.rule_id}] {f.file}: {ar.error}")
                continue
            if ar.status == "regression":
                iter_regressions += 1
                print(f"  [REGRESSION rolled back] [{f.rule_id}] {ar.error}")
                continue
            if ar.status == "regression-vb":
                iter_vb_regressions += 1
                print(f"  [REGRESSION-VB rolled back] [{f.rule_id}] {ar.error}")
                continue
            if ar.status == "regression-cascade":
                iter_cascade_regressions += 1
                print(f"  [REGRESSION cascade — manual review needed] [{f.rule_id}] {f.file}: {ar.error}")
                iter_applied += 1
                continue
            if ar.changed:
                if dry_run:
                    iter_would_fix += 1
                else:
                    iter_applied += 1
                print(f"  [{label}] [{f.rule_id}] {f.file}")
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

    print(
        f"\nSUMMARY ({iteration} iter, classes={sorted(included_classes)}): "
        f"applied={applied} would-fix={would_fix} no-op={no_op} "
        f"no-mechanical-fix={no_fix} blocked-other-class={blocked} "
        f"regressions-rolled-back={regressions} regressions-vb={vb_regressions} "
        f"regressions-cascade={cascade_regressions}"
    )
    if dry_run and would_fix > 0:
        print("Re-run with --apply to write changes.")

    # Analyzer gate diff (apply mode only, baseline disponível).
    if analyzer_baseline is not None and not dry_run and applied > 0:
        from .analyzer import run_analyzer, diff_new_issues, format_issue
        print(f"\n# analyzer-gate: post-fix re-run...")
        analyzer_post = run_analyzer(project_root, analyzer_cli_path)
        if analyzer_post is None:
            print("# analyzer-gate: post run failed/timeout. Diff incomplete.")
        else:
            new_issues = diff_new_issues(analyzer_baseline, analyzer_post)
            resolved = analyzer_baseline - analyzer_post
            new_errs = [i for i in new_issues if i.severity == "Error"]
            new_warns = [i for i in new_issues if i.severity == "Warning"]
            resolved_count = len(resolved)
            print(
                f"# analyzer-gate: {len(new_issues)} new issues "
                f"({len(new_errs)} errors, {len(new_warns)} warnings) | "
                f"{resolved_count} resolved"
            )
            if new_errs:
                print("\n[ANALYZER REGRESSION] Errors INTRODUZIDOS pelos fixes:")
                for i in new_errs[:30]:
                    print(f"  ! {format_issue(i)[:200]}")
                if len(new_errs) > 30:
                    print(f"  ... +{len(new_errs)-30} more")
                # F28: auto-rollback. Identify files com errors novos via
                # filename match. Revert pre-loop bytes (saved before fixes).
                err_files = {i.file for i in new_errs if i.file}
                rolled_back = 0
                rollback_failed = []
                for path, pre_bytes in pre_loop_bytes.items():
                    if path.name not in err_files:
                        continue
                    try:
                        path.write_bytes(pre_bytes)
                        rolled_back += 1
                    except OSError as e:
                        rollback_failed.append((path.name, str(e)))
                if rolled_back > 0:
                    print(f"\n[ANALYZER ROLLBACK] {rolled_back} files revertidos pra estado pré-loop.")
                    print("  Re-rodar review pra ver state pós-rollback.")
                if rollback_failed:
                    print(f"[ANALYZER ROLLBACK FAILED] {len(rollback_failed)} files:")
                    for name, err in rollback_failed[:5]:
                        print(f"  ! {name}: {err}")
                # Exit code reflects gate failure
                return EXIT_INTERNAL
            if new_warns:
                print(f"\n[ANALYZER WARN] Warnings introduzidas (sem block):")
                for i in new_warns[:10]:
                    print(f"  ~ {format_issue(i)[:200]}")
                if len(new_warns) > 10:
                    print(f"  ... +{len(new_warns)-10} more")

    return EXIT_OK


def _cmd_phase_out(args) -> int:
    if args.scope != "windows-only":
        return EXIT_INTERNAL

    UNIVERSALIZE = {"W-3", "W-10", "W-12", "W-16", "W-17"}
    KEEP_WINDOWS = {"W-1", "W-2", "W-4", "W-11a", "W-11b", "W-13", "W-14", "W-15"}

    rules_file = Path(args.rules_file)
    content = rules_file.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    import re
    id_pattern = re.compile(r'^\s*-\s+id:\s+([A-Z][A-Z0-9]*-\w+)\s*$')
    target_pattern = re.compile(r'^(\s+)target:\s+windows\s*$')

    changes: list[tuple[int, str, str]] = []
    current_rule = None
    rule_start_line = -1
    for i, line in enumerate(lines):
        m = id_pattern.match(line)
        if m:
            current_rule = m.group(1)
            rule_start_line = i
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


if __name__ == "__main__":
    sys.exit(main())
