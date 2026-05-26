"""F38 — XAML DOM helpers: lxml-find + byte-surgical insert.

Hybrid strategy:
  - lxml usado pra parse + find target activity element (robust XML query)
  - Inserção via byte-level manipulation no raw_bytes original (preserva
    formatting byte-exato fora da janela de mutação)

Reason: lxml `tostring()` normaliza attribute order, xmlns position,
self-closing forms → bytes não-idênticos ao source mesmo sem mutations.
XAML Studio é case-sensitive sobre xmlns position + mc:Ignorable position;
byte-surgical evita riscos analyzer cache invalidation pós-fix.

API public:
  parse_and_find_target(path, idref) → (raw_bytes, target_info | None)
  insert_xml_after_target(raw_bytes, target_info, xml_snippet, marker_text) → bytes
  has_marker_near_target(raw_bytes, target_info, marker_text, window_chars=600) → bool
  validate_xml(raw_bytes) → bool  (re-parse sanity)

Reusable: outros fixers estruturais (N-10, etc.) usam mesma infra.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import lxml.etree as etree


# Namespaces canônicos UiPath / XAML 2009. Importável por fixers.
NAMESPACES = {
    "x": "http://schemas.microsoft.com/winfx/2006/xaml",
    "sap2010": "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation",
    "sap": "http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation",
    "ui": "http://schemas.uipath.com/workflow/activities",
    "scg": "clr-namespace:System.Collections.Generic;assembly=mscorlib",
    "default": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
}

UTF8_BOM = b"\xef\xbb\xbf"

ATTR_IDREF = f"{{{NAMESPACES['sap2010']}}}WorkflowViewState.IdRef"


class XamlParseError(Exception):
    """Raised when XAML cannot be parsed via lxml (malformed XML)."""


@dataclass(frozen=True)
class TargetInfo:
    """Localização byte-exact de uma activity no raw XAML.

    - `idref`: IdRef value matched (ou None se localized via line fallback)
    - `tag_localname`: localname do elemento (ex: 'Assign', 'LogMessage')
    - `start_byte`: offset do `<` de opening tag em raw_bytes
    - `end_byte`: offset DEPOIS do `>` final (incluindo `/>` self-close OU
      `</tag>` close tag). Próxima inserção começa em `end_byte`.
    - `line`: linha sourceline (1-indexed) de start_byte
    - `indent`: whitespace prefix da linha de start_byte (replicado no
      insert pra match visual)
    """
    idref: Optional[str]
    tag_localname: str
    start_byte: int
    end_byte: int
    line: int
    indent: str


def detect_bom(raw_bytes: bytes) -> bool:
    return raw_bytes.startswith(UTF8_BOM)


def _strip_bom(raw_bytes: bytes) -> tuple[bytes, bool]:
    if detect_bom(raw_bytes):
        return raw_bytes[len(UTF8_BOM):], True
    return raw_bytes, False


def validate_xml(raw_bytes: bytes) -> bool:
    """Re-parse raw bytes via lxml; True se well-formed.

    Usado pós-insert pra detectar XAML corrupto (gate antes de write).
    """
    body, _ = _strip_bom(raw_bytes)
    parser = etree.XMLParser(
        remove_blank_text=False, resolve_entities=False,
        strip_cdata=False, remove_comments=False,
    )
    try:
        etree.fromstring(body, parser)
        return True
    except etree.XMLSyntaxError:
        return False


def _localname(tag: str | type) -> str:
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag.split(":")[-1]


def _qualified_localname_from_source(elem: etree._Element, raw_body: bytes) -> str:
    """Retrieve the local tag name as it appears in source (with prefix).

    Ex: elem.tag = '{http://schemas.uipath.com/workflow/activities}LogMessage'
    Source: `<ui:LogMessage ...>`
    Return: 'ui:LogMessage'

    Read source-line bytes diretamente pra extrair o prefix-com-localname
    exato (evita assumir prefix da nossa NAMESPACES table).
    """
    sl = elem.sourceline
    if sl is None or sl <= 0:
        return _localname(elem.tag)
    # Find line start
    line_start = _byte_offset_for_line(raw_body, sl)
    if line_start < 0:
        return _localname(elem.tag)
    # Match `<prefix:localname` ou `<localname` no início (após whitespace)
    tail = raw_body[line_start:line_start + 200]
    m = re.search(rb"<\s*([A-Za-z_][\w]*(?::[A-Za-z_][\w.]*)?)\b", tail)
    if m:
        try:
            return m.group(1).decode("utf-8", errors="replace")
        except Exception:
            pass
    return _localname(elem.tag)


def _byte_offset_for_line(raw_body: bytes, line: int) -> int:
    """Returns byte offset do início da linha N (1-indexed) em raw_body.
    -1 se line out of range.
    """
    if line < 1:
        return -1
    if line == 1:
        return 0
    nl_count = 0
    for i, b in enumerate(raw_body):
        if b == 0x0A:  # '\n'
            nl_count += 1
            if nl_count == line - 1:
                return i + 1
    return -1


def _line_indent(raw_body: bytes, line_start: int) -> str:
    """Whitespace prefix (spaces/tabs) começando em line_start."""
    end = line_start
    while end < len(raw_body) and raw_body[end] in (0x20, 0x09):  # space, tab
        end += 1
    return raw_body[line_start:end].decode("utf-8", errors="replace")


def _find_element_end_byte(
    raw_body: bytes,
    start_byte: int,
    tag_with_prefix: str,
) -> int:
    """Find byte offset DEPOIS do final tag/close de um element começando
    em start_byte.

    Estratégia:
      1. Find primeiro `>` ou `/>` após start_byte. Se self-closing (`/>`),
         retorna offset + 2 (depois de '/>').
      2. Senão, buscar `</tag_with_prefix>` matching, contando nesting
         (depth count) pra ignorar nested same-tag elements.

    Returns -1 se não encontra (XAML malformed).
    """
    # Step 1: find end of opening tag
    pos = start_byte
    depth = 0
    in_attr = False
    while pos < len(raw_body):
        c = raw_body[pos:pos + 1]
        if c == b'"':
            in_attr = not in_attr
            pos += 1
            continue
        if not in_attr:
            if raw_body[pos:pos + 2] == b"/>":
                return pos + 2
            if c == b">":
                # Opening tag closed; need to find matching close tag.
                opening_end = pos + 1
                # Scan forward counting `<tag>` opens + `</tag>` closes.
                # Negative lookahead `(?!\.)` evita matchar property elements
                # tipo `<Assign.To>` (property syntax XAML usa `.` separator
                # entre tag e property name; aquele NÃO é nested Assign).
                # Followed by `\b` então também não bate `<AssignSomething`.
                tag_re = re.escape(tag_with_prefix.encode("utf-8"))
                open_pat = re.compile(rb"<\s*" + tag_re + rb"(?![.\w])")
                close_pat = re.compile(rb"</\s*" + tag_re + rb"\s*>")
                depth = 1
                scan = opening_end
                while scan < len(raw_body):
                    # Find next either open or close
                    m_open = open_pat.search(raw_body, scan)
                    m_close = close_pat.search(raw_body, scan)
                    if m_close is None:
                        return -1
                    if m_open is not None and m_open.start() < m_close.start():
                        # Need to ensure m_open is actually a new opening (not
                        # closing). Already filtered by pattern (no `/`).
                        # But also check it ends with `/>` (self-close = no
                        # increment).
                        # Move past the opening tag's own `>` or `/>`.
                        tag_end = _find_tag_close(raw_body, m_open.start())
                        if tag_end < 0:
                            return -1
                        if raw_body[tag_end - 2:tag_end] != b"/>":
                            depth += 1
                        scan = tag_end
                    else:
                        depth -= 1
                        if depth == 0:
                            return m_close.end()
                        scan = m_close.end()
                return -1
        pos += 1
    return -1


def _find_tag_close(raw_body: bytes, start_byte: int) -> int:
    """Returns offset DEPOIS do `>` ou `/>` que fecha o tag começando em
    start_byte. -1 se malformed.
    """
    pos = start_byte
    in_attr = False
    while pos < len(raw_body):
        c = raw_body[pos:pos + 1]
        if c == b'"':
            in_attr = not in_attr
            pos += 1
            continue
        if not in_attr:
            if raw_body[pos:pos + 2] == b"/>":
                return pos + 2
            if c == b">":
                return pos + 1
        pos += 1
    return -1


def parse_and_find_target(
    path: Path,
    idref: Optional[str] = None,
    line: Optional[int] = None,
) -> tuple[bytes, Optional[TargetInfo]]:
    """Parse XAML via lxml + locate target activity.

    `idref` ou `line` deve ser fornecido (idref preferido — mais robusto).

    Returns (raw_bytes_INCLUDING_BOM, TargetInfo | None).

    raw_bytes preserva BOM se presente — caller passa pra
    `insert_xml_after_target` que retorna bytes mutados igualmente preservando.
    """
    raw_bytes = path.read_bytes()
    body, has_bom = _strip_bom(raw_bytes)
    parser = etree.XMLParser(
        remove_blank_text=False, resolve_entities=False,
        strip_cdata=False, remove_comments=False,
    )
    try:
        root = etree.fromstring(body, parser)
    except etree.XMLSyntaxError as e:
        raise XamlParseError(f"{path}: {e}") from e

    # Find element
    target: Optional[etree._Element] = None
    if idref:
        for elem in root.iter():
            if not isinstance(elem.tag, str):
                continue
            if elem.get(ATTR_IDREF) == idref:
                target = elem
                break
    if target is None and line is not None and line > 0:
        # Nearest-prev sourceline match
        exact = None
        nearest = None
        nearest_line = 0
        for elem in root.iter():
            if not isinstance(elem.tag, str):
                continue
            sl = elem.sourceline
            if sl is None:
                continue
            if sl == line:
                exact = elem
                break
            if sl < line and sl > nearest_line:
                nearest = elem
                nearest_line = sl
        target = exact if exact is not None else nearest

    if target is None:
        return raw_bytes, None

    # Compute byte-positions
    sl = target.sourceline or 1
    bom_off = len(UTF8_BOM) if has_bom else 0
    line_start_in_body = _byte_offset_for_line(body, sl)
    if line_start_in_body < 0:
        return raw_bytes, None
    indent = _line_indent(body, line_start_in_body)

    # Find `<` byte starting target (skip indent)
    start_in_body = line_start_in_body + len(indent.encode("utf-8"))
    if start_in_body >= len(body) or body[start_in_body:start_in_body + 1] != b"<":
        # sourceline aponta linha sem `<` no início — fallback: search forward
        nxt = body.find(b"<", line_start_in_body)
        if nxt < 0:
            return raw_bytes, None
        start_in_body = nxt

    # Find tag-with-prefix (`ui:LogMessage` style or `Assign` bare)
    tag_with_prefix = _qualified_localname_from_source(target, body)
    end_in_body = _find_element_end_byte(body, start_in_body, tag_with_prefix)
    if end_in_body < 0:
        return raw_bytes, None

    info = TargetInfo(
        idref=target.get(ATTR_IDREF),
        tag_localname=_localname(target.tag),
        start_byte=bom_off + start_in_body,
        end_byte=bom_off + end_in_body,
        line=sl,
        indent=indent,
    )
    return raw_bytes, info


def insert_xml_after_target(
    raw_bytes: bytes,
    target: TargetInfo,
    xml_snippet: str,
    marker_text: str,
) -> bytes:
    """Insere `<!-- marker_text -->\\n<indent><xml_snippet>` IMEDIATAMENTE
    após target.end_byte em raw_bytes.

    Layout pós-insert:
        <original-content-up-to-target.end_byte>
        \\n<target.indent><!-- marker_text -->
        \\n<target.indent><xml_snippet>
        <original-content-from-target.end_byte>

    Idempotência: caller responsável (use `has_marker_near_target` antes).

    Returns mutated raw_bytes. Caller chama `validate_xml` pra sanity check.
    """
    indent = target.indent
    insertion = (
        f"\n{indent}<!-- {marker_text} -->"
        f"\n{indent}{xml_snippet}"
    ).encode("utf-8")
    return raw_bytes[:target.end_byte] + insertion + raw_bytes[target.end_byte:]


def has_marker_near_target(
    raw_bytes: bytes,
    target: TargetInfo,
    marker_text: str,
    window_chars: int = 600,
) -> bool:
    """True se `<!-- marker_text -->` aparece em raw_bytes nos próximos
    window_chars bytes após target.end_byte.

    Idempotency check pra fixer — evita dup-insert se já aplicado em run
    anterior.
    """
    needle = f"<!-- {marker_text} -->".encode("utf-8")
    snippet = raw_bytes[target.end_byte:target.end_byte + window_chars]
    return needle in snippet


def has_trace_log_near_target(
    raw_bytes: bytes,
    target: TargetInfo,
    window_chars: int = 600,
) -> bool:
    """True se `<ui:LogMessage Level="Trace"` aparece nos próximos
    window_chars bytes após target.end_byte.

    Detecta Trace LogMessage manual pré-existente (engine não dup-insert
    se manual Trace já cobre o gap). Pattern is lenient — match qualquer
    prefix XML ns + Level=Trace attribute.
    """
    snippet = raw_bytes[target.end_byte:target.end_byte + window_chars].decode(
        "utf-8", errors="replace"
    )
    # Pattern: <prefix:LogMessage ... Level="Trace" ...
    return bool(re.search(
        r'<[A-Za-z_][\w]*:LogMessage\b[^>]*?\bLevel\s*=\s*"Trace"',
        snippet,
    ))


def build_logmessage_snippet(
    message_expr: str,
    display_name: str = "Log Message (engine-generated)",
    level: str = "Trace",
) -> str:
    """Build text XML `<ui:LogMessage ... />` pra insert.

    `message_expr` é a VB expression bruta (e.g., `[\"Started \" & vId]`).
    Engine escapa aspas duplas internas → `&quot;`.

    Returns single-line XML string (sem leading/trailing whitespace).
    """
    msg_escaped = (
        message_expr.replace("&", "&amp;")
                    .replace('"', "&quot;")
                    .replace("<", "&lt;")
    )
    dn_escaped = (
        display_name.replace("&", "&amp;")
                    .replace('"', "&quot;")
                    .replace("<", "&lt;")
    )
    return (
        f'<ui:LogMessage DisplayName="{dn_escaped}" '
        f'Level="{level}" Message="{msg_escaped}" />'
    )
