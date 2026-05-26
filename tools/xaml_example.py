#!/usr/bin/env python3
"""xaml_example.py — on-demand activity example lookup from reference models.

Replaces the static TEMPLATES.md / QUICK-REFERENCE snippet blocks with live
extraction from configured reference projects. The example returned is real
code in PRD — never invented.

Config: `models.conf` in .uip-toolchain/ root. One absolute path per line
(reference project root). Order = priority.

Usage:
    python xaml_example.py --activity LogMessage
    python xaml_example.py --activity NApplicationCard --variant 2
    python xaml_example.py --list               # dump all distinct activities found
    python xaml_example.py --activity TryCatch --model <path>    # override config
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
RULES_DIR = SCRIPT_DIR.parent
CONFIG = RULES_DIR / "models.conf"

SKIP_DIRS = {"Temp", "legacy", "lint-test-cases", ".entities", ".local",
             ".objects", ".project", ".screenshots", ".settings",
             ".templates", ".tmh", ".git"}


def read_models(override: str | None) -> list[Path]:
    if override:
        return [Path(override)]
    if not CONFIG.exists():
        print(f"ERROR: {CONFIG} not found. Add at least one reference project path.",
              file=sys.stderr)
        sys.exit(2)
    paths = []
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        p = Path(s)
        if not p.exists():
            print(f"WARNING: {s} (from models.conf) does not exist — skipping",
                  file=sys.stderr)
            continue
        paths.append(p)
    if not paths:
        print("ERROR: no valid reference projects in models.conf", file=sys.stderr)
        sys.exit(2)
    return paths


def iter_xaml_files(root: Path):
    for p in root.rglob("*.xaml"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


_TAG_RE = re.compile(r"^\{[^}]*\}(.+)$")


def local_name(tag: str) -> str:
    m = _TAG_RE.match(tag)
    return m.group(1) if m else tag


def iter_elements(path: Path):
    """Yield (element, line_no_of_start_tag) for each element in the file."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return

    # Build display-name → line map for origin reporting. Fallback to IdRef.
    idref_line: dict[str, int] = {}
    for i, line in enumerate(raw.splitlines(), start=1):
        m = re.search(r'WorkflowViewState\.IdRef="([^"]+)"', line)
        if m:
            idref_line.setdefault(m.group(1), i)

    def walk(el):
        yield el
        for c in list(el):
            yield from walk(c)

    for el in walk(root):
        line = None
        idref = el.get("{http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation}WorkflowViewState.IdRef")
        if idref and idref in idref_line:
            line = idref_line[idref]
        yield el, line


def serialize(el: ET.Element) -> str:
    """Serialize element preserving namespaces with short prefixes."""
    # Attempt short prefix registration
    nsmap = {
        "ui": "http://schemas.uipath.com/workflow/activities",
        "uix": "http://schemas.uipath.com/workflow/activities/modern",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml",
        "sap": "http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation",
        "sap2010": "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation",
        "scg": "clr-namespace:System.Collections.Generic;assembly=mscorlib",
        "s": "clr-namespace:System;assembly=mscorlib",
        "sd": "clr-namespace:System.Data;assembly=System.Data",
        "mva": "clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities",
        "ss": "clr-namespace:System.Security;assembly=mscorlib",
    }
    for prefix, uri in nsmap.items():
        ET.register_namespace(prefix, uri)
    return ET.tostring(el, encoding="unicode")


def count_children(el: ET.Element) -> int:
    return sum(1 for _ in el.iter()) - 1


def canonical_score(el: ET.Element, raw_len: int) -> tuple:
    """Score for picking canonical example. Lower tuple = better.

    Prefer: has DisplayName, not too nested, reasonable length.
    """
    has_dn = 1 if el.get("DisplayName") else 0
    depth = count_children(el)
    # prefer modest size (not tiny empty, not giant)
    size_penalty = abs(raw_len - 400)  # target ~400 chars snippet
    return (-has_dn, depth, size_penalty)


def find_examples(models: list[Path], activity: str, limit: int = 5):
    """Return list of (path, line, element_str, score) sorted by score."""
    act_lower = activity.lower()
    candidates = []
    for model in models:
        for xf in iter_xaml_files(model):
            for el, line in iter_elements(xf):
                if local_name(el.tag).lower() == act_lower:
                    s = serialize(el)
                    candidates.append((xf, line, s, canonical_score(el, len(s))))
                    if len(candidates) > 500:
                        break
            if len(candidates) > 500:
                break
    candidates.sort(key=lambda c: c[3])
    return candidates[:limit]


def list_all_activities(models: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in models:
        for xf in iter_xaml_files(model):
            for el, _ in iter_elements(xf):
                name = local_name(el.tag)
                # Skip trivial wrappers
                if "." in name or name in {"Activity", "Variable", "Property",
                                            "Members", "OutArgument", "InArgument",
                                            "InOutArgument", "Dictionary", "List",
                                            "AssemblyReference", "String", "Boolean",
                                            "Int32", "Double", "Point", "Size",
                                            "PointCollection", "Reference"}:
                    continue
                counts[name] = counts.get(name, 0) + 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description="On-demand activity example lookup")
    ap.add_argument("--activity", help="activity local-name (e.g. LogMessage, TryCatch, NApplicationCard)")
    ap.add_argument("--variant", type=int, default=1,
                    help="which ranked variant to show (1=best)")
    ap.add_argument("--model", help="override: use only this reference project path")
    ap.add_argument("--list", action="store_true",
                    help="dump all distinct activities found in reference models")
    args = ap.parse_args()

    models = read_models(args.model)

    if args.list:
        counts = list_all_activities(models)
        print(f"# Activities found in {len(models)} reference model(s)\n")
        for name in sorted(counts, key=lambda k: (-counts[k], k)):
            print(f"  {name}  ({counts[name]}x)")
        return 0

    if not args.activity:
        ap.print_help()
        return 2

    examples = find_examples(models, args.activity, limit=5)
    if not examples:
        print(f"No '{args.activity}' activity found in reference model(s). "
              f"Add an example to the model first, then retry.")
        return 1

    idx = max(1, args.variant) - 1
    if idx >= len(examples):
        print(f"Only {len(examples)} variant(s) found; --variant {args.variant} out of range.")
        return 1

    path, line, snippet, _ = examples[idx]
    origin_line = f":L.{line}" if line else ""
    print(f"# Example of <{args.activity}>")
    print(f"# Origin: {path}{origin_line}")
    print(f"# Ranked variant: {idx + 1} of {len(examples)} available")
    print()
    print(snippet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
