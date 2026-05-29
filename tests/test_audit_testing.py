"""Regression tests for audit finding S-11 (lane: testing).

S-11 promised a deterministic auto-resolve: when a XAML declares a
`clr-namespace;assembly=<pkg>` whose assembly is NOT in
project.json::dependencies but IS canonically pinned (D-1*), the detector
should emit a `xmlns_assembly_resolve` / `add_package` mechanical pinned at
the canonical version.

The bug: `_load_d1_pinned_versions` re-parsed rules.yaml looking for a
`params['min']` key on rules whose id starts with "D-1". But D-1* rules are
synthesized at parse-time from `assets/canonical_pins.yaml` (canonical.py)
with param key `exact`, and they never live in rules.yaml at all. So the
function always returned {} and the deterministic path was dead code.

Fix: read package->exact-version directly from `uip_engine.canonical`
(the same source of truth as the synthesized D-1* rules).
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from uip_engine._types import Severity
from uip_engine.heuristics import testing as t
from uip_engine.canonical import canonical_pin_for, load_canonical


def _reset_cache():
    """Clear the per-process memoization so each test sees a fresh load."""
    t._D1_VERSIONS_CACHE = None


# --------------------------------------------------------------------------
# _load_d1_pinned_versions — sources from canonical, not rules.yaml 'min'
# --------------------------------------------------------------------------

def test_load_d1_pinned_versions_not_empty():
    """The whole point of S-11: this dict must NOT be permanently empty.

    Pre-fix it always returned {} (no 'min' key on synthesized D-1* rules).
    """
    _reset_cache()
    versions = t._load_d1_pinned_versions()
    assert isinstance(versions, dict)
    assert versions, "auto-resolve dict must not be empty (was dead code pre-fix)"


def test_load_d1_pinned_versions_matches_canonical_source():
    """Values must equal the canonical exact pins (single source of truth)."""
    _reset_cache()
    versions = t._load_d1_pinned_versions()
    data = load_canonical()
    expected = {e["package"]: e["exact"] for e in data["pins"]}
    assert versions == expected


def test_load_d1_pinned_versions_known_pin():
    """Spot-check a known core package resolves to its bare exact version."""
    _reset_cache()
    versions = t._load_d1_pinned_versions()
    assert versions.get("UiPath.System.Activities") == canonical_pin_for(
        "UiPath.System.Activities"
    )
    # bare semver, no brackets
    v = versions["UiPath.System.Activities"]
    assert "[" not in v and "]" not in v


def test_load_d1_pinned_versions_cached():
    """Second call returns the same memoized object."""
    _reset_cache()
    first = t._load_d1_pinned_versions()
    second = t._load_d1_pinned_versions()
    assert first is second


# --------------------------------------------------------------------------
# detect_s11 — the mechanical now actually fires for a pinned assembly
# --------------------------------------------------------------------------

def _make_rule():
    return SimpleNamespace(
        id="S-11",
        severity=Severity.ERROR,
        category="breaking",
        title="xmlns assembly não declarado",
        detect={"params": {"skip_prefixes": ["uix"]}},
        fix={"prose": "Declarar o assembly em project.json::dependencies."},
    )


def _make_fc(path: Path, content: str):
    return SimpleNamespace(path=path, active_content=content)


def _make_pc(root: Path):
    return SimpleNamespace(root=root)


def test_s11_emits_add_package_for_canonically_pinned_assembly(tmp_path):
    """A pinned assembly missing from deps -> deterministic add_package mech."""
    _reset_cache()
    # project.json declaring NO dependencies -> the pinned assembly is missing
    (tmp_path / "project.json").write_text(
        '{"name": "Proj", "dependencies": {}}', encoding="utf-8"
    )
    pkg = "UiPath.System.Activities"
    pin = canonical_pin_for(pkg)
    assert pin, "fixture precondition: package must be canonically pinned"

    xaml = (
        '<Activity xmlns:sysact="clr-namespace:UiPath.Core.Activities;'
        f'assembly={pkg}">\n  <sysact:Foo />\n</Activity>'
    )
    fc = _make_fc(tmp_path / "Main.xaml", xaml)
    pc = _make_pc(tmp_path)

    findings = t.detect_s11_xmlns_assembly_missing(_make_rule(), fc, pc)
    assert len(findings) == 1
    mech = findings[0].fix_mechanical
    assert mech is not None, "auto-resolve mechanical must fire for pinned asm"
    assert mech["type"] == "xmlns_assembly_resolve"
    assert mech["action"] == "add_package"
    assert mech["package"] == pkg
    assert mech["version"] == pin


def test_s11_no_mech_for_unpinned_assembly(tmp_path):
    """An assembly with no canonical pin -> finding but mechanical stays None."""
    _reset_cache()
    (tmp_path / "project.json").write_text(
        '{"name": "Proj", "dependencies": {}}', encoding="utf-8"
    )
    # Some third-party assembly that is NOT in canonical_pins.yaml
    pkg = "Some.ThirdParty.Activities.NotPinned"
    assert canonical_pin_for(pkg) is None

    xaml = (
        f'<Activity xmlns:tp="clr-namespace:Some.Ns;assembly={pkg}">\n'
        "  <tp:Foo />\n</Activity>"
    )
    fc = _make_fc(tmp_path / "Main.xaml", xaml)
    pc = _make_pc(tmp_path)

    findings = t.detect_s11_xmlns_assembly_missing(_make_rule(), fc, pc)
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


def test_s11_no_finding_when_assembly_declared(tmp_path):
    """If the pinned assembly IS declared in deps, no finding at all."""
    _reset_cache()
    pkg = "UiPath.System.Activities"
    pin = canonical_pin_for(pkg)
    (tmp_path / "project.json").write_text(
        f'{{"name": "Proj", "dependencies": {{"{pkg}": "[{pin}]"}}}}',
        encoding="utf-8",
    )
    xaml = (
        f'<Activity xmlns:sysact="clr-namespace:UiPath.Core.Activities;'
        f'assembly={pkg}">\n  <sysact:Foo />\n</Activity>'
    )
    fc = _make_fc(tmp_path / "Main.xaml", xaml)
    pc = _make_pc(tmp_path)

    findings = t.detect_s11_xmlns_assembly_missing(_make_rule(), fc, pc)
    assert findings == []


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
