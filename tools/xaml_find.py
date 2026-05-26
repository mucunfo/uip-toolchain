#!/usr/bin/env python3
"""xaml_find.py — targeted lookup inside UiPath XAML without full-file reads.

Usage:
    # Find activity by DisplayName (exact or substring)
    python xaml_find.py <file.xaml> --activity "AtribuirResultado"

    # Find argument (declaration + all usages)
    python xaml_find.py <file.xaml> --arg in_DtConfig

    # Find variable (declaration + all usages)
    python xaml_find.py <file.xaml> --var vStUsuario

    # List all InvokeWorkflowFile references
    python xaml_find.py <file.xaml> --invokes

    # Return N-line window around a line number
    python xaml_find.py <file.xaml> --line 1890 --context 10
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def find_activity(lines: list[str], query: str) -> list[tuple[int, str]]:
    """Return lines containing DisplayName matching query (case-insensitive substring)."""
    q = query.lower()
    out: list[tuple[int, str]] = []
    for i, line in enumerate(lines, start=1):
        for m in re.finditer(r'DisplayName="([^"]*)"', line):
            if q in m.group(1).lower():
                out.append((i, line.strip()))
                break
    return out


def find_argument(lines: list[str], name: str) -> dict[str, list[tuple[int, str]]]:
    """Find x:Property declaration + all usages (attribute values, VB expressions)."""
    decls: list[tuple[int, str]] = []
    usages: list[tuple[int, str]] = []
    decl_re = re.compile(rf'<x:Property[^>]*\bName="{re.escape(name)}"')
    # Usage patterns: [name] or [name.Xxx] or name as attribute value
    usage_re = re.compile(rf'\b{re.escape(name)}\b')
    for i, line in enumerate(lines, start=1):
        if decl_re.search(line):
            decls.append((i, line.strip()))
        elif usage_re.search(line):
            usages.append((i, line.strip()))
    return {"declarations": decls, "usages": usages}


def find_variable(lines: list[str], name: str) -> dict[str, list[tuple[int, str]]]:
    decls: list[tuple[int, str]] = []
    usages: list[tuple[int, str]] = []
    decl_re = re.compile(rf'<Variable[^>]*\bName="{re.escape(name)}"')
    usage_re = re.compile(rf'\b{re.escape(name)}\b')
    for i, line in enumerate(lines, start=1):
        if decl_re.search(line):
            decls.append((i, line.strip()))
        elif usage_re.search(line):
            usages.append((i, line.strip()))
    return {"declarations": decls, "usages": usages}


def find_invokes(lines: list[str]) -> list[tuple[int, str, str]]:
    """Return (line, workflow_path, display_name) for each InvokeWorkflowFile."""
    out: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines, start=1):
        wf_m = re.search(r'WorkflowFileName="([^"]+)"', line)
        if not wf_m:
            continue
        dn_m = re.search(r'DisplayName="([^"]*)"', line)
        out.append((i, wf_m.group(1), dn_m.group(1) if dn_m else ""))
    return out


def get_line_context(lines: list[str], center: int, radius: int) -> list[tuple[int, str]]:
    start = max(1, center - radius)
    end = min(len(lines), center + radius)
    return [(i, lines[i - 1]) for i in range(start, end + 1)]


def _print_hits(hits: list[tuple[int, str]], label: str) -> None:
    if not hits:
        return
    print(f"--- {label} ({len(hits)}) ---")
    for line_no, text in hits:
        print(f"L.{line_no}: {text}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Targeted lookup in UiPath XAML")
    ap.add_argument("file", help="path to .xaml file")
    mx = ap.add_mutually_exclusive_group(required=True)
    mx.add_argument("--activity", help="find activity by DisplayName substring")
    mx.add_argument("--arg", help="find argument declaration + usages")
    mx.add_argument("--var", help="find variable declaration + usages")
    mx.add_argument("--invokes", action="store_true", help="list InvokeWorkflowFile references")
    mx.add_argument("--line", type=int, help="show context around this line number")
    ap.add_argument("--context", type=int, default=5, help="context radius for --line (default 5)")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 2
    lines = _read_lines(path)

    if args.activity:
        hits = find_activity(lines, args.activity)
        if not hits:
            print(f"No DisplayName matching '{args.activity}'")
            return 1
        _print_hits(hits, f"activity matches for '{args.activity}'")
        return 0

    if args.arg:
        result = find_argument(lines, args.arg)
        if not result["declarations"] and not result["usages"]:
            print(f"No argument '{args.arg}' found")
            return 1
        _print_hits(result["declarations"], f"declaration of '{args.arg}'")
        _print_hits(result["usages"], f"usages of '{args.arg}'")
        return 0

    if args.var:
        result = find_variable(lines, args.var)
        if not result["declarations"] and not result["usages"]:
            print(f"No variable '{args.var}' found")
            return 1
        _print_hits(result["declarations"], f"declaration of '{args.var}'")
        _print_hits(result["usages"], f"usages of '{args.var}'")
        return 0

    if args.invokes:
        hits = find_invokes(lines)
        if not hits:
            print("No InvokeWorkflowFile references")
            return 1
        print(f"--- invoked workflows ({len(hits)}) ---")
        for line_no, wf, dn in hits:
            dn_repr = f'  "{dn}"' if dn else ""
            print(f"L.{line_no}: {wf}{dn_repr}")
        return 0

    if args.line:
        ctx = get_line_context(lines, args.line, args.context)
        for line_no, text in ctx:
            marker = " >" if line_no == args.line else "  "
            print(f"L.{line_no}{marker} {text}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
