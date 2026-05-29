"""Adaptive `uip all` batch runner — validate many projects without manual retry.

Usage:
    python tools/batch_uip.py <input> [--report NAME.md] [--workers N] [--t1 S] [--t2 S]

<input> is either:
    - a directory: every immediate child dir (and child/child) containing a
      project.json is discovered; OR
    - a .txt file: one project path per line (or leaf folder names resolved
      under the file's dir, parent/<leaf>/project.json); OR
    - a .json file: a JSON array of absolute project paths.

WHY THIS EXISTS — timeout root-cause (observed 2026-05-28):
  `uip all` on a heavy project chains EXTERNAL .NET subprocesses that are
  legitimately CPU-busy (the engine's run_uipcli_guarded watchdog correctly
  leaves them alive, since they are NOT hung):
    - PHASE 0 Activity Migrator (target != Windows) -> full pipeline re-runs.
    - analyzer-gate (UiPath.Studio.CommandLine.exe) up to 3x/project.
    - nuget restore of large dep sets (EmguCV bundle => ~480 assemblies).
  A heavy project ~= 15-25 min SOLO; under N-way parallelism they contend for
  CPU/IO + the global nuget-cache lock and blow a flat timeout.

MECHANISM:
  1. heavy-detection (project.json target/deps) -> heavy scheduled first.
  2. two-phase adaptive timeout: Phase A parallel (t1); every TIMEOUT is
     auto-requeued to Phase B sequential (t2 >> t1). No manual intervention.
  3. nuget warms naturally after the first project; pace drops sharply.
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ENGINE = Path(__file__).resolve().parents[1]   # tools/ -> engine root
LOGS = ENGINE / ".tmp" / "batch_logs"


def discover(inp: Path) -> list[str]:
    if inp.is_dir():
        out = []
        for pj in inp.rglob("project.json"):
            if any(s in (".local", ".templates", ".tmp", "packages", ".nuget",
                         "obj", "bin") for s in pj.parts):
                continue
            out.append(str(pj.parent))
        return sorted(set(out))
    if inp.suffix == ".json":
        return json.loads(inp.read_text(encoding="utf-8"))
    # .txt — one path or leaf name per line
    base = inp.parent
    index = {p.parent.name.lower(): p.parent
             for p in base.rglob("project.json")
             if not any(s in (".local", ".templates", ".tmp", "packages",
                              ".nuget", "obj", "bin") for s in p.parts)}
    res = []
    for line in inp.read_text(encoding="utf-8").splitlines():
        leaf = line.strip()
        if not leaf:
            continue
        cand = Path(leaf)
        if (cand / "project.json").exists():
            res.append(str(cand)); continue
        parent = re.sub(r"-(dispatcher|performer)$", "", leaf)
        guess = base / parent / leaf
        if (guess / "project.json").exists():
            res.append(str(guess)); continue
        hit = index.get(leaf.lower())
        res.append(str(hit) if hit else leaf)
    return res


def is_heavy(proj: str) -> bool:
    try:
        data = json.loads((Path(proj) / "project.json").read_text(encoding="utf-8"))
    except Exception:
        return False
    tf = str(data.get("targetFramework") or data.get("expressionLanguage") or "").lower()
    return (tf not in ("windows", "")) or len(data.get("dependencies", {}) or {}) >= 8


def run_one(proj: str, timeout: int) -> dict:
    name = Path(proj).name
    t0 = time.perf_counter()
    rec = {"name": name, "path": proj}
    try:
        p = subprocess.run([sys.executable, "-m", "uip_engine.cli", "all", proj],
                           cwd=str(ENGINE), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        out = (p.stdout or "") + "\n--- STDERR ---\n" + (p.stderr or "")
        rec["exit"] = p.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout if isinstance(e.stdout, str) else "") or ""
        out += f"\n[BATCH] TIMEOUT after {timeout}s\n"
        rec["exit"] = "TIMEOUT"
    rec["secs"] = round(time.perf_counter() - t0, 1)
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"{name}.txt").write_text(out, encoding="utf-8")
    g = lambda pat: (lambda m: int(m.group(1)) if m else None)(re.search(pat, out))
    rec.update(applied=g(r"applied=(\d+)"), roll=g(r"regressions-rolled-back=(\d+)"),
               blocking=g(r"blocking=(\d+)"), pending=g(r"(\d+) findings PENDING"))
    md = re.search(r"\[(PASS-WITH-NOTES|PASS|FAIL|HALT|PENDING_REVIEW)\]", out)
    rec["decision"] = md.group(1) if md else ("TIMEOUT" if rec["exit"] == "TIMEOUT" else "?")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--report", default="batch_adaptive_report.md")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--t1", type=int, default=900)
    ap.add_argument("--t2", type=int, default=2400)
    a = ap.parse_args()
    projects = discover(Path(a.input))
    heavy = [p for p in projects if is_heavy(p)]
    order = heavy + [p for p in projects if p not in heavy]
    print(f"adaptive batch: {len(projects)} projects ({len(heavy)} heavy) | "
          f"Phase A workers={a.workers} t1={a.t1}s | Phase B seq t2={a.t2}s")
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, p, a.t1): p for p in order}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result(); results[r["name"]] = r
            print(f"[A {i:2}/{len(order)}] {str(r['exit']):8} {r['decision']:16} {r['secs']}s  {r['name']}")
    tos = [results[Path(p).name]["path"] for p in order if results[Path(p).name]["exit"] == "TIMEOUT"]
    if tos:
        print(f"\nPhase B: {len(tos)} timeout(s) -> sequential retry (t2={a.t2}s)")
        for j, p in enumerate(tos, 1):
            r = run_one(p, a.t2); results[r["name"]] = r
            print(f"[B {j}/{len(tos)}] {str(r['exit']):8} {r['decision']:16} {r['secs']}s  {r['name']}")
    final = [results[Path(p).name] for p in projects]
    npass = sum(1 for r in final if r["decision"] in ("PASS", "PASS-WITH-NOTES", "PENDING_REVIEW"))
    pct = round(100 * npass / len(final), 1) if final else 0.0
    out = [f"# Adaptive uip batch — {len(final)} projects", "",
           f"- **PASS: {npass}/{len(final)} = {pct}%**",
           f"- FAIL: {[r['name'] for r in final if r['decision']=='FAIL'] or 'none'}",
           f"- TIMEOUT (after Phase B): {[r['name'] for r in final if r['exit']=='TIMEOUT'] or 'none'}", "",
           "| projeto | exit | decisao | applied | roll | blk | pend | s |",
           "|---|---|---|---|---|---|---|---|"]
    for r in sorted(final, key=lambda x: x["name"]):
        out.append(f"| {r['name']} | {r['exit']} | {r['decision']} | {r.get('applied')} | "
                   f"{r.get('roll')} | {r.get('blocking')} | {r.get('pending')} | {r['secs']} |")
    (ENGINE / ".tmp" / a.report).write_text("\n".join(out), encoding="utf-8")
    print(f"\nPASS {npass}/{len(final)} = {pct}% | report -> .tmp/{a.report}")
    return 0 if pct >= 95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
