"""Heuristics N-3, N-5, N-6, N-7 — log conventions.

All thresholds, whitelists, blacklists e nomes especiais vinem de
rules.yaml params. Sem hardcoded.
"""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


_RE_LOG_MESSAGE = re.compile(r'<ui:LogMessage\b[^>]*?(/?)>')
# Captura attribute Message="..." dentro do open tag (forma comum).
_RE_LOG_MESSAGE_ATTR = re.compile(r'\bMessage="([^"]*)"')
# Property-element form: <ui:LogMessage>...<ui:LogMessage.Message><InArgument>X</InArgument></ui:LogMessage.Message></ui:LogMessage>
# (raro mas válido). Buscar SOMENTE dentro do escopo do próprio LogMessage.
_RE_LOG_MESSAGE_PE = re.compile(
    r'<ui:LogMessage\.Message\b[^>]*>\s*'
    r'<InArgument\s+x:TypeArguments="x:String"[^>]*>([^<]*)</InArgument>\s*'
    r'</ui:LogMessage\.Message>',
    re.DOTALL,
)
_RE_LOG_MESSAGE_CLOSE = re.compile(r'</ui:LogMessage>')


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _params(rule):
    return rule.detect.get("params", {}) or {}


def _exclude_paths(params):
    return tuple((s or "").lower() for s in (params.get("exclude_paths") or ()))


def _is_in_chain(fc, pc, exclude_paths) -> bool:
    if pc is None:
        return False
    rel = str(fc.path.relative_to(pc.root)).replace("\\", "/").lower()
    if any(seg in rel for seg in exclude_paths):
        return False
    return True


def detect_n3_log_prefixo(rule, fc, pc):
    """N-3: Workflow na cadeia Process com LogMessage deve declarar e usar
    o argumento de prefixo de log declarado em params."""
    p = _params(rule)
    excl = _exclude_paths(p)
    prefixo_arg = p.get("prefixo_arg_name") or "in_StPrefixoLog"
    if not _is_in_chain(fc, pc, excl):
        return []
    content = fc.active_content
    log_matches = list(_RE_LOG_MESSAGE.finditer(content))
    if not log_matches:
        return []
    re_prop_prefixo = re.compile(rf'<x:Property\b[^>]*Name="{re.escape(prefixo_arg)}"')
    has_prefixo = bool(re_prop_prefixo.search(content))
    if not has_prefixo:
        # Path 1 fixer: declare arg + rewrite literal Messages.
        fix_mech_spec = {
            "type": "add_prefixo_arg",
            "prefixo_arg": prefixo_arg,
        }
        return [Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, log_matches[0].start()),
            message=f"{rule.title}: workflow tem LogMessage mas não declara {prefixo_arg}",
            fix_mechanical=fix_mech_spec,
            fix_prose=(rule.fix or {}).get("prose"),
        )]
    findings = []
    for m in log_matches:
        # Open tag: m.group(0) = full open including attributes.
        open_tag = m.group(0)
        is_self_close = m.group(1) == "/"
        msg_text = None

        # Path 1: Message=... attribute em open tag (forma majoritária).
        attr_m = _RE_LOG_MESSAGE_ATTR.search(open_tag)
        if attr_m:
            # XML-unescape básico p/ checagem de prefixo_arg.
            raw = attr_m.group(1)
            msg_text = (raw.replace("&amp;", "&").replace("&lt;", "<")
                        .replace("&gt;", ">").replace("&quot;", '"'))

        # Path 2: property-element <ui:LogMessage.Message><InArgument>X</InArgument>
        # SOMENTE se não self-close E não tem attribute Message=. Lookahead é
        # bounded em </ui:LogMessage> p/ evitar pegar InArgument de PRÓXIMO
        # activity sibling (bug histórico — falso positivo em workflows com
        # `Message="..."` attribute em todos LogMessages).
        if msg_text is None and not is_self_close:
            close_m = _RE_LOG_MESSAGE_CLOSE.search(content, m.end())
            if close_m is not None:
                inner = content[m.end():close_m.start()]
                pe_m = _RE_LOG_MESSAGE_PE.search(
                    open_tag + inner + close_m.group(0)
                )
                if pe_m is not None:
                    raw = pe_m.group(1)
                    msg_text = (raw.replace("&amp;", "&").replace("&lt;", "<")
                                .replace("&gt;", ">").replace("&quot;", '"'))

        # Sem texto recuperável → no flag (LogMessage sem Message= valid? raro).
        if msg_text is None:
            continue
        if prefixo_arg in msg_text:
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: LogMessage não usa {prefixo_arg} na mensagem",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_n5_trace_log_significant(rule, fc, pc):
    """N-5: toda activity executável precisa LogMessage Level=Trace LOGO APÓS.

    Janela é unidirecional: log conta SE estiver depois da activity dentro
    de `proximity_window` chars. Log antes (intenção) NÃO satisfaz — viola
    semântica de rastreabilidade pós-execução.
    """
    p = _params(rule)
    excl = _exclude_paths(p)
    include_defaults = frozenset(p.get("include_default_activities") or ())
    exclude_ui = frozenset(p.get("exclude_ui_activities") or ())
    window = int(p.get("proximity_window") or 600)
    trace_level = p.get("trace_level") or "Trace"

    content = fc.active_content
    findings: list[Finding] = []

    if pc is not None:
        rel = str(fc.path.relative_to(pc.root)).replace("\\", "/").lower()
        if any(seg in rel for seg in excl):
            return []

    re_log_trace = re.compile(rf'<ui:LogMessage\b[^>]*\bLevel="{re.escape(trace_level)}"')
    # Qualified-property elements (<ui:Foo.Bar>) NÃO são activities — são
    # property setters do parent. Excluídos via lookahead (próximo char
    # após o nome local não pode ser ".").
    re_ui_activity = re.compile(r'<ui:([A-Z][A-Za-z0-9]+)(?![A-Za-z0-9.])')
    if include_defaults:
        re_default_activity = re.compile(
            r'<(' + "|".join(re.escape(n) for n in include_defaults) + r')\b'
        )
    else:
        re_default_activity = None

    trace_positions = [m.start() for m in re_log_trace.finditer(content)]

    activity_hits: list[tuple[int, str]] = []
    for m in re_ui_activity.finditer(content):
        name = m.group(1)
        if name in exclude_ui:
            continue
        activity_hits.append((m.start(), f"ui:{name}"))
    if re_default_activity is not None:
        for m in re_default_activity.finditer(content):
            activity_hits.append((m.start(), m.group(1)))

    # Detect prefixo arg presence — drives fixer Message template.
    has_prefixo = bool(
        re.search(r'<x:Property\b[^>]*Name="in_StPrefixoLog"', content)
    )

    for pos, name in activity_hits:
        # Log conta só se estiver DEPOIS da activity, dentro da janela.
        if any(0 < (tp - pos) <= window for tp in trace_positions):
            continue
        line = _line_for(content, pos)
        # Per-finding fix_mechanical spec — drives `insert_trace_log` fixer.
        # Includes activity offset/name so fixer can locate exact element via
        # lxml + walk to its end without re-detecting.
        fix_mech_spec = {
            "type": "insert_trace_log",
            "activity_offset": pos,
            "activity_name": name,
            "activity_line": line,
            "trace_level": trace_level,
            "has_prefixo": has_prefixo,
            "proximity_window": window,
        }
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=line,
            message=f"{rule.title}: '{name}' sem {trace_level} APÓS em até {window} chars",
            fix_mechanical=fix_mech_spec,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# --- N-9 (WARN): LogMessage com mensagem mecânica/genérica (sem contexto)

# Padrões mecânicos típicos gerados por agente/template:
#   "Iniciando: ui:X"  — pré-activity (também viola N-5 ordering, mas N-9 captura mensagem)
#   "Executando ui:X"
#   "Started X"
_RE_LOG_MESSAGE_FULL = re.compile(
    r'<ui:LogMessage\b[^>]*\bMessage="([^"]*)"', re.DOTALL
)

_MECHANICAL_PATTERNS = (
    re.compile(r'Iniciando:\s*ui:[A-Z]', re.IGNORECASE),
    re.compile(r'Executando\s*ui:[A-Z]', re.IGNORECASE),
    re.compile(r'Started\s+ui:', re.IGNORECASE),
    re.compile(r'Iniciando:\s*[A-Za-z][A-Za-z0-9_]*$'),  # "Iniciando: AddDataRow"
    # Padrões antecipatórios genéricos — começam com verbo de intenção
    # (vai fazer X) em vez de descrever resultado (fez X).
    re.compile(r'^\s*\["?[Ii]niciando\b'),
    re.compile(r'^\s*\["?[Ee]xecutando\b'),
    re.compile(r'^\s*\["?[Cc]omeçando\b'),
    re.compile(r'^\s*\["?[Vv]ai\s+(buscar|fazer|chamar|executar|enviar)\b'),
)


# --- N-10 (WARN): LogMessage antecipatório — sem activity executável imediatamente antes
#
# Padrão Sicoob: Activity → Log → Activity → Log. Log POSICIONALMENTE
# documenta a activity que veio JUSTO ANTES (ou no caso do primeiro log
# do Sequence: faz sentido só se descreve estado de entrada, mas via de
# regra deve seguir uma activity).
#
# Caso problema: Log → Activity (sem activity precedendo o Log no mesmo
# escopo). Indica log antecipatório ("vai fazer X") = anti-padrão.

_N10_TAG_RE = re.compile(
    r'<(?P<slash>/?)\s*(?P<name>[A-Za-z_][\w:.\-]*)\b(?P<attrs>[^>]*?)(?P<self>/?)>',
    re.DOTALL,
)

# Activities que NÃO contam como "activity executável precedente" pra
# satisfazer um Log. Containers de fluxo, qualified-properties, comentários,
# o próprio LogMessage, e elementos meta.
_N10_NON_EXECUTABLE_LOCAL = frozenset({
    "LogMessage", "Comment", "CommentOut", "Annotation",
    "Sequence", "Flowchart", "If", "ElseIf", "Switch", "While", "DoWhile",
    "ForEach", "ForEachRow", "ForEachFileX", "Parallel", "ParallelForEach",
    "Pick", "PickBranch", "FlowDecision", "FlowSwitch", "FlowStep",
    "StateMachine", "State", "Transition", "Trigger", "TryCatch", "Catch",
    "Catches", "Finally", "ActivityAction", "ActivityFunc",
    "DelegateInArgument", "DelegateOutArgument",
    "InArgument", "OutArgument", "InOutArgument",
    "Variable", "Property", "Members", "Literal", "Reference",
    "Assign",  # Assign é semântico mas no padrão Sicoob é precedido por Log próprio (debate)
    "Persist", "Receive", "Send", "NoPersistScope", "CompensableActivity",
    "AssignOperation", "FilterOperationArgument",
    "Target", "TargetAnchorable", "TargetApp", "VerifyExecutionOptions",
})


def _n10_local_name(qname: str) -> str:
    return qname.split(":", 1)[-1].split(".", 1)[0]


def _n10_is_qualified_property(name: str) -> bool:
    if "." not in name:
        return False
    local = name.split(":", 1)[-1]
    return "." in local


def _n10_is_executable_activity(name: str) -> bool:
    if not name:
        return False
    local = _n10_local_name(name)
    if local in _N10_NON_EXECUTABLE_LOCAL:
        return False
    if _n10_is_qualified_property(name):
        return False
    # Aceita qualquer Activity com nome PascalCase
    return local[:1].isupper()


def detect_n10_log_anticipatory(rule, fc, pc):
    """N-10: LogMessage sem activity executável como sibling imediatamente antes.

    Para cada `<ui:LogMessage>`, examina o sibling-element anterior no MESMO
    parent. Se sibling anterior NÃO é activity executável (é outro LogMessage,
    qualified-property, ou nada — log é primeiro filho), flag como
    antecipatório.
    """
    p = _params(rule)
    excl = _exclude_paths(p)
    if pc is not None:
        rel = str(fc.path.relative_to(pc.root)).replace("\\", "/").lower()
        if any(seg in rel for seg in excl):
            return []

    content = fc.active_content
    if "<ui:LogMessage" not in content:
        return []

    comment_re = re.compile(r"<!--.*?-->", re.DOTALL)
    comment_ranges = [(m.start(), m.end()) for m in comment_re.finditer(content)]

    def _in_comment(p_):
        for s, e in comment_ranges:
            if s <= p_ < e:
                return True
        return False

    findings: list[Finding] = []
    # frame: [name, last_executable_sibling_seen, log_positions_to_evaluate]
    # for each open we push fresh; on each child element we check if it
    # qualifies as last_executable; for each LogMessage child in this frame
    # we evaluate against current last_executable
    stack: list[list] = []

    for m in _N10_TAG_RE.finditer(content):
        if _in_comment(m.start()):
            continue
        name = m.group("name")
        if not name or name.startswith("?") or name.startswith("!"):
            continue
        slash = m.group("slash")
        self_close = m.group("self")
        full = m.group(0)

        if slash == "/":
            if stack and stack[-1][0] == name:
                stack.pop()
            else:
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == name:
                        del stack[i:]
                        break
            continue

        # Determine if this child is a LogMessage (self-close OR open)
        is_log = name == "ui:LogMessage"
        is_qualified = _n10_is_qualified_property(name)
        # Update parent frame: handle child arrival
        if stack and not is_qualified:
            parent = stack[-1]
            if is_log:
                # check predecessor
                if not parent[1]:
                    log_line = _line_for(content, m.start())
                    fix_mech_spec = {
                        "type": "remove_anticipatory_log",
                        "log_line": log_line,
                        "parent_name": parent[0],
                    }
                    findings.append(Finding(
                        rule_id=rule.id, severity=rule.severity, category=rule.category,
                        file=str(fc.path), line=log_line,
                        message=(
                            f"{rule.title}: LogMessage sem activity executável "
                            f"imediatamente antes (parent='{parent[0]}'). "
                            f"Padrão Sicoob: Activity→Log→Activity→Log; "
                            f"Log→Activity é antecipatório."
                        ),
                        fix_mechanical=fix_mech_spec,
                        fix_prose=(rule.fix or {}).get("prose"),
                    ))
                # log doesn't update last_executable (LogMessage não é activity executável)
            elif _n10_is_executable_activity(name):
                parent[1] = name

        if self_close == "/":
            continue
        # push frame; child's own children get fresh tracking
        stack.append([name, None])

    return findings


def detect_n9_log_message_mechanical(rule, fc, pc):
    """N-9: LogMessage com mensagem mecânica/genérica.

    Logs devem ser contextuais (descrever O QUE aconteceu de relevante,
    com valores reais quando útil). Mensagens template como "Iniciando:
    ui:X" são WARNING — sinalizam logs gerados sem interpretação.
    """
    p = _params(rule)
    excl = _exclude_paths(p)
    if pc is not None:
        rel = str(fc.path.relative_to(pc.root)).replace("\\", "/").lower()
        if any(seg in rel for seg in excl):
            return []
    content = fc.active_content
    findings: list[Finding] = []
    for m in _RE_LOG_MESSAGE_FULL.finditer(content):
        msg = m.group(1)
        # Decode HTML entities mais comuns
        decoded = msg.replace("&quot;", '"').replace("&amp;", "&")
        # tira aspas externas e brackets de bind VB: [&quot;...&quot;]
        text = decoded
        for hit in _MECHANICAL_PATTERNS:
            if hit.search(text):
                findings.append(Finding(
                    rule_id=rule.id, severity=rule.severity, category=rule.category,
                    file=str(fc.path), line=_line_for(content, m.start()),
                    message=f"{rule.title}: mensagem mecânica '{text[:80]}' — substituir por descrição contextual",
                    fix_mechanical=None,
                    fix_prose=(rule.fix or {}).get("prose"),
                ))
                break
    return findings


_RE_INVOKE_OPEN = re.compile(r'<ui:InvokeWorkflowFile[ \t\r\n][^>]*>')


def detect_n6_invoke_log_level(rule, fc, pc):
    """N-6: InvokeWorkflowFile deve ter Level=<canonical_value>."""
    p = _params(rule)
    excl = _exclude_paths(p)
    attr = p.get("level_attribute") or "Level"
    accepted = set(p.get("accepted_values") or ["Info", "[LogLevel.Info]"])
    canonical = p.get("canonical_value") or "Info"

    content = fc.active_content
    findings: list[Finding] = []

    if pc is not None:
        rel = str(fc.path.relative_to(pc.root)).replace("\\", "/").lower()
        if any(seg in rel for seg in excl):
            return []

    for m in _RE_INVOKE_OPEN.finditer(content):
        tag = m.group(0)
        level_match = re.search(rf'\b{re.escape(attr)}="([^"]*)"', tag)
        if not level_match:
            replacement = tag.rstrip(">").rstrip("/").rstrip() + f' {attr}="{canonical}">'
            replacement_safe = replacement.replace("\\", "\\\\")
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, m.start()),
                message=f"{rule.title}: InvokeWorkflowFile sem property {attr} — adicionar {attr}=\"{canonical}\"",
                fix_mechanical={
                    "type": "regex_replace",
                    "pattern": re.escape(tag),
                    "replacement": replacement_safe,
                },
                fix_prose=(rule.fix or {}).get("prose"),
            ))
            continue
        level = level_match.group(1).strip()
        if level in accepted:
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: {attr}=\"{level}\" — esperado \"{canonical}\"",
            fix_mechanical={
                "type": "regex_replace",
                "pattern": rf'(<ui:InvokeWorkflowFile\b[^>]*?)\b{re.escape(attr)}="{re.escape(level)}"',
                "replacement": rf'\1{attr}="{canonical}"',
            },
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# --- S-10 (ERROR breaking): LogMessage em parent que aceita 1 child / collection tipada
#
# Causa raiz histórica: agente aplicou N-5 (Trace log) sem checar contexto.
# Studio falha compile com mensagens como:
#   - "Then property has already been set on If"
#   - "Handler property has already been set on ActivityFunc / ActivityAction"
#   - "Add value to collection of type 'List(AssignOperation)' threw an exception"
#   - "Set property '...Dictionary(...).Value' threw an exception"

_S10_TAG_RE = re.compile(
    r'<(?P<slash>/?)\s*(?P<name>[A-Za-z_][\w:.\-]*)\b(?P<attrs>[^>]*?)(?P<self>/?)>',
    re.DOTALL,
)
_S10_LOG_RE = re.compile(r'<ui:LogMessage\b[^>]*?/>', re.DOTALL)

# Restritivos: tag aceita exatamente 1 filho activity (handler / branch / argument).
_S10_RESTRICTIVE_NAMES = frozenset({"ActivityFunc", "ActivityAction"})

# Sufixos de qualified-property children que aceitam 1 child:
# Ex.: <If.Then>, <If.Else>, <ui:RetryScope.ActivityBody>, <ui:RetryScope.Condition>,
# <ActivityAction.Argument>, <Variable.Default>.
_S10_RESTRICTIVE_DOT_SUFFIXES = frozenset({
    "Then", "Else", "ActivityBody", "Condition", "Handler",
    "Argument", "Default",
})


def _s10_is_restrictive(name: str, attrs: str) -> bool:
    if not name:
        return False
    if name in _S10_RESTRICTIVE_NAMES:
        return True
    if "." in name:
        suffix = name.split(".", 1)[1]
        if suffix in _S10_RESTRICTIVE_DOT_SUFFIXES:
            return True
    if name == "scg:List" and "AssignOperation" in (attrs or ""):
        return True
    if name == "scg:Dictionary":
        return True
    return False


def _s10_is_qualified_property_of(parent_name: str, child_name: str) -> bool:
    """`<Foo.Bar>` é qualified-property de `<Foo>` — meta, não conta como child de conteúdo."""
    if not parent_name or not child_name or "." not in child_name:
        return False
    p_local = parent_name.split(":", 1)[-1]
    c_local = child_name.split(":", 1)[-1]
    if "." not in c_local:
        return False
    c_owner = c_local.split(".", 1)[0]
    return c_owner == p_local


def _s10_is_typed_collection(name: str, attrs: str) -> bool:
    """List<AssignOperation> e Dictionary tipam o tipo de child — LogMessage nunca encaixa."""
    if name == "scg:Dictionary":
        return True
    if name == "scg:List" and "AssignOperation" in (attrs or ""):
        return True
    return False


def detect_s10_logmessage_in_restrictive_parent(rule, fc, pc):
    """S-10: LogMessage filho direto de parent restritivo quebra compile.

    Dois modos:
      A) parent single-child (ActivityFunc/ActivityAction/`*.Then`/`*.Else`/etc.):
         válido se LogMessage é o único child de conteúdo. Erro se há outro sibling.
      B) parent é collection tipada (`scg:List<AssignOperation>`, `scg:Dictionary`):
         qualquer LogMessage é erro de tipo (sempre inválido).
    """
    content = fc.active_content
    if "<ui:LogMessage" not in content:
        return []

    comment_re = re.compile(r"<!--.*?-->", re.DOTALL)
    comment_ranges = [(m.start(), m.end()) for m in comment_re.finditer(content)]

    def _in_comment(p):
        for s, e in comment_ranges:
            if s <= p < e:
                return True
        return False

    findings: list[Finding] = []
    # stack frame: [name, attrs, content_child_count, log_child_positions]
    stack: list[list] = []

    def _record_child(child_name: str, is_self_close: bool, full_tag: str, pos: int):
        if not stack:
            return
        parent = stack[-1]
        parent_name = parent[0]
        parent_attrs = parent[1]
        if _s10_is_qualified_property_of(parent_name, child_name):
            return
        parent[2] += 1
        if child_name == "ui:LogMessage" and is_self_close and _S10_LOG_RE.match(full_tag):
            if _s10_is_restrictive(parent_name, parent_attrs):
                parent[3].append(pos)

    for m in _S10_TAG_RE.finditer(content):
        if _in_comment(m.start()):
            continue
        name = m.group("name")
        if not name or name.startswith("?") or name.startswith("!"):
            continue
        slash = m.group("slash")
        attrs = m.group("attrs")
        self_close = m.group("self")
        full = m.group(0)

        if slash == "/":
            target_idx = None
            if stack and stack[-1][0] == name:
                target_idx = len(stack) - 1
            else:
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == name:
                        target_idx = i
                        break
            if target_idx is None:
                continue
            popped_frames = stack[target_idx:]
            del stack[target_idx:]
            for frame in popped_frames:
                pname, pattrs, child_count, log_positions = frame
                if not log_positions:
                    continue
                if _s10_is_typed_collection(pname, pattrs):
                    for pos in log_positions:
                        findings.append(Finding(
                            rule_id=rule.id, severity=rule.severity, category=rule.category,
                            file=str(fc.path), line=_line_for(content, pos),
                            message=(
                                f"{rule.title}: LogMessage em '{pname}' — collection tipada "
                                f"não aceita LogMessage. Studio falha compile."
                            ),
                            fix_mechanical=None,
                            fix_prose=(rule.fix or {}).get("prose"),
                        ))
                elif child_count > 1:
                    for pos in log_positions:
                        findings.append(Finding(
                            rule_id=rule.id, severity=rule.severity, category=rule.category,
                            file=str(fc.path), line=_line_for(content, pos),
                            message=(
                                f"{rule.title}: LogMessage filho de '{pname}' junto com "
                                f"outro sibling ({child_count} children) — parent aceita 1 child. "
                                f"Studio falha compile. Mover LogMessage pra dentro de Sequence."
                            ),
                            fix_mechanical=None,
                            fix_prose=(rule.fix or {}).get("prose"),
                        ))
            continue

        _record_child(name, bool(self_close), full, m.start())
        if self_close == "/":
            continue
        stack.append([name, attrs, 0, []])

    return findings


def detect_n7_invoke_log_entry_exit(rule, fc, pc):
    """N-7: InvokeWorkflowFile deve declarar attributes em params.expected_attributes."""
    p = _params(rule)
    excl = _exclude_paths(p)
    expected = dict(p.get("expected_attributes") or {})

    content = fc.active_content
    findings: list[Finding] = []

    if pc is not None:
        rel = str(fc.path.relative_to(pc.root)).replace("\\", "/").lower()
        if any(seg in rel for seg in excl):
            return []

    for m in _RE_INVOKE_OPEN.finditer(content):
        tag = m.group(0)
        for attr, exp_val in expected.items():
            attr_match = re.search(rf'\b{re.escape(attr)}="([^"]*)"', tag)
            if not attr_match:
                replacement = tag.rstrip(">").rstrip("/").rstrip() + f' {attr}="{exp_val}">'
                replacement_safe = replacement.replace("\\", "\\\\")
                findings.append(Finding(
                    rule_id=rule.id, severity=rule.severity, category=rule.category,
                    file=str(fc.path), line=_line_for(content, m.start()),
                    message=f"{rule.title}: InvokeWorkflowFile sem {attr} — adicionar {attr}=\"{exp_val}\"",
                    fix_mechanical={
                        "type": "regex_replace",
                        "pattern": re.escape(tag),
                        "replacement": replacement_safe,
                    },
                    fix_prose=(rule.fix or {}).get("prose"),
                ))
                continue
            actual = attr_match.group(1).strip()
            if actual == exp_val:
                continue
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, m.start()),
                message=f"{rule.title}: {attr}=\"{actual}\" — esperado \"{exp_val}\"",
                fix_mechanical={
                    "type": "regex_replace",
                    "pattern": rf'(<ui:InvokeWorkflowFile\b[^>]*?)\b{re.escape(attr)}="{re.escape(actual)}"',
                    "replacement": rf'\1{attr}="{exp_val}"',
                },
                fix_prose=(rule.fix or {}).get("prose"),
            ))

    return findings


# ---------------------------------------------------------------------------
# N-15 — LogMessage com primeiro verbo deve estar no infinitivo
# ---------------------------------------------------------------------------

_RE_LOGMSG_ATTR = re.compile(
    r'<ui:LogMessage\b[^>]*?\bMessage="([^"]*)"',
    re.DOTALL,
)


def _extract_first_word(msg_attr_value: str) -> str | None:
    """Extract first alphabetic word from a Message attr value.

    Returns None if message contains expression concat (`+`), is non-literal,
    or first token is non-alphabetic. Pure literals only.
    """
    s = msg_attr_value.strip()
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    # Decode XML entities first so we can check `+` against decoded form
    s = s.replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&')
    # Reject concatenation (string + expr) — only pure literals allowed
    if '+' in s:
        return None
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    s = s.lstrip(' \t-.:[(>')
    m = re.match(r'([A-Za-zÀ-ÖØ-öø-ÿ]+)', s)
    if not m:
        return None
    return m.group(1)


def detect_n15_log_infinitive(rule, fc, pc):
    """N-15: primeiro verbo de Message de LogMessage deve estar no infinitivo."""
    p = _params(rule)
    excl = _exclude_paths(p)
    if not _is_in_chain(fc, pc, excl):
        return []
    forbidden = p.get("forbidden_suffixes") or {}
    valid = tuple(p.get("valid_suffixes") or ("ar", "er", "ir", "or"))
    skip_words = set(p.get("skip_first_words") or ())
    only_pure = bool(p.get("only_pure_literals", True))

    content = fc.active_content
    findings = []

    for m in _RE_LOGMSG_ATTR.finditer(content):
        msg = m.group(1)
        if only_pure and ('+' in msg):
            continue
        first = _extract_first_word(msg)
        if not first:
            continue
        if first in skip_words:
            continue
        low = first.lower()
        # check valid first
        if any(low.endswith(suf) for suf in valid):
            continue
        violated = None
        for kind, suffixes in forbidden.items():
            for suf in suffixes:
                if low.endswith(suf) and len(low) > len(suf):
                    violated = (kind, suf)
                    break
            if violated:
                break
        if not violated:
            continue
        kind, suf = violated
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: Message inicia com '{first}' ({kind}, sufixo '-{suf}') — usar infinitivo (-ar/-er/-ir)",
            fix_mechanical=None,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
