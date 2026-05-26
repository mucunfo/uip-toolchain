"""Quick CLI for querying the activity schema.

Use cases:
- LLM agent precisa saber args de uma activity antes de emitir XAML.
- Lookup de FQN ou local name → mostra args, OverloadGroups, defaults.
- List activities por package.
- Search por palavra-chave em FQN.

Examples:
    python -m scripts.activities_meta.lookup --activity WriteRange
    python -m scripts.activities_meta.lookup --activity "UiPath.Excel.Activities.WriteRange"
    python -m scripts.activities_meta.lookup --search ReadRange --json
    python -m scripts.activities_meta.lookup --list-packages
    python -m scripts.activities_meta.lookup --package uipath.mail.activities
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure schema loader resolves relative to .uipath-rules root
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.rule_engine.heuristics.activity_meta import get_schema  # noqa: E402


def _format_arg(a, label: str | None = None) -> str:
    flags = []
    if a.required:
        flags.append("REQUIRED")
    if a.overload_group:
        flags.append(f"group={a.overload_group}")
    if not a.is_argument:
        flags.append("plain")
    flag_str = f" [{', '.join(flags)}]" if flags else ""
    type_short = (a.type or "?").replace("System.", "")
    default_str = f" = {a.default!r}" if a.default not in (None, "") else ""
    label_str = f"  // {label}" if label else ""
    return f"  {a.direction:5} {a.name:30} : {type_short}{default_str}{flag_str}{label_str}"


def cmd_activity(name: str, as_json: bool) -> int:
    s = get_schema()
    # Match by FQN exact, then by local name (last segment).
    cand = s.by_fqn(name)
    matches = []
    if cand is not None:
        matches = [cand]
    else:
        for fqn, ad in s._by_fqn.items():
            local = fqn.rsplit(".", 1)[-1].split("`")[0]
            if local == name:
                matches.append(ad)
    if not matches:
        print(f"No match for: {name}", file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps([_to_dict(m) for m in matches], indent=2, ensure_ascii=False))
        return 0
    for m in matches:
        print(f"\n=== {m.fqn} ({m.kind}) ===")
        print(f"package: {m.pkg}")
        print(f"xmlns:   {m.xmlns}")
        if m.category:
            print(f"category: {m.category}")
        print("args:")
        for a in m.args:
            print(_format_arg(a, a.label))
    return 0


def cmd_search(query: str, as_json: bool) -> int:
    s = get_schema()
    q = query.lower()
    hits = [ad for fqn, ad in s._by_fqn.items() if q in fqn.lower()]
    if not hits:
        print(f"No FQN contains: {query}", file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps([
            {"fqn": h.fqn, "kind": h.kind, "pkg": h.pkg, "args": len(h.args)}
            for h in hits
        ], indent=2, ensure_ascii=False))
        return 0
    for h in hits[:50]:
        print(f"  [{h.kind:10}] {h.fqn}  ({len(h.args)} args, pkg={h.pkg})")
    if len(hits) > 50:
        print(f"  ... +{len(hits)-50} more (use --json or narrow search)")
    return 0


def cmd_list_packages(as_json: bool) -> int:
    s = get_schema()
    counts: dict[str, int] = {}
    for ad in s._by_fqn.values():
        counts[ad.pkg] = counts.get(ad.pkg, 0) + 1
    if as_json:
        print(json.dumps(counts, indent=2, ensure_ascii=False))
        return 0
    for pkg, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:5}  {pkg}")
    return 0


def cmd_package(pkg: str, as_json: bool) -> int:
    s = get_schema()
    hits = [ad for ad in s._by_fqn.values() if ad.pkg == pkg]
    if not hits:
        print(f"No entries for package: {pkg}", file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps([{"fqn": h.fqn, "kind": h.kind, "args": len(h.args)} for h in hits], indent=2, ensure_ascii=False))
        return 0
    for h in sorted(hits, key=lambda x: x.fqn):
        print(f"  [{h.kind:10}] {h.fqn}  ({len(h.args)} args)")
    return 0


def _to_dict(ad) -> dict:
    return {
        "fqn": ad.fqn,
        "kind": ad.kind,
        "pkg": ad.pkg,
        "xmlns": ad.xmlns,
        "category": ad.category,
        "args": [
            {
                "name": a.name,
                "label": a.label,
                "type": a.type,
                "direction": a.direction,
                "is_argument": a.is_argument,
                "required": a.required,
                "overload_group": a.overload_group,
                "default": a.default,
            }
            for a in ad.args
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Query UiPath activity schema (assets/activities/activities-compact.json).")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--activity", help="Lookup activity by FQN or local name (e.g. WriteRange)")
    g.add_argument("--search", help="Search FQNs containing this substring")
    g.add_argument("--list-packages", action="store_true", help="List packages with entry counts")
    g.add_argument("--package", help="List entries in this package (e.g. uipath.excel.activities)")
    p.add_argument("--json", action="store_true", help="Output JSON instead of human-readable")
    args = p.parse_args()

    if args.activity:
        return cmd_activity(args.activity, args.json)
    if args.search:
        return cmd_search(args.search, args.json)
    if args.list_packages:
        return cmd_list_packages(args.json)
    if args.package:
        return cmd_package(args.package, args.json)
    return 1


if __name__ == "__main__":
    sys.exit(main())
