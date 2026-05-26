"""Tests for J-8 stale fileInfoCollection entries.

- Detector: uip_engine.heuristics.project_manifest.detect_j8_stale_fileinfo_entries
- Fixer:    uip_engine.fixers.apply_project_manifest_remove_stale_entries

Studio publish FALHA quando project.json::designOptions.fileInfoCollection
lista TC com fileName que não existe no disco. Detector identifica entries
órfãs; fixer remove-as preservando entries válidas.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.project_manifest import (
    detect_j8_stale_fileinfo_entries,
)
from uip_engine.fixers import (
    apply_project_manifest_remove_stale_entries,
)


# ---------- helpers ----------

def _project(tmp_path: Path, pj_data: dict) -> ProjectContext:
    (tmp_path / "project.json").write_text(
        json.dumps(pj_data, indent=2), encoding="utf-8"
    )
    return ProjectContext(root=tmp_path, project_json=pj_data)


def _fc(tmp_path: Path) -> FileContext:
    return FileContext(tmp_path / "project.json")


def _rule(**params) -> Rule:
    defaults = {
        "key_path": "designOptions.fileInfoCollection",
        "filename_field": "fileName",
    }
    defaults.update(params)
    return Rule(
        id="J-8",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="fileInfoCollection com fileName apontando file inexistente",
        description="",
        detect={
            "type": "python",
            "params": {
                "module": "uip_engine.heuristics.project_manifest",
                "function": "detect_j8_stale_fileinfo_entries",
                **defaults,
            },
        },
        fix={
            "apply_class": "deterministic",
            "mechanical": {
                "type": "project_manifest_remove_stale_entries",
                **defaults,
            },
            "prose": "remover entry stale",
        },
    )


def _make_tc(tmp_path: Path, rel: str) -> Path:
    """Create file at relative path inside tmp_path (parents auto-created)."""
    p = tmp_path / rel.replace("\\", "/")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("<Activity/>", encoding="utf-8")
    return p


# ---------- detector tests ----------

def test_1_entry_points_to_existing_file_no_findings(tmp_path):
    """Entry com fileName que existe no disco → 0 findings."""
    _make_tc(tmp_path, "Tests/Integration/TC_Existente.xaml")
    pj = {
        "name": "Foo",
        "designOptions": {
            "fileInfoCollection": [
                {
                    "fileName": "Tests\\Integration\\TC_Existente.xaml",
                    "isPublishable": True,
                }
            ]
        },
    }
    pc = _project(tmp_path, pj)
    findings = detect_j8_stale_fileinfo_entries(_rule(), _fc(tmp_path), pc)
    assert findings == []


def test_2_entry_points_to_missing_file_emits_finding(tmp_path):
    """Entry com fileName que NÃO existe → 1 finding ERROR."""
    pj = {
        "name": "Foo",
        "designOptions": {
            "fileInfoCollection": [
                {
                    "fileName": "Tests\\Integration\\TC_Inexistente.xaml",
                    "isPublishable": True,
                }
            ]
        },
    }
    pc = _project(tmp_path, pj)
    findings = detect_j8_stale_fileinfo_entries(_rule(), _fc(tmp_path), pc)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "J-8"
    assert f.severity == Severity.ERROR
    assert "TC_Inexistente.xaml" in f.message
    assert "missing file" in f.message.lower()


def test_4_multiple_stale_entries_multiple_findings(tmp_path):
    """Mix stale + válido → emit só para os stale."""
    _make_tc(tmp_path, "Tests/TC_OK.xaml")
    pj = {
        "designOptions": {
            "fileInfoCollection": [
                {"fileName": "Tests\\TC_OK.xaml"},
                {"fileName": "Tests\\TC_Stale1.xaml"},
                {"fileName": "Tests\\TC_Stale2.xaml"},
            ]
        }
    }
    pc = _project(tmp_path, pj)
    findings = detect_j8_stale_fileinfo_entries(_rule(), _fc(tmp_path), pc)
    assert len(findings) == 2
    msgs = " ".join(f.message for f in findings)
    assert "TC_Stale1.xaml" in msgs
    assert "TC_Stale2.xaml" in msgs
    assert "TC_OK.xaml" not in msgs


def test_5_empty_fileinfocollection_no_findings(tmp_path):
    """Array vazio → 0 findings (no-op)."""
    pj = {"designOptions": {"fileInfoCollection": []}}
    pc = _project(tmp_path, pj)
    findings = detect_j8_stale_fileinfo_entries(_rule(), _fc(tmp_path), pc)
    assert findings == []


def test_6_missing_fileinfocollection_key_no_findings(tmp_path):
    """Key ausente do project.json → 0 findings (no-op silencioso)."""
    pj = {"name": "Foo", "designOptions": {}}
    pc = _project(tmp_path, pj)
    findings = detect_j8_stale_fileinfo_entries(_rule(), _fc(tmp_path), pc)
    assert findings == []


def test_detector_generic_keypath_webservices(tmp_path):
    """Detector é genérico: webServices array com mesmo shape também flagged."""
    _make_tc(tmp_path, "swagger/api_ok.json")
    pj = {
        "webServices": [
            {"fileName": "swagger\\api_ok.json"},
            {"fileName": "swagger\\api_missing.json"},
        ]
    }
    pc = _project(tmp_path, pj)
    rule = _rule(key_path="webServices", filename_field="fileName")
    findings = detect_j8_stale_fileinfo_entries(rule, _fc(tmp_path), pc)
    assert len(findings) == 1
    assert "api_missing.json" in findings[0].message


def test_detector_skips_non_project_json(tmp_path):
    """FileContext apontando p/ algo != project.json → 0 findings."""
    other = tmp_path / "outro.json"
    other.write_text("{}", encoding="utf-8")
    fc = FileContext(other)
    pj = {
        "designOptions": {
            "fileInfoCollection": [{"fileName": "Missing.xaml"}]
        }
    }
    (tmp_path / "project.json").write_text(json.dumps(pj), encoding="utf-8")
    pc = ProjectContext(root=tmp_path, project_json=pj)
    findings = detect_j8_stale_fileinfo_entries(_rule(), fc, pc)
    assert findings == []


# ---------- fixer tests ----------

def test_3_fix_removes_stale_keeps_others(tmp_path):
    """Fix mechanical remove stale entry, mantém entries válidas."""
    _make_tc(tmp_path, "Tests/TC_OK.xaml")
    pj = {
        "name": "Foo",
        "designOptions": {
            "fileInfoCollection": [
                {"fileName": "Tests\\TC_OK.xaml", "isPublishable": True},
                {"fileName": "Tests\\TC_Stale.xaml", "isPublishable": True},
            ]
        },
    }
    pj_path = tmp_path / "project.json"
    pj_path.write_text(json.dumps(pj, indent=2), encoding="utf-8")
    spec = {
        "type": "project_manifest_remove_stale_entries",
        "key_path": "designOptions.fileInfoCollection",
        "filename_field": "fileName",
    }
    changed = apply_project_manifest_remove_stale_entries(
        pj_path, spec, dry_run=False, project_root=tmp_path,
    )
    assert changed is True
    out = json.loads(pj_path.read_text(encoding="utf-8"))
    arr = out["designOptions"]["fileInfoCollection"]
    assert len(arr) == 1
    assert arr[0]["fileName"] == "Tests\\TC_OK.xaml"


def test_4_fix_removes_multiple_stale(tmp_path):
    """Multiple stale → all removed em single apply."""
    _make_tc(tmp_path, "Tests/TC_OK.xaml")
    pj = {
        "designOptions": {
            "fileInfoCollection": [
                {"fileName": "Tests\\TC_OK.xaml"},
                {"fileName": "Tests\\TC_Stale1.xaml"},
                {"fileName": "Tests\\TC_Stale2.xaml"},
            ]
        }
    }
    pj_path = tmp_path / "project.json"
    pj_path.write_text(json.dumps(pj, indent=2), encoding="utf-8")
    spec = {
        "type": "project_manifest_remove_stale_entries",
        "key_path": "designOptions.fileInfoCollection",
        "filename_field": "fileName",
    }
    changed = apply_project_manifest_remove_stale_entries(
        pj_path, spec, dry_run=False, project_root=tmp_path,
    )
    assert changed is True
    out = json.loads(pj_path.read_text(encoding="utf-8"))
    arr = out["designOptions"]["fileInfoCollection"]
    assert len(arr) == 1
    assert arr[0]["fileName"] == "Tests\\TC_OK.xaml"


def test_fix_idempotent_when_all_files_exist(tmp_path):
    """Todos arquivos existem → no-op (changed=False)."""
    _make_tc(tmp_path, "Tests/TC_A.xaml")
    _make_tc(tmp_path, "Tests/TC_B.xaml")
    pj = {
        "designOptions": {
            "fileInfoCollection": [
                {"fileName": "Tests\\TC_A.xaml"},
                {"fileName": "Tests\\TC_B.xaml"},
            ]
        }
    }
    pj_path = tmp_path / "project.json"
    pj_path.write_text(json.dumps(pj, indent=2), encoding="utf-8")
    spec = {
        "type": "project_manifest_remove_stale_entries",
        "key_path": "designOptions.fileInfoCollection",
        "filename_field": "fileName",
    }
    changed = apply_project_manifest_remove_stale_entries(
        pj_path, spec, dry_run=False, project_root=tmp_path,
    )
    assert changed is False


def test_fix_dry_run_no_write(tmp_path):
    """dry_run=True → returns True (would change) mas não toca arquivo."""
    pj = {
        "designOptions": {
            "fileInfoCollection": [
                {"fileName": "Tests\\TC_Missing.xaml"},
            ]
        }
    }
    pj_path = tmp_path / "project.json"
    original = json.dumps(pj, indent=2)
    pj_path.write_text(original, encoding="utf-8")
    spec = {
        "type": "project_manifest_remove_stale_entries",
        "key_path": "designOptions.fileInfoCollection",
        "filename_field": "fileName",
    }
    changed = apply_project_manifest_remove_stale_entries(
        pj_path, spec, dry_run=True, project_root=tmp_path,
    )
    assert changed is True
    # File untouched
    assert pj_path.read_text(encoding="utf-8") == original


def test_fix_preserves_bom(tmp_path):
    """Studio escreve project.json com BOM — fixer preserva."""
    pj = {
        "designOptions": {
            "fileInfoCollection": [
                {"fileName": "Tests\\TC_Stale.xaml"},
            ]
        }
    }
    pj_path = tmp_path / "project.json"
    body = json.dumps(pj, indent=2) + "\n"
    pj_path.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    spec = {
        "type": "project_manifest_remove_stale_entries",
        "key_path": "designOptions.fileInfoCollection",
        "filename_field": "fileName",
    }
    changed = apply_project_manifest_remove_stale_entries(
        pj_path, spec, dry_run=False, project_root=tmp_path,
    )
    assert changed is True
    raw = pj_path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "BOM must be preserved"


def test_fix_noop_when_array_missing(tmp_path):
    """Array key ausente do JSON → no-op."""
    pj = {"name": "Foo"}
    pj_path = tmp_path / "project.json"
    pj_path.write_text(json.dumps(pj, indent=2), encoding="utf-8")
    spec = {
        "type": "project_manifest_remove_stale_entries",
        "key_path": "designOptions.fileInfoCollection",
        "filename_field": "fileName",
    }
    changed = apply_project_manifest_remove_stale_entries(
        pj_path, spec, dry_run=False, project_root=tmp_path,
    )
    assert changed is False


# ---------- registry sanity ----------

def test_fixer_registered():
    from uip_engine.fixers import REGISTRY
    assert "project_manifest_remove_stale_entries" in REGISTRY


def test_rule_loads_in_yaml():
    """J-8 deve carregar via loader sem schema errors."""
    from uip_engine.loader import load_rules
    from uip_engine.detectors import REGISTRY as DETECTORS
    from uip_engine.fixers import REGISTRY as FIXERS

    rules_yaml = (
        Path(__file__).resolve().parents[1] / "rules.yaml"
    )
    rules = load_rules(
        rules_yaml,
        registered_detectors=set(DETECTORS.keys()),
        registered_fixers=set(FIXERS.keys()),
    )
    j8 = [r for r in rules if r.id == "J-8"]
    assert len(j8) == 1
    r = j8[0]
    assert r.severity == Severity.ERROR
    assert r.category == "breaking"
    assert r.fix["apply_class"] == "deterministic"
    assert r.fix["mechanical"]["type"] == "project_manifest_remove_stale_entries"
