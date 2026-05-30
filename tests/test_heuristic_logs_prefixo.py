"""Tests for the Sicoob log-prefix propagation model (N-3B reworked, N-3C, N-3D)
and its fixers (seed_prefixo_binding overwrite, strip_prefixo_from_main).

Modelo:
  1. DERIVA uma vez no seed Main->Process: [TransactionItem.Reference + " - "].
  2. PROPAGA herança [in_StPrefixoLog] em Process + toda a cadeia (overwrite-always).
  3. Main NÃO declara/usa o prefixo (só semeia o valor no invoke do Process).
"""
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.logs import (
    detect_n3_prefixo_binding,
    detect_n3c_main_deownership,
    detect_n3d_propagator_declares,
)
from uip_engine.fixers import (
    apply_seed_prefixo_binding,
    apply_strip_prefixo_from_main,
)

_BINDING_PARAMS = {
    "prefixo_arg_name": "in_StPrefixoLog",
    "transaction_var_name": "TransactionItem",
    "transaction_arg_name": "in_TransactionItem",
}


def _rule(rid, params=None, severity=Severity.WARN):
    return Rule(
        id=rid, severity=severity, category="architectural", target="all",
        title=rid, description="",
        detect={"type": "python", "params": dict(params or _BINDING_PARAMS)},
    )


def _perf_pc(root: Path) -> ProjectContext:
    return ProjectContext(
        root=root,
        project_json={"name": "Foo_Performer", "main": "Main.xaml",
                      "targetFramework": "Windows"},
    )


def _write(root: Path, rel: str, members: str = "", body: str = "",
           cls: str = "Foo") -> FileContext:
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<Activity x:Class="{cls}" xmlns:ui="ui" xmlns:x="x" '
        'xmlns:this="clr-namespace:">\n'
        f'  <x:Members>\n{members}\n  </x:Members>\n'
        f'{body}\n'
        '</Activity>',
        encoding="utf-8",
    )
    return FileContext(f)


_INVOKE = (
    '  <ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">\n'
    '    <ui:InvokeWorkflowFile.Arguments>\n'
    '      <InArgument x:TypeArguments="x:String" x:Key="in_StPrefixoLog">{val}</InArgument>\n'
    '    </ui:InvokeWorkflowFile.Arguments>\n'
    '  </ui:InvokeWorkflowFile>'
)


# ---------------- N-3B: propagação na cadeia (não-Main) ----------------

def test_n3b_flags_rederivation_in_chain(tmp_path):
    """Binding NÃO-vazio re-derivado no Process/cadeia → flag + overwrite."""
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Framework/Process.xaml",
                body=_INVOKE.format(val='[in_TransactionItem.Reference + " - "]'),
                cls="Process")
    findings = detect_n3_prefixo_binding(_rule("N-3B"), fc, pc)
    assert len(findings) == 1
    spec = findings[0].fix_mechanical
    assert spec["type"] == "seed_prefixo_binding"
    assert spec["value_expr"] == "[in_StPrefixoLog]"
    assert spec["overwrite"] is True


def test_n3b_flags_empty_binding_in_chain(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Sipag/Sub.xaml", body=_INVOKE.format(val=""))
    findings = detect_n3_prefixo_binding(_rule("N-3B"), fc, pc)
    assert len(findings) == 1


def test_n3b_no_finding_when_already_inherit(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Sipag/Sub.xaml",
                body=_INVOKE.format(val="[in_StPrefixoLog]"))
    findings = detect_n3_prefixo_binding(_rule("N-3B"), fc, pc)
    assert findings == []


def test_n3b_skips_main_entry(tmp_path):
    """N-3B nunca toca o Main (seed-owner intocável)."""
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Main.xaml",
                body=_INVOKE.format(val='[in_TransactionItem.Reference + " - "]'),
                cls="Main")
    assert detect_n3_prefixo_binding(_rule("N-3B"), fc, pc) == []


# ---------------- N-3C: Main de-ownership ----------------

def test_n3c_flags_main_declaring_prefixo(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Main.xaml",
                members='    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />',
                cls="Main")
    findings = detect_n3c_main_deownership(_rule("N-3C", {"prefixo_arg_name": "in_StPrefixoLog"}), fc, pc)
    assert len(findings) == 1
    assert findings[0].fix_mechanical["type"] == "strip_prefixo_from_main"


def test_n3c_flags_main_using_prefixo_in_message(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Main.xaml",
                body='  <ui:LogMessage Message="[in_StPrefixoLog + &quot;x&quot;]" />',
                cls="Main")
    findings = detect_n3c_main_deownership(_rule("N-3C", {"prefixo_arg_name": "in_StPrefixoLog"}), fc, pc)
    assert len(findings) == 1


def test_n3c_ignores_main_seed_binding_only(tmp_path):
    """Main que SÓ semeia o valor no invoke (x:Key) — sem decl/uso — é OK."""
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Main.xaml",
                body=_INVOKE.format(val='[TransactionItem.Reference + " - "]'),
                cls="Main")
    assert detect_n3c_main_deownership(_rule("N-3C", {"prefixo_arg_name": "in_StPrefixoLog"}), fc, pc) == []


def test_n3c_skips_non_main(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Framework/Process.xaml",
                members='    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />',
                cls="Process")
    assert detect_n3c_main_deownership(_rule("N-3C", {"prefixo_arg_name": "in_StPrefixoLog"}), fc, pc) == []


# ---------------- N-3D: propagador deve declarar ----------------

def test_n3d_flags_process_propagating_without_declaring(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Framework/Process.xaml",
                body=_INVOKE.format(val="[in_StPrefixoLog]"), cls="Process")
    findings = detect_n3d_propagator_declares(_rule("N-3D", severity=Severity.ERROR), fc, pc)
    assert len(findings) == 1
    assert findings[0].fix_mechanical["type"] == "add_prefixo_arg"


def test_n3d_no_finding_when_declares(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Framework/Process.xaml",
                members='    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />',
                body=_INVOKE.format(val="[in_StPrefixoLog]"), cls="Process")
    assert detect_n3d_propagator_declares(_rule("N-3D"), fc, pc) == []


def test_n3d_no_finding_when_not_propagating(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Framework/Process.xaml", cls="Process")
    assert detect_n3d_propagator_declares(_rule("N-3D"), fc, pc) == []


def test_n3d_skips_main(tmp_path):
    pc = _perf_pc(tmp_path)
    fc = _write(tmp_path, "Main.xaml",
                body=_INVOKE.format(val="[in_StPrefixoLog]"), cls="Main")
    assert detect_n3d_propagator_declares(_rule("N-3D"), fc, pc) == []


# ---------------- Fixers ----------------

def test_seed_prefixo_overwrite_rewrites_nonempty(tmp_path):
    """overwrite=True reescreve binding NÃO-vazio errado → herança."""
    f = tmp_path / "Process.xaml"
    f.write_text(
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        + _INVOKE.format(val='[in_TransactionItem.Reference + " - "]')
        + '\n</Activity>',
        encoding="utf-8",
    )
    spec = {"arg_name": "in_StPrefixoLog", "value_expr": "[in_StPrefixoLog]",
            "overwrite": True}
    assert apply_seed_prefixo_binding(f, spec, dry_run=False) is True
    txt = f.read_text(encoding="utf-8")
    assert ">[in_StPrefixoLog]<" in txt
    assert 'in_TransactionItem.Reference + " - "' not in txt


def test_seed_prefixo_no_overwrite_keeps_nonempty(tmp_path):
    """Sem overwrite, valor não-vazio hand-set é preservado (guard clássico)."""
    f = tmp_path / "Process.xaml"
    f.write_text(
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        + _INVOKE.format(val='[algo_hand_set]')
        + '\n</Activity>',
        encoding="utf-8",
    )
    spec = {"arg_name": "in_StPrefixoLog", "value_expr": "[in_StPrefixoLog]"}
    assert apply_seed_prefixo_binding(f, spec, dry_run=False) is False
    assert "[algo_hand_set]" in f.read_text(encoding="utf-8")


def test_strip_prefixo_from_main_removes_decl_default_and_msg(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(
        '<Activity x:Class="Main" xmlns:ui="ui" xmlns:x="x" xmlns:this="clr-namespace:">\n'
        '  <x:Members>\n'
        '    <x:Property Name="in_OutroArg" Type="InArgument(x:String)" />\n'
        '    <x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />\n'
        '  </x:Members>\n'
        '  <this:Main.in_StPrefixoLog>\n'
        '    <InArgument x:TypeArguments="x:String">\n'
        '      <Literal x:TypeArguments="x:String" Value="" />\n'
        '    </InArgument>\n'
        '  </this:Main.in_StPrefixoLog>\n'
        '  <ui:LogMessage Message="[in_StPrefixoLog + &quot;oi&quot;]" />\n'
        '  <ui:InvokeWorkflowFile WorkflowFileName="Framework\\Process.xaml">\n'
        '    <ui:InvokeWorkflowFile.Arguments>\n'
        '      <InArgument x:TypeArguments="x:String" x:Key="in_StPrefixoLog">[TransactionItem.Reference + " - "]</InArgument>\n'
        '    </ui:InvokeWorkflowFile.Arguments>\n'
        '  </ui:InvokeWorkflowFile>\n'
        '</Activity>',
        encoding="utf-8",
    )
    spec = {"prefixo_arg": "in_StPrefixoLog"}
    assert apply_strip_prefixo_from_main(f, spec, dry_run=False) is True
    txt = f.read_text(encoding="utf-8")
    # declaração + bloco default + prefixo da mensagem removidos
    assert '<x:Property Name="in_StPrefixoLog"' not in txt
    assert "<this:Main.in_StPrefixoLog>" not in txt
    assert "[in_StPrefixoLog + " not in txt
    assert 'Message="[&quot;oi&quot;]"' in txt
    # seed binding (x:Key) PRESERVADO
    assert 'x:Key="in_StPrefixoLog">[TransactionItem.Reference + " - "]' in txt
    # outro arg intacto
    assert '<x:Property Name="in_OutroArg"' in txt


def test_strip_prefixo_from_main_idempotent(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(
        '<Activity x:Class="Main" xmlns:ui="ui" xmlns:x="x">\n'
        '  <x:Members></x:Members>\n'
        '  <ui:LogMessage Message="[&quot;sem prefixo&quot;]" />\n'
        '</Activity>',
        encoding="utf-8",
    )
    assert apply_strip_prefixo_from_main(f, {"prefixo_arg": "in_StPrefixoLog"},
                                         dry_run=False) is False
