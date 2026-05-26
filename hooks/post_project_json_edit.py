#!/usr/bin/env python3
"""PostToolUse hook — after Edit/Write on project.json, run
uip_engine.cli review (J-/D-* rules naturalmente filtradas por applies_to).

Hook input (stdin, JSON):
    { "tool_name": "Edit", "tool_input": { "file_path": "...project.json" }, ... }
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safe_encoding import enforce_utf8  # noqa: E402

enforce_utf8()

REPO_ROOT = Path(__file__).resolve().parent.parent
ENGINE_PKG = REPO_ROOT / "src" / "uip_engine"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path_str = tool_input.get("file_path") or ""
    if not file_path_str.lower().endswith("project.json"):
        return 0

    p = Path(file_path_str).resolve()
    if not p.exists():
        return 0
    if not ENGINE_PKG.exists():
        return 0

    project_root = p.parent

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "uip_engine.cli", "review",
             str(project_root), "--format", "json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT.parent),
            timeout=180,
        )
    except Exception as e:
        print(f"[uipath-hook] uip_engine failed: {e}", file=sys.stderr)
        return 0

    try:
        data = json.loads(proc.stdout)
    except Exception:
        return 0

    pj_findings = [
        f for f in data.get("findings", [])
        if str(f["file"]).lower().endswith("project.json")
        and not f.get("suppressed", False)
        and f["severity"] in ("ERROR", "HALT", "WARN")
    ]
    if not pj_findings:
        return 0

    def _first_line(s: str | None) -> str | None:
        if not s:
            return None
        for line in s.splitlines():
            t = line.strip()
            if t:
                return t
        return None

    print("[uipath-hook] uip_engine project.json findings:")
    for f in pj_findings:
        sev = f["severity"]
        rid = f["rule_id"]
        msg = f.get("message", "")
        print(f"  [{sev}] [{rid}] {msg}")
        why = _first_line(f.get("description"))
        prose = _first_line((f.get("fix") or {}).get("prose"))
        if why:
            print(f"      why: {why}")
        if prose and prose != why:
            print(f"      fix: {prose}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
