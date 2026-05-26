"""Tests for Phase 9E `apply_inject_missing_args` fixer + RT-LOAD-AMBIGUOUS-ARG.

Coverage:
  - Pure fixer mechanic: inject <x:Property/> em <x:Members> com type pré-resolvido.
  - Idempotência: re-run no-op.
  - Sem <x:Members>: cria block.
  - Whitelist sanitization: XML injection blocked.
  - End-to-end inline inference: runtime_loadtest._parse_output enriquece
    findings com fix_mechanical (L1/L2/L3) OU emite RT-LOAD-AMBIGUOUS-ARG (L4).

Fixer NÃO faz resolução — só consome `inferred_type` do spec. Resolução é
upstream em runtime_loadtest._infer_missing_arg_type.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.rule_engine.fixers import REGISTRY, apply_inject_missing_args
from scripts.rule_engine import runtime_loadtest as rt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_XAML_WITH_MEMBERS = '''<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Sub"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
  xmlns:sd="clr-namespace:System.Data;assembly=System.Data.Common"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <x:Property Name="in_Other" Type="InArgument(x:String)" />
  </x:Members>
  <Sequence />
</Activity>
'''

_XAML_WITHOUT_MEMBERS = '''<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Sub"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence />
</Activity>
'''

_XAML_EMPTY_MEMBERS = '''<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Sub"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members></x:Members>
  <Sequence />
</Activity>
'''


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


def test_fixer_registered():
    """Fixer must be in REGISTRY pra dispatch via fix_mechanical['type']."""
    assert "inject_missing_args" in REGISTRY
    assert REGISTRY["inject_missing_args"] is apply_inject_missing_args


# ---------------------------------------------------------------------------
# Fixer pure mechanic (inferred_type passado em spec)
# ---------------------------------------------------------------------------


def test_inject_into_existing_members(tmp_path):
    """Spec com arg_name + inferred_type => inject Property antes </x:Members>."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    spec = {
        "type": "inject_missing_args",
        "arg_name": "in_Config",
        "inferred_type": "InArgument(scg:Dictionary(x:String, x:Object))",
        "source": "canonical",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=False)
    assert changed is True
    text = xaml.read_text(encoding="utf-8")
    assert 'Name="in_Config"' in text
    assert "InArgument(scg:Dictionary(x:String, x:Object))" in text
    # Original property preservada
    assert 'Name="in_Other"' in text


def test_dry_run_no_write(tmp_path):
    """dry_run=True reports change=True mas não escreve arquivo."""
    xaml = tmp_path / "Sub.xaml"
    original = _XAML_WITH_MEMBERS
    xaml.write_text(original, encoding="utf-8")
    spec = {
        "type": "inject_missing_args",
        "arg_name": "in_StFoo",
        "inferred_type": "InArgument(x:String)",
        "source": "hungarian",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=True)
    assert changed is True
    assert xaml.read_text(encoding="utf-8") == original


def test_idempotent_already_declared(tmp_path):
    """Arg already in Members → no-op (False)."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    spec = {
        "type": "inject_missing_args",
        "arg_name": "in_Other",  # já está no XAML
        "inferred_type": "InArgument(x:String)",
        "source": "canonical",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=False)
    assert changed is False


def test_inject_into_empty_members(tmp_path):
    """<x:Members></x:Members> sem properties → inject ok."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_EMPTY_MEMBERS, encoding="utf-8")
    spec = {
        "type": "inject_missing_args",
        "arg_name": "in_StPrefixoLog",
        "inferred_type": "InArgument(x:String)",
        "source": "canonical",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=False)
    assert changed is True
    text = xaml.read_text(encoding="utf-8")
    assert 'Name="in_StPrefixoLog"' in text
    assert 'Type="InArgument(x:String)"' in text


def test_inject_creates_members_block_when_absent(tmp_path):
    """XAML sem <x:Members> → cria block + inject property dentro."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITHOUT_MEMBERS, encoding="utf-8")
    spec = {
        "type": "inject_missing_args",
        "arg_name": "io_TransactionNumber",
        "inferred_type": "InOutArgument(x:Int32)",
        "source": "canonical",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=False)
    assert changed is True
    text = xaml.read_text(encoding="utf-8")
    assert "<x:Members>" in text
    assert "</x:Members>" in text
    assert 'Name="io_TransactionNumber"' in text


def test_invalid_arg_name_rejected(tmp_path):
    """arg_name com chars inválidos → skip (False)."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    spec = {
        "type": "inject_missing_args",
        "arg_name": "in Config",  # space inválido em VB identifier
        "inferred_type": "InArgument(x:String)",
        "source": "canonical",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=False)
    assert changed is False


def test_xml_injection_in_type_rejected(tmp_path):
    """inferred_type com `<` ou `"` rejeitado pra prevenir XML break."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    spec = {
        "type": "inject_missing_args",
        "arg_name": "in_Foo",
        "inferred_type": 'InArgument(x:String)" /><!--evil',
        "source": "canonical",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=False)
    assert changed is False


def test_missing_spec_fields(tmp_path):
    """Missing arg_name ou inferred_type → False."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    assert apply_inject_missing_args(xaml, {}, dry_run=False) is False
    assert apply_inject_missing_args(
        xaml, {"arg_name": "in_Foo"}, dry_run=False,
    ) is False
    assert apply_inject_missing_args(
        xaml, {"inferred_type": "InArgument(x:String)"}, dry_run=False,
    ) is False


def test_xaml_still_parses_after_inject(tmp_path):
    """Post-fix XAML deve parse OK via xml.etree (apply_with_gate safety)."""
    import xml.etree.ElementTree as ET

    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    spec = {
        "type": "inject_missing_args",
        "arg_name": "in_Config",
        "inferred_type": "InArgument(scg:Dictionary(x:String, x:Object))",
        "source": "canonical",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=False)
    assert changed
    # Should not raise
    ET.parse(str(xaml))


def test_preserves_bom(tmp_path):
    """BOM-prefixed XAML mantém BOM pós-fix."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_bytes(b"\xef\xbb\xbf" + _XAML_WITH_MEMBERS.encode("utf-8"))
    spec = {
        "type": "inject_missing_args",
        "arg_name": "in_Config",
        "inferred_type": "InArgument(scg:Dictionary(x:String, x:Object))",
        "source": "canonical",
    }
    changed = apply_inject_missing_args(xaml, spec, dry_run=False)
    assert changed
    assert xaml.read_bytes().startswith(b"\xef\xbb\xbf")


# ---------------------------------------------------------------------------
# End-to-end inference em runtime_loadtest._parse_output
# ---------------------------------------------------------------------------


def _fake_runtime_loadtest_output(file_path: str, error: str) -> str:
    """Build JSON stdout que .NET runtime_loadtest produziria."""
    payload = {
        "results": [
            {
                "Status": "INVALID_WORKFLOW",
                "File": file_path,
                "Category": "load",
                "Error": error,
                "Line": 0,
            }
        ]
    }
    return json.dumps(payload)


def test_parse_output_layer1_canonical(tmp_path):
    """`in_Config` is_not_declared → finding enriched w/ canonical type."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    stdout = _fake_runtime_loadtest_output(
        str(xaml), "'in_Config' is not declared. It may be inaccessible.",
    )
    findings = rt._parse_output(stdout, tmp_path)
    iw = [f for f in findings if f.rule_id == "RT-LOAD-INVALID_WORKFLOW"]
    amb = [f for f in findings if f.rule_id == "RT-LOAD-AMBIGUOUS-ARG"]
    assert len(iw) == 1
    assert len(amb) == 0
    spec = iw[0].fix_mechanical
    assert spec is not None
    assert spec["type"] == "inject_missing_args"
    assert spec["arg_name"] == "in_Config"
    assert "Dictionary" in spec["inferred_type"]
    assert spec["source"] == "canonical"


def test_parse_output_layer3_hungarian(tmp_path):
    """Arg in_StFooQuePotencialmenteNuncaExiste → Hungarian L3 hit (St=String)."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    stdout = _fake_runtime_loadtest_output(
        str(xaml),
        "'in_StFooQuePotencialmenteNuncaExiste' is not declared.",
    )
    findings = rt._parse_output(stdout, tmp_path)
    iw = [f for f in findings if f.rule_id == "RT-LOAD-INVALID_WORKFLOW"]
    assert len(iw) == 1
    spec = iw[0].fix_mechanical
    assert spec is not None
    # Pode bater em canonical se nome coincidir, mas no caso é único + St → L3
    assert spec["arg_name"] == "in_StFooQuePotencialmenteNuncaExiste"
    assert spec["inferred_type"] == "InArgument(x:String)"
    assert spec["source"] in ("canonical", "hungarian")


def test_parse_output_layer4_halt_unknown(tmp_path):
    """Arg sem canonical hit + sem Hungarian prefix + sem callers → HALT."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    # `xyz` não bate em direção (in/io/out) — Hungarian falha. Não está em
    # canonical. Sem callers no tmp_path. → L4 HALT.
    stdout = _fake_runtime_loadtest_output(
        str(xaml), "'xyz_unknownArgWeird' is not declared.",
    )
    findings = rt._parse_output(stdout, tmp_path)
    iw = [f for f in findings if f.rule_id == "RT-LOAD-INVALID_WORKFLOW"]
    amb = [f for f in findings if f.rule_id == "RT-LOAD-AMBIGUOUS-ARG"]
    assert len(iw) == 1
    # IW finding sem fix_mechanical (engine bypassa fixer)
    assert iw[0].fix_mechanical is None
    # HALT finding emitido em paralelo
    assert len(amb) == 1
    from scripts.rule_engine._types import Severity
    assert amb[0].severity == Severity.HALT
    assert "xyz_unknownArgWeird" in amb[0].message


def test_parse_output_non_missing_arg_error_unaffected(tmp_path):
    """Errors que NÃO são `is not declared` não disparam Phase 9E machinery."""
    xaml = tmp_path / "Sub.xaml"
    xaml.write_text(_XAML_WITH_MEMBERS, encoding="utf-8")
    stdout = _fake_runtime_loadtest_output(
        str(xaml),
        "Type 'Foo.Bar.Baz' could not be resolved. AssemblyRef missing.",
    )
    findings = rt._parse_output(stdout, tmp_path)
    iw = [f for f in findings if f.rule_id == "RT-LOAD-INVALID_WORKFLOW"]
    amb = [f for f in findings if f.rule_id == "RT-LOAD-AMBIGUOUS-ARG"]
    assert len(iw) == 1
    assert iw[0].fix_mechanical is None  # nada pra auto-fixar
    assert len(amb) == 0


# ---------------------------------------------------------------------------
# YAML rules registered
# ---------------------------------------------------------------------------


def test_phase_9e_rules_in_yaml():
    """RT-LOAD-INVALID_WORKFLOW + RT-LOAD-AMBIGUOUS-ARG registered."""
    import yaml as _yaml
    yaml_path = (
        Path(__file__).resolve().parents[1] / "rules.yaml"
    )
    raw = _yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    ids = {r["id"] for r in raw["rules"]}
    assert "RT-LOAD-INVALID_WORKFLOW" in ids
    assert "RT-LOAD-AMBIGUOUS-ARG" in ids
    # AMBIGUOUS-ARG é HALT severity
    amb = next(r for r in raw["rules"] if r["id"] == "RT-LOAD-AMBIGUOUS-ARG")
    assert str(amb["severity"]).upper() == "HALT"
