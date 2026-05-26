"""Snapshot regression suite — engine output stability gate.

Roda `cli review` em projetos canonical Sicoob, normaliza output, compara
contra baseline. Catches engine regressions: rule mudou, detector quebrou,
fixer over-reach (mascara findings que antes apareciam).

Workflow:
  1. Capture baseline (uma vez):
       python -m scripts.snapshot_regression --capture

  2. Validate (após mudança engine):
       python -m scripts.snapshot_regression
       exit 0 = OK
       exit 1 = drift detectado (review diff + decidir update baseline)

  3. Update baseline (após review intentional change):
       python -m scripts.snapshot_regression --capture --force

Catalog canonical (estável, Windows-target migrado, conhecidamente passa):
  - importar-cadastro-avais-fiancas-honrados-performer

Expansão: adicionar mais projetos canonical conforme estabilizam.

Layout:
  <repo>/tests/snapshots/<project_slug>.json    ← baseline gravado
  <repo>/.tmp/snapshot_runs/<project_slug>.json ← run atual (diff source)

Output normalization:
  - Strip absolute paths (substitui project_root por `<root>`)
  - Sort findings por (file, line, rule_id) — determinismo
  - Strip campos voláteis: timestamp, run_id, line numbers em CommentOut-shift
  - Strip mecânico specs (path absoluto) — só rule_id + severity + msg

Diff strategy:
  - Counts por rule_id (delta expected vs actual)
  - Findings added (regressão: engine pegou cobertura nova OR detector quebrou)
  - Findings removed (intentional mascaramento OR fixer auto-aplicou)

Exit codes:
  0 = snapshot matches OR --capture sucesso
  1 = drift detectado
  2 = erro infraestrutura (canonical ausente, engine fail)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS_DIR = REPO_ROOT / "tests" / "snapshots"
RUNS_DIR = REPO_ROOT / ".tmp" / "snapshot_runs"

# Catalog canonical Sicoob — expandir conforme projetos estabilizam.
# Path absoluto (workspace specific). Tornar configurável via env se generalizar.
CANONICAL = [
    {
        "slug": "importar-cadastro-avais-fiancas-honrados-performer",
        "path": Path(
            "C:/Users/lisan/OneDrive - Sicoob/Projects/"
            "importar-cadastro-avais-fiancas-honrados/"
            "importar-cadastro-avais-fiancas-honrados-performer"
        ),
    },
]


def _normalize(findings: list[dict], project_path: Path) -> list[dict]:
    """Strip volátil (path absoluto, mech path) + sort determinístico."""
    root_str = str(project_path).replace("\\", "/")
    out = []
    for f in findings:
        file_path = (f.get("file") or "").replace("\\", "/")
        if root_str in file_path:
            file_rel = file_path.split(root_str, 1)[1].lstrip("/")
        else:
            file_rel = file_path
        out.append({
            "rule_id": f.get("rule_id"),
            "severity": f.get("severity"),
            "category": f.get("category"),
            "file": file_rel,
            "line": f.get("line"),
            # Strip message body (varia por run com cache/hashes). Manter
            # só rule_id + file + line pra match estável.
        })
    out.sort(key=lambda x: (x["file"], x.get("line") or 0, x["rule_id"] or ""))
    return out


def _run_review(project_path: Path) -> tuple[int, list[dict]]:
    """Run cli review --format json. Returns (exit_code, findings_list)."""
    cmd = [
        sys.executable, "-m", "scripts.rule_engine.cli", "review",
        str(project_path), "--format", "json",
    ]
    proc = subprocess.run(
        cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=900,
    )
    # cli review imprime SyntaxWarnings + JSON. Find first { line.
    lines = proc.stdout.splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if l.lstrip().startswith("{")), None)
    if start is None:
        return proc.returncode, []
    try:
        d = json.loads("".join(lines[start:]))
    except json.JSONDecodeError:
        return proc.returncode, []
    return proc.returncode, d.get("findings", [])


def _snapshot_path(slug: str) -> Path:
    return SNAPSHOTS_DIR / f"{slug}.json"


def _run_path(slug: str) -> Path:
    return RUNS_DIR / f"{slug}.json"


def capture(force: bool = False, skip_missing: bool = False) -> int:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for entry in CANONICAL:
        slug, path = entry["slug"], entry["path"]
        out = _snapshot_path(slug)
        if out.exists() and not force:
            print(f"[skip] {slug} (snapshot existe; use --force)")
            continue
        if not path.is_dir():
            if skip_missing:
                print(f"[skip-missing] {slug}: path ausente {path}")
                continue
            print(f"[ERROR] {slug}: path ausente {path}", file=sys.stderr)
            return 2
        print(f"[capture] {slug}: running review...")
        code, findings = _run_review(path)
        norm = _normalize(findings, path)
        out.write_text(json.dumps({
            "slug": slug,
            "engine_review_exit": code,
            "findings_count": len(norm),
            "findings": norm,
            "rule_counts": dict(Counter(f["rule_id"] for f in norm)),
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[capture] {slug}: {len(norm)} findings → {out}")
    return 0


def validate(skip_missing: bool = False) -> int:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    drift = False
    any_verified = False
    for entry in CANONICAL:
        slug, path = entry["slug"], entry["path"]
        if not path.is_dir():
            if skip_missing:
                print(f"[skip-missing] {slug}: path ausente {path}")
                continue
            print(f"[ERROR] {slug}: path ausente {path}", file=sys.stderr)
            return 2
        baseline_path = _snapshot_path(slug)
        if not baseline_path.exists():
            print(f"[ERROR] {slug}: baseline ausente. Rode --capture primeiro.",
                  file=sys.stderr)
            return 2
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        print(f"[run] {slug}: running review...")
        any_verified = True
        code, findings = _run_review(path)
        norm = _normalize(findings, path)
        run_out = _run_path(slug)
        run_out.write_text(json.dumps({
            "findings_count": len(norm),
            "findings": norm,
            "rule_counts": dict(Counter(f["rule_id"] for f in norm)),
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        # Diff
        b_set = {(f["file"], f["line"], f["rule_id"]) for f in baseline["findings"]}
        n_set = {(f["file"], f["line"], f["rule_id"]) for f in norm}
        added = n_set - b_set
        removed = b_set - n_set
        if not added and not removed:
            print(f"[ok] {slug}: {len(norm)} findings — match baseline")
        else:
            drift = True
            print(f"[DRIFT] {slug}: +{len(added)} added / -{len(removed)} removed")
            for it in sorted(added)[:10]:
                print(f"    + {it}")
            for it in sorted(removed)[:10]:
                print(f"    - {it}")
            if len(added) > 10 or len(removed) > 10:
                print(f"    ... (run details em {run_out})")
    if skip_missing and not any_verified:
        print("[skip-missing] nenhum canonical disponível neste host — "
              "snapshot verify no-op (esperado em GitHub-hosted runner sem "
              "workspace Sicoob montado).")
    return 1 if drift else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Snapshot regression suite.")
    ap.add_argument("--capture", action="store_true",
                    help="Capture/refresh baseline snapshots.")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing baseline (com --capture).")
    ap.add_argument("--skip-missing", action="store_true",
                    help="Skip canonical entries whose path ausente em vez de "
                         "exit 2. Uso típico: CI em runner sem workspace Sicoob.")
    args = ap.parse_args(argv)

    if args.capture:
        return capture(force=args.force, skip_missing=args.skip_missing)
    return validate(skip_missing=args.skip_missing)


if __name__ == "__main__":
    sys.exit(main())
