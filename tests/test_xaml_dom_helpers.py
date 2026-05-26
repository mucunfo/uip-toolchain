"""F38 — xaml_dom helpers: parse + byte-surgical insert.

Coverage:
  - BOM detection + preservation
  - parse_and_find_target via IdRef
  - parse_and_find_target via line fallback
  - Element end-byte detection: self-close, explicit close, nested same-tag
  - insert_xml_after_target: byte-exact insertion, preserve surroundings
  - has_marker_near_target idempotency
  - has_trace_log_near_target detection of manual Trace
  - build_logmessage_snippet: escapes correctly
  - validate_xml: rejects malformed
"""
from __future__ import annotations

from pathlib import Path

import pytest

from uip_engine._helpers.xaml_dom import (
    UTF8_BOM,
    detect_bom,
    parse_and_find_target,
    insert_xml_after_target,
    has_marker_near_target,
    has_trace_log_near_target,
    build_logmessage_snippet,
    validate_xml,
    XamlParseError,
    TargetInfo,
)


_XAML_TEMPLATE = (
    '<Activity mc:Ignorable="sap sap2010" x:Class="X" '
    'xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation" '
    'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
    'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
    '  <Sequence DisplayName="Main">\n'
    '{body}'
    '  </Sequence>\n'
    '</Activity>\n'
)


def _write_xaml(tmp_path: Path, body: str, name: str = "Test.xaml",
                bom: bool = False) -> Path:
    content = _XAML_TEMPLATE.format(body=body).encode("utf-8")
    if bom:
        content = UTF8_BOM + content
    p = tmp_path / name
    p.write_bytes(content)
    return p


# ---- BOM detection -----------------------------------------------------

def test_detect_bom_present():
    assert detect_bom(UTF8_BOM + b"<x/>") is True


def test_detect_bom_absent():
    assert detect_bom(b"<x/>") is False


# ---- Find by IdRef -----------------------------------------------------

def test_find_target_by_idref_self_close(tmp_path):
    body = (
        '    <ui:LogMessage sap2010:WorkflowViewState.IdRef="Log_1" '
        'DisplayName="Log A" Level="Info" Message="[&quot;hello&quot;]" />\n'
    )
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="Log_1")
    assert target is not None
    assert target.idref == "Log_1"
    assert target.tag_localname == "LogMessage"
    # end_byte points DEPOIS de "/>"
    assert raw[target.end_byte - 2:target.end_byte] == b"/>"


def test_find_target_by_idref_with_explicit_close(tmp_path):
    body = (
        '    <Assign sap2010:WorkflowViewState.IdRef="Assign_1" '
        'DisplayName="A">\n'
        '      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v]</OutArgument></Assign.To>\n'
        '      <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>\n'
        '    </Assign>\n'
    )
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="Assign_1")
    assert target is not None
    assert target.tag_localname == "Assign"
    # end_byte points DEPOIS de "</Assign>"
    assert raw[target.end_byte - len(b"</Assign>"):target.end_byte] == b"</Assign>"


def test_find_target_idref_not_found(tmp_path):
    body = '    <Assign sap2010:WorkflowViewState.IdRef="X_1" />\n'
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="NONEXISTENT")
    assert target is None


# ---- Find by line ------------------------------------------------------

def test_find_target_by_line_exact(tmp_path):
    body = (
        '    <Assign DisplayName="A" />\n'
        '    <Assign DisplayName="B" />\n'
    )
    p = _write_xaml(tmp_path, body)
    # Line 10 should hit second Assign (after 8 header lines + Sequence + first Assign)
    raw, target = parse_and_find_target(p, line=10)
    assert target is not None
    assert target.tag_localname == "Assign"


def test_find_target_idref_takes_precedence_over_line(tmp_path):
    body = (
        '    <Assign sap2010:WorkflowViewState.IdRef="A_1" DisplayName="A" />\n'
        '    <Assign sap2010:WorkflowViewState.IdRef="A_2" DisplayName="B" />\n'
    )
    p = _write_xaml(tmp_path, body)
    # IdRef A_2 hits line ~10; if idref provided, line ignored
    raw, target = parse_and_find_target(p, idref="A_1", line=99)
    assert target.idref == "A_1"


# ---- Nested same-tag end detection ------------------------------------

def test_find_end_byte_nested_same_tag(tmp_path):
    body = (
        '    <Sequence sap2010:WorkflowViewState.IdRef="Outer_1" DisplayName="Outer">\n'
        '      <Sequence DisplayName="Inner">\n'
        '        <Assign DisplayName="X" />\n'
        '      </Sequence>\n'
        '    </Sequence>\n'
    )
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="Outer_1")
    assert target is not None
    # end_byte should point after the OUTER </Sequence>, not inner
    closing = b"</Sequence>"
    assert raw[target.end_byte - len(closing):target.end_byte] == closing
    # And there should be NO more </Sequence> after target.end_byte
    # (project-level Sequence closure is the only one remaining)
    remaining = raw[target.end_byte:]
    # Count exactly 1 remaining </Sequence> (the wrapper Main)
    assert remaining.count(b"</Sequence>") == 1


# ---- Indent detection -------------------------------------------------

def test_indent_detected_correctly(tmp_path):
    body = '        <Assign sap2010:WorkflowViewState.IdRef="A_1" />\n'
    p = _write_xaml(tmp_path, body)
    _, target = parse_and_find_target(p, idref="A_1")
    assert target.indent == "        "  # 8 spaces


# ---- Insert ------------------------------------------------------------

def test_insert_xml_after_target_preserves_surroundings(tmp_path):
    body = (
        '    <Assign sap2010:WorkflowViewState.IdRef="A_1" DisplayName="A" />\n'
        '    <Assign sap2010:WorkflowViewState.IdRef="A_2" DisplayName="B" />\n'
    )
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="A_1")
    snippet = build_logmessage_snippet('["test"]', display_name="trace")
    mutated = insert_xml_after_target(raw, target, snippet, "engine-trace:N-5")

    # Original bytes 0..target.end_byte preserved
    assert mutated[:target.end_byte] == raw[:target.end_byte]
    # Original bytes from target.end_byte onwards still present after insertion
    inserted_len = len(mutated) - len(raw)
    assert mutated[target.end_byte + inserted_len:] == raw[target.end_byte:]
    # Marker present
    assert b"<!-- engine-trace:N-5 -->" in mutated
    # ui:LogMessage present
    assert b"<ui:LogMessage" in mutated
    # Still well-formed
    assert validate_xml(mutated) is True


def test_insert_uses_target_indent(tmp_path):
    body = '      <Assign sap2010:WorkflowViewState.IdRef="A_1" />\n'  # 6 spaces
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="A_1")
    snippet = build_logmessage_snippet('["x"]')
    mutated = insert_xml_after_target(raw, target, snippet, "marker")

    # New lines should start with 6 spaces (same as target)
    inserted = mutated[target.end_byte:target.end_byte + 200].decode("utf-8")
    assert "\n      <!-- marker -->" in inserted
    assert "\n      <ui:LogMessage" in inserted


# ---- BOM preservation -------------------------------------------------

def test_bom_preserved_through_insert(tmp_path):
    body = '    <Assign sap2010:WorkflowViewState.IdRef="A_1" />\n'
    p = _write_xaml(tmp_path, body, bom=True)
    raw, target = parse_and_find_target(p, idref="A_1")
    assert raw.startswith(UTF8_BOM)
    snippet = build_logmessage_snippet('["x"]')
    mutated = insert_xml_after_target(raw, target, snippet, "marker")
    assert mutated.startswith(UTF8_BOM)
    assert validate_xml(mutated) is True


# ---- Idempotency markers ----------------------------------------------

def test_has_marker_near_target_finds_post_insert(tmp_path):
    body = '    <Assign sap2010:WorkflowViewState.IdRef="A_1" />\n'
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="A_1")
    snippet = build_logmessage_snippet('["x"]')
    mutated = insert_xml_after_target(raw, target, snippet, "engine-trace:N-5")
    # Re-find target in mutated (start_byte unchanged since insertion was AFTER)
    _, target2 = parse_and_find_target(tmp_path / "Test.xaml", idref="A_1")  # not yet written
    # Easier: test directly with mutated bytes by manually reconstructing TargetInfo
    # — has_marker_near_target uses target.end_byte relative to passed bytes.
    assert has_marker_near_target(mutated, target, "engine-trace:N-5") is True


def test_has_marker_absent_when_unmarked(tmp_path):
    body = '    <Assign sap2010:WorkflowViewState.IdRef="A_1" />\n'
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="A_1")
    assert has_marker_near_target(raw, target, "engine-trace:N-5") is False


def test_has_trace_log_detected(tmp_path):
    body = (
        '    <Assign sap2010:WorkflowViewState.IdRef="A_1" />\n'
        '    <ui:LogMessage Level="Trace" Message="[&quot;x&quot;]" />\n'
    )
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="A_1")
    assert has_trace_log_near_target(raw, target) is True


def test_has_trace_log_absent_when_only_info(tmp_path):
    body = (
        '    <Assign sap2010:WorkflowViewState.IdRef="A_1" />\n'
        '    <ui:LogMessage Level="Info" Message="[&quot;x&quot;]" />\n'
    )
    p = _write_xaml(tmp_path, body)
    raw, target = parse_and_find_target(p, idref="A_1")
    assert has_trace_log_near_target(raw, target) is False


# ---- Snippet builder --------------------------------------------------

def test_build_snippet_escapes_double_quotes():
    snippet = build_logmessage_snippet('["hello \\"world\\""]')
    assert '&quot;' in snippet
    assert '"hello' not in snippet  # raw double-quote inside attr value escaped


def test_build_snippet_includes_level_trace_default():
    snippet = build_logmessage_snippet('["x"]')
    assert 'Level="Trace"' in snippet


def test_build_snippet_custom_display_name():
    snippet = build_logmessage_snippet('["x"]', display_name="MyTrace")
    assert 'DisplayName="MyTrace"' in snippet


def test_build_snippet_escapes_ampersand():
    snippet = build_logmessage_snippet('["a & b"]')
    assert '&amp;' in snippet


# ---- validate_xml -----------------------------------------------------

def test_validate_xml_accepts_well_formed():
    assert validate_xml(b'<x><y/></x>') is True


def test_validate_xml_rejects_malformed():
    assert validate_xml(b'<x><y></x>') is False


def test_validate_xml_strips_bom():
    assert validate_xml(UTF8_BOM + b'<x/>') is True


# ---- Real Sicoob XAML round-trip --------------------------------------

def test_real_xaml_parse_and_find_via_idref():
    """Smoke test: real project XAML parses + IdRef lookup works."""
    real = Path(
        r"C:\Users\lisan\Desktop\temp\contestacao-de-compras-ajuste-na-reserva-de-fraude-performer"
        r"\Framework\InitAllApplications.xaml"
    )
    if not real.is_file():
        pytest.skip("real test project not available")
    raw, _ = parse_and_find_target(real, idref="NONEXISTENT_IDREF")
    # Just verify parse succeeds + raw bytes returned
    assert len(raw) > 100
    assert validate_xml(raw) is True


# ---- Parse errors -----------------------------------------------------

def test_parse_error_on_malformed(tmp_path):
    p = tmp_path / "bad.xaml"
    p.write_bytes(b'<Activity><unclosed>')
    with pytest.raises(XamlParseError):
        parse_and_find_target(p, idref="X")
