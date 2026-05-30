"""Heuristics N-3, N-5, N-6, N-7 — log conventions.

All thresholds, whitelists, blacklists e nomes especiais vinem de
rules.yaml params. Sem hardcoded.
"""
from __future__ import annotations

import re

from uip_engine._types import Finding


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


def _is_performer_project(pc) -> bool:
    """True se o projeto é um Performer REFramework.

    Primário: project.json.name termina com '_Performer' (canonical Orchestrator
    mapping — name é fonte de verdade, pasta kebab-case não é).
    Fallback estrutural: Framework/Process.xaml E Framework/GetTransactionData.xaml
    existem (esqueleto REFramework Performer; Dispatcher só monta fila, não tem).
    """
    if pc is None:
        return False
    name = (pc.project_json.get("name") or "").strip()
    if name.lower().endswith("_performer"):
        return True
    fw = pc.root / "Framework"
    return (fw / "Process.xaml").is_file() and (fw / "GetTransactionData.xaml").is_file()


def _is_main_entry(fc, pc) -> bool:
    """True se fc é o workflow de entrada (Main) do projeto.

    Fonte de verdade: project.json::main (canonical — Studio aponta o entry
    aqui). Fallback: basename Main.xaml. Identifica o ÚNICO site onde o prefixo
    de log é DERIVADO de TransactionItem.Reference (seed Main→Process). Em todo
    o resto da cadeia o prefixo é HERDADO (propagado como [in_StPrefixoLog])."""
    if pc is None:
        return False
    main_rel = (pc.project_json.get("main") or "Main.xaml").strip().replace("\\", "/")
    try:
        rel = str(fc.path.relative_to(pc.root)).replace("\\", "/")
    except Exception:
        rel = fc.path.name
    return rel.lower() == main_rel.lower()


def detect_n3_log_prefixo(rule, fc, pc):
    """N-3: Workflow na cadeia Process com LogMessage deve declarar e usar
    o argumento de prefixo de log declarado em params.

    Aplica SOMENTE a Performers (Dispatcher monta fila, sem TransactionItem →
    prefixo de Reference não se aplica). Main excluído via exclude_paths +
    applies_to (logs pré-transação não padronizam prefixo)."""
    p = _params(rule)
    excl = _exclude_paths(p)
    prefixo_arg = p.get("prefixo_arg_name") or "in_StPrefixoLog"
    if not _is_performer_project(pc):
        return []
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
            "transaction_var_name": p.get("transaction_var_name") or "TransactionItem",
            "transaction_arg_name": p.get("transaction_arg_name") or "in_TransactionItem",
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

    # Activities cujo PARENT é restrictive collection (sc:BindingList of
    # IfElseIfBlock items, ActivityFunc.Body slot etc.) NAO podem receber
    # Trace como sibling — wrap quebra layout. Exclui da deteccao porque
    # Trace conceitualmente pertence ao BODY interno da activity, nao como
    # sibling externo.
    _EXCLUDE_BY_NAME = exclude_ui | {
        "IfElseIfBlock",  # children of sc:BindingList em IfElseIf collection
    }

    activity_hits: list[tuple[int, str]] = []
    for m in re_ui_activity.finditer(content):
        name = m.group(1)
        if name in _EXCLUDE_BY_NAME:
            continue
        activity_hits.append((m.start(), f"ui:{name}"))
    if re_default_activity is not None:
        for m in re_default_activity.finditer(content):
            activity_hits.append((m.start(), m.group(1)))

    # Detect prefixo arg presence — drives fixer Message template.
    has_prefixo = bool(
        re.search(r'<x:Property\b[^>]*Name="in_StPrefixoLog"', content)
    )

    # Find activity end offset via tag matching (handles self-close + nested).
    # Proximity window measured from END of activity, NOT start — activities
    # com declaracoes inline longas (>1000 chars) tinham falsos positivos.
    def _walk_to_end(start: int, local_name: str) -> int | None:
        # `start` aponta para '<' do open tag.
        # Find end of open tag first.
        i = content.find(">", start)
        if i == -1:
            return None
        if content[i - 1] == "/":
            return i + 1  # self-close
        depth = 1
        cursor = i + 1
        # Match nested <local_name ...> | </local_name>.
        # Negative lookahead `(?![\w.])` evita match `<Assign.To>` /
        # `<Assign.Value>` (qualified properties) como aninhamento.
        open_re = re.compile(rf'<{re.escape(local_name)}(?![\w.])')
        close_re = re.compile(rf'</{re.escape(local_name)}\s*>')
        while depth > 0 and cursor < len(content):
            nxt_o = open_re.search(content, cursor)
            nxt_c = close_re.search(content, cursor)
            if nxt_c is None:
                return None
            if nxt_o is not None and nxt_o.start() < nxt_c.start():
                # nested open — but skip if self-close
                eo = content.find(">", nxt_o.end())
                if eo == -1:
                    return None
                if content[eo - 1] == "/":
                    cursor = eo + 1
                else:
                    depth += 1
                    cursor = eo + 1
            else:
                depth -= 1
                cursor = nxt_c.end()
        return cursor if depth == 0 else None

    for pos, name in activity_hits:
        # Compute end offset of this activity to measure proximity FROM end.
        # Passa QUALIFIED name (ui:MessageBox) — XAML tags são qualified.
        end_off = _walk_to_end(pos, name)
        ref = end_off if end_off is not None else pos
        # Log conta só se estiver DEPOIS do END da activity, dentro da janela.
        if any(0 <= (tp - ref) <= window for tp in trace_positions):
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
        # Skip auto-inserts pelo fixer N-5 (`insert_trace_log`): por construção
        # eles SAO posicionados como next-sibling de activity executable. Se
        # parecem antecipatorios eh because eles foram movidos OR parent layout
        # changed — caso raro, ignorar evita false-positive N-5↔N-10 oscillation.
        is_auto_insert = False
        if is_log:
            tag_src = full
            if 'sap2010:WorkflowViewState.IdRef="LogMessage_Auto_' in tag_src:
                is_auto_insert = True
            elif 'DisplayName="Log Message -' in tag_src or 'DisplayName="Registrar' in tag_src:
                # "Registrar" mantido legacy (XAMLs antigos pre-2026-05); "Log Message -" eh padrao novo
                is_auto_insert = True
        # Update parent frame: handle child arrival
        if stack and not is_qualified:
            parent = stack[-1]
            # ActivityAction body é reativo (Catch/ForEach lambda/etc.) — LogMessage
            # primeiro filho NAO eh antecipatorio, eh logging de reacao ao evento
            # que disparou ActivityAction. Skip N-10 nesse contexto.
            parent_is_reactive = (parent[0] == "ActivityAction")
            if is_log:
                # check predecessor (skip se auto-insert — by-construction OK,
                # ou se parent é ActivityAction reativo)
                if not parent[1] and not is_auto_insert and not parent_is_reactive:
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
# Self-closed LogMessage shape. Retained for reference only — the
# restrictive-parent recorder no longer gates on self-close (both self-closed
# and expanded open+close LogMessage forms are recorded; audit 2026-05-28).
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
        # Record the LogMessage child regardless of self-close (audit 2026-05-28).
        # Previously only the SELF-CLOSED form (`<ui:LogMessage .../>`) was
        # captured, so the EXPANDED open+close form
        # (`<ui:LogMessage ...><ui:LogMessage.Message>...</ui:LogMessage.Message>
        # </ui:LogMessage>` — the traceable form Sicoob prefers for complex VB
        # Message expressions) was silently missed in a restrictive parent,
        # leaking a breaking Studio compile error. Use the offset of the OPEN
        # tag for the finding line in both forms.
        if child_name == "ui:LogMessage":
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

# N-15 FP-reduction (audit 2026-05-28): the single-letter `presente` suffix
# bucket (a/e/i) is inherently ambiguous — most PT-BR words ending in -a/-e/-i
# are NOUNS/adjectives (Conta, Linha, Senha, Base, Chave, Lote, Pagina), not
# present-indicative verbs. Pure terminal-letter matching over-flags them,
# contradicting the rule's stated VERB-only intent. So for the `presente`
# bucket ONLY we additionally require the first word to match a known PT-BR
# verb form (3rd-person present indicative) before flagging. Multi-char
# forbidden buckets (gerundio -ando/-endo/-indo, passado -ou/-eu/-iu/-ei/
# -ava/-ia) stay terminal-letter only — they are unambiguous verb endings.
#
# The verb list mirrors N-13's curated `verbs` (naming.detect_n13_verb_infinitive):
# present-indicative 3rd-person forms that SHOULD be infinitive. Accent-folded +
# lowercased for matching. Drop the presente bucket's noise without losing the
# genuine "Busca dados" / "Atualiza TAG" verb-leading messages.
_N15_PRESENTE_BUCKET = frozenset({"a", "e", "i"})
_N15_KNOWN_VERB_STEMS = frozenset({
    "busca", "atualiza", "carrega", "extrai", "recupera", "verifica",
    "valida", "anexa", "salva", "lista", "obtem", "executa", "envia",
    "cria", "conecta", "calcula", "processa", "trata", "converte",
    "vincula", "captura", "encerra", "inicia", "reinicia", "limpa",
    "recebe", "monta",
})


def _n15_fold_accents(word: str) -> str:
    """Lowercase + strip common PT-BR accents for verb-stem matching."""
    low = word.lower()
    table = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüç",
        "aaaaaeeeeiiiiooooouuuuc",
    )
    return low.translate(table)


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


_RE_LOGMSG_OPEN_DN = re.compile(
    r'<ui:LogMessage\b[^>]*\bDisplayName="([^"]*)"',
    re.DOTALL,
)
_POOR_DN_PATTERNS = [
    re.compile(r'^\s*Trace\s*:'),
    re.compile(r'^\s*Log\s*:'),
    # "Log Message" exact ja em _POOR_DN_EXACT; "Log Message - <empty>" e "Log Message -X"
    # (sem espaco) caem em prefix sem contexto util:
    re.compile(r'^\s*Log Message\s*-\s*$'),  # "Log Message -" ou "Log Message - "
]
_POOR_DN_EXACT = {"Log Message", "Log", "LogMessage", "Message"}


def detect_n17_log_displayname_quality(rule, fc, pc):
    """N-17: LogMessage DisplayName deve ser descritivo (Sicoob convention).

    Falhas:
      - DisplayName igual a default Studio ('Log Message', 'Log', 'LogMessage')
      - Prefix 'Trace:', 'Log -', 'Log:' (template auto-gen herdou DisplayName pobre)
      - Não usa verbo no infinitivo (-ar/-er/-ir) na primeira palavra significativa

    Bom DisplayName: 'Log Message - <contexto>' (convencao Sicoob: ActivityType + contexto).
    """
    content = fc.active_content
    findings = []
    for m in _RE_LOGMSG_OPEN_DN.finditer(content):
        dn = m.group(1).strip()
        if not dn:
            continue
        is_poor = False
        if dn in _POOR_DN_EXACT:
            is_poor = True
        else:
            for pat in _POOR_DN_PATTERNS:
                if pat.match(dn):
                    is_poor = True
                    break
        if not is_poor:
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: DisplayName '{dn[:60]}' nao-descritivo — verbo infinitivo + acao",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


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
                    # `presente` bucket (single-letter a/e/i) over-matches PT-BR
                    # nouns. Require a known verb form before flagging — keeps the
                    # rule's VERB-only intent and kills the noun false positives.
                    if set(suffixes) == _N15_PRESENTE_BUCKET:
                        if _n15_fold_accents(first) not in _N15_KNOWN_VERB_STEMS:
                            continue
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


# ===========================================================================
# N-3B — invoke-binding seed for in_StPrefixoLog (2026-05-28)
# ===========================================================================
#
# Corrected binding-seed model: N-3 cobre DECLARAÇÃO+consumo de in_StPrefixoLog;
# N-3B cobre o VALOR passado nos bindings <ui:InvokeWorkflowFile.Arguments>.
# Dono da transação (Process) deriva [in_TransactionItem.Reference + " - "];
# quem recebe o prefixo herda [in_StPrefixoLog]; vazios ("") são UPGRADED.

# Bloco InvokeWorkflowFile.Arguments (ui-prefixed). Group 1 = inner body.
_RE_INVOKE_ARGS_BLOCK = re.compile(
    r'<ui:InvokeWorkflowFile\.Arguments\s*>(.*?)</ui:InvokeWorkflowFile\.Arguments\s*>',
    re.DOTALL,
)


def _binding_re(arg_name):
    """InArgument binding p/ arg_name, attribute-order agnostic. Captura attrs
    e (forma element-content) o valor interno; forma self-closed não tem valor."""
    return re.compile(
        r'<InArgument\b(?P<attrs>[^>]*?\bx:Key="' + re.escape(arg_name) + r'"[^>]*?)'
        r'(?:/>|>(?P<value>.*?)</InArgument>)',
        re.DOTALL,
    )


def _prefixo_value_is_empty(value):
    """True se o valor do InArgument deve ser UPGRADED (vazio/whitespace/literal).

    `value` é None p/ binding self-closed (sem grupo value), senão o texto raw
    do element-content. Formas vazias: '', whitespace, literal VB `""`,
    entity-encoded, ou <Literal ... Value="" />."""
    if value is None:
        return True
    stripped = value.strip()
    if stripped in ("", '""', '&quot;&quot;', '[""]', '[&quot;&quot;]'):
        return True
    if re.fullmatch(r'<Literal\b[^>]*\bValue=""[^>]*/>', stripped):
        return True
    return False


def _empty_prefixo_binding_sites(content, arg_name, value_expr):
    """Offsets de bindings in_StPrefixoLog (dentro de InvokeWorkflowFile.Arguments)
    cujo valor é vazio/upgradeable e NÃO já == value_expr. A presença do binding
    implica que o callee declara o arg (Studio só serializa binding p/ arg
    declarado), então não é preciso resolver o callee."""
    binding_re = _binding_re(arg_name)
    sites = []
    for block in _RE_INVOKE_ARGS_BLOCK.finditer(content):
        body = block.group(1)
        body_start = block.start(1)
        for bm in binding_re.finditer(body):
            value = bm.group("value")
            if value is not None and value.strip() == value_expr:
                continue  # já correto — idempotente
            if _prefixo_value_is_empty(value):
                sites.append(body_start + bm.start())
    return sites


def _wrong_prefixo_binding_sites(content, arg_name, value_expr):
    """Offsets de bindings in_StPrefixoLog (dentro de InvokeWorkflowFile.Arguments)
    cujo valor NÃO é exatamente value_expr (vazio OU derivação errada OU qualquer
    outro). Política Sicoob da CADEIA (não-Main): só há UM valor legítimo —
    a herança [in_StPrefixoLog]. Tudo diferente é upgradeável (overwrite-always).
    A presença do binding implica que o callee declara o arg."""
    binding_re = _binding_re(arg_name)
    sites = []
    for block in _RE_INVOKE_ARGS_BLOCK.finditer(content):
        body = block.group(1)
        body_start = block.start(1)
        for bm in binding_re.finditer(body):
            value = bm.group("value")
            if value is not None and value.strip() == value_expr:
                continue  # já correto — idempotente
            sites.append(body_start + bm.start())
    return sites


def detect_n3_prefixo_binding(rule, fc, pc):
    """N-3B (modelo Sicoob de propagação): em workflows da CADEIA (NÃO-Main —
    applies_to exclui Main/Tests/Launch), todo binding in_StPrefixoLog dentro de
    <ui:InvokeWorkflowFile.Arguments> deve HERDAR [in_StPrefixoLog].

    Política (3 regras Sicoob):
      1. O prefixo é DERIVADO de TransactionItem.Reference UMA única vez, no seed
         Main→Process (tratado pelo cascade do add_prefixo_arg, escopo do Main —
         único arquivo com `<Variable Name="TransactionItem">`). N-3B NÃO roda no
         Main (applies_to exclui), então nunca toca/sobrescreve o seed.
      2. Process e TODOS os invokes filhos carregam o MESMO prefixo herdado →
         só há um valor legítimo na cadeia: [in_StPrefixoLog]. Qualquer binding
         diferente (vazio, derivação re-feita `[*.Reference + " - "]`, ou outro)
         é upgradeável SEMPRE (overwrite-always) — fixer recebe overwrite=True.

    Emite UM finding por arquivo (fixer faz upgrade de todos os bindings).
    Performer-only. Roda em Framework/Process.xaml (applies_to NÃO exclui
    Framework). A declaração do arg no propagador é coberta pela N-3D.
    """
    p = _params(rule)
    prefixo_arg = p.get("prefixo_arg_name") or "in_StPrefixoLog"

    if not _is_performer_project(pc):
        return []
    # Defesa-em-profundidade: jamais derivar/sobrescrever no Main (seed-owner).
    # applies_to já exclui Main, mas o gate explícito protege contra include solto.
    if _is_main_entry(fc, pc):
        return []

    content = fc.active_content
    if not content or "InvokeWorkflowFile" not in content:
        return []

    value_expr = f"[{prefixo_arg}]"  # CADEIA: sempre herança, nunca derivação
    binding_sites = _wrong_prefixo_binding_sites(content, prefixo_arg, value_expr)
    if not binding_sites:
        return []

    fix_mech_spec = {
        "type": "seed_prefixo_binding",
        "arg_name": prefixo_arg,
        "value_expr": value_expr,
        "mode": "inherit",
        "overwrite": True,  # regra 2: só um valor legítimo na cadeia
    }
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=_line_for(content, binding_sites[0]),
        message=(
            f"{rule.title}: {len(binding_sites)} binding(s) de {prefixo_arg} "
            f"!= {value_expr} em InvokeWorkflowFile.Arguments — propagar herança "
            f"(overwrite)"
        ),
        fix_mechanical=fix_mech_spec,
        fix_prose=(rule.fix or {}).get("prose"),
    )]


def detect_n3c_main_deownership(rule, fc, pc):
    """N-3C: o Main (entry) NÃO pode declarar nem USAR in_StPrefixoLog. O prefixo
    de log só existe em Process + filhos (regra 3 Sicoob). O Main apenas SEMEIA o
    valor no invoke do Process (binding x:Key=in_StPrefixoLog) — isso é mantido.

    Detecta: Main declara `<x:Property Name="in_StPrefixoLog">` OU usa
    `[in_StPrefixoLog + ...]` em alguma LogMessage. Fixer strip_prefixo_from_main
    remove: a declaração, o bloco default `<this:<Class>.in_StPrefixoLog>`, e o
    prefixo das mensagens (`[in_StPrefixoLog + ` → `[`). NÃO toca nos bindings
    `x:Key="in_StPrefixoLog"` (o seed que o Main passa pro Process)."""
    p = _params(rule)
    prefixo_arg = p.get("prefixo_arg_name") or "in_StPrefixoLog"

    if not _is_performer_project(pc):
        return []
    if not _is_main_entry(fc, pc):
        return []

    content = fc.active_content
    if not content:
        return []

    declares = bool(
        re.search(rf'<x:Property\b[^>]*Name="{re.escape(prefixo_arg)}"', content)
    )
    uses_in_msg = f"[{prefixo_arg} + " in content
    if not declares and not uses_in_msg:
        return []

    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=_line_for(content, 0),
        message=(
            f"{rule.title}: Main declara/usa {prefixo_arg} — prefixo de log só "
            f"pertence a Process + filhos (Main apenas semeia o valor)"
        ),
        fix_mechanical={"type": "strip_prefixo_from_main", "prefixo_arg": prefixo_arg},
        fix_prose=(rule.fix or {}).get("prose"),
    )]


def detect_n3d_propagator_declares(rule, fc, pc):
    """N-3D: workflow NÃO-Main que PROPAGA in_StPrefixoLog (tem binding
    x:Key=in_StPrefixoLog em <ui:InvokeWorkflowFile.Arguments>) mas NÃO declara o
    argumento como `<x:Property>` → deve declará-lo. Sem a declaração, o valor de
    propagação `[in_StPrefixoLog]` não compila no escopo do workflow.

    Caso canônico: Framework/Process.xaml (em Framework/, fora do alcance da N-3,
    mas é a RAIZ da cadeia de propagação). Fixer add_prefixo_arg declara o arg +
    cascateia o seed pros callers (Main → deriva de TransactionItem.Reference).
    """
    p = _params(rule)
    prefixo_arg = p.get("prefixo_arg_name") or "in_StPrefixoLog"

    if not _is_performer_project(pc):
        return []
    if _is_main_entry(fc, pc):
        return []

    content = fc.active_content
    if not content or "InvokeWorkflowFile" not in content:
        return []

    declares = bool(
        re.search(rf'<x:Property\b[^>]*Name="{re.escape(prefixo_arg)}"', content)
    )
    if declares:
        return []

    binding_re = _binding_re(prefixo_arg)
    propagates = any(
        binding_re.search(block.group(1))
        for block in _RE_INVOKE_ARGS_BLOCK.finditer(content)
    )
    if not propagates:
        return []

    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=_line_for(content, 0),
        message=(
            f"{rule.title}: propaga {prefixo_arg} a sub-workflows mas não declara "
            f"o argumento — [{prefixo_arg}] não resolve no escopo"
        ),
        fix_mechanical={
            "type": "add_prefixo_arg",
            "prefixo_arg": prefixo_arg,
            "transaction_var_name": p.get("transaction_var_name") or "TransactionItem",
            "transaction_arg_name": p.get("transaction_arg_name") or "in_TransactionItem",
        },
        fix_prose=(rule.fix or {}).get("prose"),
    )]
