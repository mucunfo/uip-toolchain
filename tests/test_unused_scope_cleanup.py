from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.unused import (
    detect_duplicate_variable_names,
    detect_unused_arguments,
    detect_unused_variables,
)


def _rule(rid: str, mechanical_type: str = "delete_variable_declaration") -> Rule:
    return Rule(
        id=rid,
        severity=Severity.WARN,
        category="architectural",
        target="all",
        title=f"test {rid}",
        description="",
        detect={"type": "python", "params": {}},
        fix={
            "apply_class": "deterministic",
            "mechanical": {"type": mechanical_type},
            "prose": "fix",
        },
    )


def _fc(tmp_path: Path, text: str) -> FileContext:
    f = tmp_path / "Workflow.xaml"
    f.write_text(text, encoding="utf-8")
    return FileContext(f)


def test_u1_detects_unused_duplicate_in_sibling_scope(tmp_path: Path) -> None:
    fc = _fc(
        tmp_path,
        """<Activity>
  <Sequence>
    <Sequence.Variables>
      <Variable x:TypeArguments="x:Int32" Name="vIntColumnIndex" />
    </Sequence.Variables>
    <Assign To="[vIntColumnIndex]" Value="[1]" />
  </Sequence>
  <Sequence>
    <Sequence.Variables>
      <Variable x:TypeArguments="x:Int32" Name="vIntColumnIndex" />
      <Variable x:TypeArguments="x:Int32" Name="vIntColumnIndexFinancieras" />
    </Sequence.Variables>
    <Assign To="[vIntColumnIndexFinancieras]" Value="[2]" />
  </Sequence>
</Activity>
""",
    )

    findings = detect_unused_variables(_rule("U-1"), fc, None)

    assert len(findings) == 1
    finding = findings[0]
    assert "vIntColumnIndex" in finding.message
    assert finding.fix_mechanical["type"] == "delete_variable_declaration"
    assert finding.fix_mechanical["line"] == 10


def test_u1_displayname_does_not_count_as_usage(tmp_path: Path) -> None:
    fc = _fc(
        tmp_path,
        """<Activity>
  <Sequence DisplayName="Sequence mentions vIntColumnIndex">
    <Sequence.Variables>
      <Variable x:TypeArguments="x:Int32" Name="vIntColumnIndex" />
    </Sequence.Variables>
    <Assign DisplayName="Assign - Decrementa o vIntColumnIndex" />
  </Sequence>
</Activity>
""",
    )

    findings = detect_unused_variables(_rule("U-1"), fc, None)

    assert len(findings) == 1
    assert findings[0].fix_mechanical["name"] == "vIntColumnIndex"


def test_u4_mechanical_for_inner_shadow_with_equivalent_ancestor(tmp_path: Path) -> None:
    fc = _fc(
        tmp_path,
        """<Activity>
  <Sequence>
    <Sequence.Variables>
      <Variable x:TypeArguments="x:String" Name="vStUsuarioSipagNet" />
    </Sequence.Variables>
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vStUsuarioSipagNet" />
      </Sequence.Variables>
      <Assign To="[vStUsuarioSipagNet]" Value="[&quot;ok&quot;]" />
    </Sequence>
  </Sequence>
</Activity>
""",
    )

    findings = detect_duplicate_variable_names(_rule("U-4"), fc, None)

    mechanical = [f for f in findings if f.fix_mechanical]
    assert len(mechanical) == 1
    assert "shadow duplicate" in mechanical[0].message
    assert mechanical[0].fix_mechanical["line"] == 8


def test_u4_keeps_unrelated_cross_scope_duplicate_contextual(tmp_path: Path) -> None:
    fc = _fc(
        tmp_path,
        """<Activity>
  <Sequence>
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vStStatus" />
      </Sequence.Variables>
      <Assign To="[vStStatus]" Value="[&quot;a&quot;]" />
    </Sequence>
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vStStatus" />
      </Sequence.Variables>
      <Assign To="[vStStatus]" Value="[&quot;b&quot;]" />
    </Sequence>
  </Sequence>
</Activity>
""",
    )

    findings = detect_duplicate_variable_names(_rule("U-4"), fc, None)

    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


def test_u2_unused_argument_emits_exact_declaration_fix(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text(
        '{"projectType": "Process"}',
        encoding="utf-8",
    )
    f = tmp_path / "Callee.xaml"
    declaration = '<x:Property Name="in_StUnused" Type="InArgument(x:String)" />'
    f.write_text(
        '<Activity x:Class="Workflow.Callee">\n'
        "  <x:Members>\n"
        f"    {declaration}\n"
        '    <x:Property Name="in_StUsed" Type="InArgument(x:String)" />\n'
        "  </x:Members>\n"
        "  <this:Callee.in_StUnused>\n"
        '    <InArgument x:TypeArguments="x:String">["default"]</InArgument>\n'
        "  </this:Callee.in_StUnused>\n"
        '  <Assign To="[in_StUsed]" Value="[&quot;ok&quot;]" />\n'
        "</Activity>\n",
        encoding="utf-8",
    )

    findings = detect_unused_arguments(
        _rule("U-2", "delete_argument_declaration"),
        FileContext(f),
        ProjectContext(tmp_path, {"projectType": "Process"}),
    )

    assert len(findings) == 1
    finding = findings[0]
    assert "in_StUnused" in finding.message
    assert finding.fix_mechanical == {
        "type": "delete_argument_declaration",
        "name": "in_StUnused",
        "line": 3,
        "declaration": declaration,
        "class_name": "Workflow.Callee",
    }


def test_u2_keeps_argument_bound_by_static_caller(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text(
        '{"projectType": "Process"}',
        encoding="utf-8",
    )
    callee = tmp_path / "Callee.xaml"
    callee.write_text(
        '<Activity x:Class="Workflow.Callee">\n'
        "  <x:Members>\n"
        '    <x:Property Name="in_StBound" Type="InArgument(x:String)" />\n'
        "  </x:Members>\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    caller = tmp_path / "Caller.xaml"
    caller.write_text(
        '<Activity>\n'
        '  <ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">\n'
        "    <ui:InvokeWorkflowFile.Arguments>\n"
        '      <InArgument x:Key="in_StBound">["value"]</InArgument>\n'
        "    </ui:InvokeWorkflowFile.Arguments>\n"
        "  </ui:InvokeWorkflowFile>\n"
        "</Activity>\n",
        encoding="utf-8",
    )

    findings = detect_unused_arguments(
        _rule("U-2", "delete_argument_declaration"),
        FileContext(callee),
        ProjectContext(tmp_path, {"projectType": "Process"}),
    )

    assert findings == []
