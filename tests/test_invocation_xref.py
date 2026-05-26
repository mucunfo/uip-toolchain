"""Tests for invocation_xref — caller/arg-type cross-reference scanner.

Module under test: :mod:`scripts.rule_engine.invocation_xref`.

The scanner walks a UiPath project, finds every
``<ui:InvokeWorkflowFile WorkflowFileName="...">`` activity, and (when
the resolved path matches a given target XAML) records the invocation
site along with the per-argument type declarations.

Test layers:
  - Unit tests for path normalisation, arg extraction, majority vote.
  - Integration tests on synthetic tmp_path projects.
  - One smoke test on a real Sicoob project (skipped if not present).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts.rule_engine.invocation_xref import (
    CallerSite,
    InvocationArg,
    dump_arg_to_xaml,
    extract_invoke_args,
    find_callers,
    infer_arg_type_from_callers,
    normalize_workflow_ref,
)


# ---------------------------------------------------------------------------
# XAML scaffolding helpers
# ---------------------------------------------------------------------------

# Minimal valid UiPath-style XAML with all the namespace prefixes the
# scanner expects. Body is `{body}` placeholder.
_XAML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010" x:Class="Caller"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
  xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
  xmlns:sd="clr-namespace:System.Data;assembly=System.Data.Common"
  xmlns:ui="http://schemas.uipath.com/workflow/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Root">
{body}
  </Sequence>
</Activity>
"""


def _write_xaml(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_XAML_TEMPLATE.format(body=body), encoding="utf-8")


def _write_target_stub(path: Path) -> None:
    """Write a minimal valid target XAML (no body needed — only existence
    + path matters for the scanner)."""
    _write_xaml(path, "    <Sequence DisplayName='Target'/>")


def _invoke_block(workflow_ref: str, args_xml: str = "") -> str:
    """Build an ``<ui:InvokeWorkflowFile>`` block with optional args."""
    if args_xml:
        return (
            f'    <ui:InvokeWorkflowFile DisplayName="Sub" '
            f'WorkflowFileName="{workflow_ref}">\n'
            f'      <ui:InvokeWorkflowFile.Arguments>\n'
            f'{args_xml}\n'
            f'      </ui:InvokeWorkflowFile.Arguments>\n'
            f'    </ui:InvokeWorkflowFile>'
        )
    return (
        f'    <ui:InvokeWorkflowFile DisplayName="Sub" '
        f'WorkflowFileName="{workflow_ref}"/>'
    )


# ===========================================================================
# normalize_workflow_ref
# ===========================================================================


def test_normalize_workflow_ref_relative(tmp_path):
    """``WorkflowFileName`` is *project-root-relative* in UiPath.

    Caller at ``Process/Main.xaml`` referencing ``Sub\\Foo.xaml``
    resolves to ``<project_root>/Sub/Foo.xaml`` — NOT
    ``Process/Sub/Foo.xaml``. (Verified against Studio-emitted
    real-world XAMLs.)
    """
    project_root = tmp_path / "P"
    caller_dir = project_root / "Process"
    caller_dir.mkdir(parents=True)
    resolved = normalize_workflow_ref(
        "Sub\\Foo.xaml", caller_dir, project_root,
    )
    expected = (project_root / "Sub" / "Foo.xaml").resolve()
    assert resolved == expected


def test_normalize_handles_backslash(tmp_path):
    """Forward-slash and backslash separators normalise identically."""
    project_root = tmp_path / "P"
    caller_dir = project_root / "Process"
    caller_dir.mkdir(parents=True)
    a = normalize_workflow_ref("Sub/Foo.xaml", caller_dir, project_root)
    b = normalize_workflow_ref("Sub\\Foo.xaml", caller_dir, project_root)
    assert a == b


def test_normalize_strips_leading_dotslash(tmp_path):
    """`./Foo.xaml` resolves the same as `Foo.xaml`."""
    project_root = tmp_path / "P"
    caller_dir = project_root / "X"
    caller_dir.mkdir(parents=True)
    a = normalize_workflow_ref("./Foo.xaml", caller_dir, project_root)
    b = normalize_workflow_ref("Foo.xaml", caller_dir, project_root)
    assert a == b


def test_normalize_empty_returns_empty_path(tmp_path):
    """Empty ref returns Path() (defensive)."""
    assert normalize_workflow_ref("", tmp_path, tmp_path) == Path()


# ===========================================================================
# extract_invoke_args
# ===========================================================================


def test_extract_invoke_args_parses_typeArguments():
    """Synthetic invoke block with InArgument + OutArgument + InOutArgument
    should yield three InvocationArg entries with correct fields."""
    xml = """
<ui:InvokeWorkflowFile xmlns:ui="http://schemas.uipath.com/workflow/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
  xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
  WorkflowFileName="Sub\\Foo.xaml">
  <ui:InvokeWorkflowFile.Arguments>
    <InArgument x:TypeArguments="x:String" x:Key="in_StPrefixoLog">[in_StPrefixoLog]</InArgument>
    <InArgument x:TypeArguments="scg:Dictionary(x:String, x:String)" x:Key="in_Config">[in_Config]</InArgument>
    <OutArgument x:TypeArguments="x:Int32" x:Key="out_Count">[vCount]</OutArgument>
    <InOutArgument x:TypeArguments="x:String" x:Key="io_Status">[vStatus]</InOutArgument>
  </ui:InvokeWorkflowFile.Arguments>
</ui:InvokeWorkflowFile>
""".strip()
    elem = ET.fromstring(xml)
    args = extract_invoke_args(elem)
    assert len(args) == 4

    by_name = {a.name: a for a in args}
    assert by_name["in_StPrefixoLog"].type_str == "InArgument(x:String)"
    assert by_name["in_StPrefixoLog"].direction == "In"
    assert by_name["in_StPrefixoLog"].raw_value == "[in_StPrefixoLog]"

    assert (
        by_name["in_Config"].type_str
        == "InArgument(scg:Dictionary(x:String, x:String))"
    )
    assert by_name["out_Count"].direction == "Out"
    assert by_name["out_Count"].type_str == "OutArgument(x:Int32)"
    assert by_name["io_Status"].direction == "InOut"
    assert by_name["io_Status"].type_str == "InOutArgument(x:String)"


def test_extract_invoke_args_empty_block():
    """Invoke without Arguments block returns empty tuple."""
    xml = (
        '<ui:InvokeWorkflowFile '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
        'WorkflowFileName="Foo.xaml"/>'
    )
    elem = ET.fromstring(xml)
    assert extract_invoke_args(elem) == ()


def test_extract_invoke_args_skips_unkeyed():
    """Argument elements lacking x:Key are silently skipped (defensive)."""
    xml = """
<ui:InvokeWorkflowFile xmlns:ui="http://schemas.uipath.com/workflow/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
  WorkflowFileName="Foo.xaml">
  <ui:InvokeWorkflowFile.Arguments>
    <InArgument x:TypeArguments="x:String">[anon]</InArgument>
    <InArgument x:TypeArguments="x:String" x:Key="named">[v]</InArgument>
  </ui:InvokeWorkflowFile.Arguments>
</ui:InvokeWorkflowFile>
""".strip()
    elem = ET.fromstring(xml)
    args = extract_invoke_args(elem)
    assert len(args) == 1
    assert args[0].name == "named"


# ===========================================================================
# find_callers
# ===========================================================================


def test_find_callers_simple(tmp_path):
    """B invokes A → find_callers(A) returns 1 CallerSite pointing at B."""
    project_root = tmp_path / "P"
    target = project_root / "Sub" / "A.xaml"
    caller = project_root / "B.xaml"

    _write_target_stub(target)
    _write_xaml(caller, _invoke_block("Sub\\A.xaml"))

    callers = find_callers(target, project_root)
    assert len(callers) == 1
    assert callers[0].file.resolve() == caller.resolve()
    assert callers[0].target_workflow == "Sub\\A.xaml"


def test_find_callers_no_callers_returns_empty(tmp_path):
    """Target with no callers in project → empty list."""
    project_root = tmp_path / "P"
    target = project_root / "Sub" / "Lonely.xaml"
    _write_target_stub(target)
    # Add an unrelated XAML that invokes something else.
    other = project_root / "Other.xaml"
    _write_xaml(other, _invoke_block("DoesNotExist.xaml"))

    assert find_callers(target, project_root) == []


def test_find_callers_extracts_args(tmp_path):
    """Caller with declared args populates CallerSite.args."""
    project_root = tmp_path / "P"
    target = project_root / "Sub" / "A.xaml"
    caller = project_root / "B.xaml"

    _write_target_stub(target)
    args_xml = (
        '        <InArgument x:TypeArguments="x:String" '
        'x:Key="in_StPrefixoLog">""</InArgument>\n'
        '        <InArgument x:TypeArguments="scg:Dictionary(x:String, x:Object)" '
        'x:Key="in_Config">[in_Config]</InArgument>'
    )
    _write_xaml(caller, _invoke_block("Sub\\A.xaml", args_xml))

    callers = find_callers(target, project_root)
    assert len(callers) == 1
    site = callers[0]
    arg_by_name = {a.name: a for a in site.args}
    assert arg_by_name["in_StPrefixoLog"].type_str == "InArgument(x:String)"
    assert (
        arg_by_name["in_Config"].type_str
        == "InArgument(scg:Dictionary(x:String, x:Object))"
    )


def test_find_callers_self_reference_skipped(tmp_path):
    """A workflow invoking itself does not appear as its own caller."""
    project_root = tmp_path / "P"
    target = project_root / "Self.xaml"
    body = _invoke_block("Self.xaml")
    _write_xaml(target, body)

    callers = find_callers(target, project_root)
    # Self-reference is filtered out.
    assert all(c.file.resolve() != target.resolve() for c in callers)


def test_find_callers_skips_dynamic_workflow_file_name(tmp_path):
    """`WorkflowFileName="[expr]"` (VB binding) cannot resolve statically."""
    project_root = tmp_path / "P"
    target = project_root / "Sub" / "A.xaml"
    caller = project_root / "B.xaml"
    _write_target_stub(target)
    _write_xaml(caller, _invoke_block("[in_DynamicPath]"))
    assert find_callers(target, project_root) == []


def test_find_callers_line_number(tmp_path):
    """CallerSite.line aligns with the regex-located opening tag."""
    project_root = tmp_path / "P"
    target = project_root / "A.xaml"
    caller = project_root / "B.xaml"
    _write_target_stub(target)
    _write_xaml(caller, _invoke_block("A.xaml"))

    callers = find_callers(target, project_root)
    assert len(callers) == 1
    # The template has 11 header lines before the body insertion point;
    # we don't assert an exact value (depends on template), only that
    # it's > 0 and refers to the InvokeWorkflowFile region.
    assert callers[0].line > 0
    raw = caller.read_text(encoding="utf-8").splitlines()
    assert "InvokeWorkflowFile" in raw[callers[0].line - 1]


def test_find_callers_multiple_invocations_same_file(tmp_path):
    """A single caller invoking the same target twice yields 2 sites."""
    project_root = tmp_path / "P"
    target = project_root / "A.xaml"
    caller = project_root / "B.xaml"
    _write_target_stub(target)
    body = _invoke_block("A.xaml") + "\n" + _invoke_block("A.xaml")
    _write_xaml(caller, body)

    callers = find_callers(target, project_root)
    assert len(callers) == 2
    assert {c.file.resolve() for c in callers} == {caller.resolve()}


def test_find_callers_tolerates_malformed_xaml(tmp_path):
    """Malformed XAML in the tree is skipped — does not crash scan."""
    project_root = tmp_path / "P"
    target = project_root / "A.xaml"
    good_caller = project_root / "Good.xaml"
    bad = project_root / "Bad.xaml"

    _write_target_stub(target)
    _write_xaml(good_caller, _invoke_block("A.xaml"))
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("<not valid xml InvokeWorkflowFile", encoding="utf-8")

    callers = find_callers(target, project_root)
    assert len(callers) == 1
    assert callers[0].file.resolve() == good_caller.resolve()


# ===========================================================================
# Skipped directories
# ===========================================================================


def test_skip_BeforeMigration_dirs(tmp_path):
    """A stale invocation living inside ``_BeforeMigration_*`` is not
    counted as a caller. Activity Migrator backups would otherwise
    massively inflate the caller list with obsolete pre-migration
    copies of the same workflow."""
    project_root = tmp_path / "P"
    target = project_root / "A.xaml"
    live = project_root / "Live.xaml"
    backup = project_root / "_BeforeMigration_2026-05-20T10" / "Stale.xaml"

    _write_target_stub(target)
    _write_xaml(live, _invoke_block("A.xaml"))
    # Backup XAML uses the same project-root-relative ref → WOULD match
    # the target if not skipped. The skip is what makes this test pass.
    _write_xaml(backup, _invoke_block("A.xaml"))

    callers = find_callers(target, project_root)
    assert len(callers) == 1
    assert callers[0].file.resolve() == live.resolve()


def test_skip_tmp_dirs(tmp_path):
    """Files under ``.tmp/`` are not scanned (engine intermediates)."""
    project_root = tmp_path / "P"
    target = project_root / "A.xaml"
    live = project_root / "Live.xaml"
    tmp_file = project_root / ".tmp" / "ghost.xaml"

    _write_target_stub(target)
    _write_xaml(live, _invoke_block("A.xaml"))
    _write_xaml(tmp_file, _invoke_block("A.xaml"))

    callers = find_callers(target, project_root)
    assert len(callers) == 1
    assert callers[0].file.resolve() == live.resolve()


# ===========================================================================
# infer_arg_type_from_callers — majority vote
# ===========================================================================


def _site_with_args(args: list[InvocationArg]) -> CallerSite:
    return CallerSite(
        file=Path("dummy.xaml"),
        line=1,
        target_workflow="Sub/A.xaml",
        args=tuple(args),
    )


def test_majority_vote_resolves_ambiguity():
    """Three callers: 2 declare ``InArgument(x:String)``, 1 declares
    ``InArgument(x:Object)`` → majority returns the String form."""
    callers = [
        _site_with_args([
            InvocationArg("in_X", "InArgument(x:String)", "In"),
        ]),
        _site_with_args([
            InvocationArg("in_X", "InArgument(x:String)", "In"),
        ]),
        _site_with_args([
            InvocationArg("in_X", "InArgument(x:Object)", "In"),
        ]),
    ]
    assert (
        infer_arg_type_from_callers("in_X", callers)
        == "InArgument(x:String)"
    )


def test_single_caller_unambiguous():
    """A single observation is a strict majority → returned."""
    callers = [
        _site_with_args([
            InvocationArg("in_Config", "InArgument(x:String)", "In"),
        ]),
    ]
    assert (
        infer_arg_type_from_callers("in_Config", callers)
        == "InArgument(x:String)"
    )


def test_no_callers_returns_none():
    """Empty caller list → None."""
    assert infer_arg_type_from_callers("anything", []) is None


def test_arg_not_present_returns_none():
    """Callers exist but none declare the requested arg → None."""
    callers = [
        _site_with_args([
            InvocationArg("in_Other", "InArgument(x:String)", "In"),
        ]),
    ]
    assert infer_arg_type_from_callers("in_Missing", callers) is None


def test_tie_returns_none():
    """50/50 split is NOT a strict majority → None (caller decides)."""
    callers = [
        _site_with_args([
            InvocationArg("in_X", "InArgument(x:String)", "In"),
        ]),
        _site_with_args([
            InvocationArg("in_X", "InArgument(x:Object)", "In"),
        ]),
    ]
    assert infer_arg_type_from_callers("in_X", callers) is None


# ===========================================================================
# dump_arg_to_xaml
# ===========================================================================


def test_dump_arg_to_xaml_basic():
    """Round-trip: an InvocationArg with simple type emits the canonical
    ``<x:Property Name=... Type=... />`` form."""
    arg = InvocationArg("in_Config", "InArgument(x:String)", "In")
    rendered = dump_arg_to_xaml(arg)
    assert rendered == (
        '<x:Property Name="in_Config" Type="InArgument(x:String)" />'
    )


def test_dump_arg_to_xaml_generic_type():
    """Generic type (Dictionary) emitted as-is — XAML uses `(`/`)` not
    `<`/`>` for generics, so no escaping disrupts it."""
    arg = InvocationArg(
        "in_Config",
        "InArgument(scg:Dictionary(x:String, x:Object))",
        "In",
    )
    rendered = dump_arg_to_xaml(arg)
    assert "Dictionary(x:String, x:Object)" in rendered
    assert rendered.startswith('<x:Property Name="in_Config"')


# ===========================================================================
# Real-project smoke
# ===========================================================================


_REAL_PROJECT = Path(
    r"C:\Users\lisan\Desktop\temp\contestacao-de-compras-ajuste-na-reserva-de-fraude"
    r"\contestacao-de-compras-ajuste-na-reserva-de-fraude-performer"
)
_REAL_TARGET = _REAL_PROJECT / "Arquivos" / "CriaRelatorioSaida.xaml"


@pytest.mark.skipif(
    not _REAL_TARGET.exists(),
    reason="Real Sicoob project not present on this machine",
)
def test_smoke_real_project():
    """Smoke test against the real ``contestacao`` performer project.

    ``Arquivos/CriaRelatorioSaida.xaml`` is invoked from at least one
    framework workflow (typically ``Framework/Process.xaml`` or the
    main flow). We assert >= 1 caller and that args are extracted.
    """
    callers = find_callers(_REAL_TARGET, _REAL_PROJECT)
    assert len(callers) >= 1, (
        f"Expected at least one caller of {_REAL_TARGET.name} in the "
        f"real performer project, got 0"
    )
    # The standard ``in_Config`` argument should be declared by callers.
    inferred = infer_arg_type_from_callers("in_Config", callers)
    # If we have callers AND they declare in_Config, we should get a
    # majority type (the Sicoob convention is consistent).
    if any(a.name == "in_Config" for c in callers for a in c.args):
        assert inferred is not None
        assert "Dictionary" in inferred or "Argument" in inferred
