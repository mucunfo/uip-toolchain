"""Heuristics for complexity rules (CX-*).

Métricas estáticas por workflow XAML:
  CX-1 cyclomatic — soma de decision points (If/Switch case/While/DoWhile/
       ForEach/ParallelForEach/TryCatch.Catch/Parallel branch/FlowDecision/
       FlowSwitch case). Baseline 1 + cada branch adicional.
  CX-2 nesting depth — profundidade máxima da árvore de elementos
       executáveis (ignora property-elements `X.Y` e metadata x:*).
  CX-3 fan-out — count distinto de InvokeWorkflowFile.WorkflowFileName
       (callees diretos).
  CX-4 activity count — count total de elementos executáveis.
  CX-5 god-workflow composite — flag quando >=3 das métricas
       (lines, activities, depth, args) excedem thresholds simultâneo.

Thresholds via rule.detect.params.threshold_warn/threshold_error.
"""
from __future__ import annotations

import re
from typing import Any

from lxml import etree

from scripts.rule_engine._types import Finding, Severity
from scripts.rule_engine.context import FileContext, ProjectContext


_RE_INVOKE_WF_FILE = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*WorkflowFileName="([^"]+)"'
)

# Decision-point tags (regex, fast scan). Open-tag form only.
# `[\s/>]` lookahead exclui property-element form `<If.Then>` (Then é property
# element de If, NÃO um decision point separado).
_RE_IF = re.compile(r'<If[\s/>]')
_RE_SWITCH_CASE_KEY = re.compile(r'\bx:Key="[^"]*"')  # cases dentro de Switch
_RE_SWITCH_OPEN = re.compile(r'<Switch[\s/>]')
_RE_WHILE = re.compile(r'<(?:While|DoWhile)[\s/>]')
_RE_FOREACH = re.compile(r'<(?:ForEach|ParallelForEach)[\s/>]')
_RE_TRY_CATCH = re.compile(r'<Catch[\s/>]')
_RE_PARALLEL = re.compile(r'<Parallel[\s/>]')
_RE_FLOW_DECISION = re.compile(r'<FlowDecision[\s/>]')
_RE_FLOW_SWITCH = re.compile(r'<FlowSwitch[\s/>]')

# Elements que NÃO contam como activities (metadata, property elements, args).
_NON_ACTIVITY_LOCALNAMES = frozenset({
    "Activity", "Members", "Property", "InArgument", "OutArgument",
    "InOutArgument", "Variable", "Variable.Default", "TextExpression.NamespacesForImplementation",
    "TextExpression.ReferencesForImplementation", "AssemblyReference",
    "String", "Int32", "Int64", "Boolean", "Double", "Decimal", "DateTime",
    "TypeArguments", "Reference",
})

# Namespaces metadata — skip subtree para activity count + depth.
_METADATA_NS_PREFIXES = ("x", "sap", "sap2010", "scg", "s", "sco", "mc", "mva")


def _qname(elem) -> tuple[str, str]:
    """Return (ns_prefix-ish, local_name)."""
    tag = etree.QName(elem.tag)
    return tag.namespace or "", tag.localname


def _is_property_element(local: str) -> bool:
    """`Foo.Bar` form = property element, não activity."""
    return "." in local


def _is_metadata_element(local: str, ns: str) -> bool:
    """x:Members, x:Property, etc."""
    return local in _NON_ACTIVITY_LOCALNAMES


def _parse_xaml(content: str):
    """Parse XAML retornando root. Returns None se broken."""
    try:
        # Strip BOM
        if content.startswith("﻿"):
            content = content[1:]
        return etree.fromstring(content.encode("utf-8"))
    except (etree.XMLSyntaxError, ValueError):
        return None


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


# ---------- Métricas ----------

def _cyclomatic(content: str) -> int:
    """Approx McCabe: 1 + sum(decision branches).
    Switch cases: cada x:Key dentro de <Switch> = 1; default não conta extra.
    TryCatch: cada <Catch> = 1.
    """
    c = 1
    c += len(_RE_IF.findall(content))
    c += len(_RE_WHILE.findall(content))
    c += len(_RE_FOREACH.findall(content))
    c += len(_RE_TRY_CATCH.findall(content))
    c += max(0, len(_RE_PARALLEL.findall(content)) - 1)  # baseline 1 branch
    c += len(_RE_FLOW_DECISION.findall(content))

    # Switch: precisa contar cases (x:Key dentro do span <Switch>...</Switch>)
    for m in re.finditer(r'<Switch\b[^>]*>(.*?)</Switch>', content, re.DOTALL):
        body = m.group(1)
        c += len(_RE_SWITCH_CASE_KEY.findall(body))
    for m in re.finditer(r'<FlowSwitch\b[^>]*>(.*?)</FlowSwitch>', content, re.DOTALL):
        body = m.group(1)
        c += len(_RE_SWITCH_CASE_KEY.findall(body))
    return c


def _max_nesting_depth(root) -> int:
    """Walk tree skipping property elements + metadata, track max depth.
    Baseline 0 = root Activity. Body Sequence = depth 1.
    """
    if root is None:
        return 0
    max_d = [0]

    def walk(elem, depth: int):
        ns, local = _qname(elem)
        if _is_property_element(local) or _is_metadata_element(local, ns):
            # Property element: não incrementa depth, mas walk children
            for child in elem:
                walk(child, depth)
            return
        # Activity: incrementa depth
        new_d = depth + 1
        if new_d > max_d[0]:
            max_d[0] = new_d
        for child in elem:
            walk(child, new_d)

    walk(root, 0)
    return max_d[0]


def _activity_count(root) -> int:
    """Count elementos executáveis (não property element, não metadata)."""
    if root is None:
        return 0
    count = 0
    for elem in root.iter():
        ns, local = _qname(elem)
        if _is_property_element(local) or _is_metadata_element(local, ns):
            continue
        # Skip root <Activity>
        if local == "Activity" and elem.getparent() is None:
            continue
        count += 1
    return count


def _fan_out(content: str) -> int:
    """Count distinct workflows invoked."""
    return len(set(_RE_INVOKE_WF_FILE.findall(content)))


def _arg_count(root) -> int:
    """Count x:Members → Property (= argument declarations)."""
    if root is None:
        return 0
    nsmap = {"x": "http://schemas.microsoft.com/winfx/2006/xaml"}
    members = root.find("x:Members", nsmap)
    if members is None:
        return 0
    return sum(1 for _ in members.iterchildren("{http://schemas.microsoft.com/winfx/2006/xaml}Property"))


def _line_count(content: str) -> int:
    return content.count("\n") + 1


# ---------- Detectors ----------

def _threshold(params: dict, key: str, default: int) -> int:
    try:
        return int(params.get(key, default))
    except (TypeError, ValueError):
        return default


def _emit(rule, fc, value: int, metric_name: str, threshold: int) -> Finding:
    return Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1,
        message=f"{rule.title}: {metric_name}={value} > {threshold}",
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )


def detect_cx1_cyclomatic(rule, fc: FileContext, pc) -> list[Finding]:
    params = rule.detect.get("params", {}) or {}
    warn = _threshold(params, "threshold_warn", 10)
    err = _threshold(params, "threshold_error", 20)
    cc = _cyclomatic(fc.active_content)
    if cc > err:
        f = _emit(rule, fc, cc, "cyclomatic", err)
        f.severity = Severity.ERROR
        return [f]
    if cc > warn:
        return [_emit(rule, fc, cc, "cyclomatic", warn)]
    return []


def detect_cx2_depth(rule, fc: FileContext, pc) -> list[Finding]:
    params = rule.detect.get("params", {}) or {}
    warn = _threshold(params, "threshold_warn", 5)
    err = _threshold(params, "threshold_error", 8)
    root = _parse_xaml(fc.content)
    d = _max_nesting_depth(root)
    if d > err:
        f = _emit(rule, fc, d, "nesting_depth", err)
        f.severity = Severity.ERROR
        return [f]
    if d > warn:
        return [_emit(rule, fc, d, "nesting_depth", warn)]
    return []


def detect_cx3_fanout(rule, fc: FileContext, pc) -> list[Finding]:
    params = rule.detect.get("params", {}) or {}
    warn = _threshold(params, "threshold_warn", 10)
    err = _threshold(params, "threshold_error", 15)
    fo = _fan_out(fc.active_content)
    if fo > err:
        f = _emit(rule, fc, fo, "fan_out", err)
        f.severity = Severity.ERROR
        return [f]
    if fo > warn:
        return [_emit(rule, fc, fo, "fan_out", warn)]
    return []


def detect_cx4_activities(rule, fc: FileContext, pc) -> list[Finding]:
    params = rule.detect.get("params", {}) or {}
    warn = _threshold(params, "threshold_warn", 100)
    err = _threshold(params, "threshold_error", 300)
    root = _parse_xaml(fc.content)
    ac = _activity_count(root)
    if ac > err:
        f = _emit(rule, fc, ac, "activity_count", err)
        f.severity = Severity.ERROR
        return [f]
    if ac > warn:
        return [_emit(rule, fc, ac, "activity_count", warn)]
    return []


def detect_cx5_god_workflow(rule, fc: FileContext, pc) -> list[Finding]:
    """God-workflow composite: ≥3 métricas tripped simultâneo."""
    params = rule.detect.get("params", {}) or {}
    t_lines = _threshold(params, "threshold_lines", 200)
    t_activities = _threshold(params, "threshold_activities", 50)
    t_depth = _threshold(params, "threshold_depth", 5)
    t_args = _threshold(params, "threshold_args", 7)
    t_min_tripped = _threshold(params, "min_tripped", 3)

    root = _parse_xaml(fc.content)
    metrics = {
        "lines": _line_count(fc.content),
        "activities": _activity_count(root),
        "depth": _max_nesting_depth(root),
        "args": _arg_count(root),
    }
    thresholds = {
        "lines": t_lines, "activities": t_activities,
        "depth": t_depth, "args": t_args,
    }
    tripped = {k: v for k, v in metrics.items() if v > thresholds[k]}
    if len(tripped) < t_min_tripped:
        return []
    detail = ", ".join(f"{k}={metrics[k]}>{thresholds[k]}" for k in sorted(tripped))
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1,
        message=f"{rule.title}: {len(tripped)} métricas excedidas ({detail})",
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )]
