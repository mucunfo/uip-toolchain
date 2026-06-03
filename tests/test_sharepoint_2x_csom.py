from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.fixers import (
    apply_remove_sharepoint_2x_current_user_probe,
    apply_remove_stale_csom_imports_and_refs,
)
from uip_engine.heuristics.sharepoint import (
    detect_sharepoint_2x_csom_user_leftovers,
    detect_sharepoint_2x_stale_csom_imports,
)


def _rule(rid: str) -> Rule:
    return Rule(
        id=rid,
        severity=Severity.ERROR,
        category="breaking",
        target="windows",
        title=rid,
        description="",
        detect={"type": "python", "params": {}},
        fix={"prose": "fix"},
    )


def _project(tmp_path: Path) -> ProjectContext:
    (tmp_path / "project.json").write_text(
        """
{
  "targetFramework": "Windows",
  "dependencies": {
    "UiPathTeam.SharePoint.Activities": "[2.0.3]"
  }
}
""".strip(),
        encoding="utf-8",
    )
    return ProjectContext.find_root(tmp_path / "project.json")


def _write_sharepoint_xaml(tmp_path: Path) -> Path:
    xaml = tmp_path / "DownloadFileSharePoint.xaml"
    xaml.write_text(
        '<Activity xmlns:msc="clr-namespace:Microsoft.SharePoint.Client;assembly=Microsoft.SharePoint.Client" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
        'xmlns:us="clr-namespace:UiPathTeam.SharePoint;assembly=UiPathTeam.SharePoint" '
        'xmlns:usa="clr-namespace:UiPathTeam.SharePoint.Activities;assembly=UiPathTeam.SharePoint.Activities" '
        'xmlns:usal="clr-namespace:UiPathTeam.SharePoint.Activities.Libraries;assembly=UiPathTeam.SharePoint.Activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '  <TextExpression.NamespacesForImplementation>\n'
        '    <x:String>Microsoft.SharePoint.Client</x:String>\n'
        '  </TextExpression.NamespacesForImplementation>\n'
        '  <TextExpression.ReferencesForImplementation>\n'
        '    <AssemblyReference>Microsoft.SharePoint.Client.Runtime</AssemblyReference>\n'
        '    <AssemblyReference>Microsoft.SharePoint.Client</AssemblyReference>\n'
        '  </TextExpression.ReferencesForImplementation>\n'
        '  <Sequence>\n'
        '    <Sequence.Variables>\n'
        '      <Variable x:TypeArguments="msc:User" Name="vSharepointUser" />\n'
        '    </Sequence.Variables>\n'
        '    <usa:GetWebLoginUser DisplayName="Get web login user" SharePointUser="[vSharepointUser]" />\n'
        '    <usal:GetFile DisplayName="Get file" RelativeUrl="[in_StPath]" LocalPath="[in_StDir]" />\n'
        '    <ui:CheckTrue ErrorMessage="[&quot;Falha&quot;+If(vSharepointUser IsNot Nothing, '
        '&#xD;&#xA;&#x9;&quot; | - Usuario robo: &quot;+vSharepointUser.Email,'
        '&#xD;&#xA;&#x9;&quot;&quot;&#xD;&#xA;)]" Expression="True" />\n'
        '  </Sequence>\n'
        '</Activity>',
        encoding="utf-8",
    )
    return xaml


def test_sp7_removes_legacy_csom_user_probe_then_sp8_cleans_refs(tmp_path):
    pc = _project(tmp_path)
    xaml = _write_sharepoint_xaml(tmp_path)
    fc = FileContext(xaml)

    findings = detect_sharepoint_2x_csom_user_leftovers(_rule("SP-7"), fc, pc)
    assert len(findings) == 1
    assert findings[0].fix_mechanical["variable"] == "vSharepointUser"

    assert apply_remove_sharepoint_2x_current_user_probe(
        xaml, findings[0].fix_mechanical, dry_run=False
    ) is True
    after_sp7 = xaml.read_text(encoding="utf-8")
    assert "vSharepointUser" not in after_sp7
    assert "GetWebLoginUser" not in after_sp7
    assert "<usal:GetFile" in after_sp7

    fc2 = FileContext(xaml)
    findings2 = detect_sharepoint_2x_stale_csom_imports(_rule("SP-8"), fc2, pc)
    assert len(findings2) == 1
    assert apply_remove_stale_csom_imports_and_refs(
        xaml, findings2[0].fix_mechanical, dry_run=False
    ) is True
    after_sp8 = xaml.read_text(encoding="utf-8")
    assert "Microsoft.SharePoint.Client" not in after_sp8
    assert "xmlns:msc" not in after_sp8
    assert "<usal:GetFile" in after_sp8


def test_sp7_does_not_fire_when_user_variable_has_extra_usage(tmp_path):
    pc = _project(tmp_path)
    xaml = _write_sharepoint_xaml(tmp_path)
    xaml.write_text(
        xaml.read_text(encoding="utf-8").replace(
            "</Sequence>",
            '<ui:LogMessage Message="[vSharepointUser.Title]" /></Sequence>',
        ),
        encoding="utf-8",
    )
    findings = detect_sharepoint_2x_csom_user_leftovers(
        _rule("SP-7"), FileContext(xaml), pc
    )
    assert findings == []
