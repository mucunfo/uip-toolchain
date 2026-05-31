"""Regression tests for AUDIT_2026-05-28 fixers-lane findings.

Owned lane: src/uip_engine/fixers.py. Each test calls the fixer directly via
the REGISTRY with crafted XAML/JSON and asserts the corrected behavior.

Findings covered:
  CCS-1       rename_attribute_name_in_tag (new fixer)
  J-12        retarget_project_argument_types (generic types not truncated)
  D-PINALERT  strip_xml_attribute (element-scoped strip)
  M-2         _format_property_element_value (direction wrappers, escape)
  A-19b       cascade_caller_in_args (direction + inner_type, fallback)
  W-30        replace_hostile_unicode_chars (Annotation/DisplayName untouched)
  X-2         strip_property_element_with_attribute (preserve x:/xml: directives)
  ENV-3       insert_namespace_import (loosened scg:List requirement)
  ENV-4       normalize_visualbasic_settings (optional leading newline+indent)
  N-17        rename_poor_log_displayname (element-form Message)
  S-5         strip_annotation_text (property-element form)

NOTE: several fixers (W-30, X-2) run an ET.fromstring well-formedness gate, so
the fixtures here are well-formed XML with declared namespaces.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from uip_engine.fixers import REGISTRY, _format_property_element_value


# Common namespace blob so ET.fromstring gates in W-30 / X-2 pass.
NS = (
    'xmlns="clr" xmlns:x="http://x" xmlns:ui="http://ui" '
    'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib" '
    'xmlns:sap2010="http://sap2010" xmlns:c="http://c" '
    'xmlns:uma="http://uma" xmlns:mva="http://mva"'
)


def _mk(content: str, suffix: str = ".xaml") -> Path:
    fd, p = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    path = Path(p)
    path.write_text(content, encoding="utf-8")
    return path


def _run(name, path, spec):
    return REGISTRY[name](path, spec, dry_run=False)


# --------------------------------------------------------------------------- #
# CCS-1
# --------------------------------------------------------------------------- #
def test_ccs1_renames_attribute_name_scoped_to_element():
    xaml = '<Activity><c:Login out_UiESipagDirect="[v]" Folder="keep" /></Activity>'
    f = _mk(xaml)
    try:
        ok = _run("rename_attribute_name_in_tag", f,
                  {"from": "out_UiESipagDirect", "to": "out_UIESipagDirect",
                   "element": "c:Login"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert 'out_UIESipagDirect="[v]"' in out
        assert "out_UiESipagDirect=" not in out
        # Unrelated attribute on same tag untouched.
        assert 'Folder="keep"' in out
    finally:
        os.unlink(f)


def test_ccs1_does_not_touch_other_elements():
    # Same attribute name on a DIFFERENT element must not be renamed.
    xaml = '<Activity><c:Other out_UiESipagDirect="[v]" /></Activity>'
    f = _mk(xaml)
    try:
        ok = _run("rename_attribute_name_in_tag", f,
                  {"from": "out_UiESipagDirect", "to": "out_UIESipagDirect",
                   "element": "c:Login"})
        out = f.read_text(encoding="utf-8")
        assert ok is False
        assert "out_UiESipagDirect=" in out
    finally:
        os.unlink(f)


def test_ccs1_requires_element_key():
    xaml = '<Activity><c:Login out_x="[v]" /></Activity>'
    f = _mk(xaml)
    try:
        ok = _run("rename_attribute_name_in_tag", f,
                  {"from": "out_x", "to": "out_X"})  # no element
        assert ok is False
    finally:
        os.unlink(f)


def test_ccs1_does_not_touch_attribute_value_substring():
    # `Folder="out_UiESipagDirect"` value must not be renamed — only the attr NAME.
    xaml = '<Activity><c:Login Folder="out_UiESipagDirect" out_UiESipagDirect="[v]" /></Activity>'
    f = _mk(xaml)
    try:
        _run("rename_attribute_name_in_tag", f,
             {"from": "out_UiESipagDirect", "to": "out_UIESipagDirect",
              "element": "c:Login"})
        out = f.read_text(encoding="utf-8")
        # value stays original-cased
        assert 'Folder="out_UiESipagDirect"' in out
        # attribute name corrected
        assert 'out_UIESipagDirect="[v]"' in out
    finally:
        os.unlink(f)


# --------------------------------------------------------------------------- #
# J-12
# --------------------------------------------------------------------------- #
_LEGACY_CLAUSE = "mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089"
_DICT_TYPE = (
    "System.Collections.Generic.Dictionary`2[["
    "System.String, " + _LEGACY_CLAUSE + "],"
    "[System.Int32, " + _LEGACY_CLAUSE + "]], "
    + _LEGACY_CLAUSE
)


def test_j12_simple_type_short_form():
    proj = json.dumps({"arguments": {"input": [
        {"name": "a", "type": "System.String, " + _LEGACY_CLAUSE},
    ]}}, indent=2)
    d = Path(tempfile.mkdtemp())
    pj = d / "project.json"
    pj.write_text(proj, encoding="utf-8")
    try:
        ok = _run("retarget_project_argument_types", pj, {})
        data = json.loads(pj.read_text(encoding="utf-8"))
        assert ok is True
        assert data["arguments"]["input"][0]["type"] == "System.String"
    finally:
        pj.unlink()
        d.rmdir()


def test_j12_generic_dictionary_not_truncated():
    proj = json.dumps({"arguments": {"input": [
        {"name": "d", "type": _DICT_TYPE},
    ]}}, indent=2)
    d = Path(tempfile.mkdtemp())
    pj = d / "project.json"
    pj.write_text(proj, encoding="utf-8")
    try:
        ok = _run("retarget_project_argument_types", pj, {})
        data = json.loads(pj.read_text(encoding="utf-8"))
        gen = data["arguments"]["input"][0]["type"]
        assert ok is True
        # Brackets balanced (not truncated to `...Dictionary`2[[System.String`)
        assert gen.count("[") == gen.count("]")
        assert gen.startswith("System.Collections.Generic.Dictionary`2[[")
        assert gen.endswith("]]")
        # The outermost trailing legacy clause is gone.
        assert not gen.endswith(_LEGACY_CLAUSE)
    finally:
        pj.unlink()
        d.rmdir()


def test_j12_idempotent_on_short_form():
    proj = json.dumps({"arguments": {"input": [
        {"name": "a", "type": "System.String"},
    ]}}, indent=2)
    d = Path(tempfile.mkdtemp())
    pj = d / "project.json"
    pj.write_text(proj, encoding="utf-8")
    try:
        ok = _run("retarget_project_argument_types", pj, {})
        assert ok is False
    finally:
        pj.unlink()
        d.rmdir()


# --------------------------------------------------------------------------- #
# D-PINALERT
# --------------------------------------------------------------------------- #
def test_dpinalert_strip_scoped_to_element():
    xaml = (
        f'<Activity {NS}>'
        '<uma:Office365ApplicationScope Folder="{x:Null}">x</uma:Office365ApplicationScope>'
        '<ui:CreateDirectory DisplayName="mk" Folder="C:/out" />'
        '</Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_xml_attribute", f,
                  {"attribute": "Folder", "element": "uma:Office365ApplicationScope"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        # O365 Folder removed
        assert 'Folder="{x:Null}"' not in out
        # Unrelated CreateDirectory Folder kept (no silent data loss)
        assert 'Folder="C:/out"' in out
    finally:
        os.unlink(f)


def test_dpinalert_filewide_fallback_when_no_element():
    xaml = (
        f'<Activity {NS}>'
        '<uma:Office365ApplicationScope Folder="{x:Null}">x</uma:Office365ApplicationScope>'
        '<ui:CreateDirectory DisplayName="mk" Folder="C:/out" />'
        '</Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_xml_attribute", f, {"attribute": "Folder"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "Folder=" not in out
    finally:
        os.unlink(f)


def test_dpinalert_nwindow_strip_preserves_property_elements():
    xaml = (
        f'<Activity {NS}>'
        '<uix:NApplicationCard sap2010:WorkflowViewState.IdRef="Card_1">'
        '<uix:NWindowOperation.Target>'
        '<uix:TargetAnchorable />'
        '</uix:NWindowOperation.Target>'
        '<uix:NWindowOperation DisplayName="Fechar" />'
        '</uix:NApplicationCard>'
        '</Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_nwindow_operation", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert '<uix:NWindowOperation.Target>' in out
        assert '</uix:NWindowOperation.Target>' in out
        assert '<uix:NWindowOperation DisplayName=' not in out
        assert 'CloseMode="Always"' in out
    finally:
        os.unlink(f)


def test_dpinalert_nwindow_self_closed_does_not_consume_next_pair():
    xaml = (
        f'<Activity {NS}>'
        '<uix:NApplicationCard sap2010:WorkflowViewState.IdRef="Card_1">'
        '<uix:NWindowOperation DisplayName="Activate" />'
        '<Sequence DisplayName="KeepMe" />'
        '<uix:NWindowOperation DisplayName="Close">'
        '<ui:LogMessage DisplayName="Inner" />'
        '</uix:NWindowOperation>'
        '</uix:NApplicationCard>'
        '</Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_nwindow_operation", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert 'DisplayName="KeepMe"' in out
        assert '<uix:NWindowOperation' not in out
        assert 'CloseMode="Always"' in out
    finally:
        os.unlink(f)


# --------------------------------------------------------------------------- #
# M-2
# --------------------------------------------------------------------------- #
def test_m2_in_direction_default_behavior():
    assert _format_property_element_value("System.String", None) == \
        '<InArgument x:TypeArguments="x:String" />'
    assert _format_property_element_value("System.String", "foo", "In") == \
        '<InArgument x:TypeArguments="x:String">foo</InArgument>'


def test_m2_out_direction_no_default_literal():
    out = _format_property_element_value("System.Data.DataTable", "[x]", "Out")
    assert out.startswith("<OutArgument")
    assert out.endswith("/>")
    assert "[x]" not in out  # Out emits no default literal


def test_m2_inout_direction_self_closed():
    out = _format_property_element_value("System.Data.DataTable", None, "InOut")
    assert out.startswith("<InOutArgument")
    assert out.endswith("/>")


def test_m2_generic_type_is_xml_escaped():
    out = _format_property_element_value("Collections.Generic.IList<T>", None, "In")
    # Isolate the x:TypeArguments value and assert no raw angle brackets leaked
    # (a raw '<' inside the attribute would make the XAML malformed).
    inner = out.split('x:TypeArguments="')[1].split('"')[0]
    assert "<" not in inner and ">" not in inner
    assert "&lt;T&gt;" in inner


# --------------------------------------------------------------------------- #
# A-19b
# --------------------------------------------------------------------------- #
_CALLER = (
    '<Activity><ui:InvokeWorkflowFile WorkflowFileName="Sub.xaml">'
    '<ui:InvokeWorkflowFile.Arguments></ui:InvokeWorkflowFile.Arguments>'
    '</ui:InvokeWorkflowFile></Activity>'
)


def test_a19b_inout_emits_inoutargument_correct_type():
    f = _mk(_CALLER)
    try:
        ok = _run("cascade_caller_in_args", f,
                  {"callee_path": "Sub.xaml", "arg_name": "io_TransactionItem",
                   "direction": "InOut", "inner_type": "ui:QueueItem"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert '<InOutArgument x:TypeArguments="ui:QueueItem"' in out
        assert "x:String" not in out  # wrong type/direction NOT emitted
    finally:
        os.unlink(f)


def test_a19b_int_in_emits_correct_type():
    f = _mk(_CALLER)
    try:
        ok = _run("cascade_caller_in_args", f,
                  {"callee_path": "Sub.xaml", "arg_name": "in_Count",
                   "direction": "In", "inner_type": "x:Int32"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert '<InArgument x:TypeArguments="x:Int32"' in out
    finally:
        os.unlink(f)


def test_a19b_fallback_keeps_legacy_xstring_when_no_direction():
    f = _mk(_CALLER)
    try:
        ok = _run("cascade_caller_in_args", f,
                  {"callee_path": "Sub.xaml", "arg_name": "in_Foo"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert 'InArgument x:TypeArguments="x:String"' in out
        assert ">[&quot;&quot;]</InArgument>" in out
        assert ">\"\"</InArgument>" not in out
    finally:
        os.unlink(f)


def test_a19b_missing_string_arg_uses_vb_empty_string_literal():
    f = _mk(_CALLER)
    try:
        ok = _run("cascade_caller_in_args", f,
                  {"callee_path": "Sub.xaml", "arg_name": "in_StName",
                   "direction": "In", "inner_type": "x:String"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert 'InArgument x:TypeArguments="x:String"' in out
        assert ">[&quot;&quot;]</InArgument>" in out
        assert ">\"\"</InArgument>" not in out
    finally:
        os.unlink(f)


def test_a19b_missing_datatable_arg_uses_nothing_and_declares_sd():
    f = _mk(_CALLER)
    try:
        ok = _run("cascade_caller_in_args", f,
                  {"callee_path": "Sub.xaml", "arg_name": "in_DTabRows",
                   "direction": "In", "inner_type": "sd:DataTable"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert 'xmlns:sd="clr-namespace:System.Data;assembly=System.Data.Common"' in out
        assert '<InArgument x:TypeArguments="sd:DataTable"' in out
        assert ">[Nothing]</InArgument>" in out
        assert ">[&quot;&quot;]</InArgument>" not in out
    finally:
        os.unlink(f)


def test_a19b_skips_when_args_block_already_has_duplicate_key():
    caller = (
        '<Activity><ui:InvokeWorkflowFile WorkflowFileName="Sub.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '<InArgument x:TypeArguments="x:String" x:Key="in_Duplicate">[a]</InArgument>'
        '<InArgument x:TypeArguments="x:String" x:Key="in_Duplicate">[b]</InArgument>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>'
    )
    f = _mk(caller)
    try:
        ok = _run("cascade_caller_in_args", f,
                  {"callee_path": "Sub.xaml", "arg_name": "in_StName",
                   "direction": "In", "inner_type": "x:String"})
        assert ok is False
        assert f.read_text(encoding="utf-8") == caller
    finally:
        os.unlink(f)


# --------------------------------------------------------------------------- #
# W-30
# --------------------------------------------------------------------------- #
def test_w30_preserves_annotation_and_displayname_smart_quotes():
    xaml = (
        f'<Activity {NS}>'
        '<Sequence sap2010:Annotation.AnnotationText="campo “Status”">'
        '<ui:Assign DisplayName="rotulo “X”">'
        '<ui:Assign.To>[a “b” c]</ui:Assign.To>'
        '</ui:Assign></Sequence></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("replace_hostile_unicode_chars", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        # User-facing text untouched
        assert "“Status”" in out
        assert 'DisplayName="rotulo “X”"' in out
        # VB expression context normalized
        assert "[a &quot;b&quot; c]" in out
    finally:
        os.unlink(f)


def test_w30_noop_when_only_protected_text():
    xaml = (
        f'<Activity {NS}>'
        '<Sequence sap2010:Annotation.AnnotationText="só “aqui”" />'
        '</Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("replace_hostile_unicode_chars", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is False  # nothing outside protected spans → no change
        assert "“aqui”" in out
    finally:
        os.unlink(f)


# --------------------------------------------------------------------------- #
# X-2
# --------------------------------------------------------------------------- #
def test_x2_preserves_xtypearguments_directive_in_case_b():
    xaml = (
        f'<Activity {NS}>'
        '<scg:List.Items x:TypeArguments="x:String">'
        '<x:String>a</x:String></scg:List.Items></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_property_element_with_attribute", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        # x:TypeArguments must survive (load-bearing on generic property element)
        assert 'x:TypeArguments="x:String"' in out
        # inner content preserved
        assert "<x:String>a</x:String>" in out
    finally:
        os.unlink(f)


def test_x2_case_a_still_strips_redundant_block():
    # parent has inline Level + property-element duplicates it -> remove block
    xaml = (
        f'<Activity {NS}>'
        '<ui:LogMessage Level="Trace">'
        '<ui:LogMessage.Level Level="Trace"><x:String>z</x:String></ui:LogMessage.Level>'
        '</ui:LogMessage></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_property_element_with_attribute", f,
                  {"elem": "ui:LogMessage.Level"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "<ui:LogMessage.Level" not in out
    finally:
        os.unlink(f)


# --------------------------------------------------------------------------- #
# ENV-3
# --------------------------------------------------------------------------- #
def test_env3_strict_scg_list_shape_inserts():
    xaml = (
        '<Activity><TextExpression.NamespacesForImplementation>'
        '<scg:List x:TypeArguments="x:String" Capacity="1">\n'
        '    <x:String>System.Linq</x:String>\n'
        '  </scg:List></TextExpression.NamespacesForImplementation></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("insert_namespace_import", f, {"name": "System.Net"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "<x:String>System.Net</x:String>" in out
    finally:
        os.unlink(f)


def test_env3_fallback_when_wrapper_varies():
    # Collection wrapper is NOT the canonical scg:List shape — fixer must still
    # insert (fail-safe) using the NamespacesForImplementation surface.
    xaml = (
        '<Activity><TextExpression.NamespacesForImplementation>'
        '<col:Set x:TypeArguments="x:String"><x:String>System.Linq</x:String></col:Set>'
        '</TextExpression.NamespacesForImplementation></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("insert_namespace_import", f, {"name": "System.Net"})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "<x:String>System.Net</x:String>" in out
    finally:
        os.unlink(f)


def test_env3_idempotent_when_namespace_present():
    xaml = (
        '<Activity><TextExpression.NamespacesForImplementation>'
        '<scg:List x:TypeArguments="x:String">\n'
        '    <x:String>System.Net</x:String>\n'
        '  </scg:List></TextExpression.NamespacesForImplementation></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("insert_namespace_import", f, {"name": "System.Net"})
        assert ok is False
    finally:
        os.unlink(f)


# --------------------------------------------------------------------------- #
# ENV-4
# --------------------------------------------------------------------------- #
def test_env4_inline_settings_normalizes():
    xaml = "<x><mva:VisualBasic.Settings>foo</mva:VisualBasic.Settings></x>"
    f = _mk(xaml)
    try:
        ok = _run("normalize_visualbasic_settings", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "<VisualBasic.Settings><x:Null /></VisualBasic.Settings>" in out
    finally:
        os.unlink(f)


def test_env4_line_start_settings_normalizes():
    xaml = "<x>\n    <mva:VisualBasic.Settings>foo</mva:VisualBasic.Settings>\n</x>"
    f = _mk(xaml)
    try:
        ok = _run("normalize_visualbasic_settings", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "<x:Null />" in out
        assert "<VisualBasic.Settings>" in out
    finally:
        os.unlink(f)


def test_env4_self_closing_inline_normalizes():
    xaml = "<x><mva:VisualBasic.Settings /></x>"
    f = _mk(xaml)
    try:
        ok = _run("normalize_visualbasic_settings", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "<x:Null />" in out
    finally:
        os.unlink(f)


# --------------------------------------------------------------------------- #
# N-17
# --------------------------------------------------------------------------- #
def test_n17_rewrites_displayname_with_element_form_message():
    xaml = (
        '<Activity><ui:LogMessage DisplayName="Log Message">'
        '<ui:LogMessage.Message>'
        '<InArgument x:TypeArguments="x:String">[&quot;Conta criada&quot;]</InArgument>'
        '</ui:LogMessage.Message></ui:LogMessage></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("rename_poor_log_displayname", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert 'DisplayName="Log Message"' not in out
        # pulled context from element-form Message
        assert "Conta criada" in out
    finally:
        os.unlink(f)


def test_n17_element_form_idempotent():
    xaml = (
        '<Activity><ui:LogMessage DisplayName="Log Message">'
        '<ui:LogMessage.Message>'
        '<InArgument x:TypeArguments="x:String">[&quot;Saldo&quot;]</InArgument>'
        '</ui:LogMessage.Message></ui:LogMessage></Activity>'
    )
    f = _mk(xaml)
    try:
        _run("rename_poor_log_displayname", f, {})
        once = f.read_text(encoding="utf-8")
        ok2 = _run("rename_poor_log_displayname", f, {})
        twice = f.read_text(encoding="utf-8")
        assert ok2 is False
        assert once == twice
    finally:
        os.unlink(f)


def test_n17_attribute_form_still_works():
    xaml = '<Activity><ui:LogMessage DisplayName="Log Message" Message="[&quot;Saldo&quot;]" /></Activity>'
    f = _mk(xaml)
    try:
        ok = _run("rename_poor_log_displayname", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert 'DisplayName="Log Message"' not in out
    finally:
        os.unlink(f)


# --------------------------------------------------------------------------- #
# S-5
# --------------------------------------------------------------------------- #
def test_s5_strips_attribute_form_all():
    xaml = '<Activity><Sequence sap2010:Annotation.AnnotationText="some note" /></Activity>'
    f = _mk(xaml)
    try:
        ok = _run("strip_annotation_text", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "AnnotationText" not in out
    finally:
        os.unlink(f)


def test_s5_strips_element_form():
    xaml = (
        '<Activity><Sequence>'
        '<sap2010:Annotation.AnnotationText>nota qualquer</sap2010:Annotation.AnnotationText>'
        '</Sequence></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_annotation_text", f, {})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "AnnotationText" not in out
    finally:
        os.unlink(f)


def test_s5b_element_form_prefix_gated():
    xaml = (
        '<Activity><Sequence>'
        '<sap2010:Annotation.AnnotationText>[PostMigration Action Required] todo</sap2010:Annotation.AnnotationText>'
        '</Sequence></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_annotation_text", f,
                  {"params": {"text_prefix": "[PostMigration Action Required]"}})
        out = f.read_text(encoding="utf-8")
        assert ok is True
        assert "AnnotationText" not in out
    finally:
        os.unlink(f)


def test_s5b_element_form_non_prefix_preserved():
    xaml = (
        '<Activity><Sequence>'
        '<sap2010:Annotation.AnnotationText>keep me</sap2010:Annotation.AnnotationText>'
        '</Sequence></Activity>'
    )
    f = _mk(xaml)
    try:
        ok = _run("strip_annotation_text", f,
                  {"params": {"text_prefix": "[PostMigration Action Required]"}})
        out = f.read_text(encoding="utf-8")
        assert ok is False
        assert "keep me" in out
    finally:
        os.unlink(f)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
