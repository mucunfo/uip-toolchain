#!/usr/bin/env python3
"""PostToolUse hook — runs uip_engine.cli review after Edit/Write on .xaml files.

Silent when no violations. On violations, writes a compact report to stdout so
Claude sees it and must fix before continuing.

Hook input (stdin, JSON):
    { "tool_name": "Edit", "tool_input": { "file_path": "...", ... }, ... }
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safe_encoding import enforce_utf8  # noqa: E402

enforce_utf8()

REPO_ROOT = Path(__file__).resolve().parent.parent
ENGINE_PKG = REPO_ROOT / "src" / "uip_engine"


def _find_project_root(file_path: Path) -> Path | None:
    for candidate in [file_path.parent, *file_path.parents]:
        if (candidate / "project.json").exists():
            return candidate
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in {"Edit", "Write", "MultiEdit"}:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path_str = tool_input.get("file_path") or ""
    if not file_path_str.lower().endswith(".xaml"):
        return 0

    if not ENGINE_PKG.exists():
        return 0

    file_path = Path(file_path_str).resolve()
    project_root = _find_project_root(file_path)
    if project_root is None:
        return 0

    # Hook = feedback rápido pós-edit (não pre-publish gate). Desabilita gates
    # externos (uipcli analyze/nuget/pack — 180+300+600s) que estouram qualquer
    # timeout do hook. Só detectores python (~instantâneo num XAML; ~60s em
    # projeto grande). Pre-publish completo = `uip <project>` separado.
    env = {**os.environ, "UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES": "1"}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "uip_engine.cli", "review",
             str(project_root), "--format", "json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT.parent),
            env=env,
            timeout=300,
        )
    except Exception as e:
        print(f"[uipath-hook] uip_engine failed to run: {e}", file=sys.stderr)
        return 0

    try:
        data = json.loads(proc.stdout)
    except Exception:
        return 0

    file_findings = [
        f for f in data.get("findings", [])
        if Path(f["file"]).resolve() == file_path
        and not f.get("suppressed", False)
        and f["severity"] in ("ERROR", "HALT", "WARN")
    ]
    if not file_findings:
        return 0

    def _first_line(s: str | None) -> str | None:
        if not s:
            return None
        for line in s.splitlines():
            t = line.strip()
            if t:
                return t
        return None

    print("[uipath-hook] uip_engine findings:")
    for f in file_findings:
        sev = f["severity"]
        rid = f["rule_id"]
        line = f.get("line", 0)
        msg = f.get("message", "")
        print(f"  [{sev}] [{rid}] linha {line}: {msg}")
        why = _first_line(f.get("description"))
        prose = _first_line((f.get("fix") or {}).get("prose"))
        if why:
            print(f"      why: {why}")
        if prose and prose != why:
            print(f"      fix: {prose}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
