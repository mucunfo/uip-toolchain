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

from uip_engine._types import Finding


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


# ENV-4 — normalize legacy `<mva:VisualBasic.Settings>` text-content.
#
# ROOT CAUSE isolated empiricamente (2026-05-22, projeto contestacao-de-compras-
# ajuste-na-reserva-de-fraude-performer):
#
#   <mva:VisualBasic.Settings>Assembly references and imported namespaces for
#   internal implementation</mva:VisualBasic.Settings>
#
# Esse stub Studio pré-19.x (template REFramework antigo) é interpretado pelo
# VB compiler como `Microsoft.VisualBasic.Activities.VisualBasicSettings`
# instance com payload string → ativa modo LEGACY resolution → Dictionary +
# NetworkCredential resolvem via facades v4 (mscorlib/System .NET Fx 4.x) →
# mismatch contra forwarder v6 (System.Private.CoreLib) → BC30652 + BC31424.
#
# Studio "Import References" auto-fix substituí esse element por canonical
# `<VisualBasic.Settings><x:Null /></VisualBasic.Settings>` modern empty marker
# → VB compiler usa default .NET 6 resolver → Dictionary v6 + NetworkCredential
# v6 resolvem corretamente → BC clears.
#
# Engine ENV-4 replica esse fix mecânico. Sem ele, W-11g/W-11y/ENV-2 (insert
# refs) NÃO bastam — text-content overrides resolver mode independent das refs.
#
# Detector match também self-closing `<mva:VisualBasic.Settings />` (variante
# Migrator emite às vezes — semanticamente equivalente legacy).
_RE_VB_SETTINGS_LEGACY = re.compile(
    r"<mva:VisualBasic\.Settings>[^<]*</mva:VisualBasic\.Settings>"
    r"|<mva:VisualBasic\.Settings\s*/>"
)


def detect_env4_normalize_vb_settings(rule, fc, pc):
    """ENV-4: emite finding se XAML tem `<mva:VisualBasic.Settings>` legacy
    (text-content ou self-closing). Cada finding carrega
    `mechanical=normalize_visualbasic_settings`.

    ROOT CAUSE de BC30652/BC31424 isolated 2026-05-22. Studio auto-fix
    valida o mecanismo (ver docstring module-level).

    Idempotente: skip se elemento já normalizado para canonical
    `<VisualBasic.Settings><x:Null /></VisualBasic.Settings>`.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    m = _RE_VB_SETTINGS_LEGACY.search(content)
    if not m:
        return []

    line_no = content[: m.start()].count("\n") + 1

    return [
        Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=line_no,
            message=(
                "XAML tem `<mva:VisualBasic.Settings>` legacy (text-content "
                "ou self-closing). Esse stub Studio pré-19.x ativa VB "
                "compiler resolução LEGACY → BC30652 (Dictionary "
                "System.Collections v6) + BC31424 (NetworkCredential "
                "System.Net.Primitives v6) mesmo com refs corretas. "
                "Normalize para canonical `<VisualBasic.Settings><x:Null /></"
                "VisualBasic.Settings>` modern empty marker."
            ),
            fix_mechanical={"type": "normalize_visualbasic_settings"},
            fix_prose=(
                "Substituir `<mva:VisualBasic.Settings>text</"
                "mva:VisualBasic.Settings>` (ou self-closing) por "
                "`<VisualBasic.Settings><x:Null /></VisualBasic.Settings>`. "
                "Drop `xmlns:mva=\"...System.Activities\"` se mva: prefix "
                "não usado em outros lugares."
            ),
        )
    ]


# W-32 — strip `<AssemblyReference>System.Runtime.WindowsRuntime</...>` que
# não existe em .NET 6. Studio loga warn `XamlMigration: removed reference
# System.Runtime.WindowsRuntime` a cada load do XAML (uma entrada por XAML —
# 13 entradas em 09:30:46 no projeto contestacao). Studio remove on-load mas
# não persiste no XAML — cycle infinito de migration warnings.
#
# Engine W-32 persiste o strip = engine garante limpeza idempotente, Studio
# para de logar warnings repetidos. .NET 6 não tem esse assembly (WinRT
# bridge era .NET Framework only). Strip safe sempre.
_W32_OBSOLETE_DOTNET4_REFS: frozenset[str] = frozenset({
    "System.Runtime.WindowsRuntime",
})


def detect_obsolete_dotnet4_refs(rule, fc, pc):
    """W-32: emite finding por `<AssemblyReference>X</AssemblyReference>` que
    é refs .NET Framework 4.x-only sem equivalente em .NET 6. Studio XamlMigration
    strip on-load mas não persiste — engine W-32 persiste no XAML.

    Lista canonical em `_W32_OBSOLETE_DOTNET4_REFS`. Conservadora: apenas refs
    confirmadas obsoletas em .NET 6 (Studio log valida).

    Reuse fixer `strip_assembly_reference` existente.

    Idempotente: skip se nenhum ref obsoleto presente.
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
        if name in _W32_OBSOLETE_DOTNET4_REFS:
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
                    f"XAML target=Windows tem `<AssemblyReference>{name}</"
                    f"AssemblyReference>` — assembly obsoleto .NET Framework "
                    f"4.x sem equivalente em .NET 6. Studio XamlMigration "
                    f"strip on-load mas não persiste — cycle infinito de "
                    f"WARN no Studio.Project.log a cada load."
                ),
                fix_mechanical={
                    "type": "strip_assembly_reference",
                    "name": name,
                },
                fix_prose=(
                    f"Remover `<AssemblyReference>{name}</AssemblyReference>` "
                    f"do bloco refs. Cleanup persistente — engine elimina "
                    f"o que Studio strippa ao carregar o XAML."
                ),
            )
        )

    return findings


# W-31 — scrub legacy facade refs sem usage em XAML body. Lista CONSERVADORA
# de refs que Studio "Import References" auto-fix removeu em validation
# empírica (2026-05-22, RetryCurrentTransaction.xaml). NÃO blind strip como
# W-26 errado: detector verifica que ref não tem xmlns:* mapping body usage.
#
# Lista é específica a refs LEGACY FACADE template REFramework antigo que não
# existem em .NET 6 OU não são usadas em workflows Sicoob padrão.
_W31_LEGACY_FACADE_REFS: frozenset[str] = frozenset({
    "OfficeDevPnP.Core",
    "System.Configuration.Install",
    "System.Data.Entity",
    "UiPathTeam.SharePoint",
    "UiPath.Word",
})


def detect_unused_legacy_facade_refs(rule, fc, pc):
    """W-31: emite finding por `<AssemblyReference>X</AssemblyReference>` que
    é facade Legacy template + NÃO tem usage no body XAML (sem xmlns prefix
    apontando pro mesmo assembly).

    Lista canonical em `_W31_LEGACY_FACADE_REFS`. Cada finding tem usage
    guard: ref só é flagged se body NÃO tem `assembly=<name>` em qualquer
    xmlns declaração.

    Reuse fixer `strip_assembly_reference` existente.

    Idempotente: skip se nenhum ref legacy presente sem usage.

    Diferença W-26 errado: W-26 strippava mscorlib/System/System.Core blind
    (sem guard) baseado em hipótese errada. W-31 stripa apenas facades
    template Legacy SEM usage real comprovado.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    block_m = _RE_REFS_BLOCK.search(content)
    if not block_m:
        return []

    block_body = block_m.group(1)
    # Lista xmlns declarations cuja assembly clause referencia algo
    xmlns_assemblies: set[str] = set()
    for m in re.finditer(r'xmlns:[A-Za-z_][\w]*="clr-namespace:[^"]*?;\s*assembly=([^"]+)"', content):
        xmlns_assemblies.add(m.group(1).strip())

    found: list[str] = []
    for m in _RE_ASM_REF.finditer(block_body):
        name = m.group(1).strip()
        if name in _W31_LEGACY_FACADE_REFS and name not in xmlns_assemblies:
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
                    f"XAML target=Windows tem `<AssemblyReference>{name}</"
                    f"AssemblyReference>` (facade Legacy) sem nenhum "
                    f"`xmlns:*=\"clr-namespace:*;assembly={name}\"` no body. "
                    f"Studio Import References auto-fix strippa esse ref "
                    f"como template legacy unused. Engine W-31 replica."
                ),
                fix_mechanical={
                    "type": "strip_assembly_reference",
                    "name": name,
                },
                fix_prose=(
                    f"Remover `<AssemblyReference>{name}</AssemblyReference>` "
                    f"do bloco refs — facade Legacy sem usage body. "
                    f"Validado contra W-26 errado (que strippava blind sem "
                    f"guard de usage)."
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
