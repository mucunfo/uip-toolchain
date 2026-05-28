"""Tests Tier 4 — D-TRANSITIVE-CONFLICT scanner."""
from __future__ import annotations

import json
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.transitive_dep import (
    _parse_semver,
    _strip_constraint,
    detect_transitive_conflict,
)


def _mk_rule() -> Rule:
    return Rule(
        id="D-TRANSITIVE-CONFLICT",
        severity=Severity.ERROR,
        category="breaking",
        target="windows",
        title="Transitive dependency conflict",
        description="",
        detect={"type": "python"},
        fix={"apply_class": "structural", "prose": "manual"},
    )


def _mk_pc(tmp_path: Path, assets_data: dict | None) -> ProjectContext:
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text(json.dumps({"targetFramework": "Windows"}))
    if assets_data is not None:
        (proj / ".local").mkdir()
        (proj / ".local" / "AllDependencies.json").write_text(json.dumps(assets_data))
    return ProjectContext(root=proj, project_json={"targetFramework": "Windows"})


def test_semver_parse():
    assert _parse_semver("1.0.0") > _parse_semver("0.9.9")
    assert _parse_semver("1.0.0") > _parse_semver("1.0.0-beta")


def test_strip_constraint():
    assert _strip_constraint("[1.0.0]") == "1.0.0"
    assert _strip_constraint("[1.0.0,)") == "1.0.0"
    assert _strip_constraint("1.2.3") == "1.2.3"


def test_no_assets_file_returns_empty(tmp_path):
    pc = _mk_pc(tmp_path, None)
    findings = detect_transitive_conflict(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    assert findings == []


def test_no_conflict_clean_graph(tmp_path):
    pc = _mk_pc(tmp_path, {
        "version": 3,
        "targets": {
            "net6.0-windows7.0": {
                "Foo/1.0.0": {"dependencies": {"Bar": "2.0.0"}},
                "Bar/2.0.0": {},
            }
        }
    })
    findings = detect_transitive_conflict(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    assert findings == []


def test_duplicate_identity_flagged(tmp_path):
    """Mesmo package nome resolvido em 2 versões sob mesmo TFM."""
    pc = _mk_pc(tmp_path, {
        "version": 3,
        "targets": {
            "net6.0-windows7.0": {
                "Newtonsoft.Json/12.0.3": {},
                "Newtonsoft.Json/13.0.1": {},
                "Foo/1.0.0": {},
            }
        }
    })
    findings = detect_transitive_conflict(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    msgs = [f.message for f in findings]
    assert any("Newtonsoft.Json" in m and "12.0.3" in m and "13.0.1" in m for m in msgs)


def test_downgrade_skew_flagged(tmp_path):
    """Package A pede B>=13.x mas graph tem B=12.x."""
    pc = _mk_pc(tmp_path, {
        "version": 3,
        "targets": {
            "net6.0-windows7.0": {
                "Foo/1.0.0": {"dependencies": {"Bar": "13.0.0"}},
                "Bar/12.0.0": {},
            }
        }
    })
    findings = detect_transitive_conflict(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    msgs = [f.message for f in findings]
    assert any("Foo declara Bar>=13.0.0" in m and "12.0.0" in m for m in msgs)


def test_upgrade_no_finding(tmp_path):
    """Package A pede B>=12.x e graph tem B=13.x — OK (forward compat)."""
    pc = _mk_pc(tmp_path, {
        "version": 3,
        "targets": {
            "net6.0-windows7.0": {
                "Foo/1.0.0": {"dependencies": {"Bar": "12.0.0"}},
                "Bar/13.0.0": {},
            }
        }
    })
    findings = detect_transitive_conflict(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    # Upgrade NÃO é violação — só downgrade é.
    downgrade_findings = [f for f in findings if "declara" in f.message]
    assert downgrade_findings == []
