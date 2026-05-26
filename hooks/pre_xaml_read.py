#!/usr/bin/env python3
"""PreToolUse hook — when Claude is about to Read a .xaml file:

1. Always: emit schema refs for activities used (compact list of args/required/
   OverloadGroups for each unique qualified activity).
2. If file is large (>500 lines): also run `xaml_summary.py`.

Hook does NOT block the Read — just adds context.

Hook input (stdin, JSON):
    { "tool_name": "Read", "tool_input": { "file_path": "..." }, ... }
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safe_encoding import enforce_utf8  # noqa: E402

enforce_utf8()

BIG_FILE_THRESHOLD_LINES = 500
MAX_SCHEMA_REFS = 12  # cap to avoid blowing context

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_RULES_DIR = _SCRIPTS_DIR.parent

# Allow importing rule_engine helpers without requiring engine install.
if str(_RULES_DIR) not in sys.path:
    sys.path.insert(0, str(_RULES_DIR))


def _emit_schema_refs(xaml_path: Path) -> str | None:
    """Build a compact schema digest for activities used in this XAML.

    Returns formatted string or None if no canonical UiPath activities found
    or schema unavailable.
    """
    try:
        from scripts.rule_engine.heuristics.activity_meta import (  # noqa: E402
            get_schema, parse_activities,
        )
    except Exception:
        return None

    try:
        content = xaml_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    try:
        _, refs = parse_activities(content)
    except Exception:
        return None
    if not refs:
        return None

    try:
        schema = get_schema()
    except Exception:
        return None

    # Unique activities by (xmlns, local_name), only canonical UiPath xmlns
    seen: dict[tuple[str, str], object] = {}
    for r in refs:
        if not schema.is_canonical_xmlns(r.xmlns):
            continue
        key = (r.xmlns, r.local_name)
        if key in seen:
            continue
        cands = schema.candidates(r.xmlns, r.local_name)
        if not cands:
            continue
        # If multiple candidates, pick the first Activity-kind
        chosen = next((c for c in cands if c.kind == "Activity"), cands[0])
        seen[key] = chosen
        if len(seen) >= MAX_SCHEMA_REFS:
            break

    if not seen:
        return None

    lines = []
    for (xmlns, local), ad in seen.items():
        req = [a for a in ad.args if a.required]
        groups: dict[str, list[str]] = {}
        plain_req = []
        for a in req:
            if a.overload_group:
                groups.setdefault(a.overload_group, []).append(a.name)
            else:
                plain_req.append(a.name)
        head = f"  <{local}> [{ad.kind}]"
        parts = []
        if plain_req:
            parts.append("required=" + ",".join(plain_req))
        if groups:
            grp_str = " | ".join(
                f"{g}=[{','.join(names)}]" for g, names in groups.items()
            )
            parts.append("groups: " + grp_str)
        if not parts:
            parts.append("(no required args)")
        lines.append(f"{head}  {' ; '.join(parts)}")

    extra = ""
    if len(refs) > len(seen) and len(seen) >= MAX_SCHEMA_REFS:
        extra = f"  ... (+ more activities; capped at {MAX_SCHEMA_REFS})"
    out = "[uipath-hook] activities used (schema-derived):\n" + "\n".join(lines)
    if extra:
        out += "\n" + extra
    out += "\n  Use 'python -m scripts.activities_meta.lookup --activity NAME' for full args."
    return out


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Read":
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path.lower().endswith(".xaml"):
        return 0

    # If Read already uses offset+limit, user is being targeted. Skip.
    if tool_input.get("offset") or tool_input.get("limit"):
        return 0

    p = Path(file_path)
    if not p.exists():
        return 0
    try:
        line_count = sum(1 for _ in p.open("r", encoding="utf-8", errors="replace"))
    except Exception:
        return 0

    # Schema digest for any size XAML (cheap; capped).
    schema_block = _emit_schema_refs(p)
    if schema_block:
        print(schema_block)
        print()

    if line_count < BIG_FILE_THRESHOLD_LINES:
        return 0

    scripts_dir = Path(__file__).resolve().parent.parent
    summary_script = scripts_dir / "xaml_summary.py"
    find_script = scripts_dir / "xaml_find.py"
    if not summary_script.exists():
        return 0

    # Run summary, capture output
    try:
        proc = subprocess.run(
            [sys.executable, str(summary_script), str(p)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20,
        )
        summary = proc.stdout.strip()
    except Exception as e:
        print(f"[uipath-hook] xaml_summary failed: {e}", file=sys.stderr)
        return 0

    if not summary:
        return 0

    print(f"[uipath-hook] '{p.name}' has {line_count} lines "
          f"(~{line_count * 25} tokens). Auto-generated summary below — "
          f"Read will still proceed. If summary answers your question, "
          f"consider offset+limit or cancel Read. Use "
          f"'python \"{find_script}\" \"{p}\" --activity NAME' for targeted lookup.")
    print()
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
