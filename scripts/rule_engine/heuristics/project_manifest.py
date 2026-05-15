"""Heuristics for project.json manifest hygiene (J-8 stale fileInfoCollection).

Studio publish FALHA quando `project.json::designOptions.fileInfoCollection`
lista test cases (`fileName`) que não existem mais no disco. Studio analyze
(uipcli analyze) NÃO detecta — só publish quebra.

Causa típica: TC deletado em refactor mas manifest project.json não atualizado.
Engine atua como guardrail antes do publish.

Genérico p/ outros fileInfo-style arrays no project.json (e.g. `webServices`),
parametrizado via `key_path` + `filename_field`.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.rule_engine._types import Finding


def _load(fc):
    if not str(fc.path).endswith("project.json"):
        return None
    try:
        return json.loads(fc.content)
    except Exception:
        return None


def _finding(rule, fc, msg, mech=None):
    return Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1, message=msg,
        fix_mechanical=mech if mech is not None else (rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )


def _dotted_get(data, path):
    """Resolve dotted path, e.g. 'designOptions.fileInfoCollection'."""
    if not path:
        return None
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def detect_j8_stale_fileinfo_entries(rule, fc, pc):
    """Emit Finding por cada entry em `key_path` cujo `filename_field`
    referencia arquivo inexistente no disco (resolvido relativo a pc.root).

    Params (rule.detect.params):
      key_path: dot-path do array (default: 'designOptions.fileInfoCollection')
      filename_field: nome do campo dentro de cada entry (default: 'fileName')
    """
    data = _load(fc)
    if data is None:
        return []
    params = rule.detect.get("params", {}) or {}
    key_path = params.get("key_path", "designOptions.fileInfoCollection")
    filename_field = params.get("filename_field", "fileName")

    arr = _dotted_get(data, key_path)
    if not isinstance(arr, list) or not arr:
        return []

    root = pc.root if pc is not None else fc.path.parent
    findings = []
    for entry in arr:
        if not isinstance(entry, dict):
            continue
        fname = entry.get(filename_field)
        if not fname or not isinstance(fname, str):
            continue
        # Normalize backslashes (Windows) → posix-ish for Path resolution.
        rel = fname.replace("\\", "/")
        target = (Path(root) / rel).resolve()
        if target.exists():
            continue
        msg = (
            f"{rule.title}: manifest references missing file: {fname} "
            f"(key={key_path})"
        )
        findings.append(_finding(rule, fc, msg))
    return findings
