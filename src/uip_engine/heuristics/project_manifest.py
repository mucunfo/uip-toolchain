"""Heuristics for project.json manifest hygiene (J-8 stale fileInfoCollection).

Studio publish FALHA quando `project.json::designOptions.fileInfoCollection`
lista test cases (`fileName`) que não existem mais no disco. Official analyze
NÃO detecta — só publish quebra.

Causa típica: TC deletado em refactor mas manifest project.json não atualizado.
Engine atua como guardrail antes do publish.

Genérico p/ outros fileInfo-style arrays no project.json (e.g. `webServices`),
parametrizado via `key_path` + `filename_field`.
"""
from __future__ import annotations

import json
from pathlib import Path

from uip_engine._types import Finding
from uip_engine.publish_readiness import (
    project_uiproj_needs_sync,
    stale_pack_incompatible_assembly_references_for_text,
)


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


# ENV-1 Studio compat flags — Sicoob policy (CLAUDE.md "Pin enforcement").
#
# Empresa Studio = 23.10.x (não muda). Dev Studio = 25.x/26.x. project.json
# precisa de 3 flags pra Studio 23.10 resolver transitive deps de packs 25.x:
#
#   runtimeOptions.mustRestoreAllDependencies = true
#       → força Studio restore TODOS transitive assemblies (System.Collections,
#         System.Net.Primitives, etc.). Default false = lazy load → BC30652
#         (Dictionary type missing) + BC31424 (NetworkCredential type forward
#         fail) em Studio 23.10.
#
#   designOptions.modernBehavior = true
#       → força o projeto a abrir no Modern Design Experience. Em Studio 23.10,
#         esta é a chave project-level do toggle Project Settings > General >
#         Modern Design Experience; o projeto sobrescreve o default global.
#
#   designOptions.libraryOptions.includeOriginalXaml = false
#       → não embute XAML source dentro de packs gerados. Sicoob default.
#
# Verificado contra projeto que ABRE em Studio 23.10 (solicitacao-acessos-
# sisbr-arquivo-xml-performer): 3 flags presentes + corretos. Projeto que
# QUEBRA em Studio 23.10 (contestacao-de-compras-ajuste-na-reserva-de-fraude-
# performer): mustRestoreAllDependencies=false + modernBehavior missing.
#
# Engine sempre exige valores Sicoob (env: empresa Studio 23.10 immutable).

_ENV1_REQUIRED = {
    "runtimeOptions.mustRestoreAllDependencies": True,
    "designOptions.modernBehavior": True,
    "designOptions.libraryOptions.includeOriginalXaml": False,
}


def detect_env1_studio_compat(rule, fc, pc):
    """Emit 1 Finding quando project.json falta/diverge das flags
    Sicoob Studio-compat. Single finding com fix_mechanical set_keys
    contendo TODOS keys divergentes — atomic patch.

    Idempotente: emite nada se todos keys já corretos.
    """
    data = _load(fc)
    if data is None:
        return []

    diverging: dict[str, object] = {}
    for dotted, desired in _ENV1_REQUIRED.items():
        actual = _dotted_get(data, dotted)
        if actual != desired:
            diverging[dotted] = desired

    if not diverging:
        return []

    # Build human-readable summary
    summary_parts = []
    for dotted, desired in diverging.items():
        actual = _dotted_get(data, dotted)
        if actual is None:
            summary_parts.append(f"{dotted}=<missing> (esperado: {desired})")
        else:
            summary_parts.append(f"{dotted}={actual} (esperado: {desired})")
    msg = (
        f"project.json Studio-compat flags divergentes "
        f"(Sicoob policy: Studio 23.10 compatibility): "
        f"{'; '.join(summary_parts)}"
    )

    return [
        Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=1,
            message=msg,
            fix_mechanical={
                "type": "project_manifest_set_keys",
                "keys": diverging,
            },
            fix_prose=(
                "Definir em project.json:\n"
                + "\n".join(
                    f"  {dotted} = {desired!r}"
                    for dotted, desired in diverging.items()
                )
                + "\nEsses flags garantem Studio 23.10 da empresa abrir o "
                "projeto sem BC30652 / BC31424 (transitive assembly resolution)."
            ),
        )
    ]


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


def detect_j9_project_uiproj_synced(rule, fc, pc):
    """Emit when official `uip rpa pack` descriptor is missing or stale."""
    data = _load(fc)
    if data is None:
        return []
    root = pc.root if pc is not None else fc.path.parent
    try:
        needs_sync, reason = project_uiproj_needs_sync(Path(root))
    except ValueError as exc:
        return [_finding(rule, fc, f"{rule.title}: {exc}")]
    if not needs_sync:
        return []
    return [_finding(
        rule,
        fc,
        f"{rule.title}: {reason}",
        mech={"type": "sync_project_uiproj"},
    )]


def detect_w40_pack_incompatible_stale_assembly_refs(rule, fc, pc):
    """Emit stale AssemblyReference refs that official headless pack rejects."""
    if pc is None:
        return []
    if not str(fc.path).endswith(".xaml"):
        return []
    stale = stale_pack_incompatible_assembly_references_for_text(
        Path(pc.root),
        fc.active_content,
    )
    findings: list[Finding] = []
    for assembly in stale:
        line = 1
        needle = f"<AssemblyReference>{assembly}</AssemblyReference>"
        idx = fc.content.find(needle)
        if idx >= 0:
            line = fc.content[:idx].count("\n") + 1
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=line,
            message=f"{rule.title}: {assembly}",
            fix_mechanical={"type": "strip_assembly_reference", "name": assembly},
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
