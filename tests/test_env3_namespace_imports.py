"""Tests for ENV-3: ensure namespace imports em NamespacesForImplementation.

Cobre:
  - Detector `detect_env3_ensure_namespace_imports` (finding per missing import
    quando XAML usa namespace em VB expression)
  - Fixer `insert_namespace_import` (idempotency, indent preserve, BOM)
  - Idempotency: skip se namespace presente ou usage ausente
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from uip_engine.context import FileContext
from uip_engine._types import Rule, Severity
from uip_engine.fixers import apply_insert_namespace_import, apply_strip_namespace_import
from uip_engine.heuristics.legacy_refs import (
    detect_env3_ensure_namespace_imports,
    detect_env5_studio_namespace_baseline,
    detect_env6_stale_namespace_imports,
    _ENV3_NAMESPACE_PATTERNS,
    _STUDIO_BASELINE_NAMESPACE_IMPORTS,
)


def _wrap_xaml(ns_body: str, body_extra: str = "") -> str:
    return (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '  <TextExpression.NamespacesForImplementation>\n'
        '    <scg:List x:TypeArguments="x:String" Capacity="8">\n'
        f"{ns_body}"
        '    </scg:List>\n'
        '  </TextExpression.NamespacesForImplementation>\n'
        f"{body_extra}"
        '</Activity>\n'
    )


def _make_rule() -> SimpleNamespace:
    return SimpleNamespace(
        id="ENV-3",
        severity=2,
        category="breaking",
        fix={"prose": "fix"},
    )


def _real_rule(rid: str) -> Rule:
    return Rule(
        id=rid,
        severity=Severity.INFO,
        category="architectural",
        target="windows",
        title=f"test {rid}",
        description="",
        detect={"type": "python", "params": {}},
        fix={"apply_class": "deterministic", "prose": "fix"},
    )


def _make_fc(tmp_path: Path, content: str, name: str = "x.xaml") -> FileContext:
    xaml = tmp_path / name
    xaml.write_text(content, encoding="utf-8")
    return FileContext(path=xaml)


# ---------- Detector tests ----------


def test_detect_emits_when_networkcredential_used_no_import(tmp_path: Path) -> None:
    """XAML usa `new System.Net.NetworkCredential(...)` mas falta import."""
    body_extra = (
        '  <ui:Activity in_X="[new System.Net.NetworkCredential(string.Empty, '
        'CType(vSenha,SecureString)).Password]" />\n'
    )
    fc = _make_fc(tmp_path, _wrap_xaml(
        '      <x:String>System</x:String>\n'
        '      <x:String>System.Activities</x:String>\n',
        body_extra
    ))
    findings = detect_env3_ensure_namespace_imports(_make_rule(), fc, None)
    assert len(findings) == 1
    f = findings[0]
    assert f.fix_mechanical["type"] == "insert_namespace_import"
    assert f.fix_mechanical["name"] == "System.Net"


def test_detect_idempotent_when_import_present(tmp_path: Path) -> None:
    """XAML usa NetworkCredential MAS import System.Net presente → no finding."""
    body_extra = (
        '  <ui:Activity in_X="[new System.Net.NetworkCredential().Password]" />\n'
    )
    fc = _make_fc(tmp_path, _wrap_xaml(
        '      <x:String>System</x:String>\n'
        '      <x:String>System.Net</x:String>\n',
        body_extra
    ))
    findings = detect_env3_ensure_namespace_imports(_make_rule(), fc, None)
    # System.Net presente → no finding for that. Outros patterns também não usados.
    assert findings == []


def test_detect_skip_when_no_usage(tmp_path: Path) -> None:
    """XAML sem usage System.Net.* → no finding mesmo sem import."""
    body_extra = '  <ui:Activity Message="[1+1]" />\n'
    fc = _make_fc(tmp_path, _wrap_xaml(
        '      <x:String>System</x:String>\n',
        body_extra
    ))
    findings = detect_env3_ensure_namespace_imports(_make_rule(), fc, None)
    assert findings == []


def test_detect_multiple_namespaces_missing(tmp_path: Path) -> None:
    """XAML usa System.Net.* AND System.Text.RegularExpressions.Regex → 2 findings."""
    body_extra = (
        '  <ui:Activity X="[new System.Net.NetworkCredential().Password]" '
        'Y="[System.Text.RegularExpressions.Regex.IsMatch(s, p)]" />\n'
    )
    fc = _make_fc(tmp_path, _wrap_xaml(
        '      <x:String>System</x:String>\n',
        body_extra
    ))
    findings = detect_env3_ensure_namespace_imports(_make_rule(), fc, None)
    assert len(findings) == 2
    names = sorted(f.fix_mechanical["name"] for f in findings)
    assert names == ["System.Net", "System.Text.RegularExpressions"]


def test_detect_skip_when_no_namespaces_block(tmp_path: Path) -> None:
    """XAML sem bloco TextExpression.NamespacesForImplementation → no finding."""
    content = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">\n'
        '  <Sequence>\n'
        '    <Assign X="[new System.Net.NetworkCredential().Password]"/>\n'
        '  </Sequence>\n'
        '</Activity>\n'
    )
    fc = _make_fc(tmp_path, content)
    findings = detect_env3_ensure_namespace_imports(_make_rule(), fc, None)
    assert findings == []


def test_namespace_patterns_includes_critical_set() -> None:
    """Sanity: 3 critical namespaces presentes."""
    assert "System.Net" in _ENV3_NAMESPACE_PATTERNS
    assert "System.Runtime.CompilerServices" in _ENV3_NAMESPACE_PATTERNS
    assert "System.Text.RegularExpressions" in _ENV3_NAMESPACE_PATTERNS


# ---------- Fixer tests ----------


def test_fixer_inserts_namespace(tmp_path: Path) -> None:
    """Fixer adiciona namespace ao bloco."""
    f = tmp_path / "x.xaml"
    f.write_text(_wrap_xaml(
        '      <x:String>System</x:String>\n'
        '      <x:String>System.Activities</x:String>\n'
    ), encoding="utf-8")

    changed = apply_insert_namespace_import(
        f, {"name": "System.Net"}, dry_run=False,
    )
    assert changed is True
    out = f.read_text(encoding="utf-8")
    assert '<x:String>System.Net</x:String>' in out


def test_fixer_idempotent(tmp_path: Path) -> None:
    """Re-apply mesmo namespace = no-op."""
    f = tmp_path / "x.xaml"
    f.write_text(_wrap_xaml(
        '      <x:String>System</x:String>\n'
        '      <x:String>System.Net</x:String>\n'
    ), encoding="utf-8")

    changed = apply_insert_namespace_import(
        f, {"name": "System.Net"}, dry_run=False,
    )
    assert changed is False


def test_fixer_skip_invalid_name(tmp_path: Path) -> None:
    """Nome inválido (spaces, quotes, etc.) → skip safe."""
    f = tmp_path / "x.xaml"
    f.write_text(_wrap_xaml('      <x:String>System</x:String>\n'), encoding="utf-8")

    for bad in ["", "  ", "Sys tem", "System;Net", "System.Net'X"]:
        changed = apply_insert_namespace_import(
            f, {"name": bad}, dry_run=False,
        )
        assert changed is False, f"should reject invalid name {bad!r}"


def test_fixer_skip_no_block(tmp_path: Path) -> None:
    """XAML sem bloco namespaces → no-op."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">\n'
        '  <Sequence />\n'
        '</Activity>\n',
        encoding="utf-8",
    )
    changed = apply_insert_namespace_import(
        f, {"name": "System.Net"}, dry_run=False,
    )
    assert changed is False


def test_fixer_preserves_bom(tmp_path: Path) -> None:
    f = tmp_path / "x.xaml"
    raw = b"\xef\xbb\xbf" + _wrap_xaml(
        '      <x:String>System</x:String>\n'
    ).encode("utf-8")
    f.write_bytes(raw)

    apply_insert_namespace_import(f, {"name": "System.Net"}, dry_run=False)
    assert f.read_bytes().startswith(b"\xef\xbb\xbf")


# ---------- End-to-end integration ----------


def test_detect_then_apply_round_trip(tmp_path: Path) -> None:
    body_extra = (
        '  <ui:Activity X="[new System.Net.NetworkCredential().Password]" />\n'
    )
    f = tmp_path / "x.xaml"
    f.write_text(_wrap_xaml('      <x:String>System</x:String>\n', body_extra),
                 encoding="utf-8")

    fc = FileContext(path=f)
    findings = detect_env3_ensure_namespace_imports(_make_rule(), fc, None)
    assert len(findings) == 1

    changed = apply_insert_namespace_import(
        f, findings[0].fix_mechanical, dry_run=False,
    )
    assert changed is True

    out = f.read_text(encoding="utf-8")
    assert '<x:String>System.Net</x:String>' in out

    # Re-detect should be no-op
    fc2 = FileContext(path=f)
    findings2 = detect_env3_ensure_namespace_imports(_make_rule(), fc2, None)
    assert findings2 == []


def test_env5_emits_missing_studio_baseline_namespaces(tmp_path: Path) -> None:
    fc = _make_fc(tmp_path, _wrap_xaml(
        '      <x:String>System</x:String>\n'
        '      <x:String>System.Activities</x:String>\n'
    ))

    findings = detect_env5_studio_namespace_baseline(_real_rule("ENV-5"), fc, None)

    names = {f.fix_mechanical["name"] for f in findings}
    assert "GlobalConstantsNamespace" in names
    assert "GlobalVariablesNamespace" in names
    assert "System" not in names
    assert names.issubset(_STUDIO_BASELINE_NAMESPACE_IMPORTS)


def test_env6_strips_dynamicupdate_namespace(tmp_path: Path) -> None:
    f = tmp_path / "x.xaml"
    f.write_text(_wrap_xaml(
        '      <x:String>System</x:String>\n'
        '      <x:String>System.Activities.DynamicUpdate</x:String>\n'
    ), encoding="utf-8")
    fc = FileContext(path=f)

    findings = detect_env6_stale_namespace_imports(_real_rule("ENV-6"), fc, None)

    assert len(findings) == 1
    assert findings[0].fix_mechanical == {
        "type": "strip_namespace_import",
        "name": "System.Activities.DynamicUpdate",
    }
    assert apply_strip_namespace_import(f, findings[0].fix_mechanical, dry_run=False)
    assert "System.Activities.DynamicUpdate" not in f.read_text(encoding="utf-8")
