#!/usr/bin/env python3
"""Performance bench — engine review timing per XAML.

Usage:
    python scripts/perf_bench.py <project_path>
    python scripts/perf_bench.py <project_path> --profile  # cProfile mode

Output:
    - Per-file timing (ms): parse, detect, total
    - Aggregate: p50/p95/max + total findings
    - Top hotspots if --profile

Run from .uipath-rules/ root.
"""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import sys
import time
from pathlib import Path
from typing import Any

# Allow direct execution: ensure .uipath-rules root in sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _bench_review(project_path: str) -> dict[str, Any]:
    from scripts.rule_engine.cli import _load_rules_or_die, DEFAULT_RULES_FILE
    from scripts.rule_engine.detectors import REGISTRY as DETECTOR_REGISTRY
    from scripts.rule_engine.fixers import REGISTRY as FIXER_REGISTRY
    from scripts.rule_engine.runner import Runner

    rules = _load_rules_or_die(str(DEFAULT_RULES_FILE))

    # Pre-warm schema singleton (don't count first-load cost in per-file)
    try:
        from scripts.rule_engine.heuristics.activity_meta import get_schema
        t0 = time.perf_counter()
        s = get_schema()
        schema_load_ms = (time.perf_counter() - t0) * 1000
        schema_size = s.size
    except Exception as e:
        schema_load_ms = -1
        schema_size = -1

    runner = Runner(rules=rules, detectors=DETECTOR_REGISTRY, fixers=FIXER_REGISTRY)

    # Run + monkey-patch to time per-file
    timings: list[dict[str, Any]] = []

    original_run_file = runner._run_file

    def timed_run_file(file_path, rules, pc, result):
        t0 = time.perf_counter()
        n_before = len(result.findings)
        original_run_file(file_path, rules, pc, result)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        timings.append({
            "file": file_path.name,
            "size_kb": file_path.stat().st_size / 1024,
            "elapsed_ms": elapsed_ms,
            "findings": len(result.findings) - n_before,
        })

    runner._run_file = timed_run_file

    t_total = time.perf_counter()
    result = runner.run(project_path)
    total_elapsed_ms = (time.perf_counter() - t_total) * 1000

    return {
        "schema_load_ms": schema_load_ms,
        "schema_size": schema_size,
        "total_elapsed_ms": total_elapsed_ms,
        "rule_count": len(rules),
        "file_count": len(timings),
        "timings": timings,
        "total_findings": len(result.findings),
    }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = int(len(s) * pct / 100)
    return s[min(k, len(s) - 1)]


def _format_report(bench: dict[str, Any]) -> str:
    out = []
    out.append("# Engine review perf bench")
    out.append("")
    out.append(f"- Schema load: {bench['schema_load_ms']:.1f} ms ({bench['schema_size']} entries)")
    out.append(f"- Rules: {bench['rule_count']}")
    out.append(f"- Files: {bench['file_count']}")
    out.append(f"- Total elapsed: {bench['total_elapsed_ms']:.0f} ms ({bench['total_elapsed_ms']/1000:.2f} s)")
    out.append(f"- Total findings: {bench['total_findings']}")
    out.append("")

    if not bench["timings"]:
        out.append("(no files)")
        return "\n".join(out)

    times = [t["elapsed_ms"] for t in bench["timings"]]
    sizes = [t["size_kb"] for t in bench["timings"]]
    out.append("## Per-file timing")
    out.append("")
    out.append(f"- p50: {_percentile(times, 50):.0f} ms")
    out.append(f"- p95: {_percentile(times, 95):.0f} ms")
    out.append(f"- max: {max(times):.0f} ms")
    out.append(f"- total file size: {sum(sizes):.1f} KB")
    out.append("")

    # Top 10 slowest
    slow = sorted(bench["timings"], key=lambda x: -x["elapsed_ms"])[:10]
    out.append("## Top 10 slowest files")
    out.append("")
    out.append("| File | Size (KB) | Time (ms) | Findings |")
    out.append("|---|---|---|---|")
    for t in slow:
        out.append(f"| {t['file']} | {t['size_kb']:.1f} | {t['elapsed_ms']:.0f} | {t['findings']} |")
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("project_path", help="Project root with project.json")
    p.add_argument("--profile", action="store_true", help="Run with cProfile, print top hotspots")
    p.add_argument("--json", action="store_true", help="Emit raw JSON instead of markdown")
    p.add_argument("--out", default=None, help="Write report to file (default stdout)")
    args = p.parse_args()

    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
        bench = _bench_review(args.project_path)
        pr.disable()

        report = _format_report(bench)
        if args.json:
            report = json.dumps(bench, indent=2, default=str)

        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(20)
        report += "\n\n## cProfile top 20 (cumulative)\n\n```\n" + s.getvalue() + "\n```"
    else:
        bench = _bench_review(args.project_path)
        report = json.dumps(bench, indent=2, default=str) if args.json else _format_report(bench)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
