from pathlib import Path
import pytest
from uip_engine.detectors import detect_cross_file_args
from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext


def setup_project(tmp_path):
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    return proj


def test_cross_file_caller_extra_keys(tmp_path):
    proj = setup_project(tmp_path)
    callee = proj / "Callee.xaml"
    callee.write_text("""<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <x:Members>
        <x:Property Name="in_Real" Type="InArgument(x:String)" />
      </x:Members>
      <Sequence/>
    </Activity>""")
    caller = proj / "Caller.xaml"
    caller.write_text("""<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
        xmlns:ui="http://schemas.uipath.com/workflow/activities"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <Sequence>
        <ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">
          <ui:InvokeWorkflowFile.Arguments>
            <InArgument x:TypeArguments="x:String" x:Key="in_Typo">[v]</InArgument>
          </ui:InvokeWorkflowFile.Arguments>
        </ui:InvokeWorkflowFile>
      </Sequence>
    </Activity>""")

    fc = FileContext(caller)
    pc = ProjectContext.find_root(caller)
    rule = Rule(
        id="X-50", severity=Severity.ERROR, category="breaking", target="all",
        title="x:Key fora do callee", description="",
        detect={"type": "cross_file_args", "params": {"direction": "caller_extra"}},
    )
    findings = detect_cross_file_args(rule, fc, pc)
    assert len(findings) == 1
    assert "in_Typo" in findings[0].message


def test_cross_file_callee_missing(tmp_path):
    proj = setup_project(tmp_path)
    callee = proj / "Callee.xaml"
    callee.write_text("""<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <x:Members>
        <x:Property Name="in_Required" Type="InArgument(x:String)" />
        <x:Property Name="out_Result" Type="OutArgument(x:String)" />
      </x:Members>
      <Sequence/>
    </Activity>""")
    caller = proj / "Caller.xaml"
    caller.write_text("""<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
        xmlns:ui="http://schemas.uipath.com/workflow/activities"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <Sequence>
        <ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">
          <ui:InvokeWorkflowFile.Arguments>
            <InArgument x:TypeArguments="x:String" x:Key="in_Required">[v]</InArgument>
          </ui:InvokeWorkflowFile.Arguments>
        </ui:InvokeWorkflowFile>
      </Sequence>
    </Activity>""")

    fc = FileContext(caller)
    pc = ProjectContext.find_root(caller)
    rule = Rule(
        id="X-60", severity=Severity.WARN, category="breaking", target="all",
        title="Output não capturado", description="",
        detect={"type": "cross_file_args", "params": {"direction": "callee_missing"}},
    )
    findings = detect_cross_file_args(rule, fc, pc)
    assert len(findings) == 1
    assert "out_Result" in findings[0].message
