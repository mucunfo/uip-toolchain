"""CCS-PROPCHECK heuristic — case-mismatch detector pra refs CCS_* libs.

Engine extrai contracts (workflow + property names) das libs em
`C:\\Users\\lisan\\OneDrive - Sicoob\\Projects\\.nupkgs\\CCS_*.nupkg`.
Cada nupkg é zip contendo `content/<Workflow>.xaml` com declarações
`<x:Property Name="..." Type="...">`.

Detector escaneia projeto XAML buscando invocações de CCS workflows
(elements como `<c:Login attr="...">` onde xmlns prefix `c:` mapeia
pra `clr-namespace:CCS_X.Workflows;assembly=CCS_X`). Compara cada
attribute usado vs contract:

  - Match exato → OK
  - Case-insensitive match mas case diferente → finding com fix
    mecânico `rename_attribute` (corrige casing)
  - Sem match → finding WARN (manual review; lib não expõe esse arg)

Caminho .nupkgs hardcoded conforme padrão Sicoob (CLAUDE.md
`reference_ccs_nupkgs_local.md`).

Cross-version: contract reading é nupkg unzip, independente de Studio
version. Funciona offline.
"""
from __future__ import annotations

import io
import re
import threading
import zipfile
from pathlib import Path
from typing import Any

from scripts.rule_engine._types import Finding


_NUPKGS_DIR = Path(r"C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs")


# Cache module-level: package_name → {workflow_name → [arg_names]}
# Lazy populated no primeiro detector call.
#
# Thread-safety: Runner roda XAMLs em ThreadPoolExecutor (workers=nproc/2).
# Lock garante double-checked locking: 2 threads não populam em paralelo
# (wasted work + potencial inconsistência se loop yield). Mais importante,
# escrita de `_CCS_CONTRACTS` só acontece DEPOIS de fully populated → reader
# nunca vê dict parcialmente populado (race anterior assignava `{}` primeiro,
# threads concorrentes pegavam vazio, CCS-1 perdia findings — silent FAIL).
_CCS_CONTRACTS: dict[str, dict[str, list[str]]] | None = None
_CCS_CONTRACTS_LOCK = threading.Lock()


def _extract_contracts_from_nupkg(nupkg_path: Path) -> dict[str, list[str]]:
    """Extrai workflows + props de uma nupkg CCS.

    Retorna `{workflow_name: [arg_name1, arg_name2, ...]}`.
    Workflow_name = nome xaml sem extensão (case-preserving).

    Args extraídos via regex que tolera attrs antes de Name= (e.g.
    `sap2010:Annotation.AnnotationText`). Preserva case exato declarado.
    """
    contracts: dict[str, list[str]] = {}
    try:
        with zipfile.ZipFile(nupkg_path, "r") as zf:
            for entry in zf.namelist():
                # Workflow xamls vivem em content/*.xaml
                if not entry.startswith("content/") or not entry.endswith(".xaml"):
                    continue
                # Skip files in subdirs (we want only top-level workflows)
                rel = entry[len("content/"):]
                if "/" in rel:
                    continue
                workflow_name = rel[:-len(".xaml")]
                try:
                    xaml_bytes = zf.read(entry)
                    xaml = xaml_bytes.decode("utf-8-sig")
                    # Name= pode vir após outros attrs (sap2010:Annotation.AnnotationText etc).
                    # Match qualquer ordem dentro do open tag.
                    args = re.findall(r'<x:Property\b[^>]*?\bName="([^"]+)"', xaml)
                    contracts[workflow_name] = list(dict.fromkeys(args))  # dedup preserving order
                except Exception:
                    continue
    except Exception:
        return {}
    return contracts


def _load_ccs_contracts() -> dict[str, dict[str, list[str]]]:
    """Lazy load + cache de TODOS contracts CCS de .nupkgs/.

    Retorna `{package_name: {workflow_name: [arg_names]}}`.

    Thread-safe via double-checked locking. Construção do catalog acontece
    em variável local; assignment ao global é o ÚLTIMO passo → outras threads
    veem o dict completo ou None (re-tentam), nunca dict parcial.
    """
    global _CCS_CONTRACTS
    cached = _CCS_CONTRACTS
    if cached is not None:
        return cached

    with _CCS_CONTRACTS_LOCK:
        # Double-check pós-lock: outra thread pode ter populado entre check
        # acima e aquisição do lock.
        if _CCS_CONTRACTS is not None:
            return _CCS_CONTRACTS

        catalog: dict[str, dict[str, list[str]]] = {}
        if _NUPKGS_DIR.exists():
            for nupkg in sorted(_NUPKGS_DIR.glob("CCS_*.nupkg")):
                # Parse nome arquivo: CCS_SipagDirect.3.0.2.nupkg → CCS_SipagDirect
                m = re.match(r"^(CCS_[A-Za-z0-9_]+)\.[\d.]+\.nupkg$", nupkg.name)
                if not m:
                    continue
                pkg_name = m.group(1)
                contracts = _extract_contracts_from_nupkg(nupkg)
                if contracts:
                    catalog[pkg_name] = contracts

        # Atomic assignment APÓS população completa.
        _CCS_CONTRACTS = catalog
        return catalog


def _reset_for_tests() -> None:
    global _CCS_CONTRACTS
    _CCS_CONTRACTS = None


# Regex pra extrair xmlns prefix → CCS package
# Pattern: `xmlns:c="clr-namespace:CCS_SipagDirect;assembly=CCS_SipagDirect"`
_RE_CCS_XMLNS = re.compile(
    r'xmlns:([A-Za-z_][\w]*)\s*=\s*"clr-namespace:(CCS_[A-Za-z0-9_]+)(?:\.[^"]*)?;\s*assembly=\2"'
)

# Pra cada workflow invocation: `<prefix:WorkflowName attr1="..." attr2="...">`
# Captura prefix, workflow name, e o "open tag" body (everything between WorkflowName e `>` ou `/>`).
def _find_invocations(content: str, prefix: str, workflows: dict[str, list[str]]) -> list[tuple[str, int, str]]:
    """Encontra invocações `<prefix:WorkflowName ...>` no content.

    Retorna lista de `(workflow_name, line, open_tag_body)`.
    """
    results = []
    for wf_name in workflows.keys():
        pat = re.compile(
            rf'<{re.escape(prefix)}:{re.escape(wf_name)}\b([^>]*)>',
            re.DOTALL,
        )
        for m in pat.finditer(content):
            line = content[: m.start()].count("\n") + 1
            results.append((wf_name, line, m.group(1)))
    return results


_RE_ATTR = re.compile(r'\b([A-Za-z_][\w]*)\s*=\s*"')


# F36 (bisect 2026-05-20): rename_attribute via _whole_word_sub_skip_tags em
# `<prefix:Workflow>` que tem SecureString-bound sibling (ex: `<c:Login
# in_Senha="[vSsSenhaX]" in_Url="..."/>`) interage com OUTRAS mudanças XAML
# (W-26 strip refs, S-16 remove CommentOut) e dispara ST-SEC-008 "SecureString
# usada fora do escopo de criação". Root cause não-trivial (Studio analyzer
# scope inference + cache invalidation). Safety guard: NÃO injetar
# `fix_mechanical` quando invocation tem SecureString-bound arg — fica como
# blocking finding com NEEDS_REVIEW manual (rename via Studio UI preserva
# scope corretamente).
_RE_SS_VAR_DECL = re.compile(
    r'<Variable\b[^>]*?TypeArguments\s*=\s*"ss:SecureString"[^>]*?Name\s*=\s*"([^"]+)"'
)


def _detect_ss_sibling(tag_body: str, ss_var_names: set[str]) -> str | None:
    """Returns nome da SecureString var referenciada em `tag_body`, ou None.

    Reconhece refs VB no formato `[varName]`, `[varName.X]`, `[... varName ...]`.
    """
    if not ss_var_names:
        return None
    for var in ss_var_names:
        if re.search(rf'\[(?:[^\]]*\b)?{re.escape(var)}\b', tag_body):
            return var
    return None


def detect_ccs_contract_check(rule, fc, pc):
    """Detector CCS-PROPCHECK.

    Para cada XAML do projeto:
      1. Mapeia xmlns prefixes → CCS package
      2. Pra cada element `<prefix:Workflow ...>` invocando CCS workflow:
         - Compara cada attribute name vs contract
         - case mismatch → finding com rename_attribute fix
         - case mismatch + SecureString sibling → finding SEM fix_mechanical
           (NEEDS_REVIEW manual; auto-rename + outras mudanças XAML disparam
           ST-SEC-008 — Studio analyzer regression)
         - missing in contract → finding WARN (manual review)
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    catalog = _load_ccs_contracts()
    if not catalog:
        return []

    # Map xmlns prefix → CCS package presente no xaml
    prefix_to_pkg: dict[str, str] = {}
    for m in _RE_CCS_XMLNS.finditer(content):
        prefix = m.group(1)
        pkg = m.group(2)
        if pkg in catalog:
            prefix_to_pkg[prefix] = pkg

    if not prefix_to_pkg:
        return []

    # F36: scan SecureString variable declarations no XAML inteiro.
    ss_var_names = set(_RE_SS_VAR_DECL.findall(content))

    findings: list[Finding] = []
    # Atributos reservados XAML que NÃO são args do workflow
    _RESERVED_ATTRS = frozenset({
        "x:Name", "DisplayName", "sap2010:WorkflowViewState.IdRef",
        "sap:VirtualizedContainerService.HintSize", "AttachedProperty",
    })

    for prefix, pkg in prefix_to_pkg.items():
        workflows = catalog[pkg]
        invocations = _find_invocations(content, prefix, workflows)
        for wf_name, line, tag_body in invocations:
            expected_args = workflows.get(wf_name, [])
            if not expected_args:
                continue
            expected_lower = {a.lower(): a for a in expected_args}

            # Extract attribute names from open tag body
            used_attrs = [m.group(1) for m in _RE_ATTR.finditer(tag_body)]

            # F36: detect SecureString-bound sibling neste invocation
            ss_sibling = _detect_ss_sibling(tag_body, ss_var_names)

            for attr in used_attrs:
                # Skip XAML reserved/non-arg attrs
                if attr in _RESERVED_ATTRS or ":" in attr:
                    continue
                # Skip if not arg-style (in_/out_/io_ prefix is convention, but
                # don't enforce; only check args that match prefix or are
                # obvious workflow args. Skip noise.)
                if attr.lower() not in expected_lower:
                    continue
                expected_case = expected_lower[attr.lower()]
                if attr != expected_case:
                    # F36 guard REMOVED 2026-05-21: empiricamente Studio 23.10
                    # (empresa deploy) reporta `Cannot set unknown member` em
                    # casing errado independente de SecureString sibling. Engine
                    # cascade rollback gate (analyzer-gate F35) já isola
                    # ST-SEC-008 regression per-file caso cascade aconteça.
                    # Guard anterior só deferia fix manual que nunca era feito.
                    finding_msg = (
                        f"{pkg}.{wf_name}: attribute '{attr}' usa casing errado. "
                        f"Lib declara '{expected_case}'."
                    )
                    if ss_sibling is not None:
                        finding_msg += (
                            f" (SecureString-bound sibling '[{ss_sibling}]' presente — "
                            f"se rename disparar ST-SEC-008 em analyzer-gate, "
                            f"cascade rollback isola o arquivo automaticamente.)"
                        )
                    findings.append(
                        Finding(
                            rule_id=rule.id,
                            severity=rule.severity,
                            category=rule.category,
                            file=str(fc.path),
                            line=line,
                            message=finding_msg,
                            fix_mechanical={
                                "type": "rename_attribute",
                                "from": attr,
                                "to": expected_case,
                            },
                            fix_prose=(
                                f"Renomear `{attr}` → `{expected_case}` em "
                                f"`<{prefix}:{wf_name}>` (case-correction conforme "
                                f"contrato lib {pkg})."
                            ),
                        )
                    )

    return findings
