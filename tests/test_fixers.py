from pathlib import Path
import pytest
from uip_engine.fixers import (
    apply_regex_replace, apply_rename_attribute, apply_rename_argument,
    apply_set_attribute, apply_delete_element,
    apply_rename_xclass,
    apply_rename_invoke_arg_key,
    apply_expand_self_closed_inarg,
    apply_strip_string_quotes_numeric_default,
    apply_wrap_typed_empty_array_literal,
    apply_strip_terminal_vb_line_continuation,
    apply_strip_string_format_tostring_with_delimiter,
    apply_expand_read_as_datatable_signature,
    apply_rewrite_ccs_sipagdirect_legacy_login,
    apply_rewrite_ntake_screenshot_to_classic,
    apply_set_dependency_pin,
    apply_force_attribute_in_activity_with_guards,
    apply_clear_search_steps_semantic,
    REGISTRY,
)


# ---- regex_replace ----

def test_regex_replace_modifies_file(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('DisplayName="Foo.xaml - Invoke Workflow File"')
    spec = {
        "type": "regex_replace",
        "pattern": r'DisplayName="([^"]*?)\.xaml\s*-\s*Invoke Workflow File"',
        "replacement": r'DisplayName="\1"',
    }
    changed = apply_regex_replace(f, spec, dry_run=False)
    assert changed is True
    assert 'DisplayName="Foo"' in f.read_text()


def test_regex_replace_dry_run_no_modify(tmp_path):
    f = tmp_path / "x.xaml"
    original = 'DisplayName="Foo.xaml - Invoke Workflow File"'
    f.write_text(original)
    spec = {
        "type": "regex_replace",
        "pattern": r'DisplayName="([^"]*?)\.xaml\s*-\s*Invoke Workflow File"',
        "replacement": r'DisplayName="\1"',
    }
    changed = apply_regex_replace(f, spec, dry_run=True)
    assert changed is True
    assert f.read_text() == original


def test_regex_replace_no_match_returns_false(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text("nothing to change")
    spec = {"type": "regex_replace", "pattern": "X", "replacement": "Y"}
    assert apply_regex_replace(f, spec, dry_run=False) is False


def test_set_dependency_pin_normalizes_package_casing(tmp_path):
    f = tmp_path / "project.json"
    f.write_text(
        '{"dependencies": {"UiPath.CoreIPC": "[2.0.1]"}}',
        encoding="utf-8",
    )
    changed = apply_set_dependency_pin(
        f,
        {
            "type": "set_dependency_pin",
            "package": "UiPath.CoreIpc",
            "version": "[2.0.1]",
        },
        dry_run=False,
    )
    assert changed is True
    text = f.read_text(encoding="utf-8")
    assert "UiPath.CoreIpc" in text
    assert "UiPath.CoreIPC" not in text


def test_regex_replace_w16_preserves_isnull_method(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity Condition="[foo.IsNullOrEmpty OrElse bar.IsNullOrWhiteSpace]" />',
        encoding="utf-8",
    )
    spec = {
        "type": "regex_replace",
        "pattern": (
            r'(?<![A-Za-z_:.])'
            r'(?![Ss]tring\.IsNullOr(?:Empty|WhiteSpace)\b)'
            r'([a-zA-Z_]\w*)\.(IsNullOrEmpty|IsNullOrWhiteSpace)\b'
        ),
        "replacement": r"String.\2(\1)",
    }
    assert apply_regex_replace(f, spec, dry_run=False) is True
    assert (
        'Condition="[String.IsNullOrEmpty(foo) OrElse String.IsNullOrWhiteSpace(bar)]"'
        in f.read_text(encoding="utf-8")
    )


def test_regex_replace_w39_system_net_webutility(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Assign To="[out_St]" Value="[Net.WebUtility.HtmlDecode(in_St)]" />',
        encoding="utf-8",
    )
    spec = {
        "type": "regex_replace",
        "pattern": r"(?<![A-Za-z0-9_.])Net\.WebUtility\b",
        "replacement": "System.Net.WebUtility",
    }
    assert apply_regex_replace(f, spec, dry_run=False) is True
    assert "System.Net.WebUtility.HtmlDecode" in f.read_text(encoding="utf-8")


def test_rewrite_ntake_screenshot_to_classic_preserves_outimage(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities" '
        'xmlns:uix="http://schemas.uipath.com/workflow/activities/uix" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '  <uix:NTakeScreenshot DisplayName="Take screenshot" '
        'sap2010:WorkflowViewState.IdRef="TakeScreenshot_1" '
        'OutImage="[Screenshot]" Version="V5" />\n'
        '</Activity>',
        encoding="utf-8",
    )
    assert apply_rewrite_ntake_screenshot_to_classic(f, {}, dry_run=False) is True
    out = f.read_text(encoding="utf-8")
    assert "<uix:NTakeScreenshot" not in out
    assert '<ui:TakeScreenshot DisplayName="Take screenshot"' in out
    assert 'Screenshot="[Screenshot]"' in out
    assert 'WaitBefore="{x:Null}"' in out


def test_rewrite_ntake_screenshot_to_classic_maps_inuielement_target(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities" '
        'xmlns:uix="http://schemas.uipath.com/workflow/activities/uix">\n'
        '  <uix:NTakeScreenshot DisplayName="Take Screenshot" '
        'InUiElement="[vUIFormato]" OutImage="[vImgObjFormato]" Version="V4" />\n'
        '</Activity>',
        encoding="utf-8",
    )
    assert apply_rewrite_ntake_screenshot_to_classic(f, {}, dry_run=False) is True
    out = f.read_text(encoding="utf-8")
    assert '<ui:TakeScreenshot.Target>' in out
    assert '<ui:Target Element="[vUIFormato]" />' in out
    assert 'Screenshot="[vImgObjFormato]"' in out


def test_wrap_typed_empty_array_literal_default(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:umm="clr-namespace:UiPath.MicrosoftOffice365.Models;assembly=UiPath.MicrosoftOffice365">'
        '<Variable x:TypeArguments="umm:Office365Message[]" '
        'Default="[{}]" Name="vArrMail" />',
        encoding="utf-8",
    )

    assert apply_wrap_typed_empty_array_literal(f, {}, dry_run=False) is True
    assert (
        'Default="[New UiPath.MicrosoftOffice365.Models.Office365Message() {}]"'
        in f.read_text(encoding="utf-8")
    )


def test_wrap_typed_nonempty_array_literal_default(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Variable x:TypeArguments="s:String[]" '
        'Default="[{&quot;dd/MM/yyyy HH:mm:ss&quot;, &quot;dd/MM/yyyy&quot;}]" '
        'Name="vArrFormatos" />',
        encoding="utf-8",
    )

    assert apply_wrap_typed_empty_array_literal(f, {}, dry_run=False) is True
    assert (
        'Default="[New String() {&quot;dd/MM/yyyy HH:mm:ss&quot;, &quot;dd/MM/yyyy&quot;}]"'
        in f.read_text(encoding="utf-8")
    )


def test_wrap_typed_empty_array_literal_inargument(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<InArgument x:TypeArguments="s:String[]" x:Key="in_Arr">[{}]</InArgument>',
        encoding="utf-8",
    )

    assert apply_wrap_typed_empty_array_literal(f, {}, dry_run=False) is True
    assert ">[New String() {}]</InArgument>" in f.read_text(encoding="utf-8")


def test_wrap_typed_nonempty_array_literal_inargument(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<InArgument x:TypeArguments="s:String[]" '
        'x:Key="in_Arr">[{"Settings","Constants"}]</InArgument>',
        encoding="utf-8",
    )

    assert apply_wrap_typed_empty_array_literal(f, {}, dry_run=False) is True
    assert (
        '>[New String() {"Settings","Constants"}]</InArgument>'
        in f.read_text(encoding="utf-8")
    )


def test_wrap_typed_visualbasicvalue_corrupt_empty_array(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<mva:VisualBasicValue x:TypeArguments="s:String[]" ExpressionText="{}{}" />',
        encoding="utf-8",
    )

    assert apply_wrap_typed_empty_array_literal(f, {}, dry_run=False) is True
    assert 'ExpressionText="New String() {}"' in f.read_text(encoding="utf-8")


def test_strip_terminal_vb_line_continuation(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity><FlowDecision Condition="[(foo IsNot Nothing) _]" />'
        '<Assign Value="[foo_]" /></Activity>',
        encoding="utf-8",
    )

    assert apply_strip_terminal_vb_line_continuation(f, {}, dry_run=False) is True
    content = f.read_text(encoding="utf-8")
    assert 'Condition="[(foo IsNot Nothing) ]"' in content
    assert 'Value="[foo_]"' in content


def test_strip_terminal_vb_line_continuation_dry_run(tmp_path):
    f = tmp_path / "x.xaml"
    original = '<Activity><FlowDecision Condition="[(foo) _&#xA;]" /></Activity>'
    f.write_text(original, encoding="utf-8")

    assert apply_strip_terminal_vb_line_continuation(f, {}, dry_run=True) is True
    assert f.read_text(encoding="utf-8") == original


def test_strip_string_format_tostring_with_delimiter(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity><uix:TargetApp Selector="[(String.Format(&quot;&lt;wnd title='
        "'{0}' /&gt;&quot;, in_Title)).ToStringWithDelimiter()]\" />"
        '<Assign Value="[items.ToStringWithDelimiter()]" /></Activity>',
        encoding="utf-8",
    )

    assert apply_strip_string_format_tostring_with_delimiter(f, {}, dry_run=False) is True
    content = f.read_text(encoding="utf-8")
    assert "String.Format" in content
    assert "String.Format(&quot;" in content
    assert ")).ToStringWithDelimiter()" not in content
    assert "items.ToStringWithDelimiter()" in content


def test_expand_read_as_datatable_signature(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<If Condition="[CurrentSheet.ReadAsDataTable(True,False,Nothing).Columns.Contains(&quot;X&quot;)]" />',
        encoding="utf-8",
    )

    assert apply_expand_read_as_datatable_signature(f, {}, dry_run=False) is True
    assert (
        "CurrentSheet.ReadAsDataTable(True,False,Nothing,False,Nothing).Columns"
        in f.read_text(encoding="utf-8")
    )


def test_expand_read_as_datatable_signature_ignores_already_expanded(tmp_path):
    f = tmp_path / "x.xaml"
    original = (
        '<If Condition="[CurrentSheet.ReadAsDataTable(True,False,Nothing,False,Nothing).Columns.Contains(&quot;X&quot;)]" />'
    )
    f.write_text(original, encoding="utf-8")

    assert apply_expand_read_as_datatable_signature(f, {}, dry_run=False) is False
    assert f.read_text(encoding="utf-8") == original


def test_rewrite_ccs_sipagdirect_legacy_login(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:cs="clr-namespace:CCS_SipagDirect.Sessão;assembly=CCS_SipagDirect">'
        '<x:String>CCS_SipagDirect.Sessão</x:String>'
        '<cs:LoginSipagDirect in_SSSenha="[vSenha]" '
        'in_StUrlSipagDirect="[in_Config(&quot;URLSipagDirect&quot;).ToString]" '
        'in_StUsuario="[vUsuario]" />'
        '</Activity>',
        encoding="utf-8",
    )

    assert apply_rewrite_ccs_sipagdirect_legacy_login(f, {}, dry_run=False) is True
    content = f.read_text(encoding="utf-8")
    assert 'xmlns:cs="clr-namespace:CCS_SipagDirect;assembly=CCS_SipagDirect"' in content
    assert "<x:String>CCS_SipagDirect</x:String>" in content
    assert "<cs:Login " in content
    assert "in_Senha=" in content
    assert "in_URL=" in content
    assert "in_Usuario=" in content
    assert "LoginSipagDirect" not in content


def test_rewrite_ccs_sipagdirect_legacy_login_preserves_local_property(tmp_path):
    f = tmp_path / "x.xaml"
    original = (
        '<Activity x:Class="LoginSipagDirect" xmlns:this="clr-namespace:">'
        '<this:LoginSipagDirect.in_StPrefixoLog>'
        '<InArgument x:TypeArguments="x:String" />'
        '</this:LoginSipagDirect.in_StPrefixoLog>'
        '</Activity>'
    )
    f.write_text(original, encoding="utf-8")

    assert apply_rewrite_ccs_sipagdirect_legacy_login(f, {}, dry_run=False) is False
    assert f.read_text(encoding="utf-8") == original


# ---- rename_attribute ----

def test_rename_attribute(tmp_path):
    """Renames identifier in realistic XAML positions: attribute VALUE
    (`Name="..."`) and VB body refs. Does NOT rename attribute NAMES
    (skip-by-design per 2026-05-25 safety policy — prevents renaming
    activity property names like `ColumnIndex` cascading from variable
    rename N-1 finding)."""
    f = tmp_path / "x.xaml"
    f.write_text('<Variable Name="inout_Foo" Value="bar"/>')
    spec = {"type": "rename_attribute", "from": "inout_Foo", "to": "io_Foo"}
    changed = apply_rename_attribute(f, spec, dry_run=False)
    assert changed
    assert 'Name="io_Foo"' in f.read_text()


def test_rename_attribute_case_insensitive_vb_refs(tmp_path):
    """2026-05-01 regression: declaração `dt_X` (lowercase) com refs VB
    `[Dt_X]` (mixed case) ficavam órfãs. VB é case-insensitive — rename
    deve cobrir todas variações de case fora de element-name context."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<root xmlns="urn:r" xmlns:ui="urn:ui">'
        '<Variable Name="dt_X" />'
        '<ui:ReadRange DataTable="[Dt_X]" />'
        r'<ui:LogMessage Message="[&quot;rows: &quot; + DT_X.Rows.Count.ToString]" />'
        '</root>'
    )
    spec = {"type": "rename_attribute", "from": "dt_X", "to": "vDTabX"}
    changed = apply_rename_attribute(f, spec, dry_run=False)
    assert changed
    out = f.read_text()
    # All refs (any case) renamed
    assert 'Name="vDTabX"' in out
    assert '[vDTabX]' in out
    assert 'vDTabX.Rows' in out
    # No orphan refs of any case
    assert 'dt_X' not in out and 'Dt_X' not in out and 'DT_X' not in out


def test_rename_attribute_orphan_check_skips_when_unsafe(tmp_path):
    """Se after-rename ainda existe ref `from_name`, fixer aborta ao invés
    de gravar arquivo parcialmente migrado."""
    f = tmp_path / "x.xaml"
    # Element name with same identifier — não deve ser renomeado, mas tb
    # não dispara abort (skipped by element-name context, não orphan).
    f.write_text('<root xmlns:ns="urn:n" xmlns="urn:r"><ns:foo Name="foo"/></root>')
    spec = {"type": "rename_attribute", "from": "foo", "to": "bar"}
    apply_rename_attribute(f, spec, dry_run=False)
    out = f.read_text()
    # Element name preserved (skip-tag context), Name attr renamed
    assert '<ns:foo' in out
    assert 'Name="bar"' in out


def test_rename_attribute_skips_duplicate_invoke_arg_keys(tmp_path):
    f = tmp_path / "x.xaml"
    original = (
        '<Activity>'
        '<ui:InvokeWorkflowFile WorkflowFileName="Process.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '<InArgument x:TypeArguments="ui:UiElement" x:Key="in_UiEFluig">[v]</InArgument>'
        '<InArgument x:TypeArguments="ui:UiElement" x:Key="in_UIEFluig">[v]</InArgument>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile>'
        '</Activity>'
    )
    f.write_text(original, encoding="utf-8")

    changed = apply_rename_attribute(
        f,
        {"type": "rename_attribute", "from": "in_UiEFluig", "to": "in_UIEFluig"},
        dry_run=False,
    )

    assert changed is False
    assert f.read_text(encoding="utf-8") == original


# ---- rename_argument ----

def test_rename_argument_cascades(tmp_path):
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    callee = proj / "Callee.xaml"
    callee.write_text('<x:Property Name="in_old" Type="InArgument(x:String)"/>')
    caller = proj / "Caller.xaml"
    caller.write_text('<ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml"><ui:InvokeWorkflowFile.Arguments><InArgument x:Key="in_old">[v]</InArgument></ui:InvokeWorkflowFile.Arguments></ui:InvokeWorkflowFile>')

    spec = {
        "type": "rename_argument",
        "from": "in_old",
        "to": "in_New",
        "target_workflow": "Callee.xaml",
    }
    changed = apply_rename_argument(callee, spec, dry_run=False, project_root=proj)
    assert changed
    assert 'Name="in_New"' in callee.read_text()
    assert 'x:Key="in_New"' in caller.read_text()


def test_rename_argument_skips_caller_block_when_key_would_duplicate(tmp_path):
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    callee = proj / "Callee.xaml"
    callee.write_text('<x:Property Name="in_old" Type="InArgument(x:String)"/>')
    caller = proj / "Caller.xaml"
    original_caller = (
        '<ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '<InArgument x:Key="in_old">[v]</InArgument>'
        '<InArgument x:Key="in_New">[v2]</InArgument>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile>'
    )
    caller.write_text(original_caller)

    changed = apply_rename_argument(
        callee,
        {
            "type": "rename_argument",
            "from": "in_old",
            "to": "in_New",
            "target_workflow": "Callee.xaml",
        },
        dry_run=False,
        project_root=proj,
    )

    assert changed is True
    assert 'Name="in_New"' in callee.read_text()
    assert caller.read_text() == original_caller


def test_rename_argument_skips_primary_file_when_key_would_duplicate(tmp_path):
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    callee = proj / "Callee.xaml"
    original = (
        '<x:Property Name="in_old" Type="InArgument(x:String)"/>'
        '<ui:InvokeWorkflowFile WorkflowFileName="Other.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '<InArgument x:Key="in_old">[v]</InArgument>'
        '<InArgument x:Key="in_New">[v2]</InArgument>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile>'
    )
    callee.write_text(original)

    changed = apply_rename_argument(
        callee,
        {"type": "rename_argument", "from": "in_old", "to": "in_New"},
        dry_run=False,
        project_root=proj,
    )

    assert changed is False
    assert callee.read_text() == original


def test_rename_invoke_arg_key_skips_when_target_key_already_exists(tmp_path):
    f = tmp_path / "Caller.xaml"
    original = (
        '<ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '<InArgument x:Key="in_Old">[v]</InArgument>'
        '<InArgument x:Key="in_New">[v2]</InArgument>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile>'
    )
    f.write_text(original, encoding="utf-8")

    changed = apply_rename_invoke_arg_key(
        f,
        {
            "workflow_basename": "Callee.xaml",
            "from_key": "in_Old",
            "to_key": "in_New",
        },
        dry_run=False,
    )

    assert changed is False
    assert f.read_text(encoding="utf-8") == original


def test_rename_argument_propertyelement_attribute_form(tmp_path):
    """2026-05-01: regression — caller seta default-value via attribute
    `this:Callee.in_old="value"` em <Activity> root. Rename de arg no callee
    não atualizava callers nesse pattern. Fix 1 cobre via this_arg_pattern."""
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    callee = proj / "ExtratoSisbr.xaml"
    callee.write_text(
        '<root xmlns:x="urn:x">'
        '<x:Property Name="in_StCpfCnpj" Type="InArgument(x:String)"/>'
        '</root>'
    )
    caller = proj / "Caller.xaml"
    caller.write_text(
        '<Activity x:Class="Caller" '
        'this:ExtratoSisbr.in_StCpfCnpj="03567879000146" '
        'xmlns:this="clr-namespace:" xmlns="urn:r" xmlns:x="urn:x"/>'
    )

    spec = {
        "type": "rename_argument",
        "from": "in_StCpfCnpj",
        "to": "in_StCPFCNPJ",
        "target_workflow": "ExtratoSisbr.xaml",
    }
    changed = apply_rename_argument(callee, spec, dry_run=False, project_root=proj)
    assert changed
    assert 'this:ExtratoSisbr.in_StCPFCNPJ="03567879000146"' in caller.read_text()
    assert 'in_StCpfCnpj' not in caller.read_text()


def test_rename_argument_propertyelement_element_form(tmp_path):
    """Caller seta default-value via element form
    `<this:Callee.in_old>...</this:Callee.in_old>`. Mesmo fix cobre."""
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    callee = proj / "CCB.xaml"
    callee.write_text(
        '<root xmlns:x="urn:x">'
        '<x:Property Name="in_StNumDocumento" Type="InArgument(x:String)"/>'
        '</root>'
    )
    caller = proj / "FaturaDoCartao.xaml"
    caller.write_text(
        '<root xmlns:this="clr-namespace:" xmlns="urn:r" xmlns:x="urn:x">'
        '<this:CCB.in_StNumDocumento>'
        '<InArgument x:TypeArguments="x:String">[v]</InArgument>'
        '</this:CCB.in_StNumDocumento>'
        '</root>'
    )

    spec = {
        "type": "rename_argument",
        "from": "in_StNumDocumento",
        "to": "in_StNumeroDocumento",
        "target_workflow": "CCB.xaml",
    }
    changed = apply_rename_argument(callee, spec, dry_run=False, project_root=proj)
    assert changed
    out = caller.read_text()
    assert '<this:CCB.in_StNumeroDocumento>' in out
    assert '</this:CCB.in_StNumeroDocumento>' in out
    assert 'in_StNumDocumento' not in out


def test_rename_argument_idempotent_propertyelement(tmp_path):
    """Aplicar rename 2× = sem mudança no segundo pass (idempotente)."""
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text('{"targetFramework":"Windows"}')
    callee = proj / "CCB.xaml"
    callee.write_text(
        '<root xmlns:x="urn:x">'
        '<x:Property Name="in_StCpfCnpj" Type="InArgument(x:String)"/>'
        '</root>'
    )
    caller = proj / "Garantia.xaml"
    caller.write_text(
        '<Activity x:Class="Garantia" this:CCB.in_StCpfCnpj="x" '
        'xmlns:this="clr-namespace:" xmlns="urn:r" xmlns:x="urn:x"/>'
    )
    spec = {
        "type": "rename_argument",
        "from": "in_StCpfCnpj",
        "to": "in_StCPFCNPJ",
        "target_workflow": "CCB.xaml",
    }
    apply_rename_argument(callee, spec, dry_run=False, project_root=proj)
    after_first_callee = callee.read_text()
    after_first_caller = caller.read_text()
    # 2º pass com mesma spec — após rename já feito, from_name não existe mais.
    # Detector chamaria com from→to já alinhado, retornando False (no change).
    changed2 = apply_rename_argument(callee, spec, dry_run=False, project_root=proj)
    assert changed2 is False
    assert callee.read_text() == after_first_callee
    assert caller.read_text() == after_first_caller


# ---- set_attribute ----

def test_force_attribute_replaces(tmp_path):
    """force_attribute substitui valor existente diferente do canonical."""
    from uip_engine.fixers import apply_force_attribute
    f = tmp_path / "x.xaml"
    f.write_text('<root xmlns:ui="urn:ui"><ui:LogMessage Level="Info" Message="x"/></root>')
    spec = {"type": "force_attribute", "tag": "ui:LogMessage",
            "attribute": "Level", "value": "Trace"}
    changed = apply_force_attribute(f, spec, dry_run=False)
    assert changed
    assert 'Level="Trace"' in f.read_text()
    assert 'Level="Info"' not in f.read_text()


def test_force_attribute_sendmail_use_is_connection_true_to_false(tmp_path):
    from uip_engine.fixers import apply_force_attribute
    f = tmp_path / "x.xaml"
    f.write_text(
        '<root xmlns:ui="urn:ui">'
        '<ui:SendMail UseISConnection="True" Subject="x"/>'
        '</root>'
    )
    spec = {
        "type": "force_attribute",
        "tag": "ui:SendMail",
        "attribute": "UseISConnection",
        "value": "False",
    }
    changed = apply_force_attribute(f, spec, dry_run=False)
    assert changed
    out = f.read_text()
    assert 'UseISConnection="False"' in out
    assert 'UseISConnection="True"' not in out


def test_force_attribute_adds(tmp_path):
    from uip_engine.fixers import apply_force_attribute
    f = tmp_path / "x.xaml"
    f.write_text('<root xmlns:ui="urn:ui"><ui:LogMessage Message="x"/></root>')
    spec = {"type": "force_attribute", "tag": "ui:LogMessage",
            "attribute": "Level", "value": "Trace"}
    changed = apply_force_attribute(f, spec, dry_run=False)
    assert changed
    assert 'Level="Trace"' in f.read_text()
    assert '<ui:LogMessage Message="x" Level="Trace"/>' in f.read_text()


def test_force_attribute_idempotent(tmp_path):
    from uip_engine.fixers import apply_force_attribute
    f = tmp_path / "x.xaml"
    f.write_text('<root xmlns:ui="urn:ui"><ui:LogMessage Level="Trace" Message="x"/></root>')
    spec = {"type": "force_attribute", "tag": "ui:LogMessage",
            "attribute": "Level", "value": "Trace"}
    changed = apply_force_attribute(f, spec, dry_run=False)
    assert changed is False


def test_force_attribute_in_activity_with_guards_only_matches_all_guards(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<ui:HttpClient Method="GET" ContinueOnError="True" />'
        '<ui:HttpClient Method="POST" Endpoint="u" />'
        '<ui:HttpClient ContinueOnError="True" Method="POST" />'
        '</Activity>',
        encoding="utf-8",
    )
    spec = {
        "type": "force_attribute_in_activity_with_guards",
        "prefix": "ui",
        "activity_local": "HttpClient",
        "guards": {"Method": "POST", "ContinueOnError": "True"},
        "attr_name": "ContinueOnError",
        "target_value": "False",
    }

    changed = apply_force_attribute_in_activity_with_guards(f, spec, dry_run=False)

    assert changed is True
    text = f.read_text(encoding="utf-8")
    assert '<ui:HttpClient Method="GET" ContinueOnError="True" />' in text
    assert '<ui:HttpClient Method="POST" Endpoint="u" />' in text
    assert '<ui:HttpClient ContinueOnError="False" Method="POST" />' in text
    assert apply_force_attribute_in_activity_with_guards(f, spec, dry_run=False) is False


def test_clear_search_steps_semantic_attribute_text(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:uix="http://schemas.uipath.com/workflow/activities/uix">'
        '<uix:TargetAnchorable SearchSteps="Selector | Image | SemanticSelector" />'
        '</Activity>',
        encoding="utf-8",
    )

    changed = apply_clear_search_steps_semantic(
        f, {"type": "clear_search_steps_semantic"}, dry_run=False
    )

    assert changed is True
    assert 'SearchSteps="Selector | Image"' in f.read_text(encoding="utf-8")
    assert apply_clear_search_steps_semantic(
        f, {"type": "clear_search_steps_semantic"}, dry_run=False
    ) is False


def test_clear_search_steps_semantic_numeric_and_empty_result_default(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:uix="http://schemas.uipath.com/workflow/activities/uix">'
        '<uix:TargetAnchorable SearchSteps="0x184" />'
        '<uix:TargetAnchorable SearchSteps="0x80" />'
        '</Activity>',
        encoding="utf-8",
    )

    apply_clear_search_steps_semantic(
        f, {"type": "clear_search_steps_semantic"}, dry_run=False
    )

    text = f.read_text(encoding="utf-8")
    assert 'SearchSteps="0x4"' in text
    assert 'SearchSteps="Selector | FuzzySelector"' in text


def test_clear_search_steps_semantic_property_element_static(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:uix="http://schemas.uipath.com/workflow/activities/uix" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        '<uix:TargetAnchorable>'
        '<uix:TargetAnchorable.SearchSteps>'
        '<x:Static Member="uix:TargetSearchStep.SemanticSelector" />'
        '</uix:TargetAnchorable.SearchSteps>'
        '</uix:TargetAnchorable>'
        '</Activity>',
        encoding="utf-8",
    )

    changed = apply_clear_search_steps_semantic(
        f, {"type": "clear_search_steps_semantic"}, dry_run=False
    )

    assert changed is True
    text = f.read_text(encoding="utf-8")
    assert (
        "<uix:TargetAnchorable.SearchSteps>Selector | FuzzySelector"
        "</uix:TargetAnchorable.SearchSteps>"
    ) in text
    assert "SemanticSelector" not in text


def test_set_json_field(tmp_path):
    from uip_engine.fixers import apply_set_json_field
    f = tmp_path / "project.json"
    f.write_text('{"name":"test","studioVersion":"24.10.0"}')
    spec = {"type": "set_json_field", "path": "studioVersion", "value": "23.10.13"}
    changed = apply_set_json_field(f, spec, dry_run=False)
    assert changed
    import json
    data = json.loads(f.read_text())
    assert data["studioVersion"] == "23.10.13"
    assert data["name"] == "test"


def test_set_json_field_idempotent(tmp_path):
    from uip_engine.fixers import apply_set_json_field
    f = tmp_path / "project.json"
    f.write_text('{"studioVersion":"23.10.13"}')
    spec = {"type": "set_json_field", "path": "studioVersion", "value": "23.10.13"}
    changed = apply_set_json_field(f, spec, dry_run=False)
    assert changed is False


def test_delete_variable_self_close(tmp_path):
    from uip_engine.fixers import apply_delete_variable
    f = tmp_path / "x.xaml"
    f.write_text(
        '<root xmlns:x="urn:x">'
        '<Sequence.Variables>'
        '<Variable x:TypeArguments="x:String" Name="vStUnused" />'
        '<Variable x:TypeArguments="x:Int32" Name="vIntKept" />'
        '</Sequence.Variables>'
        '</root>'
    )
    spec = {"type": "delete_variable", "name": "vStUnused"}
    changed = apply_delete_variable(f, spec, dry_run=False)
    assert changed
    out = f.read_text()
    assert 'Name="vStUnused"' not in out
    assert 'Name="vIntKept"' in out


def test_delete_variable_idempotent(tmp_path):
    from uip_engine.fixers import apply_delete_variable
    f = tmp_path / "x.xaml"
    f.write_text('<root><Variable Name="vKept" /></root>')
    spec = {"type": "delete_variable", "name": "vNotPresent"}
    changed = apply_delete_variable(f, spec, dry_run=False)
    assert changed is False


def test_delete_variable_declaration_removes_only_selected_occurrence(tmp_path):
    from uip_engine.fixers import apply_delete_variable_declaration
    f = tmp_path / "x.xaml"
    first = '<Variable x:TypeArguments="x:String" Name="vStDuplicada" />'
    second = '<Variable x:TypeArguments="x:String" Name="vStDuplicada" Default="[String.Empty]" />'
    f.write_text(
        "<root>\n"
        "  <Sequence.Variables>\n"
        f"    {first}\n"
        "  </Sequence.Variables>\n"
        "  <Sequence>\n"
        "    <Sequence.Variables>\n"
        f"      {second}\n"
        "    </Sequence.Variables>\n"
        "  </Sequence>\n"
        "</root>\n",
        encoding="utf-8",
    )
    spec = {
        "type": "delete_variable_declaration",
        "name": "vStDuplicada",
        "line": 7,
        "declaration": second,
    }
    changed = apply_delete_variable_declaration(f, spec, dry_run=False)
    assert changed
    out = f.read_text(encoding="utf-8")
    assert first in out
    assert second not in out


def test_delete_argument_declaration_removes_property_and_default(tmp_path):
    from uip_engine.fixers import apply_delete_argument_declaration

    f = tmp_path / "x.xaml"
    declaration = '<x:Property Name="in_StUnused" Type="InArgument(x:String)" />'
    f.write_text(
        '<Activity x:Class="Workflow.Main" '
        'this:Main.in_StAttrUnused="[&quot;x&quot;]">\n'
        "  <x:Members>\n"
        f"    {declaration}\n"
        '    <x:Property Name="in_StKept" Type="InArgument(x:String)" />\n'
        '    <x:Property Name="in_StAttrUnused" Type="InArgument(x:String)" />\n'
        "  </x:Members>\n"
        "  <this:Main.in_StUnused>\n"
        '    <InArgument x:TypeArguments="x:String">["x"]</InArgument>\n'
        "  </this:Main.in_StUnused>\n"
        "</Activity>\n",
        encoding="utf-8",
    )

    changed = apply_delete_argument_declaration(
        f,
        {
            "type": "delete_argument_declaration",
            "name": "in_StUnused",
            "line": 3,
            "declaration": declaration,
            "class_name": "Workflow.Main",
        },
        dry_run=False,
    )

    assert changed
    out = f.read_text(encoding="utf-8")
    assert declaration not in out
    assert "this:Main.in_StUnused" not in out
    assert 'Name="in_StKept"' in out
    assert 'Name="in_StAttrUnused"' in out
    assert 'this:Main.in_StAttrUnused="[&quot;x&quot;]"' in out


def test_strip_namespace_import(tmp_path):
    from uip_engine.fixers import apply_strip_namespace_import
    f = tmp_path / "x.xaml"
    f.write_text(
        "<Activity>\n"
        "  <TextExpression.NamespacesForImplementation>\n"
        "    <scg:List x:TypeArguments=\"x:String\">\n"
        "      <x:String>System</x:String>\n"
        "      <x:String>System.Activities.DynamicUpdate</x:String>\n"
        "    </scg:List>\n"
        "  </TextExpression.NamespacesForImplementation>\n"
        "</Activity>\n",
        encoding="utf-8",
    )
    changed = apply_strip_namespace_import(
        f, {"name": "System.Activities.DynamicUpdate"}, dry_run=False
    )
    assert changed
    out = f.read_text(encoding="utf-8")
    assert "System.Activities.DynamicUpdate" not in out
    assert "<x:String>System</x:String>" in out


def test_delete_empty_element_open_close(tmp_path):
    from uip_engine.fixers import apply_delete_empty_element
    f = tmp_path / "x.xaml"
    f.write_text(
        '<root xmlns:x="urn:x">'
        '<Sequence>'
        '<Sequence.Variables>   </Sequence.Variables>'
        '<Body/>'
        '</Sequence>'
        '</root>'
    )
    spec = {"type": "delete_empty_element", "tag": "Sequence.Variables"}
    changed = apply_delete_empty_element(f, spec, dry_run=False)
    assert changed
    out = f.read_text()
    assert '<Sequence.Variables>' not in out
    assert '<Body/>' in out


def test_delete_empty_element_self_close(tmp_path):
    from uip_engine.fixers import apply_delete_empty_element
    f = tmp_path / "x.xaml"
    f.write_text('<root><Sequence.Variables /></root>')
    spec = {"type": "delete_empty_element", "tag": "Sequence.Variables"}
    changed = apply_delete_empty_element(f, spec, dry_run=False)
    assert changed
    assert '<Sequence.Variables' not in f.read_text()


def test_delete_empty_element_idempotent(tmp_path):
    from uip_engine.fixers import apply_delete_empty_element
    f = tmp_path / "x.xaml"
    f.write_text('<root><X/></root>')
    spec = {"type": "delete_empty_element", "tag": "Sequence.Variables"}
    assert apply_delete_empty_element(f, spec, dry_run=False) is False


def test_delete_empty_element_preserves_non_empty(tmp_path):
    """Não remove se tem content real."""
    from uip_engine.fixers import apply_delete_empty_element
    f = tmp_path / "x.xaml"
    f.write_text(
        '<root xmlns:x="urn:x">'
        '<Sequence.Variables><Variable Name="v"/></Sequence.Variables>'
        '</root>'
    )
    spec = {"type": "delete_empty_element", "tag": "Sequence.Variables"}
    changed = apply_delete_empty_element(f, spec, dry_run=False)
    assert changed is False
    assert '<Variable Name="v"/>' in f.read_text()


def test_set_attribute(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<ui:SendMail UseAttachmentsBackup="True"/>')
    spec = {"type": "set_attribute", "tag": "ui:SendMail",
            "attribute": "UseISConnection", "value": "False"}
    changed = apply_set_attribute(f, spec, dry_run=False)
    assert changed
    out = f.read_text()
    assert 'UseISConnection="False"' in out
    # well-formed: self-close marker preserved corretamente, sem corrupção
    assert out == '<ui:SendMail UseAttachmentsBackup="True" UseISConnection="False"/>'


def test_set_attribute_self_close_preserved(tmp_path):
    """Regression: 2026-05-01 — set_attribute em duas passes corrompia
    self-close. Output ficava `<X attrs/ NewAttr="...">` (`/` órfão dentro
    do atributos, sem `/>` ao final). Pattern unificado com lazy `[^>]*?`
    + grupo opcional `(/?)` captura self-close em uma pass."""
    import xml.etree.ElementTree as ET
    f = tmp_path / "x.xaml"
    f.write_text('<root xmlns:ui="urn:ui" xmlns:x="urn:x"><ui:DeserializeJson x:TypeArguments="njl:JObject" JsonString="x"/></root>')
    spec = {"type": "set_attribute", "tag": "ui:DeserializeJson",
            "attribute": "JsonSample", "value": "{x:Null}"}
    changed = apply_set_attribute(f, spec, dry_run=False)
    assert changed
    # well-formed XML pós-fix
    ET.fromstring(f.read_text())
    out = f.read_text()
    assert 'JsonSample="{x:Null}"/>' in out
    assert 'JsonSample="{x:Null}"/' not in out.replace('JsonSample="{x:Null}"/>', '')


def test_set_attribute_open_close_tag(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<root xmlns:ui="urn:ui"><ui:Foo Bar="x"></ui:Foo></root>')
    spec = {"type": "set_attribute", "tag": "ui:Foo",
            "attribute": "Baz", "value": "y"}
    apply_set_attribute(f, spec, dry_run=False)
    out = f.read_text()
    assert '<ui:Foo Bar="x" Baz="y">' in out
    assert '</ui:Foo>' in out


# ---- delete_element ----

def test_delete_element(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<Sequence><Delay Duration="00:00:05"/></Sequence>')
    spec = {"type": "delete_element", "pattern": r"<Delay\s[^/>]*/>"}
    changed = apply_delete_element(f, spec, dry_run=False)
    assert changed
    assert "Delay" not in f.read_text()


# ---- Idempotency ----

def test_regex_replace_idempotent(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('DisplayName="Foo.xaml - Invoke Workflow File"')
    spec = {
        "type": "regex_replace",
        "pattern": r'DisplayName="([^"]*?)\.xaml\s*-\s*Invoke Workflow File"',
        "replacement": r'DisplayName="\1"',
    }
    apply_regex_replace(f, spec, dry_run=False)
    after1 = f.read_text()
    apply_regex_replace(f, spec, dry_run=False)
    after2 = f.read_text()
    assert after1 == after2


def test_rename_attribute_idempotent(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<Property inout_Foo="bar"/>')
    spec = {"type": "rename_attribute", "from": "inout_Foo", "to": "io_Foo"}
    apply_rename_attribute(f, spec, dry_run=False)
    after1 = f.read_text()
    apply_rename_attribute(f, spec, dry_run=False)
    after2 = f.read_text()
    assert after1 == after2


def test_set_attribute_idempotent(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<ui:SendMail X="1"/>')
    spec = {"type": "set_attribute", "tag": "ui:SendMail",
            "attribute": "UseISConnection", "value": "False"}
    apply_set_attribute(f, spec, dry_run=False)
    after1 = f.read_text()
    apply_set_attribute(f, spec, dry_run=False)
    after2 = f.read_text()
    assert after1 == after2


# ---- Registry ----

def test_registry_has_all_fixers():
    for name in ("regex_replace", "rename_attribute", "rename_argument",
                 "set_attribute", "delete_element", "rename_xclass"):
        assert name in REGISTRY, f"fixer {name} missing"


# ---- rename_xclass ----

def test_rename_xclass_renames_attribute_and_this_refs_same_file(tmp_path):
    f = tmp_path / "Login.xaml"
    f.write_text(
        '<Activity x:Class="OldLogin" xmlns:this="clr-namespace:">'
        '<this:OldLogin.in_User><InArgument x:TypeArguments="x:String">'
        '<Literal Value="x"/></InArgument></this:OldLogin.in_User>'
        '</Activity>'
    )
    spec = {"type": "rename_xclass"}
    changed = apply_rename_xclass(f, spec, dry_run=False)
    assert changed
    txt = f.read_text()
    assert 'x:Class="Login"' in txt
    assert 'this:Login.in_User' in txt
    assert 'OldLogin' not in txt


def test_rename_xclass_propagates_to_callers(tmp_path):
    proj = tmp_path
    callee = proj / "Worker.xaml"
    callee.write_text('<Activity x:Class="OldWorker" xmlns:this="clr-namespace:"/>')
    caller = proj / "Caller.xaml"
    caller.write_text(
        '<Activity><ui:InvokeWorkflowFile WorkflowFileName="Worker.xaml">'
        '<this:OldWorker.in_X><Literal Value="y"/></this:OldWorker.in_X>'
        '<InArgument x:Key="OldWorker.in_Y">[v]</InArgument>'
        '</ui:InvokeWorkflowFile></Activity>'
    )
    changed = apply_rename_xclass(callee, {"type": "rename_xclass"},
                                  dry_run=False, project_root=proj)
    assert changed
    assert 'x:Class="Worker"' in callee.read_text()
    caller_txt = caller.read_text()
    assert 'this:Worker.in_X' in caller_txt
    assert 'x:Key="Worker.in_Y"' in caller_txt
    assert 'OldWorker' not in caller_txt


def test_rename_xclass_idempotent(tmp_path):
    f = tmp_path / "Foo.xaml"
    f.write_text('<Activity x:Class="Bar"/>')
    spec = {"type": "rename_xclass"}
    apply_rename_xclass(f, spec, dry_run=False)
    after1 = f.read_text()
    changed2 = apply_rename_xclass(f, spec, dry_run=False)
    assert changed2 is False
    assert f.read_text() == after1


def test_rename_xclass_no_op_when_already_matches(tmp_path):
    f = tmp_path / "Foo.xaml"
    f.write_text('<Activity x:Class="Foo"/>')
    changed = apply_rename_xclass(f, {"type": "rename_xclass"}, dry_run=False)
    assert changed is False


def test_rename_xclass_dry_run_does_not_write(tmp_path):
    f = tmp_path / "Foo.xaml"
    original = '<Activity x:Class="Bar" xmlns:this="clr-namespace:"><this:Bar.in_X/></Activity>'
    f.write_text(original)
    changed = apply_rename_xclass(f, {"type": "rename_xclass"}, dry_run=True)
    assert changed is True
    assert f.read_text() == original


# ---- expand_self_closed_inarg (W-1) ----

def test_expand_self_closed_inarg_string(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text(
        '<Activity><InArgument x:TypeArguments="x:String" x:Key="in_StFoo" /></Activity>'
    )
    changed = apply_expand_self_closed_inarg(f, {}, dry_run=False)
    assert changed is True
    out = f.read_text()
    assert '<Literal x:TypeArguments="x:String" Value="" />' in out
    assert "/></InArgument>" in out


def test_expand_self_closed_inarg_int_default_zero(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text(
        '<Activity><InArgument x:TypeArguments="x:Int32" x:Key="in_IntFoo" /></Activity>'
    )
    apply_expand_self_closed_inarg(f, {}, dry_run=False)
    assert '<Literal x:TypeArguments="x:Int32" Value="0" />' in f.read_text()


def test_expand_self_closed_inarg_boolean_default_false(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text(
        '<Activity><InArgument x:TypeArguments="x:Boolean" x:Key="in_Bl" /></Activity>'
    )
    apply_expand_self_closed_inarg(f, {}, dry_run=False)
    assert '<Literal x:TypeArguments="x:Boolean" Value="False" />' in f.read_text()


def test_expand_self_closed_inarg_complex_type_uses_xnull(tmp_path):
    """Tipos complexos (Tuple, Dict) usam <x:Null /> — Literal Value="" quebra."""
    f = tmp_path / "X.xaml"
    f.write_text(
        '<Activity><InArgument x:TypeArguments="s:Tuple(x:String, ss:SecureString)" '
        'x:Key="in_TupleCred" /></Activity>'
    )
    apply_expand_self_closed_inarg(f, {}, dry_run=False)
    out = f.read_text()
    assert "<x:Null />" in out
    assert "Literal" not in out


def test_expand_self_closed_inarg_skip_without_xkey(tmp_path):
    """Self-closed sem x:Key não é caller-side, não expandir."""
    f = tmp_path / "X.xaml"
    original = '<Activity><InArgument x:TypeArguments="x:String" /></Activity>'
    f.write_text(original)
    changed = apply_expand_self_closed_inarg(f, {}, dry_run=False)
    assert changed is False
    assert f.read_text() == original


def test_expand_self_closed_inarg_dry_run(tmp_path):
    f = tmp_path / "X.xaml"
    original = '<Activity><InArgument x:TypeArguments="x:String" x:Key="in_X" /></Activity>'
    f.write_text(original)
    changed = apply_expand_self_closed_inarg(f, {}, dry_run=True)
    assert changed is True
    assert f.read_text() == original


# ---- strip_string_quotes_numeric_default (V-2) ----

def test_strip_int_default_element_form(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text(
        '<Activity><InArgument x:TypeArguments="x:Int32">[&quot;60&quot;]</InArgument></Activity>'
    )
    changed = apply_strip_string_quotes_numeric_default(f, {}, dry_run=False)
    assert changed is True
    assert '<InArgument x:TypeArguments="x:Int32">[60]</InArgument>' in f.read_text()


def test_strip_int_default_attr_form(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text(
        '<Activity xmlns:this="clr-namespace:" '
        'this:Foo.in_IntTimeout="[&quot;60&quot;]" />'
    )
    apply_strip_string_quotes_numeric_default(f, {}, dry_run=False)
    assert 'this:Foo.in_IntTimeout="[60]"' in f.read_text()


def test_strip_bool_default_capitalizes(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text(
        '<Activity><InArgument x:TypeArguments="x:Boolean">[&quot;true&quot;]</InArgument></Activity>'
    )
    apply_strip_string_quotes_numeric_default(f, {}, dry_run=False)
    assert '[True]</InArgument>' in f.read_text()


def test_strip_skip_non_numeric_string(tmp_path):
    """Conteúdo não-numérico — preservar (provavelmente String legítimo)."""
    f = tmp_path / "X.xaml"
    original = '<Activity><InArgument x:TypeArguments="x:Int32">[&quot;abc&quot;]</InArgument></Activity>'
    f.write_text(original)
    changed = apply_strip_string_quotes_numeric_default(f, {}, dry_run=False)
    assert changed is False
    assert f.read_text() == original


def test_strip_dry_run(tmp_path):
    f = tmp_path / "X.xaml"
    original = '<Activity><InArgument x:TypeArguments="x:Int32">[&quot;60&quot;]</InArgument></Activity>'
    f.write_text(original)
    changed = apply_strip_string_quotes_numeric_default(f, {}, dry_run=True)
    assert changed is True
    assert f.read_text() == original


def test_strip_idempotent(tmp_path):
    f = tmp_path / "X.xaml"
    f.write_text(
        '<Activity><InArgument x:TypeArguments="x:Int32">[60]</InArgument></Activity>'
    )
    changed = apply_strip_string_quotes_numeric_default(f, {}, dry_run=False)
    assert changed is False


# ---- rename_element (CRY-5, IOCR-4) ----

from uip_engine.fixers import apply_rename_element


def _rn_spec(prefix="ui", old_local="HashText", new_local="KeyedHashText"):
    return {
        "type": "rename_element",
        "prefix": prefix,
        "old_local": old_local,
        "new_local": new_local,
    }


def test_rename_element_open_close_and_property(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x">\n'
        '  <ui:HashText Key="k">\n'
        '    <ui:HashText.Input>txt</ui:HashText.Input>\n'
        '  </ui:HashText>\n'
        '</Activity>'
    )
    changed = apply_rename_element(f, _rn_spec(), dry_run=False)
    assert changed is True
    content = f.read_text()
    assert "<ui:KeyedHashText Key=" in content
    assert "<ui:KeyedHashText.Input>" in content
    assert "</ui:KeyedHashText.Input>" in content
    assert "</ui:KeyedHashText>" in content
    assert "HashText" not in content.replace("KeyedHashText", "")


def test_rename_element_word_boundary(tmp_path):
    """HashText rename NÃO deve tocar HashTextExtended."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x">\n'
        '  <ui:HashText Key="k"/>\n'
        '  <ui:HashTextExtended/>\n'
        '</Activity>'
    )
    apply_rename_element(f, _rn_spec(), dry_run=False)
    content = f.read_text()
    assert "<ui:KeyedHashText " in content
    assert "<ui:HashTextExtended/>" in content


def test_rename_element_idempotent(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<Activity xmlns:ui="x"><ui:KeyedHashText Key="k"/></Activity>')
    changed = apply_rename_element(f, _rn_spec(), dry_run=False)
    assert changed is False


def test_rename_element_dry_run(tmp_path):
    f = tmp_path / "x.xaml"
    original = '<Activity xmlns:ui="x"><ui:HashText Key="k"/></Activity>'
    f.write_text(original)
    changed = apply_rename_element(f, _rn_spec(), dry_run=True)
    assert changed is True
    assert f.read_text() == original


def test_rename_element_rejects_malformed(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<Activity xmlns:ui="x"><ui:HashText/></Activity>')
    bad = _rn_spec(prefix="ui;rm -rf /")
    assert apply_rename_element(f, bad, dry_run=False) is False


def test_rename_element_registered():
    assert "rename_element" in REGISTRY


# ---- UI-7: force_attribute_in_activity_with_guard ----

from uip_engine.fixers import apply_force_attribute_in_activity_with_guard


def _ui7_spec(prefix="uix", local="NTypeInto", guard_attr="InteractionMode",
              guard_value="Simulate", attr="DelayBefore", target="0"):
    return {
        "type": "force_attribute_in_activity_with_guard",
        "prefix": prefix,
        "activity_local": local,
        "guard_attr": guard_attr,
        "guard_value": guard_value,
        "attr_name": attr,
        "target_value": target,
        "tag_line": 1,
    }


def test_ui7_forces_attr_when_guard_matches(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:uix="x">\n'
        '  <uix:NTypeInto InteractionMode="Simulate" DelayBefore="500" />\n'
        '</Activity>'
    )
    changed = apply_force_attribute_in_activity_with_guard(f, _ui7_spec(), dry_run=False)
    assert changed is True
    assert 'DelayBefore="0"' in f.read_text()
    assert 'DelayBefore="500"' not in f.read_text()


def test_ui7_skips_when_guard_mismatch(tmp_path):
    """Guard InteractionMode=Simulate; activity tem HardwareEvents → NÃO tocar."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:uix="x">\n'
        '  <uix:NTypeInto InteractionMode="HardwareEvents" DelayBefore="500" />\n'
        '</Activity>'
    )
    changed = apply_force_attribute_in_activity_with_guard(f, _ui7_spec(), dry_run=False)
    assert changed is False
    assert 'DelayBefore="500"' in f.read_text()


def test_ui7_idempotent_when_already_target(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:uix="x"><uix:NTypeInto InteractionMode="Simulate" DelayBefore="0" /></Activity>'
    )
    changed = apply_force_attribute_in_activity_with_guard(f, _ui7_spec(), dry_run=False)
    assert changed is False


def test_ui7_mixed_scope_only_simulate_touched(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:uix="x">\n'
        '  <uix:NTypeInto InteractionMode="Simulate" DelayBefore="500" />\n'
        '  <uix:NTypeInto InteractionMode="HardwareEvents" DelayBefore="200" />\n'
        '</Activity>'
    )
    changed = apply_force_attribute_in_activity_with_guard(f, _ui7_spec(), dry_run=False)
    assert changed is True
    content = f.read_text()
    # Simulate one zeroed
    assert 'InteractionMode="Simulate" DelayBefore="0"' in content
    # HardwareEvents preserved
    assert 'InteractionMode="HardwareEvents" DelayBefore="200"' in content


def test_ui7_dry_run(tmp_path):
    f = tmp_path / "x.xaml"
    original = '<Activity xmlns:uix="x"><uix:NTypeInto InteractionMode="Simulate" DelayBefore="500" /></Activity>'
    f.write_text(original)
    changed = apply_force_attribute_in_activity_with_guard(f, _ui7_spec(), dry_run=True)
    assert changed is True
    assert f.read_text() == original


def test_ui7_rejects_malformed_prefix(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<Activity xmlns:uix="x"><uix:NTypeInto InteractionMode="Simulate" DelayBefore="500"/></Activity>')
    bad = _ui7_spec(prefix="uix;rm -rf /")
    assert apply_force_attribute_in_activity_with_guard(f, bad, dry_run=False) is False


def test_ui7_fixer_registered():
    assert "force_attribute_in_activity_with_guard" in REGISTRY


# ---- M-6: xmlns_declare ----

from uip_engine.fixers import apply_xmlns_declare

_M6_URI = "http://schemas.uipath.com/workflow/activities"


def _m6_spec(prefix="ui", uri=_M6_URI):
    return {"type": "xmlns_declare", "prefix": prefix, "xmlns_uri": uri}


def test_m6_declares_xmlns_in_root(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns="x" xmlns:x="y">\n  <ui:LogMessage />\n</Activity>'
    )
    changed = apply_xmlns_declare(f, _m6_spec(), dry_run=False)
    assert changed is True
    content = f.read_text()
    assert 'xmlns:ui="http://schemas.uipath.com/workflow/activities"' in content


def test_m6_idempotent_when_already_declared(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        f'<Activity xmlns="x" xmlns:ui="{_M6_URI}">\n  <ui:LogMessage />\n</Activity>'
    )
    changed = apply_xmlns_declare(f, _m6_spec(), dry_run=False)
    assert changed is False


def test_m6_preserves_existing_attrs(tmp_path):
    f = tmp_path / "x.xaml"
    original_attrs = ['xmlns="x"', 'xmlns:x="y"']
    f.write_text(
        f'<Activity {" ".join(original_attrs)}>\n  <ui:LogMessage />\n</Activity>'
    )
    apply_xmlns_declare(f, _m6_spec(), dry_run=False)
    content = f.read_text()
    for attr in original_attrs:
        assert attr in content


def test_m6_dry_run(tmp_path):
    f = tmp_path / "x.xaml"
    original = '<Activity xmlns="x"><ui:LogMessage /></Activity>'
    f.write_text(original)
    changed = apply_xmlns_declare(f, _m6_spec(), dry_run=True)
    assert changed is True
    assert f.read_text() == original


def test_m6_rejects_uri_with_quotes(tmp_path):
    """URI com aspas duplas tentaria injection no XML — reject."""
    f = tmp_path / "x.xaml"
    f.write_text('<Activity xmlns="x"><ui:LogMessage /></Activity>')
    bad = _m6_spec(uri='http://evil" injected="')
    assert apply_xmlns_declare(f, bad, dry_run=False) is False


def test_m6_rejects_malformed_prefix(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<Activity xmlns="x"><ui:LogMessage /></Activity>')
    assert apply_xmlns_declare(f, _m6_spec(prefix="ui:x"), dry_run=False) is False


def test_m6_fixer_registered():
    assert "xmlns_declare" in REGISTRY


# ---- M-7: strip_redundant_default ----

from uip_engine.fixers import apply_strip_redundant_default


def _m7_spec(prefix="ui", local="WriteRange", attr="StartingCell",
             expected="A1", tag_line=5):
    return {
        "type": "strip_redundant_default",
        "prefix": prefix,
        "activity_local": local,
        "attr_name": attr,
        "expected_value": expected,
        "tag_line": tag_line,
    }


def test_m7_strips_redundant_default(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x">\n'
        '  <ui:WriteRange SheetName="Plan1" StartingCell="A1" />\n'
        '</Activity>'
    )
    changed = apply_strip_redundant_default(f, _m7_spec(), dry_run=False)
    assert changed is True
    content = f.read_text()
    assert "StartingCell" not in content
    assert 'SheetName="Plan1"' in content


def test_m7_skip_when_value_differs(tmp_path):
    """expected_value='A1' mas atual é 'B2' — não strip."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x"><ui:WriteRange StartingCell="B2" /></Activity>'
    )
    changed = apply_strip_redundant_default(f, _m7_spec(expected="A1"), dry_run=False)
    assert changed is False
    assert 'StartingCell="B2"' in f.read_text()


def test_m7_only_targets_specified_activity(tmp_path):
    """WriteRange spec não toca ReadRange."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x">\n'
        '  <ui:WriteRange StartingCell="A1" />\n'
        '  <ui:ReadRange StartingCell="A1" />\n'
        '</Activity>'
    )
    changed = apply_strip_redundant_default(f, _m7_spec(local="WriteRange"), dry_run=False)
    assert changed is True
    content = f.read_text()
    assert 'StartingCell' not in content.split('<ui:ReadRange')[0]
    assert '<ui:ReadRange StartingCell="A1"' in content


def test_m7_idempotent_when_attr_absent(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<Activity xmlns:ui="x"><ui:WriteRange SheetName="X" /></Activity>')
    changed = apply_strip_redundant_default(f, _m7_spec(), dry_run=False)
    assert changed is False


def test_m7_dry_run(tmp_path):
    f = tmp_path / "x.xaml"
    original = '<Activity xmlns:ui="x"><ui:WriteRange StartingCell="A1" /></Activity>'
    f.write_text(original)
    changed = apply_strip_redundant_default(f, _m7_spec(), dry_run=True)
    assert changed is True
    assert f.read_text() == original


def test_m7_value_with_regex_metachars(tmp_path):
    """expected_value contains chars that are regex metacharacters (e.g. '.')."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x"><ui:WriteRange Path="C:\\temp\\file.xlsx" /></Activity>'
    )
    changed = apply_strip_redundant_default(
        f, _m7_spec(attr="Path", expected="C:\\temp\\file.xlsx"), dry_run=False
    )
    assert changed is True
    assert "Path" not in f.read_text()


def test_m7_fixer_registered():
    assert "strip_redundant_default" in REGISTRY


# ---- M-8: replace_nothing_value_type ----

from uip_engine.fixers import apply_replace_nothing_value_type


def _m8_spec(prefix="ui", local="WriteRange", attr="AddHeaders",
             tag_line=5, default_expr="[False]"):
    return {
        "type": "replace_nothing_value_type",
        "prefix": prefix,
        "activity_local": local,
        "attr_name": attr,
        "tag_line": tag_line,
        "default_expr": default_expr,
    }


def test_m8_replaces_nothing_with_default(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x">\n'
        '  <ui:WriteRange WorkbookPath="C:\\f.xlsx" AddHeaders="[Nothing]" />\n'
        '</Activity>'
    )
    changed = apply_replace_nothing_value_type(f, _m8_spec(), dry_run=False)
    assert changed is True
    assert 'AddHeaders="[False]"' in f.read_text()
    assert "[Nothing]" not in f.read_text()


def test_m8_idempotent_when_not_nothing(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x">\n'
        '  <ui:WriteRange AddHeaders="[True]" />\n'
        '</Activity>'
    )
    changed = apply_replace_nothing_value_type(f, _m8_spec(), dry_run=False)
    assert changed is False


def test_m8_only_targets_specified_activity(tmp_path):
    """Spec aponta WriteRange; ReadRange com [Nothing] no mesmo arquivo
    NÃO deve ser tocado."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x">\n'
        '  <ui:WriteRange AddHeaders="[Nothing]" />\n'
        '  <ui:ReadRange AddHeaders="[Nothing]" />\n'
        '</Activity>'
    )
    changed = apply_replace_nothing_value_type(f, _m8_spec(local="WriteRange"), dry_run=False)
    assert changed is True
    content = f.read_text()
    assert '<ui:WriteRange AddHeaders="[False]"' in content
    assert '<ui:ReadRange AddHeaders="[Nothing]"' in content


def test_m8_only_targets_specified_attr(tmp_path):
    """Spec aponta AddHeaders; outro attr [Nothing] na mesma tag NÃO tocar."""
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x">\n'
        '  <ui:WriteRange OtherFlag="[Nothing]" AddHeaders="[Nothing]" />\n'
        '</Activity>'
    )
    changed = apply_replace_nothing_value_type(f, _m8_spec(attr="AddHeaders"), dry_run=False)
    assert changed is True
    content = f.read_text()
    assert 'AddHeaders="[False]"' in content
    assert 'OtherFlag="[Nothing]"' in content


def test_m8_handles_self_close_tag(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x"><ui:WriteRange AddHeaders="[Nothing]"/></Activity>'
    )
    changed = apply_replace_nothing_value_type(f, _m8_spec(), dry_run=False)
    assert changed is True
    assert 'AddHeaders="[False]"/>' in f.read_text()


def test_m8_case_insensitive_nothing(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text(
        '<Activity xmlns:ui="x"><ui:WriteRange AddHeaders="[ NOTHING ]" /></Activity>'
    )
    changed = apply_replace_nothing_value_type(f, _m8_spec(), dry_run=False)
    assert changed is True
    assert 'AddHeaders="[False]"' in f.read_text()


def test_m8_dry_run(tmp_path):
    f = tmp_path / "x.xaml"
    original = '<Activity xmlns:ui="x"><ui:WriteRange AddHeaders="[Nothing]" /></Activity>'
    f.write_text(original)
    changed = apply_replace_nothing_value_type(f, _m8_spec(), dry_run=True)
    assert changed is True
    assert f.read_text() == original


def test_m8_rejects_malformed_spec(tmp_path):
    f = tmp_path / "x.xaml"
    f.write_text('<Activity xmlns:ui="x"><ui:WriteRange AddHeaders="[Nothing]"/></Activity>')
    # injection attempt via regex metachars
    bad = _m8_spec(prefix="ui;rm -rf /")
    assert apply_replace_nothing_value_type(f, bad, dry_run=False) is False


# ---- registry wiring ----

def test_w1_v2_fixers_registered():
    assert "expand_self_closed_inarg" in REGISTRY
    assert "strip_string_quotes_numeric_default" in REGISTRY


def test_m8_fixer_registered():
    assert "replace_nothing_value_type" in REGISTRY
