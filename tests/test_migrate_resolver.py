"""Tests para migrate_resolver — offline clone do MigratedPackageVersionResolver.

Cobre:
  - NuGetVersion.parse + comparisons
  - get_recommended_version (SAME / UPDATED / UNRESOLVED)
  - check_project com fetch_versions injected (no HTTP)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from uip_engine.migrate_resolver import (
    NuGetVersion,
    ResolutionAction,
    ResolutionResult,
    check_project,
    fetch_versions_with_fallback,
    get_recommended_version,
    local_nupkgs_source,
)


# ---------------------------------------------------------------------------
# NuGetVersion.parse
# ---------------------------------------------------------------------------


def test_parse_simple_three_part() -> None:
    v = NuGetVersion.parse("25.10.8")
    assert (v.major, v.minor, v.patch) == (25, 10, 8)
    assert v.revision is None
    assert v.prerelease is None


def test_parse_four_part_with_revision() -> None:
    v = NuGetVersion.parse("25.10.8.0")
    assert (v.major, v.minor, v.patch, v.revision) == (25, 10, 8, 0)
    assert v.prerelease is None


def test_parse_prerelease() -> None:
    v = NuGetVersion.parse("25.10.8-preview.1")
    assert (v.major, v.minor, v.patch) == (25, 10, 8)
    assert v.prerelease == "preview.1"
    assert v.is_prerelease() is True


def test_parse_strips_range_brackets() -> None:
    v = NuGetVersion.parse("[25.10.8]")
    assert (v.major, v.minor, v.patch) == (25, 10, 8)


def test_parse_invalid_raises() -> None:
    with pytest.raises(ValueError):
        NuGetVersion.parse("not-a-version")


# ---------------------------------------------------------------------------
# Ordering comparisons
# ---------------------------------------------------------------------------


def test_ordering_within_minor() -> None:
    a = NuGetVersion.parse("25.10.8")
    b = NuGetVersion.parse("25.10.29")
    assert a < b
    assert b > a
    assert a != b


def test_ordering_across_minors() -> None:
    a = NuGetVersion.parse("25.10.8")
    b = NuGetVersion.parse("25.11.0")
    assert a < b


def test_prerelease_less_than_release() -> None:
    pre = NuGetVersion.parse("25.10.8-preview")
    release = NuGetVersion.parse("25.10.8")
    assert pre < release


def test_equality_same_version() -> None:
    a = NuGetVersion.parse("25.10.8")
    b = NuGetVersion.parse("25.10.8")
    assert a == b
    assert hash(a) == hash(b)


def test_equality_normalizes_revision_zero() -> None:
    # "25.10.8" and "25.10.8.0" sao tratadas como iguais (revision default 0).
    a = NuGetVersion.parse("25.10.8")
    b = NuGetVersion.parse("25.10.8.0")
    assert a == b


# ---------------------------------------------------------------------------
# get_recommended_version — algoritmo §6
# ---------------------------------------------------------------------------


def test_get_recommended_same_when_exact_pin_exists() -> None:
    """Caso #1 dossier: pin exato presente => SAME (KEEP)."""
    result = get_recommended_version(
        "UiPath.System.Activities", "25.4.4", ["25.4.4", "25.10.8", "25.10.29"]
    )
    assert result.action == ResolutionAction.SAME
    assert result.recommended_version == "25.4.4"


def test_get_recommended_updated_within_minor() -> None:
    """Caso #2 dossier: sem pin exato => UPDATED to highest patch in smallest minor band.

    Available > current = [25.10.10, 25.10.29, 25.11.0]
    smallestPatch = 25.10.10 (minor band 25.10)
    TakeWhile same major.minor => [25.10.10, 25.10.29]
    Max => 25.10.29
    """
    result = get_recommended_version(
        "X", "25.10.8", ["25.10.10", "25.10.29", "25.11.0"]
    )
    assert result.action == ResolutionAction.UPDATED
    assert result.recommended_version == "25.10.29"


def test_get_recommended_unresolved_when_no_candidates() -> None:
    """Caso #3 dossier: nenhuma version > current => UNRESOLVED."""
    result = get_recommended_version("X", "25.10.8", ["24.0.0"])
    assert result.action == ResolutionAction.UNRESOLVED
    assert result.recommended_version == "25.10.8"


def test_get_recommended_unresolved_when_no_versions() -> None:
    result = get_recommended_version("X", "1.0.0", [])
    assert result.action == ResolutionAction.UNRESOLVED


def test_get_recommended_skips_malformed_entries() -> None:
    # Entradas malformadas sao puladas; pin exato existe entre as validas.
    result = get_recommended_version(
        "X", "1.0.0", ["bogus", "1.0.0", "another-bad"]
    )
    assert result.action == ResolutionAction.SAME


def test_get_recommended_picks_smallest_minor_band() -> None:
    """Sanity: se smallest_patch eh 25.11.0 e tem 25.12.x, fica em 25.11."""
    result = get_recommended_version(
        "X", "25.10.8", ["25.11.0", "25.11.5", "25.12.0", "25.12.9"]
    )
    assert result.action == ResolutionAction.UPDATED
    assert result.recommended_version == "25.11.5"


def test_get_recommended_invalid_current_version() -> None:
    result = get_recommended_version("X", "not-a-version", ["1.0.0", "2.0.0"])
    assert result.action == ResolutionAction.UNRESOLVED
    assert "invalid current_version" in result.reason


# ---------------------------------------------------------------------------
# check_project — full pipeline com fetch injection
# ---------------------------------------------------------------------------


def test_check_project_with_injected_fetcher(tmp_path: Path) -> None:
    """End-to-end: project.json sintetico + fetcher mocked => ResolutionResults."""
    project = {
        "name": "Sample",
        "dependencies": {
            "UiPath.System.Activities": "[25.4.4]",
            "UiPath.UIAutomation.Activities": "[25.10.8]",
            "ObscurePackage.Lib": "[1.0.0]",
        },
    }
    project_json = tmp_path / "project.json"
    project_json.write_text(json.dumps(project), encoding="utf-8")

    versions_map = {
        "UiPath.System.Activities": ["25.4.4", "25.10.8", "25.10.29"],
        "UiPath.UIAutomation.Activities": ["25.10.21", "25.10.29"],
        "ObscurePackage.Lib": [],
    }

    def fake_fetch(package_id, **_kwargs):
        return list(versions_map.get(package_id, []))

    results = check_project(project_json, _fetch_versions=fake_fetch)
    by_id = {r.package_id: r for r in results}

    # System.Activities: 25.4.4 presente => SAME
    assert by_id["UiPath.System.Activities"].action == ResolutionAction.SAME
    assert by_id["UiPath.System.Activities"].recommended_version == "25.4.4"

    # UIAutomation: 25.10.8 ausente, candidates [25.10.21, 25.10.29] same minor =>
    # smallest 25.10.21, max within band => 25.10.29 (UPDATED)
    assert by_id["UiPath.UIAutomation.Activities"].action == ResolutionAction.UPDATED
    assert by_id["UiPath.UIAutomation.Activities"].recommended_version == "25.10.29"

    # ObscurePackage: lista vazia => UNRESOLVED
    assert by_id["ObscurePackage.Lib"].action == ResolutionAction.UNRESOLVED


def test_check_project_strips_brackets(tmp_path: Path) -> None:
    """Confirm que '[25.4.4]' eh tratado como '25.4.4'."""
    project = {
        "dependencies": {"X.Y": "[1.2.3]"},
    }
    pj = tmp_path / "project.json"
    pj.write_text(json.dumps(project), encoding="utf-8")

    captured = {}

    def fake_fetch(package_id, **_kwargs):
        captured["called"] = package_id
        return ["1.2.3"]

    results = check_project(pj, _fetch_versions=fake_fetch)
    assert results[0].current_version == "1.2.3"
    assert results[0].action == ResolutionAction.SAME


def test_check_project_handles_fetch_failure(tmp_path: Path) -> None:
    """Fetch error => UNRESOLVED com reason explicativa, nao crash."""
    import urllib.error

    project = {"dependencies": {"X.Y": "[1.0.0]"}}
    pj = tmp_path / "project.json"
    pj.write_text(json.dumps(project), encoding="utf-8")

    def boom(*_a, **_kw):
        raise urllib.error.URLError("offline")

    results = check_project(pj, _fetch_versions=boom)
    assert len(results) == 1
    assert results[0].action == ResolutionAction.UNRESOLVED
    assert "NuGet fetch failed" in results[0].reason


def test_resolution_result_to_dict() -> None:
    r = ResolutionResult(
        package_id="X",
        current_version="1.0.0",
        recommended_version="1.0.0",
        action=ResolutionAction.SAME,
        candidates_count=3,
        reason="exact pin exists",
    )
    d = r.to_dict()
    assert d["package_id"] == "X"
    assert d["action"] == "Same"
    assert d["candidates_count"] == 3


# ---------------------------------------------------------------------------
# Phase 2.1 (2026-05): local .nupkgs/ folder fallback.
# ---------------------------------------------------------------------------


_REAL_NUPKGS = Path(r"C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs")


def _make_fake_nupkg(folder: Path, pkg_id: str, version: str, nuspec_filename: str | None = None) -> Path:
    """Helper: synthesize a minimal valid .nupkg with embedded .nuspec."""
    import zipfile
    nuspec_filename = nuspec_filename or f"{pkg_id}.nuspec"
    nuspec_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>{pkg_id}</id>
    <version>{version}</version>
    <authors>test</authors>
    <description>Fake nupkg for tests</description>
  </metadata>
</package>
"""
    path = folder / f"{pkg_id}.{version}.nupkg"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(nuspec_filename, nuspec_xml)
    return path


@pytest.mark.skipif(
    not _REAL_NUPKGS.exists(),
    reason="Real .nupkgs folder absent (skip on CI)",
)
def test_local_nupkgs_source_parses_ccs() -> None:
    """Smoke real: scaneia .nupkgs/ Sicoob, confirma CCS_SipagDirect 3.0.3."""
    index = local_nupkgs_source(_REAL_NUPKGS)
    assert "CCS_SipagDirect" in index, f"keys: {sorted(index.keys())}"
    assert "3.0.3" in index["CCS_SipagDirect"]


def test_local_nupkgs_source_synthesized(tmp_path: Path) -> None:
    """Synthesize .nupkg + verify parse retorna id/version."""
    _make_fake_nupkg(tmp_path, "FakePkg.Foo", "1.2.3")
    _make_fake_nupkg(tmp_path, "Another.Pkg", "0.9.0")
    index = local_nupkgs_source(tmp_path)
    assert index["FakePkg.Foo"] == ["1.2.3"]
    assert index["Another.Pkg"] == ["0.9.0"]


def test_local_nupkgs_source_empty_folder(tmp_path: Path) -> None:
    """Pasta vazia => dict vazio, sem raise."""
    assert local_nupkgs_source(tmp_path) == {}


def test_local_nupkgs_source_missing_folder(tmp_path: Path) -> None:
    """Pasta inexistente => dict vazio, sem raise."""
    assert local_nupkgs_source(tmp_path / "does-not-exist") == {}


def test_local_nupkgs_source_tolerates_garbage(tmp_path: Path) -> None:
    """Arquivo .nupkg corrompido (nao zip) eh skipado, parse continua."""
    (tmp_path / "garbage.nupkg").write_bytes(b"this is not a zipfile")
    _make_fake_nupkg(tmp_path, "ValidPkg", "1.0.0")
    index = local_nupkgs_source(tmp_path)
    assert "ValidPkg" in index
    assert "garbage" not in str(index).lower()


def test_local_nupkgs_supplements_remote(tmp_path: Path) -> None:
    """Remote empty, local has CCS => check_project produces SAME action."""
    _make_fake_nupkg(tmp_path, "CCS_FakeLib", "2.0.0")

    project = {"dependencies": {"CCS_FakeLib": "[2.0.0]"}}
    pj = tmp_path / "project.json"
    pj.write_text(json.dumps(project), encoding="utf-8")

    def empty_remote(package_id, **_kwargs):
        return []  # NuGet public sabe nada

    results = check_project(
        pj,
        local_nupkgs_folder=tmp_path,
        _fetch_versions=empty_remote,
    )
    assert len(results) == 1
    assert results[0].package_id == "CCS_FakeLib"
    assert results[0].action == ResolutionAction.SAME
    assert results[0].recommended_version == "2.0.0"


def test_local_takes_precedence_for_local_ids(tmp_path: Path) -> None:
    """ID presente em ambos: local wins (source-of-truth proprietario)."""
    # Local tem 2.0.0; remote tem 5.0.0. Pin = [2.0.0]. Esperado: SAME (local
    # match), NAO UPDATED para 5.0.0 (que viria do remote se priorizado).
    _make_fake_nupkg(tmp_path, "Sicoob.Mixed", "2.0.0")

    project = {"dependencies": {"Sicoob.Mixed": "[2.0.0]"}}
    pj = tmp_path / "project.json"
    pj.write_text(json.dumps(project), encoding="utf-8")

    def rich_remote(package_id, **_kwargs):
        # Se remote fosse consultado, daria UPDATED para 5.0.0.
        return ["5.0.0", "5.1.0"]

    results = check_project(
        pj,
        local_nupkgs_folder=tmp_path,
        _fetch_versions=rich_remote,
    )
    assert results[0].action == ResolutionAction.SAME
    assert results[0].recommended_version == "2.0.0"


def test_remote_used_for_non_local_ids(tmp_path: Path) -> None:
    """ID NAO presente local => remote consultado normalmente."""
    _make_fake_nupkg(tmp_path, "OnlyLocal", "1.0.0")

    project = {"dependencies": {"OnlyRemote.Pkg": "[3.0.0]"}}
    pj = tmp_path / "project.json"
    pj.write_text(json.dumps(project), encoding="utf-8")

    captured = {}

    def remote(package_id, **_kwargs):
        captured["called"] = package_id
        return ["3.0.0"]

    results = check_project(
        pj,
        local_nupkgs_folder=tmp_path,
        _fetch_versions=remote,
    )
    assert captured["called"] == "OnlyRemote.Pkg"
    assert results[0].action == ResolutionAction.SAME


def test_fetch_versions_with_fallback_local_only(tmp_path: Path) -> None:
    """Test direct API: local hit retorna local versions, sem chamar remote."""
    _make_fake_nupkg(tmp_path, "LocalOnly.Lib", "9.9.9")

    def never_called(*_a, **_kw):
        raise AssertionError("remote should not be called when local hit")

    versions = fetch_versions_with_fallback(
        "LocalOnly.Lib",
        local_nupkgs_folder=tmp_path,
        _remote_fetcher=never_called,
    )
    assert versions == ["9.9.9"]


def test_fetch_versions_with_fallback_no_local(tmp_path: Path) -> None:
    """Test direct API: sem local match, remote chamado."""
    def remote(package_id, **_kwargs):
        return ["1.0.0", "2.0.0"]

    versions = fetch_versions_with_fallback(
        "Public.Pkg",
        local_nupkgs_folder=tmp_path,  # empty folder
        _remote_fetcher=remote,
    )
    assert versions == ["1.0.0", "2.0.0"]


def test_fetch_versions_with_fallback_backward_compat() -> None:
    """Sem local_nupkgs_folder, comportamento eh remote-only (passthrough)."""
    def remote(package_id, **_kwargs):
        return ["7.7.7"]

    versions = fetch_versions_with_fallback(
        "Public.Pkg",
        _remote_fetcher=remote,
    )
    assert versions == ["7.7.7"]


def test_check_project_backward_compat_no_local(tmp_path: Path) -> None:
    """check_project sem local_nupkgs_folder usa fetcher direto (Phase 2 path)."""
    project = {"dependencies": {"X.Y": "[1.0.0]"}}
    pj = tmp_path / "project.json"
    pj.write_text(json.dumps(project), encoding="utf-8")

    def fetch(package_id, **_kwargs):
        return ["1.0.0", "1.1.0"]

    results = check_project(pj, _fetch_versions=fetch)
    assert results[0].action == ResolutionAction.SAME
