from __future__ import annotations

import json
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.displayname import detect_s8b_displayname_mismatch


def _rule() -> Rule:
    return Rule(
        id="S-8b",
        severity=Severity.WARN,
        category="architectural",
        target="all",
        title="InvokeWorkflowFile DisplayName != basename(WorkflowFileName)",
        description="",
        detect={"type": "python"},
        fix={"apply_class": "deterministic", "prose": "Renomear DisplayName."},
    )


def _project(tmp_path: Path) -> tuple[Path, ProjectContext]:
    root = tmp_path / "P"
    root.mkdir()
    data = {"targetFramework": "Windows", "dependencies": {}}
    (root / "project.json").write_text(json.dumps(data), encoding="utf-8")
    return root, ProjectContext(root=root, project_json=data)


def _caller(root: Path, body: str) -> FileContext:
    path = root / "Caller.xaml"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">\n'
        f"{body}\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    return FileContext(path)


def test_s8b_flags_display_name_when_workflow_path_is_exact(tmp_path):
    root, pc = _project(tmp_path)
    (root / "RealWorkflow.xaml").write_text("<Activity />", encoding="utf-8")
    fc = _caller(
        root,
        '<ui:InvokeWorkflowFile DisplayName="Step 1" '
        'WorkflowFileName="RealWorkflow.xaml" />',
    )

    findings = detect_s8b_displayname_mismatch(_rule(), fc, pc)

    assert len(findings) == 1
    assert findings[0].fix_mechanical
    assert 'DisplayName="RealWorkflow"' in findings[0].fix_mechanical["replacement"]


def test_s8b_skips_when_workflow_path_casing_is_invalid(tmp_path):
    root, pc = _project(tmp_path)
    (root / "GetandCheckFiles.xaml").write_text("<Activity />", encoding="utf-8")
    fc = _caller(
        root,
        '<ui:InvokeWorkflowFile DisplayName="Step 1" '
        'WorkflowFileName="GetAndCheckFiles.xaml" />',
    )

    findings = detect_s8b_displayname_mismatch(_rule(), fc, pc)

    assert findings == []

