"""D-1q-CCS-AUTO — pinar CCS_* na versão mais recente em `.nupkgs/`.

Estratégia:
  1. Glob `.nupkgs/CCS_*.nupkg`
  2. Parse filename: `^(CCS_[A-Za-z0-9_]+)\\.(<semver>)\\.nupkg$`
  3. Group por package, pick max semver
  4. Compara `project.json::dependencies[<CCS_*>]` ↔ max
  5. Scaneia XAMLs por AssemblyReference/xmlns `CCS_*` sem dependency direta
  6. Emit finding com `mechanical` dinâmico (`set_dependency_pin`, version=max)

Vs D-1a..D-1p (static canonical_pins.yaml): CCS_* versions mudam quando dev
solta novo `.nupkg`. Latest-on-disk evita atualizar YAML manualmente.
"""
from __future__ import annotations

import re
from pathlib import Path

from uip_engine._types import Finding
from uip_engine.encoding import detect_and_decode


_NUPKGS_DIR = Path(r"C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs")

# Capture grupo 1 = package name, grupo 2 = semver core (major.minor.patch).
# Aceita opcional pre-release / build metadata depois.
_FNAME_RE = re.compile(
    r"^(?P<pkg>CCS_[A-Za-z0-9_]+)"
    r"\.(?P<ver>\d+\.\d+\.\d+(?:[-.][A-Za-z0-9.+_-]+)?)"
    r"\.nupkg$",
    re.IGNORECASE,
)
_XAML_CCS_XMLNS_RE = re.compile(
    r"xmlns:(?P<prefix>[A-Za-z_][A-Za-z0-9_]*)="
    r"\"clr-namespace:[^\"]*;assembly=(?P<assembly>CCS_[A-Za-z0-9_]+)\"",
    re.IGNORECASE,
)
_TEXT_EXPRESSION_BLOCK_RE = re.compile(
    r"<TextExpression\.(?:Namespaces|References)ForImplementation>.*?"
    r"</TextExpression\.(?:Namespaces|References)ForImplementation>",
    re.IGNORECASE | re.DOTALL,
)
_XAML_CCS_QUALIFIED_RE = re.compile(r"\b(CCS_[A-Za-z0-9_]+)\.", re.IGNORECASE)


def _parse_semver(s: str) -> tuple:
    """Parse 'X.Y.Z[-pre[+build]]' → tuple ordenável.

    Heurística simples — pre-release suffix tratado como string lexicográfica
    DEPOIS dos números (padrão semver: release > pre-release dentro do mesmo
    X.Y.Z). Sufixo ausente → ordena maior que qualquer pre-release.
    """
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[-.](.+))?$", s)
    if not m:
        return (0, 0, 0, "")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    suffix = m.group(4) or ""
    # Sufixo vazio (release) ordena acima de qualquer pre-release.
    # Truque: prefix vazio → '\x7f' (DEL char) > qualquer ASCII printable.
    suffix_key = suffix if suffix else "\x7f"
    return (major, minor, patch, suffix_key)


def _scan_latest(nupkgs_dir: Path | None = None) -> dict[str, str]:
    """Mapa `{package_name: latest_version}` lendo `.nupkgs/`.

    `nupkgs_dir=None` resolve via lookup do `_NUPKGS_DIR` no módulo (não
    default param) pra que `unittest.mock.patch` funcione em testes.
    """
    if nupkgs_dir is None:
        nupkgs_dir = _NUPKGS_DIR
    if not nupkgs_dir.is_dir():
        return {}
    by_pkg: dict[str, list[str]] = {}
    for nupkg in nupkgs_dir.glob("CCS_*.nupkg"):
        m = _FNAME_RE.match(nupkg.name)
        if not m:
            continue
        by_pkg.setdefault(m.group("pkg"), []).append(m.group("ver"))
    return {pkg: max(versions, key=_parse_semver) for pkg, versions in by_pkg.items()}


def _scan_project_ccs_assemblies(root: Path) -> dict[str, Path]:
    """Map CCS package names hard-used by XAML to first source file.

    AssemblyReference/TextExpression imports alone are Studio residue. Treat a
    XAML dependency as hard only when a CCS xmlns prefix is used in an element
    tag or a qualified CCS_X. expression appears outside import/reference
    blocks.
    """
    found: dict[str, Path] = {}
    for xaml in root.rglob("*.xaml"):
        try:
            content = detect_and_decode(xaml)
        except OSError:
            continue
        stripped = _TEXT_EXPRESSION_BLOCK_RE.sub("", content)
        for match in _XAML_CCS_XMLNS_RE.finditer(content):
            prefix = match.group("prefix")
            package = match.group("assembly")
            if re.search(rf"<\s*{re.escape(prefix)}:", stripped):
                found.setdefault(package, xaml)
        for match in _XAML_CCS_QUALIFIED_RE.finditer(stripped):
            found.setdefault(match.group(1), xaml)
    return found


def detect_ccs_latest_pin(rule, fc, pc) -> list[Finding]:
    """D-1q-CCS-AUTO detector.

    Project.json:dependencies CCS_* deve = latest version em `.nupkgs/`.
    Fix mecânico dinâmico via `set_dependency_pin` com version preenchida.
    Também adiciona dependency CCS_* ausente quando XAML referencia assembly
    existente em `.nupkgs/`. Cache NuGet local NÃO é fonte de verdade para
    CCS_*; ausência em `.nupkgs/` vira diagnóstico explícito.
    """
    if pc is None:
        return []
    if not str(fc.path).lower().endswith("project.json"):
        return []
    deps = pc.project_json.get("dependencies", {})
    if not isinstance(deps, dict):
        return []
    latest_by_pkg = _scan_latest()

    findings: list[Finding] = []
    for pkg, current_raw in deps.items():
        if not str(pkg).lower().startswith("ccs_"):
            continue
        if pkg not in latest_by_pkg:
            findings.append(Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(pc.root / "project.json"),
                line=1,
                message=(
                    f"{rule.title}: project.json declara {pkg}={current_raw}, "
                    f"mas nao existe {pkg}.*.nupkg em {_NUPKGS_DIR}. "
                    "Sincronize o pacote CCS local antes de rodar os gates "
                    "oficiais."
                ),
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))
            continue
        latest = latest_by_pkg[pkg]
        # Strip brackets/spaces do pin atual pra comparar
        m = re.match(r"\[?\s*([\d.A-Za-z+\-_]+?)\s*\]?$", str(current_raw))
        current = m.group(1) if m else str(current_raw)
        if current == latest:
            continue
        fix_mechanical = {
            "type": "set_dependency_pin",
            "package": pkg,
            "version": f"[{latest}]",
        }
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(pc.root / "project.json"),
            line=1,
            message=f"{rule.title}: {pkg}={current_raw} (latest em .nupkgs: {latest})",
            fix_mechanical=fix_mechanical,
            fix_prose=(rule.fix or {}).get("prose"),
        ))

    referenced = _scan_project_ccs_assemblies(pc.root)
    deps_lower = {str(pkg).lower() for pkg in deps}
    for pkg, source_path in sorted(referenced.items()):
        if pkg.lower() in deps_lower:
            continue
        try:
            source_label = str(source_path.relative_to(pc.root))
        except ValueError:
            source_label = str(source_path)
        latest = latest_by_pkg.get(pkg)
        if not latest:
            findings.append(Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(pc.root / "project.json"),
                line=1,
                message=(
                    f"{rule.title}: XAML referencia assembly '{pkg}' em "
                    f"{source_label}, mas nao existe {pkg}.*.nupkg em "
                    f"{_NUPKGS_DIR}. Sincronize o pacote CCS local antes de "
                    "rodar os gates oficiais."
                ),
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))
            continue
        fix_mechanical = {
            "type": "set_dependency_pin",
            "package": pkg,
            "version": f"[{latest}]",
        }
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(pc.root / "project.json"),
            line=1,
            message=(
                f"{rule.title}: XAML referencia assembly '{pkg}' em "
                f"{source_label}, mas project.json::dependencies nao declara "
                f"o pacote. Versao local resolvida: {latest}."
            ),
            fix_mechanical=fix_mechanical,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
