from __future__ import annotations

import json
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.detectors import detect_cross_file_args
from uip_engine.fixers import apply_sync_project_uiproj
from uip_engine.heuristics.project_manifest import (
    detect_j9_project_uiproj_synced,
    detect_w40_pack_incompatible_stale_assembly_refs,
)
from uip_engine.loader import load_rules


def _project_json(name: str = "Proj", **extra):
    data = {
        "name": name,
        "projectVersion": "1.0.0",
        "targetFramework": "Windows",
        "expressionLanguage": "VisualBasic",
        "main": "Main.xaml",
        "designOptions": {"outputType": "Process"},
        "dependencies": {"UiPath.System.Activities": "[25.4.4]"},
    }
    data.update(extra)
    return data


def _write_project(tmp_path: Path, data: dict | None = None) -> ProjectContext:
    project = tmp_path / "Proj"
    project.mkdir()
    payload = data or _project_json()
    (project / "project.json").write_text(json.dumps(payload), encoding="utf-8")
    return ProjectContext(root=project, project_json=payload)


def _rule(
    rule_id: str,
    *,
    title: str | None = None,
    severity: Severity = Severity.ERROR,
) -> Rule:
    return Rule(
        id=rule_id,
        severity=severity,
        category="breaking",
        target="windows",
        title=title or rule_id,
        description="",
        detect={"type": "python"},
        fix={"apply_class": "deterministic", "prose": "fix"},
    )


def test_publish_readiness_rules_registered():
    rules = load_rules(Path(__file__).resolve().parents[1] / "rules.yaml")
    by_id = {rule.id: rule for rule in rules}

    assert by_id["J-9"].severity == Severity.ERROR
    assert by_id["W-40"].severity == Severity.ERROR
    assert by_id["A-19d"].severity == Severity.ERROR
    assert by_id["J-9"].fix["mechanical"]["type"] == "sync_project_uiproj"


def test_j9_detects_and_fixes_missing_project_uiproj(tmp_path):
    pc = _write_project(tmp_path)
    project_json = pc.root / "project.json"
    rule = _rule("J-9", title="project.uiproj synced")

    findings = detect_j9_project_uiproj_synced(rule, FileContext(project_json), pc)

    assert len(findings) == 1
    assert findings[0].fix_mechanical == {"type": "sync_project_uiproj"}

    assert apply_sync_project_uiproj(project_json, findings[0].fix_mechanical, dry_run=False)
    generated = json.loads((pc.root / "project.uiproj").read_text(encoding="utf-8"))
    assert generated == {
        "Name": "Proj",
        "ProjectType": "Process",
        "Description": "",
        "MainFile": "Main.xaml",
    }
    assert detect_j9_project_uiproj_synced(rule, FileContext(project_json), pc) == []


def test_w39_detects_only_stale_pack_incompatible_refs(tmp_path):
    pc = _write_project(tmp_path)
    xaml = pc.root / "Main.xaml"
    xaml.write_text(
        "\n".join([
            "<Activity>",
            "  <TextExpression.ReferencesForImplementation>",
            "    <AssemblyReference>UiPath.Python</AssemblyReference>",
            "    <AssemblyReference>System</AssemblyReference>",
            "  </TextExpression.ReferencesForImplementation>",
            "</Activity>",
            "",
        ]),
        encoding="utf-8",
    )
    rule = _rule("W-40", title="stale ref")

    findings = detect_w40_pack_incompatible_stale_assembly_refs(rule, FileContext(xaml), pc)

    assert len(findings) == 1
    assert findings[0].message.endswith("UiPath.Python")
    assert findings[0].fix_mechanical == {
        "type": "strip_assembly_reference",
        "name": "UiPath.Python",
    }


def test_w39_keeps_design_ref_when_exact_dependency_exists(tmp_path):
    pc = _write_project(
        tmp_path,
        _project_json(dependencies={
            "UiPath.System.Activities": "[25.4.4]",
            "UiPath.Word.Activities": "[1.19.0]",
            "UiPath.Word.Activities.Design": "[1.19.0]",
        }),
    )
    xaml = pc.root / "Main.xaml"
    xaml.write_text(
        "<Activity>\n"
        "  <AssemblyReference>UiPath.Word.Activities.Design</AssemblyReference>\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    rule = _rule("W-40", title="stale ref")

    assert detect_w40_pack_incompatible_stale_assembly_refs(rule, FileContext(xaml), pc) == []


def test_production_cross_file_args_flags_extra_caller_key(tmp_path):
    pc = _write_project(tmp_path)
    (pc.root / "Callee.xaml").write_text(
        '<Activity><x:Members>'
        '<x:Property Name="io_DTabCadastro" Type="InOutArgument(sd:DataTable)" />'
        '</x:Members></Activity>',
        encoding="utf-8",
    )
    caller = pc.root / "Caller.xaml"
    caller.write_text(
        '<Activity><ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '<InOutArgument x:TypeArguments="sd:DataTable" x:Key="in_DTabCadastro">[vDTab]</InOutArgument>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>',
        encoding="utf-8",
    )
    rule = Rule(
        id="A-19d",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="extra caller key",
        description="",
        detect={"type": "cross_file_args", "params": {"direction": "caller_extra"}},
    )

    findings = detect_cross_file_args(rule, FileContext(caller), pc)

    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "in_DTabCadastro" in findings[0].message
