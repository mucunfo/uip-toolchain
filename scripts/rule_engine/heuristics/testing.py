"""Heuristics for testing rules (T-*)."""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


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
    """Lê D-1* rules em rules.yaml e retorna {package_name: version}.
    Cache em memória; carregado uma vez por processo."""
    global _D1_VERSIONS_CACHE
    if _D1_VERSIONS_CACHE is not None:
        return _D1_VERSIONS_CACHE
    from pathlib import Path
    import yaml as _yaml
    rules_file = Path(__file__).resolve().parents[3] / "rules.yaml"
    versions: dict[str, str] = {}
    try:
        data = _yaml.safe_load(rules_file.read_text(encoding="utf-8"))
        for r in data.get("rules", []):
            rid = r.get("id", "")
            if not rid.startswith("D-1"):
                continue
            params = (r.get("detect") or {}).get("params", {})
            pkg = params.get("package")
            ver = params.get("min")
            if pkg and ver:
                versions[pkg] = ver
    except Exception:
        pass
    _D1_VERSIONS_CACHE = versions
    return versions


def detect_s11_xmlns_assembly_missing(rule, fc, pc):
    p = rule.detect.get("params", {}) or {}
    whitelist = set(p.get("whitelist_assemblies") or ())
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
    deps = _project_dependencies(proj_json)
    available = deps | whitelist
    pinned = _load_d1_pinned_versions()

    content = fc.active_content
    if 'assembly=' not in content:
        return []
    findings: list[Finding] = []
    seen_keys = set()
    for m in _RE_XMLNS_WITH_ASSEMBLY.finditer(content):
        prefix = m.group("prefix")
        ns = m.group("ns")
        asm = m.group("asm").strip()
        if prefix in skip_prefixes:
            continue
        if asm in available:
            continue
        if any(asm.startswith(w + ".") for w in whitelist):
            continue
        if accept_subset and any(d.startswith(asm + ".") for d in deps):
            continue
        key = (asm, prefix)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        # Resolver mechanical: se assembly tem pin em D-1*, ADD_PACKAGE.
        # Senão, mechanical=None (contextual — alerta only).
        mech = None
        version = pinned.get(asm)
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
