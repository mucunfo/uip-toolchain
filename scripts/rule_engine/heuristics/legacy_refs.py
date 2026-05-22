"""ENV-2 heuristic — ENSURE legacy compat refs em XAML de projeto Windows.

CONTEXTO (correção factual da hipótese W-26 original, agora removida):

A hipótese anterior (W-26) presumia que `<AssemblyReference>mscorlib|System|
System.Core</AssemblyReference>` eram redundantes em .NET 6 (facades vazias
supersedidas por `System.Private.CoreLib`) e que Studio resolvia via
`mscorlib v4.0.0.0` forwarder gerando mismatch `BC31424`. ERRADO empiricamente.

Verificação:
  - Projeto que ABRE em Studio 23.10 (solicitacao-acessos-sisbr-arquivo-xml-
    performer): 69/69 XAMLs com `<AssemblyReference>mscorlib</AssemblyReference>`.
  - Projeto que QUEBRA em Studio 23.10 (contestacao-de-compras-ajuste-na-
    reserva-de-fraude-performer): 0/25 XAMLs com mscorlib.
  - Mesmo padrão `new System.Net.NetworkCredential(...)` e `scg:Dictionary`
    em ambos. Diff isolado: mscorlib + System + System.Core presença.

Realidade: Studio 23.10 USA `mscorlib` + `System` + `System.Core` como
forwarder bridge para resolver types .NET 6 declarados em refs modernos
(`System.Private.CoreLib`, `System.Net.Primitives v6`, etc.). Sem esses 3
refs legacy, Studio 23.10 não bridja a versão moderna → BC30652 + BC31424.

Activity Migrator GA do Studio 25.x strip esses refs (não precisa em deploy
Studio 25.x nativo). Mas deploy Sicoob = Studio 23.10 (imutável). Engine
deve garantir presença pra forward-compat.

Triplet correto pós-Migrator p/ deploy Studio 23.10:
  W-20  → strip xmlns:* Legacy (header) — OK, xmlns alias diferente
  ENV-2 → ENSURE <AssemblyReference> legacy compat (body)   ← este
  W-11g → insert System.Net.Primitives (body) — complementar

Conservadora: lista fixa {mscorlib, System, System.Core}. Outros refs
legacy (System.Configuration.Install, System.Data.Entity, WindowsBase,
System.Data.DataSetExtensions) ficam separados — alguns são WCF/EF6/WPF
specific.

NOTA HISTÓRICA: detector legado `detect_legacy_bcl_refs` (W-26) foi
removido. Tests `tests/test_w26_legacy_refs.py` substituídos por
`tests/test_env2_legacy_compat.py`.
"""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


# Refs legacy compat OBRIGATÓRIOS pra deploy Studio 23.10 resolver type
# forwarders pra .NET 6 modern refs. Inversão da blacklist W-26 anterior.
_LEGACY_REFS_REQUIRED: frozenset[str] = frozenset({
    "mscorlib",
    "System",
    "System.Core",
})

# W-5: WCF stack órfão pós-Migrator. Pacotes pinados Sicoob (D-1) não usam
# WCF em runtime; refs permanecem como herança template Legacy.
#
# NÃO incluir `System.ServiceModel` (base): W-11y baseline_refs inclui esse
# como ref cross-version → strip+add divergence infinita no fix loop.
# Mesmo padrão de W-26 carve-out (mscorlib/System/System.Core). Lista
# restrita a sub-assemblies WCF que NÃO estão no W-11y baseline.
_SERVICEMODEL_REFS_BLACKLIST: frozenset[str] = frozenset({
    "System.ServiceModel.Internals",
    "System.ServiceModel.Web",
})

_RE_REFS_BLOCK = re.compile(
    r"<TextExpression\.ReferencesForImplementation>(.*?)"
    r"</TextExpression\.ReferencesForImplementation>",
    re.DOTALL,
)
_RE_ASM_REF = re.compile(r"<AssemblyReference>([^<]+)</AssemblyReference>")


def detect_env2_ensure_legacy_refs(rule, fc, pc):
    """ENV-2: emite finding por cada legacy compat ref FALTANDO no bloco
    `<TextExpression.ReferencesForImplementation>`. Cada finding carrega
    `mechanical=insert_assembly_reference`.

    Studio 23.10 (deploy Sicoob imutável) precisa mscorlib + System +
    System.Core pra resolver type forwarders modernos. Activity Migrator
    de Studio 25.x strip esses refs — engine ENV-2 ensure presença.

    Detector aplicado SÓ a XAMLs que já têm bloco refs (workflows, not
    fragments). Idempotente: skip se TODOS 3 refs presentes.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    block_m = _RE_REFS_BLOCK.search(content)
    if not block_m:
        # XAML sem bloco refs (fragment, library, etc.) — nada a ensure.
        return []

    block_body = block_m.group(1)
    present: set[str] = set()
    for m in _RE_ASM_REF.finditer(block_body):
        present.add(m.group(1).strip())

    missing = sorted(_LEGACY_REFS_REQUIRED - present)
    if not missing:
        return []

    findings: list[Finding] = []
    for name in missing:
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=1,
                message=(
                    f"XAML target=Windows missing legacy compat ref "
                    f"`<AssemblyReference>{name}</AssemblyReference>`. "
                    f"Sicoob deploy = Studio 23.10 — sem esse ref, Studio "
                    f"não bridja .NET 6 modern refs (System.Private.CoreLib, "
                    f"System.Net.Primitives v6) → BC30652 (Dictionary type) "
                    f"+ BC31424 (NetworkCredential forwarder fail) quando "
                    f"XAML usa esses types em VB expressions."
                ),
                fix_mechanical={
                    "type": "insert_assembly_reference",
                    "name": name,
                },
                fix_prose=(
                    f"Inserir `<AssemblyReference>{name}</AssemblyReference>` "
                    f"no bloco `<TextExpression.ReferencesForImplementation>`. "
                    f"Required pra Studio 23.10 resolver type forwarders pra "
                    f".NET 6 modern refs. Forward-compat: Studio 25.x ignora "
                    f"se já tem refs modernos."
                ),
            )
        )

    return findings


# ENV-3 — ensure namespace imports em NamespacesForImplementation pra
# Studio 23.10 resolver types em forwarder chains.
#
# Empiricamente isolated (2026-05-21): broken project sem `<x:String>System.Net</x:String>`
# emite BC30652/BC31424 pra `new System.Net.NetworkCredential(...)`. Working project
# tem o import → resolve corretamente.
#
# Pattern → namespace map: cada chave é regex que matcha VB expression usage;
# valor é namespace que deve ser importado. ENV-3 emite finding APENAS quando
# usage detectado + namespace não importado.
_ENV3_NAMESPACE_PATTERNS = {
    "System.Net": re.compile(
        r"\b(?:new\s+)?System\.Net\.(?:NetworkCredential|IPEndPoint|IPAddress|"
        r"Dns|WebClient|HttpWebRequest|HttpWebResponse|WebRequest|WebResponse|"
        r"Cookie|CookieContainer)\b"
    ),
    "System.Runtime.CompilerServices": re.compile(
        r"\bSystem\.Runtime\.CompilerServices\.(?:RuntimeHelpers|"
        r"CallerMemberName|CallerLineNumber)\b"
    ),
    "System.Text.RegularExpressions": re.compile(
        r"\bSystem\.Text\.RegularExpressions\.(?:Regex|Match|MatchCollection|"
        r"Group|Capture|RegexOptions)\b"
    ),
}


_RE_NS_FOR_IMPL_BLOCK = re.compile(
    r"<TextExpression\.NamespacesForImplementation>(.*?)"
    r"</TextExpression\.NamespacesForImplementation>",
    re.DOTALL,
)
_RE_NS_STRING = re.compile(r"<x:String>([^<]+)</x:String>")


def detect_env3_ensure_namespace_imports(rule, fc, pc):
    """ENV-3: emite finding por namespace usado em VB expressions MAS não
    importado em `<TextExpression.NamespacesForImplementation>`.

    Fix `insert_namespace_import` injeta `<x:String>NS</x:String>` no bloco.
    Idempotente: skip se namespace já presente OU usage não detectado.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    block_m = _RE_NS_FOR_IMPL_BLOCK.search(content)
    if not block_m:
        # XAML sem bloco namespaces — não-workflow ou fragment.
        return []

    block_body = block_m.group(1)
    present_namespaces: set[str] = set()
    for m in _RE_NS_STRING.finditer(block_body):
        present_namespaces.add(m.group(1).strip())

    findings: list[Finding] = []
    for namespace, pattern in _ENV3_NAMESPACE_PATTERNS.items():
        if namespace in present_namespaces:
            continue
        # Verifica se há usage daquele namespace em VB expression no XAML
        if not pattern.search(content):
            continue

        # Identifica exemplo do usage pra mensagem útil
        match = pattern.search(content)
        sample = match.group(0)[:60] if match else namespace

        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=1,
                message=(
                    f"XAML usa `{sample}` mas namespace `{namespace}` não "
                    f"importado em `<TextExpression.NamespacesForImplementation>`. "
                    f"Studio 23.10 (deploy Sicoob) precisa import explícito pra "
                    f"VB resolver type via forwarder chain (BC30652/BC31424 senão)."
                ),
                fix_mechanical={
                    "type": "insert_namespace_import",
                    "name": namespace,
                },
                fix_prose=(
                    f"Inserir `<x:String>{namespace}</x:String>` no bloco "
                    f"`<TextExpression.NamespacesForImplementation>` (lista). "
                    f"Required pra Studio 23.10 resolver types forwarded "
                    f"em `{sample[:40]}`."
                ),
            )
        )

    return findings


def detect_servicemodel_refs(rule, fc, pc):
    """W-5: emite finding por `<AssemblyReference>System.ServiceModel*` órfã
    no bloco refs. WCF stack não é usado pelos pacotes pinados Sicoob (D-1) em
    runtime — herança template Legacy. Cada finding carrega
    `mechanical=strip_assembly_reference` (fixer compartilhado).

    Filtro `target: windows` no rule já garante invocação só em projetos
    Windows. Idempotente: skip se nenhum ref ServiceModel presente.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    block_m = _RE_REFS_BLOCK.search(content)
    if not block_m:
        return []

    block_body = block_m.group(1)
    found: list[str] = []
    for m in _RE_ASM_REF.finditer(block_body):
        name = m.group(1).strip()
        if name in _SERVICEMODEL_REFS_BLACKLIST:
            found.append(name)

    if not found:
        return []

    findings: list[Finding] = []
    for name in found:
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=1,
                message=(
                    f"XAML target=Windows referencia `{name}` (WCF stack). "
                    f"Pacotes pinados Sicoob (D-1) não usam WCF — ref é "
                    f"herança template Legacy. Cleanup pós-Migrator."
                ),
                fix_mechanical={
                    "type": "strip_assembly_reference",
                    "name": name,
                },
                fix_prose=(
                    f"Remover `<AssemblyReference>{name}</AssemblyReference>` "
                    f"do bloco refs. WCF não usado pelos pacotes pinados; "
                    f"ref órfã apenas adiciona surface de auditoria."
                ),
            )
        )

    return findings
