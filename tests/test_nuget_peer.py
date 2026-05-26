"""Tests for D-2 — NuGet peer dependency conflict (NU1605 prevention).

Detector lê `.nuspec` do cache local de packages e cruza peer requirements
com pins do project.json. Fixtures criam .nuspec sintéticos numa tmp dir
que substitui o cache via param `nupkgs_cache_dir`.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.nuget_peer import (
    detect_nuget_peer_conflict,
    _parse_version,
    _range_satisfies,
    _parse_pin,
    _parse_peer_deps,
)


def _mk_rule(cache_dir: Path | None = None) -> Rule:
    params = {}
    if cache_dir is not None:
        params["nupkgs_cache_dir"] = str(cache_dir)
    return Rule(
        id="D-2",
        severity=Severity.ERROR,
        category="breaking",
        target="windows",
        title="NuGet peer dependency conflict (NU1605 prevention)",
        description="",
        detect={"type": "python", "params": params},
        fix={
            "apply_class": "contextual",
            "prose": "Resolver conflito atualizando pin.",
        },
    )


def _mk_project(
    tmp_path: Path, deps: dict
) -> tuple[Path, ProjectContext, FileContext]:
    proj = tmp_path / "P"
    proj.mkdir(exist_ok=True)
    pj = proj / "project.json"
    pj.write_text(
        json.dumps({"targetFramework": "Windows", "dependencies": deps}),
        encoding="utf-8",
    )
    pc = ProjectContext(
        root=proj, project_json=json.loads(pj.read_text(encoding="utf-8"))
    )
    fc = FileContext(pj)
    return proj, pc, fc


def _make_nuspec_hierarchical(
    cache_root: Path,
    package_id: str,
    version: str,
    peer_deps: list[tuple[str, str]],
) -> Path:
    """Cria .nuspec em layout NuGet padrão:
    `<cache>/<id_lower>/<version>/<id_lower>.nuspec`.
    `peer_deps` = lista (peer_id, version_range).
    """
    pkg_dir = cache_root / package_id.lower() / version
    pkg_dir.mkdir(parents=True, exist_ok=True)
    nuspec_path = pkg_dir / f"{package_id.lower()}.nuspec"
    deps_xml = "\n".join(
        f'        <dependency id="{pid}" version="{pver}" />'
        for pid, pver in peer_deps
    )
    nuspec_path.write_text(
        f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>{package_id}</id>
    <version>{version}</version>
    <dependencies>
      <group targetFramework="net6.0-windows7.0">
{deps_xml}
      </group>
    </dependencies>
  </metadata>
</package>
""",
        encoding="utf-8",
    )
    return nuspec_path


def _make_nuspec_flat_nupkg(
    cache_root: Path,
    package_id: str,
    version: str,
    peer_deps: list[tuple[str, str]],
) -> Path:
    """Cria .nupkg (ZIP) em layout flat (Sicoob CCS_*):
    `<cache>/<id>.<version>.nupkg` com .nuspec dentro."""
    nupkg = cache_root / f"{package_id}.{version}.nupkg"
    deps_xml = "\n".join(
        f'        <dependency id="{pid}" version="{pver}" />'
        for pid, pver in peer_deps
    )
    nuspec_content = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>{package_id}</id>
    <version>{version}</version>
    <dependencies>
      <group targetFramework="net6.0">
{deps_xml}
      </group>
    </dependencies>
  </metadata>
</package>
"""
    with zipfile.ZipFile(nupkg, "w") as zf:
        zf.writestr(f"{package_id}.nuspec", nuspec_content)
    return nupkg


# ============================================================================
# Unit tests: helpers
# ============================================================================

def test_parse_version_basic():
    assert _parse_version("25.10.8") == (25, 10, 8)


def test_parse_version_with_prerelease():
    assert _parse_version("25.10.8-preview.1") == (25, 10, 8, 1)


def test_parse_version_empty():
    assert _parse_version("") == (0,)


def test_parse_pin_bracket_exact():
    assert _parse_pin("[25.10.8]") == (25, 10, 8)


def test_parse_pin_plain():
    assert _parse_pin("25.10.8") == (25, 10, 8)


def test_parse_pin_none_on_empty():
    assert _parse_pin("") is None


def test_range_satisfies_exact_match():
    ok, _ = _range_satisfies((25, 10, 8), "[25.10.8]")
    assert ok is True


def test_range_satisfies_exact_mismatch():
    ok, expected = _range_satisfies((25, 10, 7), "[25.10.8]")
    assert ok is False
    assert "25.10.8" in expected


def test_range_satisfies_floor_below():
    ok, _ = _range_satisfies((1, 0, 0), "3.24.0")
    assert ok is False


def test_range_satisfies_floor_above():
    ok, _ = _range_satisfies((3, 25, 0), "3.24.0")
    assert ok is True


def test_range_satisfies_bracket_range():
    ok, _ = _range_satisfies((1, 5, 0), "[1.0.0, 2.0.0)")
    assert ok is True
    ok2, _ = _range_satisfies((2, 0, 0), "[1.0.0, 2.0.0)")
    assert ok2 is False  # exclusive upper


def test_parse_peer_deps_extracts_all_groups():
    """Nuspec com múltiplos groups — agrega todos, dedupe."""
    xml = """<?xml version="1.0"?>
    <package>
      <metadata>
        <dependencies>
          <group targetFramework="net6.0">
            <dependency id="Foo" version="[1.0.0]" />
            <dependency id="Bar" version="2.0.0" />
          </group>
          <group targetFramework="net4.6.1">
            <dependency id="Foo" version="[1.0.0]" />
          </group>
        </dependencies>
      </metadata>
    </package>"""
    deps = _parse_peer_deps(xml)
    assert ("Foo", "[1.0.0]") in deps
    assert ("Bar", "2.0.0") in deps
    # Dedup (Foo aparece em 2 groups com mesma version)
    foo_count = sum(1 for (k, v) in deps if k == "Foo")
    assert foo_count == 1


# ============================================================================
# Integration: detector via fake cache
# ============================================================================

def test_d2_flags_peer_pin_below_required(tmp_path):
    """UIA 25.10.29 requer Runtime [25.10.29]; project pinou Runtime [25.10.8]
    → 1 finding."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _make_nuspec_hierarchical(
        cache,
        "UiPath.UIAutomation.Activities",
        "25.10.29",
        [("UiPath.UIAutomation.Activities.Runtime", "[25.10.29]")],
    )
    _make_nuspec_hierarchical(
        cache,
        "UiPath.UIAutomation.Activities.Runtime",
        "25.10.8",
        [],  # peer dummy sem subdeps
    )
    _, pc, fc = _mk_project(
        tmp_path,
        {
            "UiPath.UIAutomation.Activities": "[25.10.29]",
            "UiPath.UIAutomation.Activities.Runtime": "[25.10.8]",
        },
    )
    findings = detect_nuget_peer_conflict(_mk_rule(cache), fc, pc)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "D-2"
    assert "UiPath.UIAutomation.Activities" in f.message
    assert "Runtime" in f.message
    assert "25.10.29" in f.message
    assert "25.10.8" in f.message


def test_d2_silent_when_peer_pin_matches_required(tmp_path):
    """Quando peer pin satisfaz requirement → 0 findings."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _make_nuspec_hierarchical(
        cache,
        "UiPath.UIAutomation.Activities",
        "25.10.8",
        [("UiPath.UIAutomation.Activities.Runtime", "[25.10.8]")],
    )
    _, pc, fc = _mk_project(
        tmp_path,
        {
            "UiPath.UIAutomation.Activities": "[25.10.8]",
            "UiPath.UIAutomation.Activities.Runtime": "[25.10.8]",
        },
    )
    findings = detect_nuget_peer_conflict(_mk_rule(cache), fc, pc)
    assert findings == []


def test_d2_silent_when_peer_not_in_project_deps(tmp_path):
    """Peer requirement existe no nuspec mas peer NÃO está em project.json
    → 0 findings (NuGet resolve transitivamente sem conflito)."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _make_nuspec_hierarchical(
        cache,
        "UiPath.UIAutomation.Activities",
        "25.10.8",
        [("SomeTransitive", "[1.0.0]")],
    )
    _, pc, fc = _mk_project(
        tmp_path, {"UiPath.UIAutomation.Activities": "[25.10.8]"}
    )
    assert detect_nuget_peer_conflict(_mk_rule(cache), fc, pc) == []


def test_d2_silent_when_nuspec_not_found(tmp_path):
    """Cache vazio (nuspec não localizado) → 0 findings (offline-tolerant)."""
    cache = tmp_path / "empty_cache"
    cache.mkdir()
    _, pc, fc = _mk_project(
        tmp_path, {"UiPath.UIAutomation.Activities": "[25.10.8]"}
    )
    # Override cache + também precisamos garantir que default ~/.nuget não
    # interfira: usamos package id que sabidamente não está no cache real.
    rule = _mk_rule(cache)
    findings = detect_nuget_peer_conflict(rule, fc, pc)
    # Não deveria emit nada — primary nem cached.
    # (Se ~/.nuget acidentalmente tiver, o teste poderia falsar; usar pkg name fake.)
    assert findings == []


def test_d2_handles_flat_nupkg_layout(tmp_path):
    """Cache flat (Sicoob CCS_*): `<id>.<version>.nupkg` com .nuspec dentro
    do ZIP. Detector deve extrair."""
    cache = tmp_path / "flat_cache"
    cache.mkdir()
    _make_nuspec_flat_nupkg(
        cache,
        "CCS_Primary",
        "1.0.0",
        [("CCS_Peer", "[2.0.0]")],
    )
    _, pc, fc = _mk_project(
        tmp_path,
        {
            "CCS_Primary": "[1.0.0]",
            "CCS_Peer": "[1.0.0]",  # peer pinado abaixo do exigido
        },
    )
    findings = detect_nuget_peer_conflict(_mk_rule(cache), fc, pc)
    assert len(findings) == 1
    assert "CCS_Peer" in findings[0].message


def test_d2_skips_non_project_json_files(tmp_path):
    """fc apontando para XAML (não project.json) → 0 findings."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _, pc, _ = _mk_project(
        tmp_path, {"UiPath.UIAutomation.Activities": "[25.10.8]"}
    )
    xaml = pc.root / "Foo.xaml"
    xaml.write_text(
        '<?xml version="1.0"?>\n<Activity/>', encoding="utf-8"
    )
    fc = FileContext(xaml)
    assert detect_nuget_peer_conflict(_mk_rule(cache), fc, pc) == []


def test_d2_returns_empty_when_no_project_context(tmp_path):
    """pc=None → 0 findings."""
    f = tmp_path / "project.json"
    f.write_text("{}", encoding="utf-8")
    fc = FileContext(f)
    assert detect_nuget_peer_conflict(_mk_rule(), fc, None) == []


def test_d2_multiple_conflicts_multiple_findings(tmp_path):
    """Múltiplos peer conflicts → múltiplos findings (1 por conflito)."""
    cache = tmp_path / "cache"
    cache.mkdir()
    _make_nuspec_hierarchical(
        cache,
        "Primary",
        "1.0.0",
        [("PeerA", "[2.0.0]"), ("PeerB", "[3.0.0]")],
    )
    _, pc, fc = _mk_project(
        tmp_path,
        {
            "Primary": "[1.0.0]",
            "PeerA": "[1.0.0]",  # abaixo de [2.0.0]
            "PeerB": "[1.0.0]",  # abaixo de [3.0.0]
        },
    )
    findings = detect_nuget_peer_conflict(_mk_rule(cache), fc, pc)
    assert len(findings) == 2
    msgs = " ".join(f.message for f in findings)
    assert "PeerA" in msgs
    assert "PeerB" in msgs


# ============================================================================
# Schema validation
# ============================================================================

def test_d2_loader_validates_apply_class():
    """D-2 em rules.yaml deve declarar apply_class explícito (python
    detector). Loader rejeita silente default contextual."""
    from uip_engine.loader import load_rules
    from uip_engine import detectors, fixers

    rules_path = Path(__file__).resolve().parents[1] / "rules.yaml"
    rules = load_rules(
        rules_path,
        registered_detectors=set(detectors.REGISTRY.keys()),
        registered_fixers=set(fixers.REGISTRY.keys()),
    )
    d2 = next((r for r in rules if r.id == "D-2"), None)
    assert d2 is not None
    assert d2.severity == Severity.ERROR
    assert d2.fix and d2.fix.get("apply_class") == "contextual"
