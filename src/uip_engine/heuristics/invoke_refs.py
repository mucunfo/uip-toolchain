"""S-19 heuristic — Production XAML invoca workflow listado em ignoredFiles.

Background:
  Official analyzer só valida XAMLs production e não detecta
  `<ui:InvokeWorkflowFile WorkflowFileName="...">` referenciando arquivo
  que está em `project.json::designOptions.processOptions.ignoredFiles`.
  Resultado: review "passa", mas Studio Publish quebra:

    The following invoked workflows are missing: <file>
    Called from: <caller>

  Cenário típico Sicoob: mock condicional (`in_BlUsarMockSisbrWeb=True`)
  invocado via static reference; mock listado em `ignoredFiles` para reduzir
  tamanho do package. Studio publish valida static reference, ignora
  conditional gating runtime.

Detector strategy:
  1. Carregar `ignoredFiles` de project.json (set de paths normalizados).
  2. Para cada XAML production (Tests/ excluído via applies_to.exclude),
     achar `<ui:InvokeWorkflowFile ... WorkflowFileName="X" ...>` (ou attr
     reversed). WorkflowFileName pode ter prefixo path
     (``Subfolder\\File.xaml`` ou ``Subfolder/File.xaml``) e usar ``\\``
     ou ``/`` como separator.
  3. Normalizar (lowercase + forward slashes + strip leading `./`) e checar
     se está no set ignoredFiles.
  4. Skip expressions (`[expr]` ou `{Binding}`) — não dá pra resolver
     estático.
"""
from __future__ import annotations

import re

from uip_engine._types import Finding


# Casa InvokeWorkflowFile com DisplayName antes ou depois de WorkflowFileName.
# Captura WorkflowFileName em group 1.
_RE_INVOKE_WFF = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*?WorkflowFileName="([^"]+)"',
    re.DOTALL,
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _normalize(path: str) -> str:
    """Canonical lowercase forward-slash path.

    `Subfolder\\Mock.xaml`, `Subfolder/Mock.xaml`, `./Subfolder/Mock.xaml`
    todos viram `subfolder/mock.xaml`.
    """
    p = path.replace("\\", "/").strip().lstrip("./")
    # Strip leading `/` defensivo (paths em ignoredFiles geralmente relativos)
    while p.startswith("/"):
        p = p[1:]
    return p.lower()


def _ignored_files_set(pc) -> set[str]:
    """Extract ignoredFiles list normalized."""
    raw = (
        (pc.project_json.get("designOptions") or {})
        .get("processOptions", {})
        .get("ignoredFiles", [])
    )
    if not isinstance(raw, list):
        return set()
    return {_normalize(str(p)) for p in raw if p}


def detect_invoke_ignoredfile_ref(rule, fc, pc):
    if pc is None:
        return []
    if fc.path.suffix.lower() != ".xaml":
        return []

    ignored = _ignored_files_set(pc)
    if not ignored:
        return []  # projeto sem ignoredFiles — short-circuit

    findings: list[Finding] = []
    content = fc.active_content

    for m in _RE_INVOKE_WFF.finditer(content):
        wff = m.group(1)
        # Skip dynamic expressions: VB `[expr]` ou WPF `{Binding}`
        if wff.startswith("[") or wff.startswith("{"):
            continue
        norm = _normalize(wff)
        if norm in ignored:
            line = _line_for(content, m.start())
            findings.append(
                Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    category=rule.category,
                    file=str(fc.path),
                    line=line,
                    message=(
                        f"{rule.title}: WorkflowFileName='{wff}' está em "
                        f"project.json ignoredFiles. Studio Publish quebrará "
                        f"com 'invoked workflows are missing'."
                    ),
                    fix_prose=(rule.fix or {}).get("prose"),
                )
            )

    return findings
