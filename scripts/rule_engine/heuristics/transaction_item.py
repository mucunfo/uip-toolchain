"""Heuristics para A-19 (io_TransactionItem) e A-19b (In args missing)."""
from __future__ import annotations

import re

from scripts.rule_engine._types import Finding


_RE_INVOKE_BLOCK = re.compile(
    r'<ui:InvokeWorkflowFile[^>]*WorkflowFileName="([^"]+)"[^>]*>(.*?)</ui:InvokeWorkflowFile>',
    re.DOTALL,
)
_RE_INVOKE_ARGS = re.compile(
    r'<ui:InvokeWorkflowFile\.Arguments>(.*?)</ui:InvokeWorkflowFile\.Arguments>',
    re.DOTALL,
)
_RE_KEY = re.compile(r'x:Key="([^"]+)"')

_RE_PROPERTY = re.compile(
    r'<x:Property[^>]*Name="([^"]+)"[^>]*Type="([^"]+)"',
    re.DOTALL,
)
_RE_PROPERTY_ALT = re.compile(
    r'<x:Property[^>]*Type="([^"]+)"[^>]*Name="([^"]+)"',
    re.DOTALL,
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _parse_callee_props(target_content: str) -> list[tuple[str, str]]:
    """Return [(name, type_str)] for declared <x:Property>."""
    props = []
    for m in _RE_PROPERTY.finditer(target_content):
        props.append((m.group(1), m.group(2)))
    for m in _RE_PROPERTY_ALT.finditer(target_content):
        props.append((m.group(2), m.group(1)))
    seen = set()
    out = []
    for name, ty in props:
        if name in seen:
            continue
        seen.add(name)
        out.append((name, ty))
    return out


def _resolve_callee(pc, target_file: str):
    if target_file.startswith("[") or "{" in target_file:
        return None
    normalized = target_file.replace("\\", "/").lstrip("./")
    target_path = pc.root / normalized
    if not target_path.exists():
        return None
    try:
        return target_path.read_text(encoding="utf-8-sig")
    except Exception:
        return None


def detect_a19_io_transaction_item(rule, fc, pc):
    """A-19: callee escreve io_TransactionItem.Output mas caller não bindou."""
    if pc is None:
        return []
    if "InvokeWorkflowFile" not in fc.active_content:
        return []

    findings = []
    content = fc.active_content
    for invoke in _RE_INVOKE_BLOCK.finditer(content):
        target = invoke.group(1)
        callee_content = _resolve_callee(pc, target)
        if callee_content is None:
            continue

        props = _parse_callee_props(callee_content)
        has_io_ti = any(
            n == "io_TransactionItem" and "InOutArgument" in t for n, t in props
        )
        if not has_io_ti:
            continue

        if not re.search(r'io_TransactionItem\.Output\b', callee_content):
            continue

        args_match = _RE_INVOKE_ARGS.search(invoke.group(0))
        caller_keys = (
            set(_RE_KEY.findall(args_match.group(1))) if args_match else set()
        )
        if "io_TransactionItem" in caller_keys:
            continue

        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, invoke.start()),
            message=f"{rule.title}: {target} modifica io_TransactionItem.Output mas caller não passou",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# --- A-19c: caller arg key name divergente do callee (auto-fix por similaridade)

# Prefixos de tipo conhecidos (longest-match desc) para strip durante normalização
_KNOWN_TYPE_PREFIXES = (
    "DTab", "SSt", "JObj", "JArr", "Dict", "Lst", "Arr",
    "Row", "Int", "Dbl", "Lng", "Obj", "St", "Bl", "Dt", "UI",
)
_DIR_PREFIXES = ("inout_", "in_out_", "in_", "out_", "io_")


def _strip_dir(name: str):
    for d in sorted(_DIR_PREFIXES, key=len, reverse=True):
        if name.startswith(d):
            return name[len(d):], d
    return name, ""


def _strip_type_prefix(rest: str) -> str:
    for p in sorted(_KNOWN_TYPE_PREFIXES, key=len, reverse=True):
        if rest.startswith(p):
            tail = rest[len(p):]
            if not tail or tail[0].isupper() or tail[0].isdigit():
                return tail
    return rest


def _tokenize_camel(s: str) -> list[str]:
    if not s:
        return []
    return [t.lower() for t in re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z0-9]+|[A-Z]+|[a-z0-9]+', s) if t]


def _norm_tokens(name: str) -> tuple[str, list[str]]:
    """Returns (direction_prefix, semantic_tokens). Strip dir + type-prefix.
    Tokens são lowercase para matching tolerante."""
    rest, dir_ = _strip_dir(name)
    rest = _strip_type_prefix(rest)
    return dir_, _tokenize_camel(rest)


def _arg_direction(arg_type: str) -> str:
    if arg_type.startswith("InOutArgument"):
        return "io_"
    if arg_type.startswith("OutArgument"):
        return "out_"
    if arg_type.startswith("InArgument"):
        return "in_"
    return ""


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


_RE_INVOKE_BLOCK_FULL = re.compile(
    r'<ui:InvokeWorkflowFile\b(?P<attrs>[^>]*)>(?P<inner>.*?)</ui:InvokeWorkflowFile>',
    re.DOTALL,
)
_RE_INVOKE_SELFCLOSE = re.compile(
    r'<ui:InvokeWorkflowFile\b(?P<attrs>[^>]*)/>',
)
_RE_KEY_AND_TYPE = re.compile(
    r'<(?P<dir>In|Out|InOut)Argument\b[^>]*x:TypeArguments="(?P<ta1>[^"]+)"[^>]*x:Key="(?P<key>[^"]+)"'
    r'|'
    r'<(?P<dir2>In|Out|InOut)Argument\b[^>]*x:Key="(?P<key2>[^"]+)"[^>]*x:TypeArguments="(?P<ta2>[^"]+)"',
)
_RE_IDREF = re.compile(r'sap2010:WorkflowViewState\.IdRef="([^"]+)"')
_RE_WFNAME = re.compile(r'WorkflowFileName="([^"]+)"')


def _caller_args_with_dir_type(args_inner: str) -> dict[str, tuple[str, str]]:
    """Returns {key: (direction_prefix, type_args)}."""
    out = {}
    for m in re.finditer(
        r'<(In|Out|InOut)Argument\b(?P<rest>[^>]*?)>',
        args_inner,
        re.DOTALL,
    ):
        d = m.group(1)
        rest = m.group("rest")
        key_m = re.search(r'x:Key="([^"]+)"', rest)
        ta_m = re.search(r'x:TypeArguments="([^"]+)"', rest)
        if not key_m:
            continue
        out[key_m.group(1)] = (f"{d.lower()}_", ta_m.group(1) if ta_m else "")
    return out


def _caller_args_with_dir(args_inner: str) -> dict[str, str]:
    """Returns {key: direction_prefix} (compat — calls _caller_args_with_dir_type)."""
    return {k: v[0] for k, v in _caller_args_with_dir_type(args_inner).items()}


def _callee_type_norm(prop_type: str) -> str:
    """Extract inner type from `InArgument(ui:UiElement)` → `UiElement`. Strip namespace."""
    m = re.search(r'\(([^)]+)\)', prop_type)
    inner = m.group(1).strip() if m else prop_type
    if ":" in inner:
        inner = inner.split(":", 1)[-1]
    return inner.strip()


def _caller_type_norm(type_args: str) -> str:
    """Extract type local name from `ui:UiElement` → `UiElement`."""
    if not type_args:
        return ""
    s = type_args.strip()
    if ":" in s:
        s = s.split(":", 1)[-1]
    return s


def detect_a19c_caller_arg_misnamed(rule, fc, pc):
    """A-19c: caller passa x:Key que não existe no callee, mas há candidato
    com alta similaridade (mesma direção + token overlap >= threshold).
    Gera fix mecânico `rename_invoke_arg_key`.
    """
    if pc is None:
        return []
    if "InvokeWorkflowFile" not in fc.active_content:
        return []

    p = (rule.detect.get("params", {}) or {})
    threshold = float(p.get("similarity_threshold", 0.5))

    findings: list[Finding] = []
    content = fc.active_content

    for invoke in _RE_INVOKE_BLOCK_FULL.finditer(content):
        attrs = invoke.group("attrs")
        inner = invoke.group("inner")
        wf = _RE_WFNAME.search(attrs)
        if not wf:
            continue
        target = wf.group(1)
        callee_content = _resolve_callee(pc, target)
        if callee_content is None:
            continue
        props = _parse_callee_props(callee_content)
        # Map callee: direction -> [(name, type_norm)]
        callee_by_dir: dict[str, list[tuple[str, str]]] = {}
        callee_all_names: set[str] = set()
        for n, t in props:
            d = _arg_direction(t)
            tn = _callee_type_norm(t)
            callee_by_dir.setdefault(d, []).append((n, tn))
            callee_all_names.add(n)
        if not callee_all_names:
            continue
        idref = _RE_IDREF.search(attrs)
        idref_val = idref.group(1) if idref else None

        args_match = _RE_INVOKE_ARGS.search(inner)
        if not args_match:
            continue
        args_inner = args_match.group(1)
        caller_args = _caller_args_with_dir_type(args_inner)

        # 2026-05-01 root-cause fix: tracking de candidatos consumidos POR
        # invoke block. Cada callee property só pode ser alvo de UM caller
        # key. Sem isso, múltiplas caller keys colapsavam pro mesmo target,
        # criando duplicate x:Key (Studio: "Add value to dictionary threw").
        consumed_candidates: set[str] = set()
        # Caller keys já matched no callee (não precisam rename).
        for k in caller_args:
            if k in callee_all_names:
                consumed_candidates.add(k)

        # Lista ordenada de unmatched keys do caller (deterministic order).
        unmatched_keys = [
            (k, d_t) for k, d_t in caller_args.items()
            if k not in callee_all_names
        ]

        # Type-unique fallback só faz sentido se houver exatamente 1
        # unmatched caller key. Múltiplos unmatched + 1 candidato = mismatch
        # estrutural, exige human review.
        single_unmatched = (len(unmatched_keys) == 1)

        for key, (caller_dir, caller_ta) in unmatched_keys:
            caller_tn = _caller_type_norm(caller_ta)
            _, caller_tokens = _norm_tokens(key)

            candidates = [
                (n, t) for (n, t) in callee_by_dir.get(caller_dir, [])
                if n not in consumed_candidates
            ]
            if not candidates:
                continue

            type_filtered = (
                [(n, t) for n, t in candidates if t == caller_tn] if caller_tn else candidates
            )

            best_match = None
            best_score = 0.0
            for n, _t in type_filtered:
                _, cand_tokens = _norm_tokens(n)
                score = _jaccard(caller_tokens, cand_tokens)
                if score > best_score:
                    best_score = score
                    best_match = n

            unique_by_type = (len(type_filtered) == 1)
            ambiguous = False
            if best_match and best_score >= threshold:
                if sum(
                    1 for n, _t in type_filtered
                    if _jaccard(caller_tokens, _norm_tokens(n)[1]) >= best_score
                ) > 1:
                    ambiguous = True
            elif single_unmatched and unique_by_type and type_filtered:
                # Fallback type-unique SOMENTE quando há 1 unmatched caller
                # key (1:1 unambiguous). Múltiplos unmatched → estrutural.
                best_match = type_filtered[0][0]
                best_score = -1.0
            else:
                best_match = None

            if best_match is None or ambiguous:
                continue

            consumed_candidates.add(best_match)

            mech = {
                "type": "rename_invoke_arg_key",
                "workflow_basename": target.replace("\\", "/").split("/")[-1],
                "invoke_idref": idref_val,
                "from_key": key,
                "to_key": best_match,
            }
            score_str = (
                f"score={best_score:.2f}" if best_score >= 0
                else "type-unique-fallback"
            )
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, invoke.start()),
                message=(
                    f"{rule.title}: caller passa '{key}' mas callee '{target}' "
                    f"declara '{best_match}' ({score_str}) — provável "
                    f"cascade de rename não-aplicada"
                ),
                fix_mechanical=mech,
                fix_prose=(rule.fix or {}).get("prose"),
            ))
    return findings


def detect_a19b_in_args_missing(rule, fc, pc):
    """A-19b: caller falta argumento In/InOut declarado pelo callee.

    Out-only args missing são descarte legítimo (não dispara).
    """
    if pc is None:
        return []
    if "InvokeWorkflowFile" not in fc.active_content:
        return []

    findings = []
    content = fc.active_content
    for invoke in _RE_INVOKE_BLOCK.finditer(content):
        target = invoke.group(1)
        callee_content = _resolve_callee(pc, target)
        if callee_content is None:
            continue

        props = _parse_callee_props(callee_content)
        # Required = In ou InOut. NOT Out.
        required = {
            n for n, t in props
            if t.startswith("InArgument") or t.startswith("InOutArgument")
        }
        if not required:
            continue
        # Args com default-value via `this:<Class>.<arg>` block (attribute ou
        # property-element form) são opcionais p/ caller — Studio resolve com
        # default literal. Excluir do `required`.
        with_default = set()
        for arg_name in required:
            # Attribute form: `this:<Class>.<arg>="value"` no <Activity> root
            attr_re = re.compile(
                rf'\bthis:\w+\.{re.escape(arg_name)}=\"[^\"]*\"'
            )
            # Element form: `<this:<Class>.<arg>>...</this:<Class>.<arg>>`
            elem_re = re.compile(
                rf'<this:\w+\.{re.escape(arg_name)}\b'
            )
            if attr_re.search(callee_content) or elem_re.search(callee_content):
                with_default.add(arg_name)
        required -= with_default

        args_match = _RE_INVOKE_ARGS.search(invoke.group(0))
        caller_keys = (
            set(_RE_KEY.findall(args_match.group(1))) if args_match else set()
        )

        missing = required - caller_keys
        if not missing:
            continue

        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, invoke.start()),
            message=f"{rule.title}: {target} falta {sorted(missing)}",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
