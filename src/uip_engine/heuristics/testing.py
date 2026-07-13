"""Heuristics for testing rules (T-*)."""
from __future__ import annotations

import re

from uip_engine._types import Finding


_RE_INVOKE_FILE = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*WorkflowFileName="([^"]+)"'
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def detect_t5_missing_workflow(rule, fc, pc):
    if pc is None:
        return []
    content = fc.active_content
    findings = []
    for m in _RE_INVOKE_FILE.finditer(content):
        target = m.group(1)
        if target.startswith("[") or "{" in target:
            continue
        normalized = target.replace("\\", "/").lstrip("./")
        target_path = pc.root / normalized
        if target_path.exists():
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: '{target}' não existe",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# --- S-11: xmlns prefix com assembly não declarado em project.json ---

import json as _json

_RE_XMLNS_WITH_ASSEMBLY = re.compile(
    r'xmlns:(?P<prefix>[A-Za-z][\w\-]*)="clr-namespace:(?P<ns>[^;"]*);assembly=(?P<asm>[^"]+)"'
)


def _find_project_json(start_path):
    p = start_path
    for _ in range(8):
        candidate = p / "project.json"
        if candidate.exists():
            return candidate
        if p.parent == p:
            break
        p = p.parent
    return None


def _project_dependencies(project_json_path):
    try:
        data = _json.loads(project_json_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return set()
    deps = data.get("dependencies") or {}
    return set(deps.keys())


_D1_VERSIONS_CACHE: dict[str, str] | None = None


def _load_d1_pinned_versions() -> dict[str, str]:
    """Retorna {package_name: exact_version} dos pins canonical Sicoob.

    Os D-1* rules NÃO vivem em rules.yaml: são sintetizados em parse-time
    por `canonical.py::_synthesize_d1_rule` a partir de
    `assets/canonical_pins.yaml`, e o param emitido é `exact` (não `min`).
    Re-parsear rules.yaml procurando `min` retornava dict vazio permanente
    (auto-add dead code). Lemos a MESMA fonte-de-verdade que os D-1*
    sintetizados — `uip_engine.canonical.load_canonical` — garantindo
    package→exact-version consistente. Cache em memória; uma vez por processo."""
    global _D1_VERSIONS_CACHE
    if _D1_VERSIONS_CACHE is not None:
        return _D1_VERSIONS_CACHE
    versions: dict[str, str] = {}
    try:
        from uip_engine.canonical import load_canonical
        data = load_canonical()
        for entry in data.get("pins", []) or ():
            pkg = entry.get("package")
            ver = entry.get("exact")
            if pkg and ver:
                versions[pkg] = ver
    except Exception:
        pass
    _D1_VERSIONS_CACHE = versions
    return versions


# (path, mtime) → set de ids/assemblies transitivos lowercase
_TRANSITIVE_CACHE: dict[tuple[str, float], set[str]] = {}


def _transitive_available(proj_json) -> set[str]:
    """Packages + assemblies (.dll stems) do graph NuGet restaurado.

    Fonte: `.local/AllDependencies.json` (formato project.assets.json,
    gerado pelo restore oficial). Assembly presente no graph transitivo
    resolve no Studio/runtime mesmo sem declaração direta em
    `project.json::dependencies` — ex.: `Microsoft.Graph` via
    `UiPath.MicrosoftOffice365.Activities`. Sem o arquivo (restore nunca
    rodou), retorna vazio e S-11 mantém o comportamento estrito.
    """
    assets = proj_json.parent / ".local" / "AllDependencies.json"
    try:
        key = (str(assets), assets.stat().st_mtime)
    except OSError:
        return set()
    cached = _TRANSITIVE_CACHE.get(key)
    if cached is not None:
        return cached
    names: set[str] = set()
    try:
        import json
        data = json.loads(assets.read_text(encoding="utf-8-sig"))
        for lib_key, lib in (data.get("libraries") or {}).items():
            names.add(lib_key.split("/", 1)[0].lower())
            for f in (lib or {}).get("files") or ():
                if f.lower().endswith(".dll"):
                    names.add(f.rsplit("/", 1)[-1][:-4].lower())
    except Exception:
        names = set()
    _TRANSITIVE_CACHE[key] = names
    return names


def detect_s11_xmlns_assembly_missing(rule, fc, pc):
    p = rule.detect.get("params", {}) or {}
    # Normalize case — XAML pode usar `UiPath.UiAutomation.Activities` (Ui mixed)
    # enquanto whitelist usa `UiPath.UIAutomation.Activities` (UI capital). Match
    # case-insensitive prevent false-positive engine ERROR. NuGet IDs são
    # case-insensitive por spec; engine deve seguir o mesmo princípio.
    whitelist_raw = set(p.get("whitelist_assemblies") or ())
    whitelist = {w.lower() for w in whitelist_raw}
    skip_prefixes = set(p.get("skip_prefixes") or ())
    accept_subset = bool(p.get("accept_subset_of_declared", False))
    if pc is not None:
        proj_json = pc.root / "project.json"
        if not proj_json.exists():
            proj_json = _find_project_json(fc.path.parent)
    else:
        proj_json = _find_project_json(fc.path.parent)
    if not proj_json or not proj_json.exists():
        return []
    deps_raw = _project_dependencies(proj_json)
    deps_lc = {d.lower() for d in deps_raw}
    # deps + whitelist + graph transitivo restaurado — tudo lowercase
    available = deps_lc | whitelist | _transitive_available(proj_json)
    pinned = _load_d1_pinned_versions()
    pinned_lc = {k.lower(): v for k, v in pinned.items()}

    content = fc.active_content
    if 'assembly=' not in content:
        return []
    findings: list[Finding] = []
    seen_keys = set()
    for m in _RE_XMLNS_WITH_ASSEMBLY.finditer(content):
        prefix = m.group("prefix")
        ns = m.group("ns")
        # `asm` no XAML pode vir fully-qualified:
        #   `System, Version=4.0.0.0, Culture=neutral, PublicKeyToken=...`
        # Whitelist + deps usam simple names. Extrair só a parte antes da `,`.
        asm_raw = m.group("asm").strip()
        asm = asm_raw.split(",", 1)[0].strip()
        asm_lc = asm.lower()
        if prefix in skip_prefixes:
            continue
        if asm_lc in available:
            continue
        if any(asm_lc.startswith(w + ".") for w in whitelist):
            continue
        if accept_subset and any(d.startswith(asm_lc + ".") for d in deps_lc):
            continue
        key = (asm, prefix)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        # Resolver mechanical: se assembly tem pin em D-1*, ADD_PACKAGE.
        # Senão, mechanical=None (contextual — alerta only).
        mech = None
        version = pinned_lc.get(asm_lc)
        if version:
            mech = {
                "type": "xmlns_assembly_resolve",
                "action": "add_package",
                "package": asm,
                "version": version,
            }
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=(
                f"{rule.title}: xmlns:{prefix} usa assembly '{asm}' "
                f"não declarado em project.json::dependencies"
                + (f" — auto-add pinned {version}" if version else " — sem pin D-1*, manual")
            ),
            fix_mechanical=mech,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
