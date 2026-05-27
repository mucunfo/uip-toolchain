"""W-11-family heuristics — AssemblyReference coverage cross-version Studio.

Três detectores ortogonais:

  - `detect_xmlns_required_refs` (W-11x): cada xmlns:prefix="clr-namespace:NS;assembly=ASM"
    implica ASM usado. Se não está em refs, missing.

  - `detect_vb_symbol_refs` (W-11z): scan VB expressions inline ([New System.X(...)],
    Default="[...]"). Extract type FQNs. Resolve assembly via catálogo
    `assets/dotnet6_symbol_catalog.yaml`. Missing → fix.

  - `detect_baseline_refs` (W-11y): garante baseline refs comuns presentes em
    TODO xaml com bloco ReferencesForImplementation. Lista vem de
    `params.required_refs` no rule yaml.

Studio dialog "Some references are not imported" dispara quando XAML usa
type cujo assembly não está em `<TextExpression.ReferencesForImplementation>`.
Combo cobre 95%+ casos sem precisar abrir Studio.

Cross-version safe: .NET 6 BCL stable entre Studio 23.10 e 26.x.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from uip_engine._types import Finding


_RE_XMLNS_ASSEMBLY = re.compile(
    r'xmlns:[A-Za-z_][\w]*\s*=\s*"clr-namespace:[^"]*?;\s*assembly=([^"\s]+)"'
)
_RE_ASM_REF = re.compile(r"<AssemblyReference>([^<]+)</AssemblyReference>")
_RE_REFS_BLOCK = re.compile(
    r'<TextExpression\.ReferencesForImplementation>'
)

# Assemblies que NÃO devem ser auto-adicionados via xmlns detection
# (cobertos por outras rules ou skipados por design).
#   - System.Private.CoreLib: synthetic .NET 6 internal, Studio reclama
#     se incluído explicitamente em alguns contextos.
#   - mscorlib/System/System.Core: cobertos por ENV-2 (legacy compat refs
#     deploy Studio 23.10). Skipar aqui evita conflito entre xmlns-detection
#     genérica e rule dedicada ENV-2.
#   - Empty/whitespace
_SKIP_ASSEMBLIES: frozenset[str] = frozenset({
    "",
    "mscorlib",
    "System",
    "System.Core",
})


# Catálogo lazy-loaded de assets/dotnet6_symbol_catalog.yaml
_SYMBOL_CATALOG: dict[str, str] | None = None


def _load_catalog() -> dict[str, str]:
    """Lazy load do symbol→assembly catalog. Cache module-level."""
    global _SYMBOL_CATALOG
    if _SYMBOL_CATALOG is not None:
        return _SYMBOL_CATALOG
    engine_root = Path(__file__).resolve().parents[3]
    path = engine_root / "assets" / "dotnet6_symbol_catalog.yaml"
    if not path.exists():
        _SYMBOL_CATALOG = {}
        return _SYMBOL_CATALOG
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        _SYMBOL_CATALOG = data.get("mappings", {}) or {}
    except Exception:
        _SYMBOL_CATALOG = {}
    return _SYMBOL_CATALOG


def _reset_catalog_for_tests() -> None:
    global _SYMBOL_CATALOG
    _SYMBOL_CATALOG = None


# Regex pra extrair FQN symbols de VB expressions.
# Match: `System.X.Y` or `System.X.Y.Z` etc — PascalCase segments after `System.`
# Skip: `system.x.y` (lowercase), `system_X` (underscore).
# Constraint: PascalCase = starts with uppercase letter.
_RE_VB_SYMBOL = re.compile(
    r'\b(System(?:\.[A-Z][A-Za-z0-9_]*)+)\b'
)


def detect_xmlns_required_refs(rule, fc, pc):
    """Para cada `xmlns:X="...;assembly=Y"` no XAML, garante que `Y` está
    em `<AssemblyReference>Y</AssemblyReference>`. Emite finding por miss.

    Idempotente: skip se ref já presente. Skip se xaml sem refs block
    (não dá pra inserir).
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content

    # Requer bloco refs existir — fixer insert_assembly_reference precisa dele
    if not _RE_REFS_BLOCK.search(content):
        return []

    # Extract assemblies declared via xmlns
    needed: set[str] = set()
    for m in _RE_XMLNS_ASSEMBLY.finditer(content):
        asm = m.group(1).strip()
        if asm and asm not in _SKIP_ASSEMBLIES:
            needed.add(asm)

    if not needed:
        return []

    # Current declared refs
    current: set[str] = {m.group(1).strip() for m in _RE_ASM_REF.finditer(content)}

    missing = sorted(needed - current)
    if not missing:
        return []

    findings: list[Finding] = []
    for asm in missing:
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=1,
                message=(
                    f"XAML usa xmlns assembly='{asm}' mas falta "
                    f"<AssemblyReference>{asm}</AssemblyReference> em "
                    f"TextExpression.ReferencesForImplementation"
                ),
                fix_mechanical={
                    "type": "insert_assembly_reference",
                    "name": asm,
                },
                fix_prose=(
                    f"Adicionar `<AssemblyReference>{asm}</AssemblyReference>` "
                    f"ao bloco refs. Studio analyzer precisa pra resolver "
                    f"types declarados via xmlns."
                ),
            )
        )

    return findings


def detect_vb_symbol_refs(rule, fc, pc):
    """W-11z: scan VB expressions buscando type FQNs (System.X.Y...) e
    resolve assembly via catálogo. Emite finding por miss.

    Cobre types usados em expressions inline (`[New System.Net.NetworkCredential(...)]`,
    `Default="[New System.Security.SecureString()]"`, etc.) que NÃO aparecem
    em xmlns declarations — gap do W-11x.

    Catálogo `assets/dotnet6_symbol_catalog.yaml` define type FQN → assembly.
    Cross-version safe (.NET 6 BCL stable).
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    if not _RE_REFS_BLOCK.search(content):
        return []

    catalog = _load_catalog()
    if not catalog:
        return []

    # Extract all type FQNs mentioned in xaml (inclui attribute values + element text)
    symbols_seen: set[str] = {m.group(1) for m in _RE_VB_SYMBOL.finditer(content)}
    if not symbols_seen:
        return []

    # Map symbols → required assemblies via catálogo
    needed: set[str] = set()
    for sym in symbols_seen:
        # Try full FQN first; fall back to parent types (e.g., 'System.Net.NetworkCredential.X'
        # falls back to 'System.Net.NetworkCredential' if exists)
        if sym in catalog:
            needed.add(catalog[sym])
            continue
        # Try strip last segment iteratively
        parts = sym.split(".")
        while len(parts) > 2:  # keep at least "System.X"
            parts.pop()
            candidate = ".".join(parts)
            if candidate in catalog:
                needed.add(catalog[candidate])
                break

    if not needed:
        return []

    # Diff vs current refs
    current: set[str] = {m.group(1).strip() for m in _RE_ASM_REF.finditer(content)}
    missing = sorted(needed - current)
    if not missing:
        return []

    findings: list[Finding] = []
    for asm in missing:
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=1,
                message=(
                    f"XAML usa type que precisa '{asm}' (resolved via catálogo) "
                    f"mas falta <AssemblyReference>{asm}</AssemblyReference>"
                ),
                fix_mechanical={
                    "type": "insert_assembly_reference",
                    "name": asm,
                },
                fix_prose=(
                    f"Adicionar `<AssemblyReference>{asm}</AssemblyReference>` ao bloco refs. "
                    f"Required pra Studio analyzer resolver types em VB expressions."
                ),
            )
        )

    return findings


def detect_baseline_refs(rule, fc, pc):
    """W-11y: garante baseline refs (lista vinda de `rule.detect.params.required_refs`)
    presentes em TODO xaml com bloco ReferencesForImplementation.

    Brute-force baseline. Lista hardcoded em rules.yaml — qualquer xaml sem
    algum ref dessa lista emite finding + fix mecânico.

    Use case: refs comuns que todo xaml Windows precisa (mscorlib,
    PresentationCore, etc.) mas que não vêm de xmlns nem de symbol scan
    porque Studio synth implícito.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []

    content = fc.active_content
    if not _RE_REFS_BLOCK.search(content):
        return []

    params = (rule.detect or {}).get("params", {}) or {}
    required: list[str] = params.get("required_refs", []) or []
    if not required:
        return []

    current: set[str] = {m.group(1).strip() for m in _RE_ASM_REF.finditer(content)}
    missing = [r for r in required if r and r not in current]
    if not missing:
        return []

    findings: list[Finding] = []
    for asm in missing:
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=1,
                message=(
                    f"XAML falta baseline ref '<AssemblyReference>{asm}</AssemblyReference>'"
                ),
                fix_mechanical={
                    "type": "insert_assembly_reference",
                    "name": asm,
                },
                fix_prose=(
                    f"Adicionar `<AssemblyReference>{asm}</AssemblyReference>` ao bloco refs "
                    f"(baseline cross-version Windows target)."
                ),
            )
        )

    return findings


# W-20: orphan xmlns aliases
_RE_XMLNS_DECL = re.compile(r'\s+xmlns:([A-Za-z_][\w]*)="[^"]*"')
_W20_CORE_PREFIXES = frozenset({"x", "mc", "xml"})


def detect_w20_orphan_xmlns(rule, fc, pc):
    """W-20: emite finding por XAML que tenha pelo menos 1 xmlns alias órfã
    (declarada mas NÃO usada no document body).

    1 finding por (file, prefix) com fix_mechanical=strip_orphan_xmlns
    (fixer scaneia file todo, idempotente — apenas 1 finding por XAML é
    suficiente pra disparar fix). Mas pra rastreabilidade no review,
    emitimos 1 por prefix órfão.

    Pre-check evita 246 false-positive findings (versão anterior emitia
    1 finding por xmlns DECLARATION, mesmo quando usada → fixer no-op
    massivo).
    """
    if fc.path.suffix.lower() != ".xaml":
        return []
    content = fc.active_content or ""
    declarations = list(_RE_XMLNS_DECL.finditer(content))
    if not declarations:
        return []

    findings: list[Finding] = []
    for decl in declarations:
        prefix = decl.group(1)
        if prefix in _W20_CORE_PREFIXES:
            continue
        # Conta usages `prefix:` fora da própria xmlns declaration
        usage_pat = re.compile(rf'(?<!xmlns:)\b{re.escape(prefix)}:')
        if usage_pat.search(content):
            continue
        line = content[:decl.start()].count("\n") + 1
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=line,
            message=(
                f"{rule.title}: xmlns:{prefix} declarado mas 0 usages no "
                f"document body — strip cleanup pós-Migrator."
            ),
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
