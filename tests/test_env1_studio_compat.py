"""Tests for ENV-1 Studio compat flags rule.

Cobre:
  - apply_project_manifest_set_keys fixer (idempotency, atomic patch,
    create intermediate sub-dicts, type safety).
  - detect_env1_studio_compat detector (emits 1 finding com fix_mechanical
    quando flags divergentes, no-op quando todos corretos).
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from uip_engine.fixers import apply_project_manifest_set_keys
from uip_engine.heuristics.project_manifest import (
    detect_env1_studio_compat,
    _ENV1_REQUIRED,
)


# ---- apply_project_manifest_set_keys ----

def _write_json(path: Path, data: dict, bom: bool = False) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    raw = (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8")
    path.write_bytes(raw)


def test_set_keys_creates_intermediate_subdicts(tmp_path):
    """designOptions / libraryOptions ausentes → fixer cria sub-dicts."""
    f = tmp_path / "project.json"
    _write_json(f, {"name": "X"})
    spec = {
        "keys": {
            "designOptions.libraryOptions.includeOriginalXaml": False,
            "designOptions.modernBehavior": False,
        }
    }
    changed = apply_project_manifest_set_keys(f, spec, dry_run=False)
    assert changed is True
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    assert data["designOptions"]["libraryOptions"]["includeOriginalXaml"] is False
    assert data["designOptions"]["modernBehavior"] is False


def test_set_keys_overrides_existing(tmp_path):
    """Existing value different from desired → overwrite."""
    f = tmp_path / "project.json"
    _write_json(f, {
        "runtimeOptions": {"mustRestoreAllDependencies": False},
    })
    spec = {"keys": {"runtimeOptions.mustRestoreAllDependencies": True}}
    changed = apply_project_manifest_set_keys(f, spec, dry_run=False)
    assert changed is True
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    assert data["runtimeOptions"]["mustRestoreAllDependencies"] is True


def test_set_keys_idempotent_when_all_correct(tmp_path):
    """Todos keys já com valor desejado → no-op."""
    f = tmp_path / "project.json"
    _write_json(f, {
        "runtimeOptions": {"mustRestoreAllDependencies": True},
        "designOptions": {"modernBehavior": False},
    })
    spec = {
        "keys": {
            "runtimeOptions.mustRestoreAllDependencies": True,
            "designOptions.modernBehavior": False,
        }
    }
    changed = apply_project_manifest_set_keys(f, spec, dry_run=False)
    assert changed is False


def test_set_keys_preserves_bom(tmp_path):
    """BOM em arquivo original preservado no write."""
    f = tmp_path / "project.json"
    _write_json(f, {"name": "X"}, bom=True)
    spec = {"keys": {"designOptions.modernBehavior": False}}
    apply_project_manifest_set_keys(f, spec, dry_run=False)
    raw = f.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")


def test_set_keys_rejects_non_primitive_leaf(tmp_path):
    """Safety: leaf não-primitivo (dict/list) é skipado pra evitar
    mutações estruturais acidentais."""
    f = tmp_path / "project.json"
    _write_json(f, {"name": "X"})
    spec = {"keys": {"foo": {"nested": "dict"}}}
    changed = apply_project_manifest_set_keys(f, spec, dry_run=False)
    assert changed is False
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    assert "foo" not in data


def test_set_keys_dry_run_no_write(tmp_path):
    """dry_run=True → returns True (changed) mas não escreve."""
    f = tmp_path / "project.json"
    _write_json(f, {"name": "X"})
    original = f.read_bytes()
    spec = {"keys": {"designOptions.modernBehavior": False}}
    changed = apply_project_manifest_set_keys(f, spec, dry_run=True)
    assert changed is True
    assert f.read_bytes() == original


def test_set_keys_skip_when_intermediate_collision(tmp_path):
    """Intermediate path é scalar/array → skip esse key, não sobrescrever."""
    f = tmp_path / "project.json"
    _write_json(f, {"designOptions": "STRING_NOT_DICT"})
    spec = {"keys": {"designOptions.modernBehavior": False}}
    changed = apply_project_manifest_set_keys(f, spec, dry_run=False)
    # Skipa esse key (designOptions é string, não dict); outros podem aplicar.
    # Spec só tem esse → changed=False.
    assert changed is False
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    assert data["designOptions"] == "STRING_NOT_DICT"  # preserved


# ---- detect_env1_studio_compat ----

class _MockFC:
    """Fake FileContext: só path + content needed pelo detector."""

    def __init__(self, path: Path, content: str):
        self.path = path
        self.content = content


class _MockRule:
    id = "ENV-1"
    severity = "ERROR"
    category = "breaking"


def _fc_from_data(tmp_path: Path, data: dict) -> _MockFC:
    f = tmp_path / "project.json"
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    f.write_text(text, encoding="utf-8")
    return _MockFC(f, text)


def test_env1_detect_emits_when_all_flags_missing(tmp_path):
    """project.json sem nenhum dos 3 flags → emit 1 finding com TODOS keys."""
    fc = _fc_from_data(tmp_path, {"name": "X"})
    findings = detect_env1_studio_compat(_MockRule(), fc, None)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "ENV-1"
    assert f.fix_mechanical is not None
    assert f.fix_mechanical["type"] == "project_manifest_set_keys"
    keys = f.fix_mechanical["keys"]
    assert set(keys.keys()) == set(_ENV1_REQUIRED.keys())
    for k, v in _ENV1_REQUIRED.items():
        assert keys[k] == v


def test_env1_detect_emits_only_diverging_keys(tmp_path):
    """Apenas 1 flag errado → finding inclui só esse key no fix."""
    fc = _fc_from_data(tmp_path, {
        "runtimeOptions": {"mustRestoreAllDependencies": False},
        "designOptions": {
            "modernBehavior": False,
            "libraryOptions": {"includeOriginalXaml": False},
        },
    })
    findings = detect_env1_studio_compat(_MockRule(), fc, None)
    assert len(findings) == 1
    keys = findings[0].fix_mechanical["keys"]
    assert keys == {"runtimeOptions.mustRestoreAllDependencies": True}


def test_env1_detect_noop_when_all_correct(tmp_path):
    """Todos 3 flags presentes + corretos → no findings (idempotent)."""
    fc = _fc_from_data(tmp_path, {
        "runtimeOptions": {"mustRestoreAllDependencies": True},
        "designOptions": {
            "modernBehavior": False,
            "libraryOptions": {"includeOriginalXaml": False},
        },
    })
    findings = detect_env1_studio_compat(_MockRule(), fc, None)
    assert findings == []


def test_env1_detect_handles_broken_json(tmp_path):
    """JSON inválido → no findings (defensive)."""
    f = tmp_path / "project.json"
    f.write_text("not { valid json", encoding="utf-8")
    fc = _MockFC(f, "not { valid json")
    findings = detect_env1_studio_compat(_MockRule(), fc, None)
    assert findings == []


def test_env1_end_to_end_detect_then_apply(tmp_path):
    """Pipeline integrado: detector emite finding → fixer aplica → re-detector
    confirma resolução."""
    f = tmp_path / "project.json"
    initial = {
        "name": "TestProject",
        "runtimeOptions": {"mustRestoreAllDependencies": False},
        "designOptions": {"libraryOptions": {"privateWorkflows": []}},
    }
    f.write_text(
        json.dumps(initial, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    fc = _MockFC(f, f.read_text(encoding="utf-8"))

    # Detect 1
    findings = detect_env1_studio_compat(_MockRule(), fc, None)
    assert len(findings) == 1
    spec = findings[0].fix_mechanical
    assert spec["type"] == "project_manifest_set_keys"

    # Apply
    changed = apply_project_manifest_set_keys(f, spec, dry_run=False)
    assert changed is True

    # Detect 2 — should be no-op now
    fc2 = _MockFC(f, f.read_text(encoding="utf-8"))
    findings2 = detect_env1_studio_compat(_MockRule(), fc2, None)
    assert findings2 == []

    # Verify final state
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    assert data["runtimeOptions"]["mustRestoreAllDependencies"] is True
    assert data["designOptions"]["modernBehavior"] is False
    assert data["designOptions"]["libraryOptions"]["includeOriginalXaml"] is False
    # Preserved fields
    assert data["name"] == "TestProject"
    assert data["designOptions"]["libraryOptions"]["privateWorkflows"] == []
