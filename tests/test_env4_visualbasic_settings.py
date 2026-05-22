"""Tests for ENV-4: normalize legacy `<mva:VisualBasic.Settings>` text-content.

ROOT CAUSE de BC30652/BC31424 isolated empiricamente (2026-05-22):
  - Studio "Import References" auto-fix substitui `<mva:VisualBasic.Settings>
    Assembly references...</mva:VisualBasic.Settings>` por
    `<VisualBasic.Settings><x:Null /></VisualBasic.Settings>` → BC clears.
  - Sem ENV-4 normalize, W-11g/W-11y/ENV-2 NÃO bastam — text-content força
    VB compiler em modo legacy resolution → facades v4 vs forwarders v6.

Cobre:
  - Detector emite finding pra forma text-content + self-closing
  - Skip canonical `<VisualBasic.Settings><x:Null /></VisualBasic.Settings>`
  - Skip XAML sem element
  - Fixer normalize text → canonical
  - Fixer normalize self-closing → canonical
  - Drop `xmlns:mva=...` se prefix unused (post-replacement)
  - Preserve `xmlns:mva=...` se mva: usado em outros lugares
  - Idempotente: re-apply em canonical = no-op
  - dry_run não escreve
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.rule_engine.context import FileContext
from scripts.rule_engine.fixers import apply_normalize_visualbasic_settings
from scripts.rule_engine.heuristics.legacy_refs import (
    detect_env4_normalize_vb_settings,
)


_XAML_LEGACY_TEXT = """\
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" \
xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities" \
xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <mva:VisualBasic.Settings>Assembly references and imported namespaces for internal implementation</mva:VisualBasic.Settings>
  <Sequence />
</Activity>
"""


_XAML_CANONICAL = """\
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" \
xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <VisualBasic.Settings>
    <x:Null />
  </VisualBasic.Settings>
  <Sequence />
</Activity>
"""


_XAML_SELF_CLOSING = """\
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" \
xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities" \
xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <mva:VisualBasic.Settings />
  <Sequence />
</Activity>
"""


_XAML_NO_VB_SETTINGS = """\
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence />
</Activity>
"""


_XAML_MVA_USED_ELSEWHERE = """\
<Activity xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities" \
xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" \
xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <mva:VisualBasic.Settings>legacy text</mva:VisualBasic.Settings>
  <mva:SomeOther />
</Activity>
"""


def _make_rule() -> SimpleNamespace:
    return SimpleNamespace(id="ENV-4", severity=2, category="breaking")


def _make_fc(tmp_path: Path, content: str, name: str = "x.xaml") -> FileContext:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return FileContext(path=p)


# ---------- Detector tests ----------


def test_detect_emits_for_legacy_text_content(tmp_path: Path) -> None:
    fc = _make_fc(tmp_path, _XAML_LEGACY_TEXT)
    findings = detect_env4_normalize_vb_settings(_make_rule(), fc, None)
    assert len(findings) == 1
    assert findings[0].rule_id == "ENV-4"
    assert findings[0].fix_mechanical["type"] == "normalize_visualbasic_settings"


def test_detect_emits_for_self_closing(tmp_path: Path) -> None:
    fc = _make_fc(tmp_path, _XAML_SELF_CLOSING)
    findings = detect_env4_normalize_vb_settings(_make_rule(), fc, None)
    assert len(findings) == 1


def test_detect_skip_canonical(tmp_path: Path) -> None:
    fc = _make_fc(tmp_path, _XAML_CANONICAL)
    findings = detect_env4_normalize_vb_settings(_make_rule(), fc, None)
    assert findings == []


def test_detect_skip_no_vb_settings(tmp_path: Path) -> None:
    fc = _make_fc(tmp_path, _XAML_NO_VB_SETTINGS)
    findings = detect_env4_normalize_vb_settings(_make_rule(), fc, None)
    assert findings == []


def test_detect_skip_non_xaml(tmp_path: Path) -> None:
    f = tmp_path / "project.json"
    f.write_text('{"name":"X"}', encoding="utf-8")
    fc = FileContext(path=f)
    findings = detect_env4_normalize_vb_settings(_make_rule(), fc, None)
    assert findings == []


# ---------- Fixer tests ----------


def test_apply_normalize_text_form(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_LEGACY_TEXT, encoding="utf-8")
    changed = apply_normalize_visualbasic_settings(xaml, {}, dry_run=False)
    assert changed is True
    out = xaml.read_text(encoding="utf-8")
    assert "<VisualBasic.Settings>" in out
    assert "<x:Null />" in out
    assert "</VisualBasic.Settings>" in out
    assert "<mva:VisualBasic.Settings" not in out
    # mva xmlns dropped (no other usage)
    assert "xmlns:mva" not in out


def test_apply_self_closing_form(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_SELF_CLOSING, encoding="utf-8")
    changed = apply_normalize_visualbasic_settings(xaml, {}, dry_run=False)
    assert changed is True
    out = xaml.read_text(encoding="utf-8")
    assert "<VisualBasic.Settings>" in out
    assert "<x:Null />" in out
    assert "<mva:VisualBasic.Settings" not in out


def test_apply_preserves_mva_when_used_elsewhere(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_MVA_USED_ELSEWHERE, encoding="utf-8")
    changed = apply_normalize_visualbasic_settings(xaml, {}, dry_run=False)
    assert changed is True
    out = xaml.read_text(encoding="utf-8")
    assert "<VisualBasic.Settings>" in out
    # mva xmlns kept (used by SomeOther)
    assert "xmlns:mva" in out
    assert "<mva:SomeOther" in out


def test_apply_idempotent(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_CANONICAL, encoding="utf-8")
    changed = apply_normalize_visualbasic_settings(xaml, {}, dry_run=False)
    assert changed is False


def test_apply_dry_run_no_write(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_LEGACY_TEXT, encoding="utf-8")
    before = xaml.read_bytes()
    changed = apply_normalize_visualbasic_settings(xaml, {}, dry_run=True)
    assert changed is True
    after = xaml.read_bytes()
    assert before == after


def test_apply_preserves_bom(tmp_path: Path) -> None:
    xaml = tmp_path / "x.xaml"
    xaml.write_bytes(b"\xef\xbb\xbf" + _XAML_LEGACY_TEXT.encode("utf-8"))
    changed = apply_normalize_visualbasic_settings(xaml, {}, dry_run=False)
    assert changed is True
    raw = xaml.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")


# ---------- End-to-end pipeline ----------


def test_pipeline_detect_then_fix_then_redetect(tmp_path: Path) -> None:
    """detect→apply→re-detect cycle: pós-fix detector must return empty."""
    xaml = tmp_path / "x.xaml"
    xaml.write_text(_XAML_LEGACY_TEXT, encoding="utf-8")
    fc = FileContext(path=xaml)

    findings = detect_env4_normalize_vb_settings(_make_rule(), fc, None)
    assert len(findings) == 1

    apply_normalize_visualbasic_settings(xaml, {}, dry_run=False)

    fc2 = FileContext(path=xaml)
    findings2 = detect_env4_normalize_vb_settings(_make_rule(), fc2, None)
    assert findings2 == []
