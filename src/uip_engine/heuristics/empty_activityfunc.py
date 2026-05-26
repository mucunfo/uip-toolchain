"""S-18 detector — ActivityFunc body vazio em property .OCREngine/.CVEngine.

Background:
  Properties Modern UI como `<uix:NApplicationCard.OCREngine>` recebem
  `<ActivityFunc>` callback. Studio Activity Migrator pos Legacy→Windows
  deixa ActivityFunc com SOMENTE `<ActivityFunc.Argument>` (DelegateInArgument
  placeholder) sem activity child — placeholder XAML.

  Build Studio falha: `OCR Engine must be set` / `CV Engine must be set`.
  Causa: parent NApplicationCard exige factory que produza OCR/CV activity
  ao executar; ActivityFunc body vazio = factory retorna null.

  Fix obrigatório: plug activity OCR/CV no body. Sicoob default =
  `<p1:UiPathScreenOCR Image="[Image]" ... />` (pacote uipath.ocr.activities,
  pin D-1k = 3.22.0).

Detector strategy:
  Scan content. Para cada propriedade `<...:Foo.{OCREngine|CVEngine}>`:
    1. Encontrar ActivityFunc dentro
    2. Strip ActivityFunc.Argument block
    3. Strip XML comments (não contam como activity)
    4. Verificar se sobrou QUALQUER outro elemento dentro de ActivityFunc
    5. Se NÃO sobrou, emit finding

Estrategia regex-based stack-aware: usar `_find_balanced_close` style do
empty_sequence.py para encontrar fechamento real do ActivityFunc (handle
ActivityFunc aninhado teoricamente).
"""
from __future__ import annotations

import re

from uip_engine._types import Finding


# Properties que exigem activity plug — não bastam ActivityFunc placeholder.
# Sicoob: OCREngine (UiPathScreenOCR), CVEngine (UI CV — futuro).
_ENGINE_PROPS = ("OCREngine", "CVEngine")


# Match: <prefix:Owner.{Engine}>...</prefix:Owner.{Engine}>
# Capturing groups:
#   1 = prefix (ex: 'uix')
#   2 = owner local name (ex: 'NApplicationCard')
#   3 = engine prop suffix (OCREngine|CVEngine)
#   4 = full inner content of property element
_OUTER_RE = {
    prop: re.compile(
        rf'<(\w+):(\w+)\.({prop})\b[^>]*>(.*?)</\1:\2\.\3>',
        re.DOTALL,
    )
    for prop in _ENGINE_PROPS
}

# ActivityFunc open tag (any attrs) and close tag.
# Lookahead `(?=[\s/>])` evita match em `<ActivityFunc.Argument>` (property
# element child) — só pega `<ActivityFunc ` ou `<ActivityFunc>` ou
# `<ActivityFunc/>`.
_ACTIVITYFUNC_OPEN_RE = re.compile(r'<ActivityFunc(?=[\s/>])[^>]*?>', re.DOTALL)
_ACTIVITYFUNC_SELF_CLOSE_RE = re.compile(
    r'<ActivityFunc(?=[\s/>])[^>]*?/>', re.DOTALL,
)
_ACTIVITYFUNC_CLOSE_RE = re.compile(r'</ActivityFunc>')

# Block to strip when checking emptiness — não conta como activity child.
_ACTIVITYFUNC_ARGUMENT_RE = re.compile(
    r'<ActivityFunc\.Argument\b[^>]*?(?:/>|>.*?</ActivityFunc\.Argument>)',
    re.DOTALL,
)
_XML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)

# Detect any element start (skip processing instructions, comments).
_ANY_ELEMENT_RE = re.compile(r'<(?!!|\?)\w')


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _find_balanced_close(content: str, open_end: int) -> int:
    """Encontra `</ActivityFunc>` matching o open em `open_end`, respeitando
    nesting. Retorna posição END do close, ou -1 se não encontrado."""
    depth = 1
    pos = open_end
    while pos < len(content):
        nxt_o = _ACTIVITYFUNC_OPEN_RE.search(content, pos)
        nxt_c = _ACTIVITYFUNC_CLOSE_RE.search(content, pos)
        if not nxt_c:
            return -1
        # Skip self-close opens inside body
        while (
            nxt_o
            and nxt_o.group(0).rstrip().endswith("/>")
            and nxt_o.start() < nxt_c.start()
        ):
            pos = nxt_o.end()
            nxt_o = _ACTIVITYFUNC_OPEN_RE.search(content, pos)
        if nxt_o and nxt_o.start() < nxt_c.start():
            depth += 1
            pos = nxt_o.end()
        else:
            depth -= 1
            if depth == 0:
                return nxt_c.end()
            pos = nxt_c.end()
    return -1


def _body_has_activity_child(body: str) -> bool:
    """True se body do ActivityFunc tem activity child real (não só Argument/comment)."""
    stripped = _ACTIVITYFUNC_ARGUMENT_RE.sub("", body)
    stripped = _XML_COMMENT_RE.sub("", stripped)
    return bool(_ANY_ELEMENT_RE.search(stripped))


def detect_empty_ocr_activityfunc(rule, fc, pc):
    """Detect ActivityFunc body vazio em property .OCREngine/.CVEngine."""
    # Guard: só XAML.
    if fc.path.suffix.lower() != ".xaml":
        return []
    content = fc.active_content
    findings: list[Finding] = []

    for prop, outer_re in _OUTER_RE.items():
        for outer_m in outer_re.finditer(content):
            prefix = outer_m.group(1)
            owner = outer_m.group(2)
            inner = outer_m.group(4)
            inner_start_abs = outer_m.start(4)

            # Caso 1: ActivityFunc self-close — body trivialmente vazio.
            for sc_m in _ACTIVITYFUNC_SELF_CLOSE_RE.finditer(inner):
                abs_offset = inner_start_abs + sc_m.start()
                findings.append(_make_finding(
                    rule, fc, content, abs_offset, prefix, owner, prop,
                ))

            # Caso 2: ActivityFunc open/close — checar body.
            # Iterar open tags non-self-close
            for om in _ACTIVITYFUNC_OPEN_RE.finditer(inner):
                if om.group(0).rstrip().endswith("/>"):
                    continue
                # Find balanced close in absolute content
                abs_open_end = inner_start_abs + om.end()
                abs_close_end = _find_balanced_close(content, abs_open_end)
                if abs_close_end < 0:
                    continue
                close_start = abs_close_end - len("</ActivityFunc>")
                body = content[abs_open_end:close_start]
                if _body_has_activity_child(body):
                    continue
                abs_offset = inner_start_abs + om.start()
                findings.append(_make_finding(
                    rule, fc, content, abs_offset, prefix, owner, prop,
                ))

    return findings


def _make_finding(rule, fc, content, offset, prefix, owner, prop):
    line = _line_for(content, offset)
    engine_word = "OCR" if prop == "OCREngine" else "CV"
    return Finding(
        rule_id=rule.id,
        severity=rule.severity,
        category=rule.category,
        file=str(fc.path),
        line=line,
        message=(
            f"ActivityFunc body vazio em <{prefix}:{owner}.{prop}>. "
            f"Studio compile falha com '{engine_word} Engine must be set'. "
            f"Plug activity {engine_word} no body do ActivityFunc."
        ),
        fix_prose=(rule.fix or {}).get("prose"),
    )
