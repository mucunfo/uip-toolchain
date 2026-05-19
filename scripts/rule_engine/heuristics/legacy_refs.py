"""W-26 heuristic — detecta AssemblyReference .NET Framework Legacy em XAML
de projeto target=Windows.

Activity Migrator GA strip `xmlns:` aliases Legacy mas mantém
`<AssemblyReference>mscorlib|System|System.Core</AssemblyReference>` no body
de `<TextExpression.ReferencesForImplementation>`. Em Windows .NET 6 esses
3 refs são redundantes (facades vazias ou supersedidos por
`System.Private.CoreLib`).

Quando XAML usa type forwarded em VB expression (ex:
`new System.Net.NetworkCredential(...)` p/ unwrap SecureString), Studio
resolve via `mscorlib v4.0.0.0` forwarder → expects `System.Net.Primitives
v4.0.0.0` no closure → mismatch com `System.Net.Primitives v6.0.0.0`
referenced → BC31424.

Engine W-20 já strip `xmlns:` aliases Legacy. W-26 complementa strippando
`<AssemblyReference>` body. Triplet completo cleanup pós-Migrator:
  W-20  → strip xmlns:* Legacy (header)
  W-26  → strip <AssemblyReference> Legacy (body)   ← este
  W-11g → insert System.Net.Primitives (body)

Conservadora: lista fixa apenas {mscorlib, System, System.Core}. Refs
extras candidatas (System.Configuration.Install, System.Data.Entity,
System.ServiceModel, WindowsBase, System.Data.DataSetExtensions) ficam
para v2 após evidência empírica adicional — alguns podem ser used em
projetos WCF/EF6/WPF.
"""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


_LEGACY_REFS_BLACKLIST: frozenset[str] = frozenset({
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


def detect_legacy_bcl_refs(rule, fc, pc):
    """Emite finding por `<AssemblyReference>` Legacy redundante encontrada
    no bloco refs. Cada finding carrega `mechanical=strip_assembly_reference`.

    Filtro `target: windows` no rule já garante invocação só em projetos
    Windows — detector não precisa checar `pc.target_framework`.

    Idempotente: skip se nenhum ref Legacy presente.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    block_m = _RE_REFS_BLOCK.search(content)
    if not block_m:
        return []

    block_body = block_m.group(1)
    legacy_found: list[str] = []
    for m in _RE_ASM_REF.finditer(block_body):
        name = m.group(1).strip()
        if name in _LEGACY_REFS_BLACKLIST:
            legacy_found.append(name)

    if not legacy_found:
        return []

    findings: list[Finding] = []
    for name in legacy_found:
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=1,
                message=(
                    f"XAML target=Windows referencia `{name}` (.NET Framework "
                    f"Legacy). Type forwarder de mscorlib v4 conflita com "
                    f".NET 6 resolution → BC31424 quando XAML usa type "
                    f"forwarded (NetworkCredential, etc.)."
                ),
                fix_mechanical={
                    "type": "strip_assembly_reference",
                    "name": name,
                },
                fix_prose=(
                    f"Remover `<AssemblyReference>{name}</AssemblyReference>` "
                    f"do bloco refs. Em Windows .NET 6 esse assembly é facade "
                    f"redundante coberto por System.Private.CoreLib. Cleanup "
                    f"pós-Migrator GA."
                ),
            )
        )

    return findings


def detect_servicemodel_refs(rule, fc, pc):
    """W-5: emite finding por `<AssemblyReference>System.ServiceModel*` órfã
    no bloco refs. WCF stack não é usado pelos pacotes pinados Sicoob (D-1) em
    runtime — herança template Legacy. Cada finding carrega
    `mechanical=strip_assembly_reference` (reuse W-26 fixer).

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
