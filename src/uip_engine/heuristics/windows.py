"""Heuristics for Windows-target rules (W-*)."""
from __future__ import annotations

import re

from uip_engine._types import Finding


_RE_LINQ_ON_ARG = re.compile(
    r'\b(in_\w+|io_\w+)\.(Contains|Any|Where|Select|First|Single|All)\('
)
_RE_SENDMAIL_OPEN = re.compile(r'<ui:SendMail\s[^>]*>')

_RE_ISNULL_INSTANCE = re.compile(
    r'(?<![A-Za-z_:])'
    r'((?:[a-zA-Z_]\w*\.)*[a-zA-Z_]\w*)'
    r'\.(IsNullOrEmpty|IsNullOrWhiteSpace)\b'
)
_RE_TOINT32 = re.compile(
    r'(?<![A-Za-z_:])((?:[a-zA-Z_]\w*\.)*[a-zA-Z_]\w*)\.ToInt32\b'
)
_RE_QUEUE_ITEM_INDEXER = re.compile(
    r'(?<![A-Za-z_:])'
    r'(?P<recv>(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*)'
    r'\.(?P<prop>SpecificContent|Output)'
    r'\s*\(\s*(?P<key>&quot;[^&]+&quot;|"[^"]+")\s*\)'
)
_RE_QUEUE_ITEM_TYPED_NAME = re.compile(
    r'\b(?:Name|x:Key)\s*=\s*"(?P<name>[A-Za-z_]\w*)"[^\n<>]{0,240}'
    r'QueueItem\b'
    r'|QueueItem\b[^\n<>]{0,240}'
    r'\b(?:Name|x:Key)\s*=\s*"(?P<name2>[A-Za-z_]\w*)"',
    re.IGNORECASE,
)
_INVOKE_ARGS_VARIABLE_AND_PROPERTY_RE = re.compile(
    r'<(?P<prefix>[A-Za-z_]\w*):InvokeWorkflowFile(?=[\s/>])'
    r'(?=[^>]*\bArgumentsVariable\s*=\s*"\{x:Null\}")'
    r'[^>]*>'
    r'(?P<body>.*?)'
    r'</(?P=prefix):InvokeWorkflowFile>',
    re.DOTALL,
)
_TERMINAL_VB_LINE_CONTINUATION_RE = re.compile(
    r'(?P<prefix>(?:[ \t\r\n]|&#x(?:A|D|9);|&#(?:10|13|9);)+)'
    r'_'
    r'(?P<suffix>(?:[ \t\r\n]|&#x(?:A|D|9);|&#(?:10|13|9);)*)'
    r'\]'
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _params(rule):
    return rule.detect.get("params", {}) or {}


_HOSTILE_UNICODE_CHARS = "“”‘’\u00a0\u200b\u200c\u200d\ufeff"
_HOSTILE_UNICODE_RE = re.compile(f"[{re.escape(_HOSTILE_UNICODE_CHARS)}]")
_PROTECTED_TEXT_ATTR_RE = re.compile(
    r'(?:[A-Za-z_][\w]*:)?'
    r'(?:DisplayName|AnnotationText|Annotation)\s*=\s*"([^"]*)"'
)


def _protected_text_spans(content: str) -> list[tuple[int, int]]:
    """Attribute value spans intentionally not normalized by W-30 fixer."""
    return [
        (m.start(1), m.end(1)) for m in _PROTECTED_TEXT_ATTR_RE.finditer(content)
    ]


def _offset_in_spans(offset: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= offset < end for start, end in spans)


def _last_segment(chain: str) -> str:
    return chain.rsplit(".", 1)[-1]


def detect_w30_hostile_unicode(rule, fc, pc):
    """W-30: hostile Unicode outside user-facing annotation/display text.

    Must stay in sync with fixers.apply_replace_hostile_unicode_chars: the
    detector only reports chars the deterministic fixer is allowed to mutate.
    """
    content = fc.active_content
    protected = _protected_text_spans(content)
    findings = []
    for m in _HOSTILE_UNICODE_RE.finditer(content):
        if _offset_in_spans(m.start(), protected):
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=rule.title,
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w34_invoke_arguments_variable_duplicate(rule, fc, pc):
    """W-34: `ArgumentsVariable={x:Null}` duplicates Arguments property element.

    UiPath Windows loader treats the legacy `ArgumentsVariable` attribute as the
    same member family as `InvokeWorkflowFile.Arguments`; when both are present,
    analyzer raises XamlDuplicateMemberException for `Arguments`.
    """
    content = fc.active_content
    findings = []
    for m in _INVOKE_ARGS_VARIABLE_AND_PROPERTY_RE.finditer(content):
        prefix = m.group("prefix")
        body = m.group("body")
        if not re.search(
            rf'<{re.escape(prefix)}:InvokeWorkflowFile\.Arguments(?=[\s/>])',
            body,
        ):
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=rule.title,
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w35_terminal_vb_line_continuation(rule, fc, pc):
    """W-35: terminal VB `_` before a closing XAML expression bracket.

    UiPath's Windows compiler reports this as opaque BC30203/BC30198. The
    local source is mechanical: a VB line-continuation marker can continue to
    another token, but not to the end of a bracketed XAML expression.
    """
    content = fc.active_content
    findings = []
    for m in _TERMINAL_VB_LINE_CONTINUATION_RE.finditer(content):
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=_line_for(content, m.start()),
            message=f"{rule.title}: '_' terminal antes de ']'",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def _w2_mechanical_available(arg: str, method: str) -> bool:
    """Mirror de `fixers.apply_guard_linq_arg_ref::_default_for`.
    True quando fixer tem default sensato pra wrap. False = type-dependent,
    fixer skipa (e detector deve emitir fix_mechanical=None).

    Sync OBRIGATÓRIO com fixer — divergência = detector mente sobre o que
    engine pode fixar.
    """
    if method in ("Contains", "Any", "All"):
        return True  # Boolean return, default False sempre safe
    bare = re.sub(r'^(in|io)_', '', arg)
    if bare.startswith('DTab'):
        return False  # DataTable.Select chain — guard parcial mascara erro
    if method == 'AsEnumerable':
        return False
    if bare.startswith('Arr') and method in ('Select', 'Where'):
        return True  # idempotente self-wrap
    return False  # Dict/Lst/etc type-dependent


def detect_w2_linq_no_guard(rule, fc, pc):
    content = fc.active_content
    findings = []
    rule_mech = (rule.fix or {}).get("mechanical")
    for m in _RE_LINQ_ON_ARG.finditer(content):
        arg, method = m.group(1), m.group(2)
        start = max(0, m.start() - 200)
        prefix = content[start:m.start()]
        guarded = (
            f"{arg} Is Nothing" in prefix
            or f"If({arg} Is Nothing" in prefix
            or f"If({arg} IsNot Nothing" in prefix
        )
        if guarded:
            continue
        # Per-finding mech: só se fixer realmente cobre esse caso.
        mech_for_this = rule_mech if _w2_mechanical_available(arg, method) else None
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {arg}.{method}(...) sem guard",
            fix_mechanical=mech_for_this,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w13_sendmail(rule, fc, pc):
    content = fc.active_content
    findings = []
    for m in _RE_SENDMAIL_OPEN.finditer(content):
        if 'UseISConnection="False"' in m.group(0):
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w16_isnullorempty(rule, fc, pc):
    """W-16: `<expr>.IsNullOr*` em VB Windows — usar chamada estática.

    Skip já-correto via params.static_class_names + params.last_segment_skip.
    """
    p = _params(rule)
    static_names = {s.lower() for s in (p.get("static_class_names") or ())}
    skip_last = {s.lower() for s in (p.get("last_segment_skip") or ())}

    content = fc.active_content
    findings = []
    for m in _RE_ISNULL_INSTANCE.finditer(content):
        chain = m.group(1)
        method = m.group(2)
        if chain.lower() in static_names:
            continue
        if _last_segment(chain).lower() in skip_last:
            continue
        # Multi-part chain (obj.Field.IsNullOrEmpty): fixer regex só cobre bare
        # identifier — emitir mech aqui mente sobre auto-fix (silent no-op).
        # Mirror W-12/W-2: route multi-part p/ manual (contextual).
        mech_for_this = None if "." in chain else (rule.fix or {}).get("mechanical")
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {chain}.{method}",
            fix_mechanical=mech_for_this,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


_RE_W12_ARRAYROW = re.compile(r'ArrayRow="\[\{(?!New\s)[^"}]+\}\]"')
_RE_W12_EMPTY = re.compile(r'>\[\{\}\]<|"\[\{\}\]"')
_RE_W12_TYPED_LITERAL = re.compile(r'\[\{(?!New\s)(?P<items>[^<>\r\n]*?)\}\]')
_RE_XTYPE_ARRAY = re.compile(r'\bx:TypeArguments="(?P<type>[^"]+\[\])"')
_RE_W12_TYPED_VBVALUE_EMPTY = re.compile(
    r'<[^<>]*\bx:TypeArguments="[^"]+\[\]"'
    r'[^<>]*\bExpressionText="\{\}\{\}"[^<>]*>'
)
_RE_STRING_FORMAT_TOSTRING_WITH_DELIMITER = re.compile(
    r'(?i)string\.format\([^"\r\n]*(?:"[^"\r\n]*"[^"\r\n]*)*\)'
    r'\)\.ToStringWithDelimiter\(\)'
    r'|(?i:string\.format\([^"\r\n]*(?:"[^"\r\n]*"[^"\r\n]*)*\)'
    r'\.ToStringWithDelimiter\(\))'
)
_RE_READ_AS_DATATABLE_THREE_ARGS = re.compile(
    r'\.ReadAsDataTable\('
    r'(?P<a1>[^(),\r\n]+),'
    r'(?P<a2>[^(),\r\n]+),'
    r'(?P<a3>[^(),\r\n]+)'
    r'\)'
)
_RE_CCS_SIPAGDIRECT_LEGACY_LOGIN = re.compile(
    r'clr-namespace:CCS_SipagDirect\.Sessão;assembly=CCS_SipagDirect'
    r'|<(?P<prefix>[A-Za-z_]\w*):LoginSipagDirect(?=[\s/>])'
)


def _typed_empty_array_mechanical(content: str, start: int) -> dict | None:
    """Return mechanical fix when `[{}]` sits in a typed array context."""
    line_start = content.rfind("\n", 0, start) + 1
    tag_start = content.rfind("<", 0, start)
    if tag_start < line_start:
        tag_start = line_start
    tag_end = content.find(">", start)
    if tag_end < 0:
        tag_end = content.find("\n", start)
    if tag_end < 0:
        tag_end = len(content)
    window = content[tag_start:tag_end + 1]
    if _RE_XTYPE_ARRAY.search(window):
        return {"type": "wrap_typed_empty_array_literal"}
    return None


def _is_arrayrow_literal(content: str, start: int) -> bool:
    prefix = content[max(0, start - 20):start]
    return bool(re.search(r'ArrayRow\s*=\s*"$', prefix))


def detect_w12_array_literal(rule, fc, pc):
    """W-12: array literal sem type explícito.

    Distingue:
      - `ArrayRow="[{a,b}]"` em AddDataRow — wrap mecânico Object().
      - `[{}]` vazio em contexto `x:TypeArguments="T[]"` — wrap mecânico T().
      - `[{}]` vazio sem tipo próximo — manual (precisa context p/ type).

    Emite fix_mechanical apenas quando o tipo pode ser inferido localmente.
    """
    content = fc.active_content
    findings: list[Finding] = []
    mech = (rule.fix or {}).get("mechanical")
    for m in _RE_W12_ARRAYROW.finditer(content):
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: ArrayRow sem tipo — auto-wrap Object()",
            fix_mechanical=mech,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    for m in _RE_W12_EMPTY.finditer(content):
        empty_mech = _typed_empty_array_mechanical(content, m.start())
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=(
                f"{rule.title}: array vazio sem tipo — "
                + ("auto-wrap por x:TypeArguments" if empty_mech else "manual (context-dependent)")
            ),
            fix_mechanical=empty_mech,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    seen_empty_offsets = {m.start() for m in _RE_W12_EMPTY.finditer(content)}
    for m in _RE_W12_TYPED_LITERAL.finditer(content):
        if not m.group("items").strip() or m.start() in seen_empty_offsets or _is_arrayrow_literal(content, m.start()):
            continue
        typed_mech = _typed_empty_array_mechanical(content, m.start())
        if not typed_mech:
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: array tipado sem New T() — auto-wrap por x:TypeArguments",
            fix_mechanical=typed_mech,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    for m in _RE_W12_TYPED_VBVALUE_EMPTY.finditer(content):
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: VisualBasicValue array vazio corrompido — auto-wrap por x:TypeArguments",
            fix_mechanical={"type": "wrap_typed_empty_array_literal"},
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w36_string_format_tostring_with_delimiter(rule, fc, pc):
    """W-36: `(String.Format(...)).ToStringWithDelimiter()` no longer compiles.

    Activity Migrator/Windows compiler treats the receiver as String and
    raises BC30456. In this selector pattern the legacy call is a no-op.
    """
    content = fc.active_content
    findings = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        if "ToStringWithDelimiter()" not in line:
            continue
        if not re.search(r'(?i)string\.format\(', line):
            continue
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=line_no,
            message=f"{rule.title}: String.Format(...).ToStringWithDelimiter()",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w37_read_as_datatable_three_args(rule, fc, pc):
    """W-37: UiPath.Excel 3.x ReadAsDataTable requires 5 arguments."""
    content = fc.active_content
    findings = []
    for m in _RE_READ_AS_DATATABLE_THREE_ARGS.finditer(content):
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=_line_for(content, m.start()),
            message=f"{rule.title}: ReadAsDataTable com 3 argumentos",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w38_ccs_sipagdirect_legacy_login(rule, fc, pc):
    """W-38: CCS_SipagDirect 3.x exposes Login, not Sessão.LoginSipagDirect."""
    content = fc.active_content
    findings = []
    for m in _RE_CCS_SIPAGDIRECT_LEGACY_LOGIN.finditer(content):
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=_line_for(content, m.start()),
            message=f"{rule.title}: namespace/activity legacy CCS_SipagDirect",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
        break
    return findings


_RE_OCRENGINE_EMPTY = re.compile(
    r'<uix:NApplicationCard\.OCREngine>\s*'
    r'<ActivityFunc\b[^>]*>\s*'
    r'(?:<ActivityFunc\.Argument>\s*<DelegateInArgument\b[^>]*/?>\s*</ActivityFunc\.Argument>\s*)*'
    r'</ActivityFunc>\s*'
    r'</uix:NApplicationCard\.OCREngine>',
    re.DOTALL,
)


def detect_ocr1_empty_engine(rule, fc, pc):
    """OCR-1: NApplicationCard.OCREngine com ActivityFunc body vazio.

    Detecta apenas placeholders Migrator-injetados (sem activity OCR concreto
    dentro). Workflows com engine explícito preservados.
    """
    content = fc.active_content
    findings = []
    for m in _RE_OCRENGINE_EMPTY.finditer(content):
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=(
                f"{rule.title}: OCREngine sem activity concreto — "
                "Studio analyzer falha 'OCR Engine must be set'"
            ),
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_w17_toint32(rule, fc, pc):
    """W-17: `<expr>.ToInt32` em VB Windows — usar `Convert.ToInt32(<expr>)`."""
    p = _params(rule)
    static_names = {s.lower() for s in (p.get("static_class_names") or ())}
    skip_last = {s.lower() for s in (p.get("last_segment_skip") or ())}

    content = fc.active_content
    findings = []
    for m in _RE_TOINT32.finditer(content):
        chain = m.group(1)
        if chain.lower() in static_names:
            continue
        if _last_segment(chain).lower() in skip_last:
            continue
        # Multi-part chain (obj.Field.ToInt32): fixer regex só cobre bare
        # identifier — emitir mech aqui mente sobre auto-fix (silent no-op).
        # Mirror W-12/W-2: route multi-part p/ manual (contextual).
        mech_for_this = None if "." in chain else (rule.fix or {}).get("mechanical")
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {chain}.ToInt32",
            fix_mechanical=mech_for_this,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def _queue_item_names(content: str) -> set[str]:
    names = {
        "TransactionItem",
        "in_TransactionItem",
        "io_TransactionItem",
        "out_TransactionItem",
    }
    for m in _RE_QUEUE_ITEM_TYPED_NAME.finditer(content):
        name = m.group("name") or m.group("name2")
        if name:
            names.add(name)
    return names


def _is_safe_queue_item_receiver(receiver: str, queue_names: set[str]) -> bool:
    # Keep this intentionally conservative. Chained receivers are only safe
    # when the last segment is a known QueueItem-shaped variable name.
    last = receiver.rsplit(".", 1)[-1]
    return (
        receiver in queue_names
        or last in queue_names
        or last.endswith("TransactionItem")
        or last.endswith("QueueItem")
    )


def detect_w19_queue_item_indexer(rule, fc, pc):
    """W-19: SpecificContent/Output indexer rewrite only when receiver is safe.

    The old regex detector offered the mechanical fix for every
    `.SpecificContent("x")` shape. That can be wrong when the receiver is not
    a UiPath QueueItem, so ambiguous findings are reported without
    fix_mechanical and become contextual notes instead of deploy blockers.
    """
    content = fc.active_content
    queue_names = _queue_item_names(content)
    rule_mech = (rule.fix or {}).get("mechanical")
    findings = []
    for m in _RE_QUEUE_ITEM_INDEXER.finditer(content):
        receiver = m.group("recv")
        safe = _is_safe_queue_item_receiver(receiver, queue_names)
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=_line_for(content, m.start()),
            message=(
                f"{rule.title}: {receiver}."
                f"{m.group('prop')}({m.group('key')})"
                + ("" if safe else " (receiver não tipado como QueueItem)")
            ),
            fix_mechanical=rule_mech if safe else None,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# UI-7: Simulate InteractionMode → DelayBefore/After devem ser 0
#
# Detecta activities UIA com `InteractionMode="Simulate"` que tenham
# `DelayBefore` ou `DelayAfter` definidos com valor != 0. Simulate é
# background-capable; delays só fazem sentido em HardwareEvents.

_RE_UIA_ACTIVITY = re.compile(
    r'<(uix?|uia):([A-Za-z][\w]*)\b([^>]*?)/?>', re.DOTALL
)
_RE_ATTR_KV = re.compile(r'\b([A-Za-z_][\w]*)\s*=\s*"([^"]*)"')


def _is_zero_delay(value: str) -> bool:
    """True se valor é '0', '[0]', '0.0', '[0.0]' (Double zero)."""
    if value is None:
        return True
    v = value.strip()
    if not v:
        return True
    # Strip outer [...] bind expression
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1].strip()
    # Numeric zero literal
    try:
        return float(v) == 0.0
    except ValueError:
        return False


def _is_numeric_delay(value: str) -> bool:
    """True se valor é literal numérico reducível (`500`, `[500]`, `0.0`).

    False p/ binding expression VB não-reducível (`[in_Config(...)]`),
    `{x:Null}`, ou qualquer coisa que float() não consegue avaliar. Nesses
    casos force-"0" determinístico apagaria valor config-bound — deve ser
    contextual (humano decide).
    """
    if value is None:
        return False
    v = value.strip()
    if not v:
        return False
    # Strip outer [...] bind expression (mirror _is_zero_delay)
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1].strip()
    try:
        float(v)
        return True
    except ValueError:
        return False


def detect_ui7_simulate_delays(rule, fc, pc):
    """UI-7: activities UIA com InteractionMode=Simulate + DelayBefore/After != 0.

    Emite 1 finding por (activity, attr) violador. fix_mechanical scope-strict
    via apply_force_attribute_in_activity_with_guard.
    """
    if fc.path.suffix.lower() != ".xaml":
        return []
    content = fc.active_content or ""
    findings = []
    for m in _RE_UIA_ACTIVITY.finditer(content):
        prefix = m.group(1)
        local = m.group(2)
        body = m.group(3) or ""
        attrs = {am.group(1): am.group(2) for am in _RE_ATTR_KV.finditer(body)}
        mode = (attrs.get("InteractionMode") or "").strip()
        if mode != "Simulate":
            continue
        line = _line_for(content, m.start())
        for delay_attr in ("DelayBefore", "DelayAfter"):
            if delay_attr not in attrs:
                continue
            if _is_zero_delay(attrs[delay_attr]):
                continue
            # Só force-"0" determinístico p/ literal numérico não-zero.
            # Binding expression não-reducível (`[in_Config(...)]`) ou
            # `{x:Null}` => contextual (fix_mechanical=None): force-"0"
            # apagaria valor config-bound (data loss). Humano decide.
            if _is_numeric_delay(attrs[delay_attr]):
                fix_mech = {
                    "type": "force_attribute_in_activity_with_guard",
                    "prefix": prefix,
                    "activity_local": local,
                    "guard_attr": "InteractionMode",
                    "guard_value": "Simulate",
                    "attr_name": delay_attr,
                    "target_value": "0",
                    "tag_line": line,
                }
            else:
                fix_mech = None
            findings.append(Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=line,
                message=(
                    f"{rule.title}: <{prefix}:{local}> "
                    f'InteractionMode="Simulate" mas '
                    f'{delay_attr}="{attrs[delay_attr]}" (esperado 0)'
                ),
                fix_mechanical=fix_mech,
                fix_prose=(rule.fix or {}).get("prose"),
            ))
    return findings
