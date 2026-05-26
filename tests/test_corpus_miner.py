"""Tests for scripts/rule_engine/corpus_miner.py."""
from __future__ import annotations

import textwrap
import zipfile
from pathlib import Path

import pytest

from scripts.rule_engine import corpus_miner
from scripts.rule_engine.corpus_miner import (
    ArgSpec,
    MineStats,
    extract_property_declarations,
    generate_python_module,
    iter_nupkg_xamls,
    iter_xaml_files,
    mine,
)


# ---------------------------------------------------------------------------
# Fixtures: synthetic XAMLs
# ---------------------------------------------------------------------------

_XAML_TMPL = textwrap.dedent("""\
<Activity mc:Ignorable="sap sap2010" x:Class="{cls}"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:s="clr-namespace:System;assembly=System.Private.CoreLib"
    xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
{members}
  </x:Members>
  <Sequence />
</Activity>
""")


def _make_xaml(cls: str, properties: list[tuple[str, str]]) -> bytes:
    members = "\n".join(
        f'    <x:Property Name="{n}" Type="{t}" />' for n, t in properties
    )
    return _XAML_TMPL.format(cls=cls, members=members).encode("utf-8")


# ---------------------------------------------------------------------------
# extract_property_declarations
# ---------------------------------------------------------------------------

def test_extract_property_declarations_basic():
    data = _make_xaml(
        "Foo",
        [
            ("in_Config", "InArgument(scg:Dictionary(x:String, x:String))"),
            ("in_StPrefixoLog", "InArgument(x:String)"),
            ("out_BlSuccess", "OutArgument(x:Boolean)"),
        ],
    )
    result = list(extract_property_declarations(data))
    assert ("in_Config", "InArgument(scg:Dictionary(x:String, x:String))") in result
    assert ("in_StPrefixoLog", "InArgument(x:String)") in result
    assert ("out_BlSuccess", "OutArgument(x:Boolean)") in result
    assert len(result) == 3


def test_extract_property_declarations_skips_non_direction_prefix():
    data = _make_xaml(
        "Foo",
        [
            ("in_Config", "InArgument(x:String)"),
            ("PrivateField", "InArgument(x:String)"),     # no direction prefix
            ("strSomething", "InArgument(x:String)"),     # no direction prefix
        ],
    )
    result = list(extract_property_declarations(data))
    names = [n for n, _ in result]
    assert "in_Config" in names
    assert "PrivateField" not in names
    assert "strSomething" not in names


def test_extract_property_declarations_skips_local_namespace():
    data = _make_xaml(
        "Foo",
        [
            ("in_Config", "InArgument(x:String)"),
            ("in_MyEntity", "InArgument(local:MyEntity)"),
        ],
    )
    result = list(extract_property_declarations(data))
    names = [n for n, _ in result]
    assert "in_Config" in names
    assert "in_MyEntity" not in names  # local: namespace excluded


def test_extract_property_declarations_handles_malformed_xml():
    data = b"<not really xml </Activity"
    result = list(extract_property_declarations(data))
    assert result == []


def test_extract_property_declarations_handles_bom():
    data = b"\xef\xbb\xbf" + _make_xaml("Foo", [("in_Config", "InArgument(x:String)")])
    result = list(extract_property_declarations(data))
    assert result == [("in_Config", "InArgument(x:String)")]


# ---------------------------------------------------------------------------
# iter_xaml_files -- skip _BeforeMigration_* and hidden dirs
# ---------------------------------------------------------------------------

def test_skip_BeforeMigration(tmp_path: Path):
    # Normal XAML
    (tmp_path / "Main.xaml").write_bytes(_make_xaml("Main", [("in_Config", "InArgument(x:String)")]))

    # _BeforeMigration_ file at root
    (tmp_path / "_BeforeMigration_Main.xaml").write_bytes(
        _make_xaml("BMain", [("in_Foo", "InArgument(x:String)")])
    )

    # _BeforeMigration_* sibling dir with XAMLs inside (should be pruned)
    bm_dir = tmp_path / "_BeforeMigration_2026_05_25"
    bm_dir.mkdir()
    (bm_dir / "Old.xaml").write_bytes(_make_xaml("Old", [("in_Bar", "InArgument(x:String)")]))

    # Hidden dir
    hidden = tmp_path / ".tmp"
    hidden.mkdir()
    (hidden / "Tmp.xaml").write_bytes(_make_xaml("Tmp", [("in_Baz", "InArgument(x:String)")]))

    # Nested normal XAML
    sub = tmp_path / "Workflows"
    sub.mkdir()
    (sub / "Sub.xaml").write_bytes(_make_xaml("Sub", [("in_Config", "InArgument(x:String)")]))

    found = {p.name for p in iter_xaml_files(tmp_path)}
    assert "Main.xaml" in found
    assert "Sub.xaml" in found
    assert "_BeforeMigration_Main.xaml" not in found
    assert "Old.xaml" not in found
    assert "Tmp.xaml" not in found


# ---------------------------------------------------------------------------
# iter_nupkg_xamls -- real nupkg
# ---------------------------------------------------------------------------

_NUPKGS_DIR = Path(r"C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs")
_SAMPLE_NUPKG = _NUPKGS_DIR / "CCS_SipagDirect.3.0.3.nupkg"


@pytest.mark.skipif(not _SAMPLE_NUPKG.exists(), reason="sample CCS nupkg not present")
def test_nupkg_iteration():
    xamls = list(iter_nupkg_xamls(_SAMPLE_NUPKG))
    assert len(xamls) >= 1, "expected at least one XAML in CCS_SipagDirect"
    # Each entry should be (member_name, bytes)
    for member, data in xamls[:3]:
        assert member.lower().endswith(".xaml")
        assert isinstance(data, (bytes, bytearray))
        assert len(data) > 0


def test_iter_nupkg_xamls_handles_bad_zip(tmp_path: Path):
    bad = tmp_path / "broken.nupkg"
    bad.write_bytes(b"not a real zip file")
    result = list(iter_nupkg_xamls(bad))
    assert result == []


# ---------------------------------------------------------------------------
# mine -- majority vote, confidence, min_occurrences
# ---------------------------------------------------------------------------

def _seed_xamls(root: Path, declarations: list[tuple[str, str]], *, copies: int = 1) -> None:
    """Write `copies` XAMLs each declaring all `declarations` properties."""
    for i in range(copies):
        path = root / f"wf_{len(list(root.glob('*.xaml')))}_{i}.xaml"
        path.write_bytes(_make_xaml(f"Wf{i}", declarations))


def test_majority_vote_confidence(tmp_path: Path):
    """10x type A + 2x type B -> dominant A, confidence 10/12."""
    type_a = "InArgument(x:String)"
    type_b = "InArgument(x:Int32)"

    # 10 XAMLs declaring in_Mixed as type_a
    for i in range(10):
        (tmp_path / f"A_{i}.xaml").write_bytes(_make_xaml(f"A{i}", [("in_Mixed", type_a)]))
    # 2 XAMLs declaring in_Mixed as type_b
    for i in range(2):
        (tmp_path / f"B_{i}.xaml").write_bytes(_make_xaml(f"B{i}", [("in_Mixed", type_b)]))

    result = mine([tmp_path], include_nupkgs=False, min_occurrences=1)
    assert "in_Mixed" in result
    spec = result["in_Mixed"]
    assert spec.canonical_type == type_a
    assert spec.occurrences == 12
    assert spec.confidence == pytest.approx(10 / 12, abs=1e-4)
    # Alternatives should record type_b with count 2
    assert (type_b, 2) in spec.alternatives


def test_min_occurrences_filter(tmp_path: Path):
    # in_Rare seen 2x, in_Common seen 5x
    for i in range(2):
        (tmp_path / f"R_{i}.xaml").write_bytes(_make_xaml(f"R{i}", [("in_Rare", "InArgument(x:String)")]))
    for i in range(5):
        (tmp_path / f"C_{i}.xaml").write_bytes(_make_xaml(f"C{i}", [("in_Common", "InArgument(x:String)")]))

    result = mine([tmp_path], include_nupkgs=False, min_occurrences=3)
    assert "in_Common" in result
    assert "in_Rare" not in result


def test_mine_collects_stats(tmp_path: Path):
    for i in range(3):
        (tmp_path / f"X_{i}.xaml").write_bytes(_make_xaml(f"X{i}", [("in_Config", "InArgument(x:String)")]))
    stats = MineStats(roots=[])
    result = mine([tmp_path], include_nupkgs=False, min_occurrences=1, stats=stats)
    assert stats.fs_xamls == 3
    assert stats.raw_declarations == 3
    assert stats.unique_args == 1
    assert stats.canonical_args_after_filter == 1
    assert "in_Config" in result


# ---------------------------------------------------------------------------
# generate_python_module
# ---------------------------------------------------------------------------

def test_generate_python_module_round_trip(tmp_path: Path):
    canonical = {
        "in_Config": ArgSpec("InArgument(scg:Dictionary(x:String, x:String))", 1.0, 100),
        "in_StPrefixoLog": ArgSpec("InArgument(x:String)", 0.95, 80, (("InArgument(x:Int32)", 4),)),
    }
    stats = MineStats(
        roots=[Path("fake/root")],
        fs_xamls=10, nupkg_xamls=5, nupkgs_scanned=2,
        raw_declarations=200, unique_args=20, canonical_args_after_filter=2,
    )
    out = tmp_path / "_canonical_args.py"
    generate_python_module(canonical, out, stats=stats, min_occurrences=3)

    # Module should be importable
    import importlib.util
    spec = importlib.util.spec_from_file_location("_gen_canonical_args", out)
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)

    assert "in_Config" in mod.CANONICAL_ARGS
    assert mod.CANONICAL_ARGS["in_Config"].canonical_type == "InArgument(scg:Dictionary(x:String, x:String))"
    assert mod.lookup("in_Config") == "InArgument(scg:Dictionary(x:String, x:String))"
    assert mod.lookup("nonexistent") is None
    # Below threshold returns None
    assert mod.lookup("in_StPrefixoLog", min_confidence=0.99) is None
    assert mod.lookup("in_StPrefixoLog", min_confidence=0.5) == "InArgument(x:String)"


# ---------------------------------------------------------------------------
# Smoke test on real corpus
# ---------------------------------------------------------------------------

_DESKTOP_TEMP = Path(r"C:\Users\lisan\Desktop\temp")


@pytest.mark.skipif(
    not _NUPKGS_DIR.exists(),
    reason="real .nupkgs corpus not present",
)
def test_smoke_real_corpus():
    """Scan real .nupkgs/ + a slice of Desktop/temp/; expect in_Config canonical."""
    roots: list[Path] = [_NUPKGS_DIR]
    if _DESKTOP_TEMP.exists():
        # Limit to one subdir to keep test fast
        subdirs = [p for p in _DESKTOP_TEMP.iterdir() if p.is_dir()][:2]
        roots.extend(subdirs)

    stats = MineStats(roots=[])
    result = mine(roots, include_nupkgs=True, min_occurrences=1, stats=stats)

    # CCS libs almost always reference in_Config or in_StPrefixoLog
    assert stats.fs_xamls + stats.nupkg_xamls > 0
    # At least one canonical arg should emerge
    assert len(result) >= 1
    # Confidence values are bounded
    for spec in result.values():
        assert 0.0 < spec.confidence <= 1.0
        assert spec.occurrences >= 1
