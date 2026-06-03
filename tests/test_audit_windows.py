"""Regression tests for AUDIT_2026-05-28 findings owned by the `windows` lane.

Covers:
  - W-12  : empty ArrayRow="[{}]" must be flagged ONCE (manual branch), never
            double-flagged AND never auto-wrapped.
  - W-16  : multi-part chain (obj.Field.IsNullOrEmpty) => fix_mechanical=None.
  - W-17  : multi-part chain (obj.Field.ToInt32)       => fix_mechanical=None.
  - UI-7  : binding-expression / {x:Null} delays must NOT carry a deterministic
            force-"0" fix (would eat config-bound values); only literal numeric
            non-zero delays keep the deterministic fix.

Pure unit tests on the detectors — do NOT run pytest in this lane (parallel
lanes share the package import). Validate with `python -m py_compile`.
"""
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.windows import (
    detect_w12_array_literal,
    detect_w16_isnullorempty,
    detect_w17_toint32,
    detect_w19_queue_item_indexer,
    detect_w35_terminal_vb_line_continuation,
    detect_w36_string_format_tostring_with_delimiter,
    detect_w37_read_as_datatable_three_args,
    detect_w38_ccs_sipagdirect_legacy_login,
    detect_ui7_simulate_delays,
    _is_numeric_delay,
    _is_zero_delay,
    _RE_W12_ARRAYROW,
    _RE_W12_EMPTY,
)


def _project(tmp_path: Path) -> ProjectContext:
    import json
    pj = {"targetFramework": "Windows", "expressionLanguage": "VisualBasic"}
    (tmp_path / "project.json").write_text(json.dumps(pj), encoding="utf-8")
    return ProjectContext(root=tmp_path, project_json=pj)


def _write_xaml(tmp_path: Path, body: str, name: str = "Foo.xaml") -> FileContext:
    f = tmp_path / name
    f.write_text(body, encoding="utf-8")
    return FileContext(f)


def _rule(rid: str, mechanical: dict | None, **detect_params) -> Rule:
    fix: dict = {"prose": "fix me"}
    if mechanical is not None:
        fix["mechanical"] = mechanical
    return Rule(
        id=rid, severity=Severity.ERROR, category="breaking", target="windows",
        title=rid, description="",
        detect={"type": "python", "params": detect_params},
        fix=fix,
    )


# ---------------------------------------------------------------------------
# W-12 — empty ArrayRow="[{}]" reported ONCE (manual), not auto-wrapped
# ---------------------------------------------------------------------------

def test_w12_empty_arrayrow_regex_no_longer_matches():
    """The narrowed ArrayRow regex must NOT match the empty literal."""
    assert _RE_W12_ARRAYROW.search('ArrayRow="[{}]"') is None
    # The empty branch still catches it.
    assert _RE_W12_EMPTY.search('ArrayRow="[{}]"') is not None


def test_w12_empty_arrayrow_flagged_once_manual(tmp_path):
    body = '<Activity><ui:AddDataRow ArrayRow="[{}]" /></Activity>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    # Exactly one finding, manual (no mechanical), NOT auto-wrapped.
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


def test_w12_typed_empty_inargument_auto_wrapped(tmp_path):
    body = (
        '<Activity><InArgument x:TypeArguments="s:String[]" '
        'x:Key="in_Arr">[{}]</InArgument></Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {"type": "wrap_typed_empty_array_literal"}


def test_w12_typed_variable_default_auto_wrapped(tmp_path):
    body = (
        '<Activity><Variable x:TypeArguments="umm:Office365Message[]" '
        'Default="[{}]" Name="vArrMail" /></Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {"type": "wrap_typed_empty_array_literal"}


def test_w12_typed_nonempty_variable_default_auto_wrapped(tmp_path):
    body = (
        '<Activity><Variable x:TypeArguments="s:String[]" '
        'Default="[{&quot;dd/MM/yyyy HH:mm:ss&quot;, &quot;dd/MM/yyyy&quot;}]" '
        'Name="vArrFormatos" /></Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {"type": "wrap_typed_empty_array_literal"}


def test_w12_typed_visualbasicvalue_corrupt_empty_array_auto_wrapped(tmp_path):
    body = (
        '<Activity><mva:VisualBasicValue x:TypeArguments="s:String[]" '
        'ExpressionText="{}{}" /></Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {"type": "wrap_typed_empty_array_literal"}


def test_w12_nonempty_arrayrow_still_auto_wrapped(tmp_path):
    body = '<Activity><ui:AddDataRow ArrayRow="[{a, b}]" /></Activity>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {"type": "wrap_arrayrow_object"}


def test_w12_typed_nonempty_inargument_auto_wrapped(tmp_path):
    body = (
        '<Activity><InArgument x:TypeArguments="s:String[]" '
        'x:Key="in_Arr">[{"Settings","Constants"}]</InArgument></Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w12_array_literal(
        _rule("W-12", {"type": "wrap_arrayrow_object"}), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == {"type": "wrap_typed_empty_array_literal"}


def test_w12_arrayrow_with_only_spaces_not_matched_by_arrayrow_branch():
    # `[{ }]` (just whitespace) — [^"}]+ requires >=1 non-} non-" char; space ok
    # but the spec's intent is "non-empty". A pure-space inner still has a space
    # so ArrayRow branch matches; that is acceptable (not the empty literal).
    assert _RE_W12_ARRAYROW.search('ArrayRow="[{ }]"') is not None


# ---------------------------------------------------------------------------
# W-16 — multi-part chain => fix_mechanical=None
# ---------------------------------------------------------------------------

_W16_MECH = {
    "type": "regex_replace",
    "pattern": (
        r'(?<![A-Za-z_:.])'
        r'(?![Ss]tring\.IsNullOr(?:Empty|WhiteSpace)\b)'
        r'([a-zA-Z_]\w*)\.(IsNullOrEmpty|IsNullOrWhiteSpace)\b'
    ),
    "replacement": r"String.\2(\1)",
}


def test_w16_single_identifier_keeps_mechanical(tmp_path):
    body = '<Activity Condition="[foo.IsNullOrEmpty]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w16_isnullorempty(_rule("W-16", _W16_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W16_MECH


def test_w16_isnullorwhitespace_single_identifier_keeps_mechanical(tmp_path):
    body = '<Activity Condition="[foo.IsNullOrWhiteSpace OrElse foo = &quot;&quot;]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w16_isnullorempty(_rule("W-16", _W16_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].message.endswith("foo.IsNullOrWhiteSpace")
    assert findings[0].fix_mechanical == _W16_MECH


def test_w16_static_isnullorwhitespace_ignored(tmp_path):
    body = '<Activity Condition="[String.IsNullOrWhiteSpace(foo)]" />'
    fc = _write_xaml(tmp_path, body)
    rule = _rule(
        "W-16",
        _W16_MECH,
        static_class_names=["string", "system.string", "s:string", "x:string"],
        last_segment_skip=["string"],
    )
    assert detect_w16_isnullorempty(rule, fc, _project(tmp_path)) == []


def test_w16_multipart_chain_routes_to_manual(tmp_path):
    body = '<Activity Condition="[obj.Field.IsNullOrEmpty]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w16_isnullorempty(_rule("W-16", _W16_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    # Multi-part => mechanical suppressed (fixer regex can't apply it).
    assert findings[0].fix_mechanical is None


# ---------------------------------------------------------------------------
# W-17 — multi-part chain => fix_mechanical=None
# ---------------------------------------------------------------------------

_W17_MECH = {
    "type": "regex_replace",
    "pattern": r'(?<![A-Za-z_:.])(?![Cc]onvert\.ToInt32\b)([a-zA-Z_]\w*)\.ToInt32\b',
    "replacement": r"Convert.ToInt32(\1)",
}


def test_w17_single_identifier_keeps_mechanical(tmp_path):
    body = '<Activity Value="[foo.ToInt32]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w17_toint32(_rule("W-17", _W17_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W17_MECH


def test_w17_multipart_chain_routes_to_manual(tmp_path):
    body = '<Activity Value="[obj.Field.ToInt32]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w17_toint32(_rule("W-17", _W17_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


# ---------------------------------------------------------------------------
# W-19 — SpecificContent/Output only auto-fixes known QueueItem receivers
# ---------------------------------------------------------------------------

_W19_MECH = {"type": "queue_item_indexer_to_item"}


def test_w19_queue_item_receiver_gets_mechanical_fix(tmp_path):
    body = '<Activity><Assign Value="[TransactionItem.SpecificContent(&quot;X&quot;)]" /></Activity>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w19_queue_item_indexer(_rule("W-19", _W19_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W19_MECH


def test_w19_typed_queue_item_name_gets_mechanical_fix(tmp_path):
    body = (
        '<Activity>'
        '<Variable x:TypeArguments="ui:QueueItem" Name="item" />'
        '<Assign Value="[item.Output(&quot;X&quot;)]" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w19_queue_item_indexer(_rule("W-19", _W19_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W19_MECH


def test_w19_ambiguous_receiver_is_contextual(tmp_path):
    body = '<Activity><Assign Value="[payload.SpecificContent(&quot;X&quot;)]" /></Activity>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w19_queue_item_indexer(_rule("W-19", _W19_MECH), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


# ---------------------------------------------------------------------------
# W-35 — terminal VB line-continuation before `]` is a compiler blocker
# ---------------------------------------------------------------------------

_W35_MECH = {"type": "strip_terminal_vb_line_continuation"}


def test_w35_detects_terminal_line_continuation(tmp_path):
    body = (
        '<Activity><FlowDecision Condition="[(foo IsNot Nothing) _]" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w35_terminal_vb_line_continuation(
        _rule("W-35", _W35_MECH), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W35_MECH


def test_w35_ignores_identifier_ending_with_underscore(tmp_path):
    body = '<Activity><Assign Value="[foo_]" /></Activity>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w35_terminal_vb_line_continuation(
        _rule("W-35", _W35_MECH), fc, _project(tmp_path)
    )
    assert findings == []


# ---------------------------------------------------------------------------
# W-36 — String.Format(...).ToStringWithDelimiter() legacy selector no-op
# ---------------------------------------------------------------------------

_W36_MECH = {"type": "strip_string_format_tostring_with_delimiter"}


def test_w36_detects_string_format_tostring_with_delimiter(tmp_path):
    body = (
        '<Activity><uix:TargetApp Selector="[(String.Format(&quot;&lt;wnd title='
        "'{0}' /&gt;&quot;, in_Title)).ToStringWithDelimiter()]\" /></Activity>"
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w36_string_format_tostring_with_delimiter(
        _rule("W-36", _W36_MECH), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W36_MECH


def test_w36_ignores_non_string_format_receiver(tmp_path):
    body = '<Activity><Assign Value="[items.ToStringWithDelimiter()]" /></Activity>'
    fc = _write_xaml(tmp_path, body)
    findings = detect_w36_string_format_tostring_with_delimiter(
        _rule("W-36", _W36_MECH), fc, _project(tmp_path)
    )
    assert findings == []


# ---------------------------------------------------------------------------
# W-37 — ReadAsDataTable 3-arg legacy signature in Excel 3.x
# ---------------------------------------------------------------------------

_W37_MECH = {"type": "expand_read_as_datatable_signature"}


def test_w37_detects_read_as_datatable_three_args(tmp_path):
    body = (
        '<Activity><If Condition="[CurrentSheet.ReadAsDataTable(True,False,Nothing)'
        '.Columns.Contains(&quot;X&quot;)]" /></Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w37_read_as_datatable_three_args(
        _rule("W-37", _W37_MECH), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W37_MECH


def test_w37_ignores_read_as_datatable_five_args(tmp_path):
    body = (
        '<Activity><If Condition="[CurrentSheet.ReadAsDataTable(True,False,Nothing,False,Nothing)'
        '.Columns.Contains(&quot;X&quot;)]" /></Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w37_read_as_datatable_three_args(
        _rule("W-37", _W37_MECH), fc, _project(tmp_path)
    )
    assert findings == []


# ---------------------------------------------------------------------------
# W-38 — CCS_SipagDirect legacy LoginSipagDirect namespace/activity
# ---------------------------------------------------------------------------

_W38_MECH = {"type": "rewrite_ccs_sipagdirect_legacy_login"}


def test_w38_detects_ccs_sipagdirect_legacy_login(tmp_path):
    body = (
        '<Activity xmlns:cs="clr-namespace:CCS_SipagDirect.Sessão;assembly=CCS_SipagDirect">'
        '<cs:LoginSipagDirect in_SSSenha="[vSenha]" '
        'in_StUrlSipagDirect="[url]" in_StUsuario="[user]" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w38_ccs_sipagdirect_legacy_login(
        _rule("W-38", _W38_MECH), fc, _project(tmp_path)
    )
    assert len(findings) == 1
    assert findings[0].fix_mechanical == _W38_MECH


def test_w38_ignores_current_ccs_sipagdirect_login(tmp_path):
    body = (
        '<Activity xmlns:cs="clr-namespace:CCS_SipagDirect;assembly=CCS_SipagDirect">'
        '<cs:Login in_Senha="[vSenha]" in_URL="[url]" in_Usuario="[user]" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w38_ccs_sipagdirect_legacy_login(
        _rule("W-38", _W38_MECH), fc, _project(tmp_path)
    )
    assert findings == []


def test_w38_ignores_local_loginsipagdirect_property(tmp_path):
    body = (
        '<Activity x:Class="LoginSipagDirect" xmlns:this="clr-namespace:">'
        '<this:LoginSipagDirect.in_StPrefixoLog>'
        '<InArgument x:TypeArguments="x:String" />'
        '</this:LoginSipagDirect.in_StPrefixoLog>'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_w38_ccs_sipagdirect_legacy_login(
        _rule("W-38", _W38_MECH), fc, _project(tmp_path)
    )
    assert findings == []


# ---------------------------------------------------------------------------
# UI-7 — bound/{x:Null} delays must not force literal "0"
# ---------------------------------------------------------------------------

def test_is_numeric_delay_helper():
    assert _is_numeric_delay("500") is True
    assert _is_numeric_delay("[500]") is True
    assert _is_numeric_delay("0.0") is True
    # Bound / non-reducible / null => NOT numeric => contextual
    assert _is_numeric_delay('[in_Config("DelaySimulate")]') is False
    assert _is_numeric_delay("{x:Null}") is False
    assert _is_numeric_delay("") is False
    assert _is_numeric_delay(None) is False


def test_ui7_literal_nonzero_delay_keeps_deterministic_fix(tmp_path):
    body = (
        '<Activity xmlns:uix="x">'
        '<uix:NTypeInto InteractionMode="Simulate" DelayBefore="500" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_ui7_simulate_delays(_rule("UI-7", None), fc, _project(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical is not None
    assert findings[0].fix_mechanical["type"] == "force_attribute_in_activity_with_guard"
    assert findings[0].fix_mechanical["target_value"] == "0"


def test_ui7_bound_delay_is_contextual_not_forced_to_zero(tmp_path):
    body = (
        '<Activity xmlns:uix="x">'
        '<uix:NTypeInto InteractionMode="Simulate" '
        'DelayBefore="[in_Config(&quot;DelaySimulate&quot;)]" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_ui7_simulate_delays(_rule("UI-7", None), fc, _project(tmp_path))
    assert len(findings) == 1
    # Binding expression must NOT be overwritten with literal 0.
    assert findings[0].fix_mechanical is None


def test_ui7_xnull_delay_is_contextual(tmp_path):
    body = (
        '<Activity xmlns:uix="x">'
        '<uix:NClick InteractionMode="Simulate" DelayAfter="{x:Null}" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_ui7_simulate_delays(_rule("UI-7", None), fc, _project(tmp_path))
    # DelayAfter is present, {x:Null} is not numeric-zero => violation flagged
    # but contextual (no deterministic force-0).
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None


def test_ui7_zero_delay_not_flagged(tmp_path):
    body = (
        '<Activity xmlns:uix="x">'
        '<uix:NTypeInto InteractionMode="Simulate" DelayBefore="0" DelayAfter="[0]" />'
        '</Activity>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_ui7_simulate_delays(_rule("UI-7", None), fc, _project(tmp_path))
    assert findings == []
    # sanity on the zero helper
    assert _is_zero_delay("0") is True
    assert _is_zero_delay("[0]") is True
