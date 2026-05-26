"""Tests for ENV-2: ensure legacy compat refs em XAML deploy Studio 23.10.

Cobre:
  - Detector `detect_env2_ensure_legacy_refs` (finding per ref faltando)
  - Integração com fixer `insert_assembly_reference` (já existente)
  - Idempotency (no findings quando todos 3 refs presentes)
  - Skip silente em XAMLs sem bloco refs
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from uip_engine.context import FileContext
from uip_engine.fixers import apply_insert_assembly_reference
from uip_engine.heuristics.legacy_refs import (
    detect_env2_ensure_legacy_refs,
    _LEGACY_REFS_REQUIRED,
)


_XAML_MISSING_ALL = """\
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


_XAML_COMPLETE = """\
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


_XAML_PARTIAL = """\
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" \
xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib" \
xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <TextExpression.ReferencesForImplementation>
    <scg:List x:TypeArguments="AssemblyReference" Capacity="4">
      <AssemblyReference>UiPath.System.Activities</AssemblyReference>
      <AssemblyReference>mscorlib</AssemblyReference>
      <AssemblyReference>System.Private.CoreLib</AssemblyReference>
      <AssemblyReference>System.Net.Primitives</AssemblyReference>
    </scg:List>
  </TextExpression.ReferencesForImplementation>
</Activity>
"""


_XAML_NO_REFS_BLOCK = """\
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence>
    <Assign />
  </Sequence>
</Activity>
"""


def _make_rule() -> SimpleNamespace:
    return SimpleNamespace(id="ENV-2", severity=2, category="breaking")


def _make_fc(tmp_path: Path, content: str, name: str = "x.xaml") -> FileContext:
    xaml = tmp_path / name
    xaml.write_text(content, encoding="utf-8")
    return FileContext(path=xaml)


# ---------- Detector tests ----------


def test_detect_emits_for_all_missing(tmp_path: Path) -> None:
    """XAML com TextExpression block mas zero refs legacy → 3 findings."""
    fc = _make_fc(tmp_path, _XAML_MISSING_ALL)
    findings = detect_env2_ensure_legacy_refs(_make_rule(), fc, None)
    assert len(findings) == 3
    names = sorted(f.fix_mechanical["name"] for f in findings)
    assert names == ["System", "System.Core", "mscorlib"]
    for f in findings:
        assert f.rule_id == "ENV-2"
        assert f.fix_mechanical["type"] == "insert_assembly_reference"


def test_detect_idempotent_when_all_present(tmp_path: Path) -> None:
    """XAML com TODOS 3 refs presentes → no findings."""
    fc = _make_fc(tmp_path, _XAML_COMPLETE)
    findings = detect_env2_ensure_legacy_refs(_make_rule(), fc, None)
    assert findings == []


def test_detect_emits_only_missing_subset(tmp_path: Path) -> None:
    """XAML com mscorlib mas faltando System + System.Core → 2 findings."""
    fc = _make_fc(tmp_path, _XAML_PARTIAL)
    findings = detect_env2_ensure_legacy_refs(_make_rule(), fc, None)
    assert len(findings) == 2
    names = sorted(f.fix_mechanical["name"] for f in findings)
    assert names == ["System", "System.Core"]


def test_detect_skip_when_no_refs_block(tmp_path: Path) -> None:
    """XAML sem TextExpression block (fragment/lib) → no findings."""
    fc = _make_fc(tmp_path, _XAML_NO_REFS_BLOCK)
    findings = detect_env2_ensure_legacy_refs(_make_rule(), fc, None)
    assert findings == []


def test_detect_skip_non_xaml(tmp_path: Path) -> None:
    """Não-XAML (ex: project.json) → no findings."""
    f = tmp_path / "project.json"
    f.write_text('{"name":"X"}', encoding="utf-8")
    fc = FileContext(path=f)
    findings = detect_env2_ensure_legacy_refs(_make_rule(), fc, None)
    assert findings == []


def test_required_set_matches_expected() -> None:
    """Smoke check da config — garante lista canonical."""
    assert _LEGACY_REFS_REQUIRED == frozenset({"mscorlib", "System", "System.Core"})


# ---------- End-to-end integration ----------


def test_detect_then_apply_insertion(tmp_path: Path) -> None:
    """Pipeline: detect emite finding → fixer insere ref → re-detect no-op."""
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_MISSING_ALL, encoding="utf-8")
    fc = FileContext(path=xaml)

    findings = detect_env2_ensure_legacy_refs(_make_rule(), fc, None)
    assert len(findings) == 3

    # Apply each fix
    for f in findings:
        changed = apply_insert_assembly_reference(
            xaml, f.fix_mechanical, dry_run=False,
        )
        assert changed is True

    # Verify all 3 refs now present
    out = xaml.read_text(encoding="utf-8")
    for required in _LEGACY_REFS_REQUIRED:
        assert f"<AssemblyReference>{required}</AssemblyReference>" in out

    # Re-detect must be no-op
    fc2 = FileContext(path=xaml)
    findings2 = detect_env2_ensure_legacy_refs(_make_rule(), fc2, None)
    assert findings2 == []
