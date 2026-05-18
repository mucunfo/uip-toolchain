"""Tests para W-26: strip AssemblyReference Legacy redundante em Windows target.

Cobre:
  - Fixer `strip_assembly_reference` (idempotência, dry-run, BOM preserve)
  - Detector `detect_legacy_bcl_refs` (finding per ref Legacy)
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.rule_engine.context import FileContext
from scripts.rule_engine.fixers import apply_strip_assembly_reference
from scripts.rule_engine.heuristics.legacy_refs import detect_legacy_bcl_refs


_XAML_WITH_LEGACY_REFS = """\
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" \
xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib" \
xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <TextExpression.ReferencesForImplementation>
    <scg:List x:TypeArguments="AssemblyReference" Capacity="6">
      <AssemblyReference>UiPath.System.Activities</AssemblyReference>
      <AssemblyReference>mscorlib</AssemblyReference>
      <AssemblyReference>System.Core</AssemblyReference>
      <AssemblyReference>System</AssemblyReference>
      <AssemblyReference>System.Private.CoreLib</AssemblyReference>
      <AssemblyReference>System.Net.Primitives</AssemblyReference>
    </scg:List>
  </TextExpression.ReferencesForImplementation>
</Activity>
"""


_XAML_CLEAN = """\
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" \
xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib" \
xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <TextExpression.ReferencesForImplementation>
    <scg:List x:TypeArguments="AssemblyReference" Capacity="3">
      <AssemblyReference>UiPath.System.Activities</AssemblyReference>
      <AssemblyReference>System.Private.CoreLib</AssemblyReference>
      <AssemblyReference>System.Net.Primitives</AssemblyReference>
    </scg:List>
  </TextExpression.ReferencesForImplementation>
</Activity>
"""


def _make_rule() -> SimpleNamespace:
    return SimpleNamespace(id="W-26", severity=2, category="breaking")


# ---------- Fixer tests ----------


def test_strip_mscorlib(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_WITH_LEGACY_REFS, encoding="utf-8")
    changed = apply_strip_assembly_reference(xaml, {"name": "mscorlib"}, dry_run=False)
    assert changed is True
    result = xaml.read_text(encoding="utf-8")
    assert "<AssemblyReference>mscorlib</AssemblyReference>" not in result
    # Outras refs preservadas
    assert "<AssemblyReference>UiPath.System.Activities</AssemblyReference>" in result
    assert "<AssemblyReference>System.Private.CoreLib</AssemblyReference>" in result
    assert "<AssemblyReference>System.Net.Primitives</AssemblyReference>" in result
    assert "<AssemblyReference>System.Core</AssemblyReference>" in result  # ainda não strippado nessa chamada


def test_strip_idempotent(tmp_path: Path) -> None:
    """Second invocation should be no-op when ref already absent."""
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_WITH_LEGACY_REFS, encoding="utf-8")
    apply_strip_assembly_reference(xaml, {"name": "mscorlib"}, dry_run=False)
    changed = apply_strip_assembly_reference(xaml, {"name": "mscorlib"}, dry_run=False)
    assert changed is False


def test_strip_all_three(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_WITH_LEGACY_REFS, encoding="utf-8")
    for ref in ("mscorlib", "System", "System.Core"):
        assert apply_strip_assembly_reference(xaml, {"name": ref}, dry_run=False) is True
    result = xaml.read_text(encoding="utf-8")
    assert "<AssemblyReference>mscorlib</AssemblyReference>" not in result
    assert "<AssemblyReference>System</AssemblyReference>" not in result
    assert "<AssemblyReference>System.Core</AssemblyReference>" not in result
    # .NET 6 refs intactas
    assert "System.Private.CoreLib" in result
    assert "System.Net.Primitives" in result
    # Não strip "System.X" como se fosse "System"
    assert "System.Private.CoreLib" in result


def test_strip_dry_run_no_write(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    original = _XAML_WITH_LEGACY_REFS
    xaml.write_text(original, encoding="utf-8")
    changed = apply_strip_assembly_reference(xaml, {"name": "mscorlib"}, dry_run=True)
    assert changed is True
    # Sem escrita em dry_run
    assert xaml.read_text(encoding="utf-8") == original


def test_strip_preserves_bom(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    bom = b"\xef\xbb\xbf"
    xaml.write_bytes(bom + _XAML_WITH_LEGACY_REFS.encode("utf-8"))
    apply_strip_assembly_reference(xaml, {"name": "mscorlib"}, dry_run=False)
    raw = xaml.read_bytes()
    assert raw.startswith(bom)


def test_strip_invalid_name(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_WITH_LEGACY_REFS, encoding="utf-8")
    # Empty
    assert apply_strip_assembly_reference(xaml, {"name": ""}, dry_run=False) is False
    # None
    assert apply_strip_assembly_reference(xaml, {}, dry_run=False) is False
    # Caractere inválido (espaço)
    assert apply_strip_assembly_reference(xaml, {"name": "mscorlib v4"}, dry_run=False) is False


def test_strip_no_match_returns_false(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_CLEAN, encoding="utf-8")
    changed = apply_strip_assembly_reference(xaml, {"name": "mscorlib"}, dry_run=False)
    assert changed is False


# ---------- Detector tests ----------


def test_detect_emits_finding_per_legacy_ref(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_WITH_LEGACY_REFS, encoding="utf-8")
    fc = FileContext(path=xaml)
    findings = detect_legacy_bcl_refs(_make_rule(), fc, None)
    names = {f.fix_mechanical["name"] for f in findings}
    assert names == {"mscorlib", "System", "System.Core"}
    # Mechanical type correto
    for f in findings:
        assert f.fix_mechanical["type"] == "strip_assembly_reference"
        assert f.rule_id == "W-26"


def test_detect_clean_xaml_no_findings(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_CLEAN, encoding="utf-8")
    fc = FileContext(path=xaml)
    findings = detect_legacy_bcl_refs(_make_rule(), fc, None)
    assert findings == []


def test_detect_skip_non_xaml(tmp_path: Path) -> None:
    other = tmp_path / "x.txt"
    other.write_text(_XAML_WITH_LEGACY_REFS, encoding="utf-8")
    fc = FileContext(path=other)
    findings = detect_legacy_bcl_refs(_make_rule(), fc, None)
    assert findings == []


def test_detect_skip_xaml_without_refs_block(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />\n',
        encoding="utf-8",
    )
    fc = FileContext(path=xaml)
    findings = detect_legacy_bcl_refs(_make_rule(), fc, None)
    assert findings == []
