"""D-2 heuristic — NuGet peer dependency conflict (NU1605 prevention).

Background:
  Studio analyzer (uipcli analyze) NÃO valida peer dependencies declaradas
  no `.nuspec` dos pacotes primários. Quando peer requirement de uma primary
  dep conflita com pin de outro pacote no `project.json`, Studio Publish
  gera `NU1605: package downgrade`.

  Engine valida cruzando cache local de `.nupkg` (extrai `.nuspec` via ZIP)
  com `project.json::dependencies`. Offline-safe, determinístico.

Detector strategy:
  1. Para cada (primary_id, primary_version) em project.json::dependencies:
     a. Localizar `.nupkg` no cache local.
     b. Extrair `.nuspec` (zip member) e parsear `<dependencies>/<group>`.
        UiPath nuspecs declaram múltiplos groups (net4.6.1, net6.0-windows,
        net6.0). Lê de todos — qualquer peer requirement que conflita gera
        finding.
     c. Para cada peer requirement (peer_id, version_range):
        - Se peer_id está em project.json::dependencies: comparar versão
          pinada vs range. Se incompatível → finding.
        - Se peer_id não está em project.json::dependencies: skip (peer
          é dependência implícita resolvida transitivamente).
  2. Range parsing simplificado:
     - `[X.Y.Z]` (bracket) = exact match required.
     - `X.Y.Z` (plain) = floor (>= X.Y.Z) na convenção NuGet.
     - `[X.Y.Z, A.B.C)` ranges complexos = parse min/max bounds.

Cache lookup:
  Path padrão NuGet: `<root>/<id_lower>/<version>/<id_lower>.nuspec`.
  Param `nupkgs_cache_dir` override (default = ~/.nuget/packages).
  Também tenta `<root>/<id>.<version>.nupkg` (flat layout — Sicoob CCS_*).

Não levanta se cache ausente (offline-tolerant): detector emit ZERO findings
se .nuspec não localizado. Comentário fica explícito.
"""
from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path
from typing import Any

from uip_engine._types import Finding


_RE_NUSPEC_DEP = re.compile(
    r'<dependency\s+id="([^"]+)"\s+version="([^"]+)"',
    re.IGNORECASE,
)


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse version string to tuple of ints. Pre-release/build suffix
    stripped. `25.10.8-preview.1` → (25, 10, 8). `1.0.0-20250519.7` →
    (1, 0, 0). Empty → (0,)."""
    nums = re.findall(r"\d+", v)
    if not nums:
        return (0,)
    return tuple(int(x) for x in nums[:4])  # cap em 4 components (major.minor.patch.build)


def _parse_pin(raw: str) -> tuple[int, ...] | None:
    """Extract version tuple from project.json dep value.
    Aceita `[X.Y.Z]`, `X.Y.Z`, `[X.Y.Z,)`, etc."""
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)*)", str(raw))
    if not m:
        return None
    return _parse_version(m.group(1))


def _range_satisfies(actual: tuple[int, ...], range_str: str) -> tuple[bool, str]:
    """Check if `actual` satisfies NuGet `range_str`.

    Returns (ok, expected_text) where expected_text is human-readable.

    Supported:
      `[X.Y.Z]` → exact match required.
      `X.Y.Z` (no bracket) → floor (>= X.Y.Z).
      `[X.Y.Z,)` → >= X.Y.Z.
      `[X.Y.Z, A.B.C)` → X.Y.Z <= v < A.B.C.
      `(X.Y.Z, A.B.C]` → X.Y.Z < v <= A.B.C.
    Tudo mais → conservatively True (não bloqueia falsamente).
    """
    s = range_str.strip()
    # Exact match: [X.Y.Z]
    m = re.fullmatch(r"\[([\d.]+)\]", s)
    if m:
        expected = _parse_version(m.group(1))
        return (actual == expected, f"=={m.group(1)}")

    # Range with brackets: [min,max] / [min,max) / (min,max] / (min,max)
    m = re.fullmatch(r"([\[\(])\s*([\d.]*)\s*,\s*([\d.]*)\s*([\]\)])", s)
    if m:
        inc_l, lo, hi, inc_r = m.group(1), m.group(2), m.group(3), m.group(4)
        lo_v = _parse_version(lo) if lo else None
        hi_v = _parse_version(hi) if hi else None
        ok = True
        if lo_v is not None:
            ok = ok and (actual >= lo_v if inc_l == "[" else actual > lo_v)
        if hi_v is not None:
            ok = ok and (actual <= hi_v if inc_r == "]" else actual < hi_v)
        return (ok, s)

    # Plain version = floor
    m = re.fullmatch(r"([\d.]+)", s)
    if m:
        floor = _parse_version(m.group(1))
        return (actual >= floor, f">={m.group(1)}")

    # Unknown format — não bloquear
    return (True, s)


def _find_nuspec(cache_root: Path, package_id: str, version: str) -> Path | None:
    """Localiza .nuspec do (package_id, version) em cache_root.

    Tenta NuGet padrão `<id_lower>/<version>/<id_lower>.nuspec` E flat
    `<id>.<version>.nupkg` (extrai zip).

    Versão pode vir com brackets: `[25.10.29]` → `25.10.29`.
    """
    v_clean = re.sub(r"[\[\]()]", "", version).strip()
    # Pode haver range com vírgula — pega só lower bound
    if "," in v_clean:
        v_clean = v_clean.split(",")[0].strip()

    id_lower = package_id.lower()

    # NuGet hierarchical layout
    candidate = cache_root / id_lower / v_clean / f"{id_lower}.nuspec"
    if candidate.exists():
        return candidate

    # Flat layout: <id>.<version>.nupkg (Sicoob CCS_)
    for nupkg in cache_root.glob(f"{package_id}.{v_clean}.nupkg"):
        return nupkg  # caller extrai .nuspec do ZIP

    return None


def _extract_nuspec_xml(path: Path) -> str | None:
    """Lê .nuspec content. Se path é .nupkg, extrai member .nuspec do ZIP."""
    try:
        if path.suffix.lower() == ".nuspec":
            return path.read_text(encoding="utf-8-sig", errors="ignore")
        if path.suffix.lower() == ".nupkg":
            with zipfile.ZipFile(path) as zf:
                for name in zf.namelist():
                    if name.lower().endswith(".nuspec"):
                        return zf.read(name).decode("utf-8-sig", errors="ignore")
    except (OSError, zipfile.BadZipFile):
        return None
    return None


def _parse_peer_deps(nuspec_xml: str) -> list[tuple[str, str]]:
    """Extrai (peer_id, version_range) de TODOS `<dependency>` no nuspec
    (todos `<group>` agregados, dedupe por (id, range))."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for m in _RE_NUSPEC_DEP.finditer(nuspec_xml):
        peer_id = m.group(1).strip()
        peer_range = m.group(2).strip()
        key = (peer_id, peer_range)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _default_cache_dirs() -> list[Path]:
    """Default lookup chain para .nupkg / .nuspec."""
    out: list[Path] = []
    # NuGet user cache
    home = Path(os.path.expanduser("~"))
    nuget = home / ".nuget" / "packages"
    if nuget.exists():
        out.append(nuget)
    # Sicoob CCS_ flat cache (override via param)
    flat = Path(r"C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs")
    if flat.exists():
        out.append(flat)
    return out


def detect_nuget_peer_conflict(rule, fc, pc):
    """Para cada primary dep em project.json::dependencies, lê seu .nuspec
    e flagia peer requirements conflitantes com pins do mesmo project.json.
    """
    if pc is None:
        return []
    # Apenas dispara no project.json (não em XAMLs).
    if not str(fc.path).lower().endswith("project.json"):
        return []

    deps = pc.project_json.get("dependencies") or {}
    if not isinstance(deps, dict):
        return []

    params = rule.detect.get("params", {}) or {}
    override = params.get("nupkgs_cache_dir")
    cache_dirs: list[Path] = []
    if override:
        cd = Path(override)
        if cd.exists():
            cache_dirs.append(cd)
    cache_dirs.extend(_default_cache_dirs())
    if not cache_dirs:
        return []  # sem cache → não consegue resolver peer (offline-tolerant)

    # Pre-compute parsed pins
    pinned: dict[str, tuple[tuple[int, ...], str]] = {}
    for k, v in deps.items():
        parsed = _parse_pin(str(v))
        if parsed is not None:
            pinned[k] = (parsed, str(v))

    findings: list[Finding] = []

    for primary_id, primary_raw in deps.items():
        nuspec_path: Path | None = None
        for cd in cache_dirs:
            nuspec_path = _find_nuspec(cd, primary_id, str(primary_raw))
            if nuspec_path:
                break
        if nuspec_path is None:
            continue  # nuspec não cached — skip silente (não pode validar)

        nuspec_xml = _extract_nuspec_xml(nuspec_path)
        if not nuspec_xml:
            continue

        peers = _parse_peer_deps(nuspec_xml)
        for peer_id, peer_range in peers:
            if peer_id not in pinned:
                continue  # peer não declarado em project.json — skip
            actual_v, actual_raw = pinned[peer_id]
            ok, expected_text = _range_satisfies(actual_v, peer_range)
            if ok:
                continue
            findings.append(
                Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    category=rule.category,
                    file=str(fc.path),
                    line=1,
                    message=(
                        f"{rule.title}: '{primary_id}' {primary_raw} exige "
                        f"'{peer_id}' {expected_text} mas pin atual é "
                        f"{actual_raw}. Studio Publish gerará NU1605 "
                        f"(package downgrade)."
                    ),
                    fix_prose=(rule.fix or {}).get("prose"),
                )
            )

    return findings
