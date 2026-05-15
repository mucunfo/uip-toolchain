"""Tests for heuristics/hygiene.py — HY-1..6."""
import json
from pathlib import Path

import pytest

from scripts.rule_engine._types import Rule, Severity
from scripts.rule_engine.context import FileContext, ProjectContext
from scripts.rule_engine.heuristics.hygiene import (
    detect_hy1_merge_markers,
    detect_hy2_placeholder_description,
    detect_hy3_main_empty,
    detect_hy4_gitignore,
    detect_hy5_eol_mix,
    detect_hy6_bom_json,
)
from scripts.rule_engine.fixers import REGISTRY as FIXER_REGISTRY


def _rule(rid: str, sev: Severity = Severity.WARN, mech: dict | None = None) -> Rule:
    return Rule(
        id=rid, severity=sev, category="architectural", target="all",
        title=f"test {rid}", description="",
        detect={"type": "python", "params": {}},
        fix={"apply_class": "deterministic" if mech else "contextual",
             "mechanical": mech, "prose": "fix"} if mech is not None
            else {"apply_class": "contextual", "prose": "fix"},
    )


def _pc(tmp_path: Path, manifest: dict | None = None) -> ProjectContext:
    pj = tmp_path / "project.json"
    manifest = manifest or {"name": "TestProject", "description": "Test"}
    pj.write_text(json.dumps(manifest), encoding="utf-8")
    return ProjectContext(root=tmp_path, project_json=manifest)


# ---------- HY-1 merge markers ----------

def test_hy1_no_markers(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text("<Activity><Sequence /></Activity>", encoding="utf-8")
    fc = FileContext(f)
    assert detect_hy1_merge_markers(_rule("HY-1"), fc, None) == []


def test_hy1_detects_markers(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text(
        "<Activity>\n<<<<<<< HEAD\n<Sequence />\n=======\n<Sequence x:Key='b' />\n>>>>>>> branch\n</Activity>",
        encoding="utf-8",
    )
    fc = FileContext(f)
    findings = detect_hy1_merge_markers(_rule("HY-1", Severity.ERROR), fc, None)
    assert len(findings) == 3


# ---------- HY-2 placeholder description ----------

def test_hy2_real_description_ok(tmp_path):
    pc = _pc(tmp_path, {"name": "Foo", "description": "Real automation purpose"})
    fc = FileContext(pc.root / "project.json")
    r = _rule("HY-2", mech={"type": "set_json_field"})
    assert detect_hy2_placeholder_description(r, fc, pc) == []


def test_hy2_blank_process(tmp_path):
    pc = _pc(tmp_path, {"name": "Foo", "description": "Blank Process"})
    fc = FileContext(pc.root / "project.json")
    r = _rule("HY-2", mech={"type": "set_json_field"})
    findings = detect_hy2_placeholder_description(r, fc, pc)
    assert len(findings) == 1
    assert findings[0].fix_mechanical["value"].startswith("Projeto Sicoob — ")


def test_hy2_empty_description(tmp_path):
    pc = _pc(tmp_path, {"name": "Foo", "description": ""})
    fc = FileContext(pc.root / "project.json")
    r = _rule("HY-2", mech={"type": "set_json_field"})
    findings = detect_hy2_placeholder_description(r, fc, pc)
    assert len(findings) == 1


# ---------- HY-3 Main.xaml empty ----------

_EMPTY_MAIN = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
    '<x:Members></x:Members>\n'
    '<Sequence />\n'
    '</Activity>\n'
)
_NONEMPTY_MAIN = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
    'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
    '<x:Members></x:Members>\n'
    '<Sequence><ui:LogMessage /></Sequence>\n'
    '</Activity>\n'
)


def test_hy3_empty(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(_EMPTY_MAIN, encoding="utf-8")
    fc = FileContext(f)
    findings = detect_hy3_main_empty(_rule("HY-3"), fc, None)
    assert len(findings) == 1


def test_hy3_non_main_skip(tmp_path):
    f = tmp_path / "Process.xaml"
    f.write_text(_EMPTY_MAIN, encoding="utf-8")
    fc = FileContext(f)
    assert detect_hy3_main_empty(_rule("HY-3"), fc, None) == []


def test_hy3_nonempty_no_finding(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(_NONEMPTY_MAIN, encoding="utf-8")
    fc = FileContext(f)
    assert detect_hy3_main_empty(_rule("HY-3"), fc, None) == []


# ---------- HY-4 .gitignore ----------

def test_hy4_missing_gitignore(tmp_path):
    pc = _pc(tmp_path)
    fc = FileContext(pc.root / "project.json")
    r = _rule("HY-4", mech={"type": "gitignore_append_lines"})
    findings = detect_hy4_gitignore(r, fc, pc)
    assert len(findings) == 1
    assert ".local/" in findings[0].fix_mechanical["missing"]


def test_hy4_complete_gitignore(tmp_path):
    pc = _pc(tmp_path)
    (pc.root / ".gitignore").write_text(
        ".local/\nbin/\nobj/\n*.user\n.uipath/\n", encoding="utf-8"
    )
    fc = FileContext(pc.root / "project.json")
    r = _rule("HY-4", mech={"type": "gitignore_append_lines"})
    assert detect_hy4_gitignore(r, fc, pc) == []


def test_hy4_partial_gitignore(tmp_path):
    pc = _pc(tmp_path)
    (pc.root / ".gitignore").write_text("bin/\nobj/\n", encoding="utf-8")
    fc = FileContext(pc.root / "project.json")
    r = _rule("HY-4", mech={"type": "gitignore_append_lines"})
    findings = detect_hy4_gitignore(r, fc, pc)
    assert len(findings) == 1
    missing = findings[0].fix_mechanical["missing"]
    assert ".local/" in missing
    assert "bin/" not in missing


def test_hy4_fixer_appends(tmp_path):
    gi = tmp_path / ".gitignore"
    gi.write_text("bin/\nobj/\n", encoding="utf-8")
    fixer = FIXER_REGISTRY["gitignore_append_lines"]
    changed = fixer(gi, {"missing": [".local/", "*.user"]}, dry_run=False)
    assert changed
    new_content = gi.read_text(encoding="utf-8")
    assert ".local/" in new_content
    assert "*.user" in new_content


def test_hy4_fixer_idempotent(tmp_path):
    gi = tmp_path / ".gitignore"
    gi.write_text("bin/\nobj/\n.local/\n", encoding="utf-8")
    fixer = FIXER_REGISTRY["gitignore_append_lines"]
    assert fixer(gi, {"missing": [".local/"]}, dry_run=False) is False


# ---------- HY-5 EOL mix ----------

def test_hy5_pure_crlf(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_bytes(b"line1\r\nline2\r\n")
    fc = FileContext(f)
    assert detect_hy5_eol_mix(_rule("HY-5", Severity.INFO), fc, None) == []


def test_hy5_pure_lf(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_bytes(b"line1\nline2\n")
    fc = FileContext(f)
    assert detect_hy5_eol_mix(_rule("HY-5", Severity.INFO), fc, None) == []


def test_hy5_mix(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_bytes(b"line1\r\nline2\nline3\r\n")
    fc = FileContext(f)
    findings = detect_hy5_eol_mix(_rule("HY-5", Severity.INFO), fc, None)
    assert len(findings) == 1


def test_hy5_fixer_normalize(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_bytes(b"a\r\nb\nc\r\n")
    fixer = FIXER_REGISTRY["normalize_eol_crlf"]
    assert fixer(f, {}, dry_run=False)
    assert f.read_bytes() == b"a\r\nb\r\nc\r\n"


def test_hy5_fixer_idempotent(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_bytes(b"a\r\nb\r\n")
    fixer = FIXER_REGISTRY["normalize_eol_crlf"]
    assert fixer(f, {}, dry_run=False) is False


# ---------- HY-6 BOM em JSON ----------

def test_hy6_no_bom(tmp_path):
    f = tmp_path / "project.json"
    f.write_bytes(b'{"name":"X"}\n')
    fc = FileContext(f)
    assert detect_hy6_bom_json(_rule("HY-6", Severity.INFO), fc, None) == []


def test_hy6_with_bom(tmp_path):
    f = tmp_path / "project.json"
    f.write_bytes(b'\xef\xbb\xbf{"name":"X"}\n')
    fc = FileContext(f)
    findings = detect_hy6_bom_json(_rule("HY-6", Severity.INFO), fc, None)
    assert len(findings) == 1


def test_hy6_fixer_strips(tmp_path):
    f = tmp_path / "project.json"
    f.write_bytes(b'\xef\xbb\xbf{"a":1}')
    fixer = FIXER_REGISTRY["strip_bom"]
    assert fixer(f, {}, dry_run=False)
    assert f.read_bytes() == b'{"a":1}'


def test_hy6_fixer_idempotent(tmp_path):
    f = tmp_path / "project.json"
    f.write_bytes(b'{"a":1}')
    fixer = FIXER_REGISTRY["strip_bom"]
    assert fixer(f, {}, dry_run=False) is False
