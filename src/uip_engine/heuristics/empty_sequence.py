"""Heuristic S-15: empty `<Sequence>` removal com parent-guard.

Empty Sequence (sem children executáveis ou só whitespace) pode ser:
  - Cosmético: `<Sequence>` vazio dentro de outro `<Sequence>` → remover.
  - REQUIRED placeholder: `<If.Else><Sequence /></If.Else>` — parent property
    elements exigem 1 child activity. Remover quebra o parent.

Estratégia: encontrar empty Sequences via regex; pra cada, identificar o
parent imediato via stack-scan; só emitir fix se parent NÃO for required.
"""
from __future__ import annotations

import re
from uip_engine._types import Finding


# Parents onde empty Sequence é REQUIRED placeholder (remoção quebra o parent).
# Lista MINIMAL — só control-flow clássico que exige body activity:
_REQUIRED_PARENTS = frozenset({
    # Classic control flow — Then/Else/Body são exigidos pela activity:
    "If.Then",                    # If sem Then = compile error
    "If.Else",                    # quando presente, exige 1 child (regex_replace
                                  # simples não pode remover If.Else wrapper junto)
    "While.Body", "DoWhile.Body", # loop body required
    "ForEach.Body", "ParallelForEach.Body",
    # TryCatch.Try — Try block sempre tem 1 activity body
    "TryCatch.Try",
    # ActivityFunc/Action quando body é exigido (callback/handler)
    # — geralmente inside lambda Conditions, fica required.
    "ActivityFunc", "ActivityAction",
    # RetryScope: ActivityBody e Condition required (sem condition = retry infinito)
    "ui:RetryScope.ActivityBody", "ui:RetryScope.Condition",
    # FlowDecision: True/False branches required
    "FlowDecision.True", "FlowDecision.False",
    # State machine: structural
    "Transition.Action", "Transition.Condition",
    # Root Activity body
    "Activity",
})

# Parents onde empty Sequence é OPCIONAL (Modern UI, optional handlers).
# Removível auto: If.Else, OnError, TargetAppears, NApplicationCard.Body, etc.
# Não listados explicitamente — caem no else-branch (não required → remove).
# Documentação para audit:
#   - "If.Else" — Else clause é opcional (If pode existir sem Else)
#   - "uix:NCheckAppState.TargetAppears/TargetDisappears" — optional handlers
#   - "uix:NApplicationCard.Body" — body opcional (escopo declarativo só)
#   - "Catch", "Catches" — catch handlers podem ser empty (handler vazio pode
#     ser intencional pra suprimir exception silenciosamente, mas Sequence
#     vazio sem msg/log normalmente é dead code)

_RE_EMPTY_SEQ_LITERAL = re.compile(
    r'<Sequence\b[^>]*?(?:/>|>\s*</Sequence>)',
    re.DOTALL,
)
# Open+close form com possível conteúdo (testado depois por _is_structural_empty)
_RE_SEQ_OPEN_CLOSE = re.compile(
    r'<Sequence\b[^>]*?>(?P<inner>.*?)</Sequence>',
    re.DOTALL,
)
_RE_TAG = re.compile(
    r'<(/?)([A-Za-z_][\w:.\-]*)\b[^>]*?(/?)>',
    re.DOTALL,
)

# Metadata children que NÃO contam como "executable activity":
_RE_METADATA_BLOCKS = [
    re.compile(r'<sap2010:WorkflowViewState\.IdRef\b[^>]*?(?:/>|>.*?</sap2010:WorkflowViewState\.IdRef>)', re.DOTALL),
    re.compile(r'<sap:WorkflowViewStateService\.ViewState\b[^>]*?(?:/>|>.*?</sap:WorkflowViewStateService\.ViewState>)', re.DOTALL),
    re.compile(r'<sap2010:WorkflowViewState\b[^>]*?(?:/>|>.*?</sap2010:WorkflowViewState>)', re.DOTALL),
    re.compile(r'<Sequence\.Variables\b[^>]*?(?:/>|>.*?</Sequence\.Variables>)', re.DOTALL),
    re.compile(r'<sap2010:Annotation\.AnnotationText\b[^>]*?(?:/>|>.*?</sap2010:Annotation\.AnnotationText>)', re.DOTALL),
]


def _is_structural_empty(inner: str) -> bool:
    """True se inner contém só whitespace + metadata blocks (Variables, ViewState).
    Sem activity executável."""
    cleaned = inner
    for pat in _RE_METADATA_BLOCKS:
        cleaned = pat.sub("", cleaned)
    return cleaned.strip() == ""


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _enclosing_parent(content: str, target_start: int) -> str | None:
    """Stack-scan do início até target_start. Retorna nome do parent imediato."""
    stack: list[str] = []
    for m in _RE_TAG.finditer(content[:target_start]):
        is_close = bool(m.group(1))
        name = m.group(2)
        is_self_close = bool(m.group(3))
        if is_close:
            while stack and stack[-1] != name:
                stack.pop()
            if stack:
                stack.pop()
        elif is_self_close:
            continue
        else:
            stack.append(name)
    return stack[-1] if stack else None


def _find_balanced_close(content: str, open_end: int, open_re, close_re) -> int:
    """Encontra `</Sequence>` matching o open em `open_end`, respeitando nesting.
    Retorna posição END do close, ou -1 se não encontrado."""
    depth = 1
    pos = open_end
    while pos < len(content):
        nxt_o = open_re.search(content, pos)
        nxt_c = close_re.search(content, pos)
        if not nxt_c:
            return -1
        # Skip self-close opens
        while nxt_o and nxt_o.group(0).rstrip().endswith("/>") and nxt_o.start() < nxt_c.start():
            pos = nxt_o.end()
            nxt_o = open_re.search(content, pos)
        if nxt_o and nxt_o.start() < nxt_c.start():
            depth += 1
            pos = nxt_o.end()
        else:
            depth -= 1
            if depth == 0:
                return nxt_c.end()
            pos = nxt_c.end()
    return -1


def detect_empty_sequence(rule, fc, pc):
    content = fc.active_content
    findings: list[Finding] = []
    seen_starts: set[int] = set()

    # Pass 1: literal empty (self-close ou whitespace-only inside).
    for m in _RE_EMPTY_SEQ_LITERAL.finditer(content):
        parent = _enclosing_parent(content, m.start())
        if parent in _REQUIRED_PARENTS:
            continue
        seen_starts.add(m.start())
        tag_text = m.group(0)
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path),
            line=_line_for(content, m.start()),
            message=f"{rule.title}: empty Sequence em '{parent}' — removível",
            fix_mechanical={
                "type": "regex_replace",
                "pattern": re.escape(tag_text),
                "replacement": "",
            },
            fix_prose=(rule.fix or {}).get("prose"),
        ))

    # Pass 2: structurally empty (só metadata children dentro).
    open_re = re.compile(r'<Sequence\b[^>]*?>')
    close_re = re.compile(r'</Sequence>')
    for om in open_re.finditer(content):
        if om.start() in seen_starts:
            continue
        if om.group(0).rstrip().endswith("/>"):
            continue
        end = _find_balanced_close(content, om.end(), open_re, close_re)
        if end < 0:
            continue
        # Inner = content from after open to before close.
        close_start = end - len("</Sequence>")
        inner = content[om.end():close_start]
        if not _is_structural_empty(inner):
            continue
        parent = _enclosing_parent(content, om.start())
        if parent in _REQUIRED_PARENTS:
            continue
        full_text = content[om.start():end]
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path),
            line=_line_for(content, om.start()),
            message=f"{rule.title}: structurally empty Sequence em '{parent}' (só metadata)",
            fix_mechanical={
                "type": "regex_replace",
                "pattern": re.escape(full_text),
                "replacement": "",
            },
            fix_prose=(rule.fix or {}).get("prose"),
        ))

    return findings
