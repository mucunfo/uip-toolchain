"""E-1 / E-2 — error-handling anti-patterns atados a falha REAL de producao.

Origem: sustentacao Sicoob (.scripts/sustentacao/data/known_patterns.yaml) — sao
os UNICOS 2 padroes de falha de producao que sao estaticamente detectaveis (as
demais ~7 causas reais sao runtime/UI/externo, fora de analise estatica):

  E-1 (id throw_falha_tecnica_opaca, "Padrao #1"): dentro de um <Catch>, um
      <Throw> que constroi uma exception NOVA a partir de UM unico argumento
      (mensagem) descarta a exception capturada (stack trace + inner). Mascara a
      causa raiz no log → sustentacao perde tempo.

  E-2 (id nre_in_max_retry_check, "Padrao #2"): dentro de um <Catch>, um
      <LogMessage> que acessa `<exc>.Message` sem guard `IsNot Nothing`. Se a var
      for Nothing → NRE no Catch global mascara o erro real e o Job vira Faulted
      em vez de Failed (retried).

DETECCAO-ONLY (sem fixer): reescrever Throw/Catch mecanicamente e' inseguro —
fix_mechanical=None, so' prose explica a correcao manual. Severity WARN
(heuristica + risco de FP nao-trivial). Scope FISICO dentro de <Catch> via
scanner stack-based (regex puro nao escopa <Catch> em XAML serializado) —
espelha detect_s10/detect_n10 (logs.py) + o guard de proximidade do W-2.
"""
from __future__ import annotations

import re

from .._types import Finding


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


_TAG_RE = re.compile(
    r'<(?P<slash>/?)\s*(?P<name>[A-Za-z_][\w:.\-]*)\b(?P<attrs>[^>]*?)(?P<self>/?)>',
    re.DOTALL,
)


def _local_name(qname: str) -> str:
    """`ui:Throw` -> `Throw`; `ui:LogMessage.Message` -> `LogMessage`."""
    return qname.split(":", 1)[-1].split(".", 1)[0]


def _iter_with_catch_scope(content: str):
    """Single-pass stack scanner. Yields (tag_match, name, in_catch) for every
    open/self-close tag (non-comment), where in_catch == an open <Catch> frame is
    on the stack at that point. Pop is tolerant (mirror detect_s10/n10)."""
    comment_re = re.compile(r"<!--.*?-->", re.DOTALL)
    comment_ranges = [(m.start(), m.end()) for m in comment_re.finditer(content)]

    def _in_comment(p_):
        for s, e in comment_ranges:
            if s <= p_ < e:
                return True
        return False

    stack: list[str] = []
    for m in _TAG_RE.finditer(content):
        if _in_comment(m.start()):
            continue
        name = m.group("name")
        if not name or name[0] in "?!":
            continue
        local = _local_name(name)
        if m.group("slash") == "/":
            if stack and stack[-1] == local:
                stack.pop()
            else:
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i] == local:
                        del stack[i:]
                        break
            continue
        in_catch = "Catch" in stack
        yield m, name, in_catch
        if m.group("self") != "/":
            stack.append(local)


def _count_top_level_commas(args: str) -> int:
    """Conta virgulas no nivel TOP — fora de strings (`&quot;` ou raw `"`) e fora
    de parenteses aninhados (ex: in_Config(&quot;a,b&quot;) NAO conta)."""
    depth = 0
    in_str = False
    commas = 0
    i = 0
    n = len(args)
    while i < n:
        if args.startswith("&quot;", i):
            in_str = not in_str
            i += 6
            continue
        c = args[i]
        if c == '"':
            in_str = not in_str
        elif not in_str:
            if c == "(":
                depth += 1
            elif c == ")":
                depth = max(0, depth - 1)
            elif c == "," and depth == 0:
                commas += 1
        i += 1
    return commas


# --- E-1 -------------------------------------------------------------------

# Exception attr value: [ New <Optionally.Qualified>Exception( <args> ) ]
# prefixo opcional p/ casar tanto `Exception` puro quanto `System.Exception`,
# `SystemException`, `BusinessRuleException`, custom `*Exception`.
_E1_NEW_EXC_RE = re.compile(
    r'\[\s*New\s+((?:[A-Za-z_][\w.]*)?Exception)\s*\((?P<args>.*)\)\s*\]',
    re.DOTALL,
)
_E1_EXC_ATTR_RE = re.compile(r'\bException="([^"]*)"', re.DOTALL)


def detect_e1_throw_swallows_inner(rule, fc, pc):
    """E-1: <Throw> dentro de <Catch> com New <T>Exception(<1 arg>) — descarta
    a exception capturada (sem innerException)."""
    if fc.path.suffix.lower() != ".xaml":
        return []
    content = fc.active_content
    if "Throw" not in content or "Catch" not in content:
        return []
    findings: list[Finding] = []
    for m, name, in_catch in _iter_with_catch_scope(content):
        if not in_catch or _local_name(name) != "Throw":
            continue
        am = _E1_EXC_ATTR_RE.search(m.group(0))
        if not am:
            continue
        nm = _E1_NEW_EXC_RE.search(am.group(1))
        if not nm:
            continue
        args = nm.group("args").strip()
        if not args or _count_top_level_commas(args) != 0:
            continue  # vazio, ou 2+ args (innerException preservada) -> OK
        exc_type = nm.group(1)
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=(
                f"{rule.title}: New {exc_type}(<1 arg>) dentro de Catch descarta "
                f"a exception capturada (stack trace + inner perdidos)"
            ),
            fix_mechanical=None,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# --- E-2 -------------------------------------------------------------------

_E2_VAR_MESSAGE_RE = re.compile(r'(?<![\w.])([A-Za-z_]\w*)\.Message\b')
# Alvo: var de exception PASSADA entre workflows (in_/io_), que PODE ser Nothing.
# O `exception`/`ex` LOCAL do <Catch> e' non-null por contrato UiPath (baixo risco
# real de NRE) — NAO e' alvo (era so' ruido: 49 hits, 0 falha real). O Padrao #2
# real (nre_in_max_retry_check) e' in_BusinessException/in_SystemException.Message.
_E2_PASSED_EXC_RE = re.compile(r"(?i)^(?:in|io)_\w*(?:exception|excecao|exceção)\w*$")
_E2_COND_ATTR_RE = re.compile(r'\bCondition="([^"]*)"', re.DOTALL)
_E2_ISNOT_RE = re.compile(r'(?i)([A-Za-z_]\w*)\s+isnot\s+nothing')
_E2_LOG_CLOSE = "</ui:LogMessage>"
# frames que carregam um guard de controle de fluxo via Condition
_E2_COND_FRAMES = frozenset({
    "If", "ElseIf", "IfElseIfBlock", "FlowDecision", "While", "DoWhile",
})


def _e2_guarded_vars(attrs: str) -> set[str]:
    """Vars asseguradas non-null pela Condition de um frame (`<var> IsNot Nothing`)."""
    cm = _E2_COND_ATTR_RE.search(attrs)
    if not cm:
        return set()
    return {g.lower() for g in _E2_ISNOT_RE.findall(cm.group(1))}


def detect_e2_log_message_no_exc_guard(rule, fc, pc):
    """E-2: <LogMessage> usa `<in_*Exception>.Message` (var passada, nullable) sem
    guard `IsNot Nothing` — nem na Condition de um If/FlowDecision/ElseIf envolvente,
    nem inline, nem na proximidade. NRE mascara o erro real (Job vira Faulted em vez
    de Failed-retried). Control-flow-aware: o guard estrutural da REFramework
    (If in_X IsNot Nothing Then log in_X.Message) e' reconhecido e NAO dispara."""
    if fc.path.suffix.lower() != ".xaml":
        return []
    content = fc.active_content
    if "LogMessage" not in content or ".Message" not in content:
        return []

    comment_re = re.compile(r"<!--.*?-->", re.DOTALL)
    comment_ranges = [(mm.start(), mm.end()) for mm in comment_re.finditer(content)]

    def _in_comment(p_):
        return any(s <= p_ < e for s, e in comment_ranges)

    findings: list[Finding] = []
    # stack de frames: (local_name, guarded_vars_set acumulado ate' este frame)
    stack: list[tuple[str, frozenset]] = []
    for m in _TAG_RE.finditer(content):
        if _in_comment(m.start()):
            continue
        name = m.group("name")
        if not name or name[0] in "?!":
            continue
        local = _local_name(name)
        if m.group("slash") == "/":
            if stack and stack[-1][0] == local:
                stack.pop()
            else:
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == local:
                        del stack[i:]
                        break
            continue

        guarded_now = stack[-1][1] if stack else frozenset()
        # LogMessage: avaliar acessos .Message a var passada nao-guardada
        if local == "LogMessage":
            if m.group("self") == "/":
                extent = m.group(0)
            else:
                close = content.find(_E2_LOG_CLOSE, m.end())
                extent = content[m.start(): close] if close != -1 else content[m.start(): m.end() + 2000]
            extent_low = extent.lower()
            seen = set()
            for vm in _E2_VAR_MESSAGE_RE.finditer(extent):
                var = vm.group(1)
                vlow = var.lower()
                if vlow in seen or not _E2_PASSED_EXC_RE.match(var):
                    continue
                seen.add(vlow)
                # guard 1: Condition de frame envolvente (estrutural REFramework)
                if vlow in guarded_now:
                    continue
                # guard 2: inline na propria expr (If(var IsNot Nothing, var.Message,...))
                if f"{vlow} isnot nothing" in extent_low:
                    continue
                findings.append(Finding(
                    rule_id=rule.id, severity=rule.severity, category=rule.category,
                    file=str(fc.path), line=_line_for(content, m.start()),
                    message=(
                        f"{rule.title}: LogMessage usa '{var}.Message' (exception "
                        f"passada, pode ser Nothing) sem guard 'IsNot Nothing' — NRE "
                        f"mascara o erro real (Job vira Faulted em vez de Failed-retried)"
                    ),
                    fix_mechanical=None,
                    fix_prose=(rule.fix or {}).get("prose"),
                ))
                break  # uma finding por LogMessage basta

        if m.group("self") != "/":
            new_guarded = guarded_now
            if local in _E2_COND_FRAMES:
                g = _e2_guarded_vars(m.group("attrs"))
                if g:
                    new_guarded = guarded_now | g
            stack.append((local, frozenset(new_guarded)))
    return findings
