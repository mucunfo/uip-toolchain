"""N-3 scope-aware prefix derivation (2026-05-28).

Cobre:
  - _is_performer_project: name _Performer, dispatcher, fallback estrutural, None.
  - Gate Performer-only no detector N-3.
  - Exclusão de Main.xaml.
  - Detector dispara em workflow Process de Performer + thread de txn params.
  - Cascade derive-tier: Main→Process deriva TransactionItem.Reference;
    Process→child propaga; fallback "".
  - Idempotência do cascade derive.

Spec: docs/superpowers/specs/2026-05-28-n3-prefix-scope-derivation-design.md
Plan: docs/superpowers/plans/2026-05-28-n3-prefix-scope-derivation.md
"""
from __future__ import annotations

from pathlib import Path

from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.logs import (
    _is_performer_project, detect_n3_log_prefixo, detect_n3_prefixo_binding,
)
from uip_engine.fixers import _cascade_arg_to_callers, apply_seed_prefixo_binding
from uip_engine.loader import load_rules


_RULES_PATH = Path(__file__).resolve().parents[1] / "rules.yaml"


def _n3_rule():
    return next(r for r in load_rules(str(_RULES_PATH)) if r.id == "N-3")


def _write_pj(tmp_path: Path, name: str) -> None:
    (tmp_path / "project.json").write_text(
        f'{{"name":"{name}","targetFramework":"Windows"}}', encoding="utf-8")


def _wf(content_members: str, content_body: str = "") -> str:
    return (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        f'<x:Members>{content_members}</x:Members>{content_body}</Activity>'
    )


# ---------------------------------------------------------------------------
# _is_performer_project
# ---------------------------------------------------------------------------


def test_is_performer_by_name(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    assert _is_performer_project(ProjectContext.find_root(tmp_path)) is True


def test_is_performer_dispatcher_name_no_framework(tmp_path):
    _write_pj(tmp_path, "FooBar_Dispatcher")
    assert _is_performer_project(ProjectContext.find_root(tmp_path)) is False


def test_is_performer_structural_fallback(tmp_path):
    _write_pj(tmp_path, "LegacyBotNoSuffix")
    fw = tmp_path / "Framework"
    fw.mkdir()
    (fw / "Process.xaml").write_text("<Activity/>", encoding="utf-8")
    (fw / "GetTransactionData.xaml").write_text("<Activity/>", encoding="utf-8")
    assert _is_performer_project(ProjectContext.find_root(tmp_path)) is True


def test_is_performer_none_pc():
    assert _is_performer_project(None) is False


# ---------------------------------------------------------------------------
# Detector gate + Main exclusion
# ---------------------------------------------------------------------------


def test_n3_silent_on_non_performer(tmp_path):
    _write_pj(tmp_path, "FooBar_Dispatcher")
    wf = tmp_path / "MontaFila.xaml"
    wf.write_text(_wf("", '<ui:LogMessage Level="Info" Message="[&quot;oi&quot;]" />'),
                  encoding="utf-8")
    findings = detect_n3_log_prefixo(_n3_rule(), FileContext(wf),
                                     ProjectContext.find_root(tmp_path))
    assert findings == []


def test_n3_excludes_main(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    main = tmp_path / "Main.xaml"
    main.write_text(_wf("", '<ui:LogMessage Level="Info" Message="[&quot;oi&quot;]" />'),
                    encoding="utf-8")
    findings = detect_n3_log_prefixo(_n3_rule(), FileContext(main),
                                     ProjectContext.find_root(tmp_path))
    assert findings == []


def test_n3_fires_on_performer_process_workflow(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    wf = tmp_path / "RealizaAlgo.xaml"
    wf.write_text(_wf("", '<ui:LogMessage Level="Info" Message="[&quot;oi&quot;]" />'),
                  encoding="utf-8")
    findings = detect_n3_log_prefixo(_n3_rule(), FileContext(wf),
                                     ProjectContext.find_root(tmp_path))
    assert len(findings) >= 1
    fm = findings[0].fix_mechanical
    assert fm["type"] == "add_prefixo_arg"
    assert fm["transaction_var_name"] == "TransactionItem"
    assert fm["transaction_arg_name"] == "in_TransactionItem"


# ---------------------------------------------------------------------------
# Cascade derive-tier
# ---------------------------------------------------------------------------


def _process_xaml() -> str:
    return _wf(
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'
    )


def test_cascade_main_derives_from_transactionitem(tmp_path):
    (tmp_path / "Process.xaml").write_text(_process_xaml(), encoding="utf-8")
    main = tmp_path / "Main.xaml"
    main.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<Variable x:TypeArguments="ui:QueueItem" Name="TransactionItem" />'
        '<ui:InvokeWorkflowFile WorkflowFileName="Process.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    n = _cascade_arg_to_callers(tmp_path, tmp_path / "Process.xaml",
                                "in_StPrefixoLog", default_expr='""', dry_run=False)
    assert n == 1
    out = main.read_text(encoding="utf-8")
    assert 'x:Key="in_StPrefixoLog">[TransactionItem.Reference + " - "]</InArgument>' in out


def test_cascade_process_child_propagates(tmp_path):
    child = tmp_path / "Child.xaml"
    child.write_text(
        _wf('<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'),
        encoding="utf-8")
    proc = tmp_path / "Process.xaml"
    proc.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<x:Members>'
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'
        '</x:Members>'
        '<ui:InvokeWorkflowFile WorkflowFileName="Child.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    n = _cascade_arg_to_callers(tmp_path, child, "in_StPrefixoLog",
                                default_expr='""', dry_run=False)
    assert n == 1
    out = proc.read_text(encoding="utf-8")
    assert 'x:Key="in_StPrefixoLog">[in_StPrefixoLog]</InArgument>' in out


def test_cascade_fallback_empty(tmp_path):
    callee = tmp_path / "Callee.xaml"
    callee.write_text(
        _wf('<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'),
        encoding="utf-8")
    caller = tmp_path / "Caller.xaml"
    caller.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<x:Members></x:Members>'
        '<ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    n = _cascade_arg_to_callers(tmp_path, callee, "in_StPrefixoLog",
                                default_expr='""', dry_run=False)
    assert n == 1
    out = caller.read_text(encoding="utf-8")
    assert 'x:Key="in_StPrefixoLog">""</InArgument>' in out


def test_cascade_main_derive_idempotent(tmp_path):
    (tmp_path / "Process.xaml").write_text(_process_xaml(), encoding="utf-8")
    main = tmp_path / "Main.xaml"
    main.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<Variable x:TypeArguments="ui:QueueItem" Name="TransactionItem" />'
        '<ui:InvokeWorkflowFile WorkflowFileName="Process.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    _cascade_arg_to_callers(tmp_path, tmp_path / "Process.xaml",
                            "in_StPrefixoLog", dry_run=False)
    first = main.read_text(encoding="utf-8")
    n2 = _cascade_arg_to_callers(tmp_path, tmp_path / "Process.xaml",
                                 "in_StPrefixoLog", dry_run=False)
    second = main.read_text(encoding="utf-8")
    assert n2 == 0
    assert first == second


# ===========================================================================
# N-3B — invoke-binding seed model (detector + fixer)
# ===========================================================================


def _n3b_rule():
    return next(r for r in load_rules(str(_RULES_PATH)) if r.id == "N-3B")


_NS = (
    'xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
    'xmlns:ui="http://schemas.uipath.com/workflow/activities"'
)


def _invoke_block(callee: str, prefixo_value: str = '""') -> str:
    return (
        f'<ui:InvokeWorkflowFile WorkflowFileName="{callee}">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '<InArgument x:TypeArguments="x:String" '
        f'x:Key="in_StPrefixoLog">{prefixo_value}</InArgument>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile>'
    )


def _owner_derive_arg_wf(callee: str = "Child.xaml", prefixo_value: str = '""') -> str:
    return (
        f'<Activity {_NS}>'
        '<x:Members>'
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '<x:Property Name="in_Config" Type="InArgument(x:Object)" />'
        '</x:Members>'
        + _invoke_block(callee, prefixo_value)
        + '</Activity>'
    )


def _inherit_wf(callee: str = "Child.xaml", prefixo_value: str = '""') -> str:
    return (
        f'<Activity {_NS}>'
        '<x:Members>'
        '<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '</x:Members>'
        + _invoke_block(callee, prefixo_value)
        + '</Activity>'
    )


def _owner_derive_var_wf(callee: str = "Process.xaml", prefixo_value: str = '""') -> str:
    return (
        f'<Activity {_NS}>'
        '<x:Members></x:Members>'
        '<Variable x:TypeArguments="ui:QueueItem" Name="TransactionItem" />'
        + _invoke_block(callee, prefixo_value)
        + '</Activity>'
    )


# ---- detector ----

def test_n3b_derive_arg_empty_binding(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_text(_owner_derive_arg_wf(), encoding="utf-8")
    findings = detect_n3_prefixo_binding(_n3b_rule(), FileContext(wf),
                                         ProjectContext.find_root(tmp_path))
    assert len(findings) == 1
    fm = findings[0].fix_mechanical
    assert fm["type"] == "seed_prefixo_binding"
    assert fm["arg_name"] == "in_StPrefixoLog"
    assert fm["value_expr"] == '[in_TransactionItem.Reference + " - "]'
    assert fm["mode"] == "derive-arg"


def test_n3b_inherit_empty_binding(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    wf = tmp_path / "Inheritor.xaml"
    wf.write_text(_inherit_wf(), encoding="utf-8")
    findings = detect_n3_prefixo_binding(_n3b_rule(), FileContext(wf),
                                         ProjectContext.find_root(tmp_path))
    assert len(findings) == 1
    fm = findings[0].fix_mechanical
    assert fm["value_expr"] == "[in_StPrefixoLog]"
    assert fm["mode"] == "inherit"


def test_n3b_derive_var_main_side(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    wf = tmp_path / "MainSide.xaml"
    wf.write_text(_owner_derive_var_wf(), encoding="utf-8")
    findings = detect_n3_prefixo_binding(_n3b_rule(), FileContext(wf),
                                         ProjectContext.find_root(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical["value_expr"] == '[TransactionItem.Reference + " - "]'
    assert findings[0].fix_mechanical["mode"] == "derive-var"


def test_n3b_no_source_no_finding(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    wf = tmp_path / "NoSource.xaml"
    wf.write_text(
        f'<Activity {_NS}><x:Members></x:Members>'
        + _invoke_block("Child.xaml")
        + '</Activity>', encoding="utf-8")
    findings = detect_n3_prefixo_binding(_n3b_rule(), FileContext(wf),
                                         ProjectContext.find_root(tmp_path))
    assert findings == []


def test_n3b_performer_gate_dispatcher(tmp_path):
    _write_pj(tmp_path, "FooBar_Dispatcher")
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_text(_owner_derive_arg_wf(), encoding="utf-8")
    findings = detect_n3_prefixo_binding(_n3b_rule(), FileContext(wf),
                                         ProjectContext.find_root(tmp_path))
    assert findings == []


def test_n3b_skips_already_correct(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_text(
        _owner_derive_arg_wf(prefixo_value='[in_TransactionItem.Reference + " - "]'),
        encoding="utf-8")
    findings = detect_n3_prefixo_binding(_n3b_rule(), FileContext(wf),
                                         ProjectContext.find_root(tmp_path))
    assert findings == []


def test_n3b_skips_nonempty_handset(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_text(_owner_derive_arg_wf(prefixo_value='[vCustomPrefix]'),
                  encoding="utf-8")
    findings = detect_n3_prefixo_binding(_n3b_rule(), FileContext(wf),
                                         ProjectContext.find_root(tmp_path))
    assert findings == []


def test_n3b_applies_to_includes_framework_process():
    import pathspec
    rule = _n3b_rule()
    excl = rule.applies_to.get("exclude") or []
    spec = pathspec.PathSpec.from_lines("gitwildmatch", excl)
    assert spec.match_file("Framework/Process.xaml") is False
    assert spec.match_file("Framework/GetTransactionData.xaml") is False
    assert spec.match_file("Main.xaml") is True
    assert spec.match_file("Tests/SmokeTest.xaml") is True
    assert spec.match_file("Framework/SetTransactionStatusLaunch.xaml") is True


def test_n3b_fires_on_framework_process(tmp_path):
    _write_pj(tmp_path, "FooBar_Performer")
    fw = tmp_path / "Framework"
    fw.mkdir()
    (fw / "GetTransactionData.xaml").write_text("<Activity/>", encoding="utf-8")
    proc = fw / "Process.xaml"
    proc.write_text(_owner_derive_arg_wf(callee="Sipag_Net\\Algo.xaml"), encoding="utf-8")
    findings = detect_n3_prefixo_binding(_n3b_rule(), FileContext(proc),
                                         ProjectContext.find_root(tmp_path))
    assert len(findings) == 1
    assert findings[0].fix_mechanical["value_expr"] == '[in_TransactionItem.Reference + " - "]'


# ---- fixer ----

def test_seed_fixer_upgrades_empty_derive(tmp_path):
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_text(_owner_derive_arg_wf(), encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    assert apply_seed_prefixo_binding(wf, spec, dry_run=False) is True
    out = wf.read_text(encoding="utf-8")
    assert ('x:Key="in_StPrefixoLog">[in_TransactionItem.Reference + " - "]'
            '</InArgument>') in out
    assert 'x:Key="in_StPrefixoLog">""</InArgument>' not in out


def test_seed_fixer_no_double_space(tmp_path):
    """REGRESSION (workflow verify 3-lens): attrs.rstrip() leaving leading space
    + template space → '<InArgument  x:'. Must be single space, byte-clean."""
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_text(_owner_derive_arg_wf(), encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    apply_seed_prefixo_binding(wf, spec, dry_run=False)
    out = wf.read_text(encoding="utf-8")
    assert "<InArgument  " not in out, "double-space after <InArgument"
    assert '<InArgument x:TypeArguments="x:String" x:Key="in_StPrefixoLog">' in out


def test_seed_fixer_upgrades_empty_inherit(tmp_path):
    wf = tmp_path / "Inheritor.xaml"
    wf.write_text(_inherit_wf(), encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": "[in_StPrefixoLog]"}
    assert apply_seed_prefixo_binding(wf, spec, dry_run=False) is True
    out = wf.read_text(encoding="utf-8")
    assert 'x:Key="in_StPrefixoLog">[in_StPrefixoLog]</InArgument>' in out


def test_seed_fixer_upgrades_multiple_sites(tmp_path):
    wf = tmp_path / "MultiOwner.xaml"
    wf.write_text(
        f'<Activity {_NS}>'
        '<x:Members>'
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '</x:Members>'
        + _invoke_block("A.xaml") + _invoke_block("B.xaml") + _invoke_block("C.xaml")
        + '</Activity>', encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    assert apply_seed_prefixo_binding(wf, spec, dry_run=False) is True
    out = wf.read_text(encoding="utf-8")
    assert out.count(
        'x:Key="in_StPrefixoLog">[in_TransactionItem.Reference + " - "]</InArgument>') == 3
    assert '">""</InArgument>' not in out


def test_seed_fixer_does_not_clobber_nonempty(tmp_path):
    wf = tmp_path / "HandSet.xaml"
    wf.write_text(_owner_derive_arg_wf(prefixo_value='[vCustomPrefix]'), encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    assert apply_seed_prefixo_binding(wf, spec, dry_run=False) is False
    assert 'x:Key="in_StPrefixoLog">[vCustomPrefix]</InArgument>' in wf.read_text(encoding="utf-8")


def test_seed_fixer_idempotent_rerun(tmp_path):
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_text(_owner_derive_arg_wf(), encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    assert apply_seed_prefixo_binding(wf, spec, dry_run=False) is True
    first = wf.read_text(encoding="utf-8")
    assert apply_seed_prefixo_binding(wf, spec, dry_run=False) is False
    assert wf.read_text(encoding="utf-8") == first


def test_seed_fixer_dry_run_no_write(tmp_path):
    wf = tmp_path / "OwnerArg.xaml"
    original = _owner_derive_arg_wf()
    wf.write_text(original, encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    assert apply_seed_prefixo_binding(wf, spec, dry_run=True) is True
    assert wf.read_text(encoding="utf-8") == original


def test_seed_fixer_preserves_bom(tmp_path):
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_bytes(b"\xef\xbb\xbf" + _owner_derive_arg_wf().encode("utf-8"))
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    apply_seed_prefixo_binding(wf, spec, dry_run=False)
    assert wf.read_bytes()[:3] == b"\xef\xbb\xbf"


def test_seed_fixer_attr_order_agnostic(tmp_path):
    wf = tmp_path / "ReorderedAttrs.xaml"
    wf.write_text(
        f'<Activity {_NS}>'
        '<x:Members>'
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '</x:Members>'
        '<ui:InvokeWorkflowFile WorkflowFileName="X.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '<InArgument x:Key="in_StPrefixoLog" x:TypeArguments="x:String">""</InArgument>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    assert apply_seed_prefixo_binding(wf, spec, dry_run=False) is True
    out = wf.read_text(encoding="utf-8")
    assert '[in_TransactionItem.Reference + " - "]</InArgument>' in out
    assert 'x:Key="in_StPrefixoLog" x:TypeArguments="x:String"' in out


def test_seed_fixer_output_xml_wellformed(tmp_path):
    import xml.etree.ElementTree as ET
    wf = tmp_path / "OwnerArg.xaml"
    wf.write_text(_owner_derive_arg_wf(), encoding="utf-8")
    spec = {"type": "seed_prefixo_binding", "arg_name": "in_StPrefixoLog",
            "value_expr": '[in_TransactionItem.Reference + " - "]'}
    apply_seed_prefixo_binding(wf, spec, dry_run=False)
    ET.parse(wf)
