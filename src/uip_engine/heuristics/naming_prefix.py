"""Heuristics N-1 (var prefix), N-2 (arg prefix), N-4 (limite args),
N-8 (tamanho do nome).

All convenções (type prefixes, wrong-prefix map, bare-special, REFramework
template vars, threshold) vinem de rules.yaml params. Sem hardcoded.
"""
from __future__ import annotations

import re

from uip_engine._types import Finding


_RE_VARIABLE = re.compile(
    r'<Variable\b[^>]*Name="([^"]+)"[^>]*x:TypeArguments="([^"]+)"',
    re.DOTALL,
)
_RE_VARIABLE_ALT = re.compile(
    r'<Variable\b[^>]*x:TypeArguments="([^"]+)"[^>]*Name="([^"]+)"',
    re.DOTALL,
)
_RE_PROPERTY = re.compile(
    r'<x:Property\b[^>]*Name="([^"]+)"[^>]*Type="([^"]+)"',
    re.DOTALL,
)
_RE_PROPERTY_ALT = re.compile(
    r'<x:Property\b[^>]*Type="([^"]+)"[^>]*Name="([^"]+)"',
    re.DOTALL,
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _params(rule):
    return rule.detect.get("params", {}) or {}


def _type_prefix_pairs(params):
    """Return ordered list of (type_name, prefix_or_None)."""
    raw = params.get("type_prefix") or []
    pairs = []
    for entry in raw:
        if isinstance(entry, dict):
            t = entry.get("type")
            p = entry.get("prefix")
            if t:
                pairs.append((t, p if p else None))
    return pairs


def _wrong_prefix_map(params):
    return dict(params.get("wrong_prefix_map") or {})


def _reframework_main_vars(params):
    return frozenset(params.get("reframework_main_vars") or ())


def _bare_arg_names(params):
    return frozenset(params.get("bare_arg_names") or ())


def _bare_special_rules(params):
    """List of {type_substring, name_in?, name_starts_with?}."""
    return list(params.get("bare_special") or [])


def _detect_wrong_prefix(rest, wrong_map):
    """Detect wrong prefix at start of `rest`.

    Boundary chars válidos depois do prefix candidato:
      - uppercase letter (CamelCase: `vNuTimeout` → `Nu` + `Timeout`)
      - underscore (Hungarian legacy: `Dt_Credentials` → `Dt` + `_Credentials`)
      - digit (`Int32` → `Int` + `32`)
      - end of string

    Sem boundary check, prefixos curtos matcheariam dentro de palavras
    (`vNumero` → strip `Nu` → `meroX` corrompendo o nome).
    """
    for wrong, expected in wrong_map.items():
        if not rest.startswith(wrong):
            continue
        boundary_idx = len(wrong)
        if boundary_idx == len(rest):
            return wrong
        next_char = rest[boundary_idx]
        if next_char.isupper() or next_char == "_" or next_char.isdigit():
            return wrong
    return None


def _has_valid_prefix(rest, prefix):
    """Prefixo válido = `rest` começa com `prefix` E (acabou OU próximo char é UPPER/digit).

    Convenção `[Prefixo][Nome]` exige Nome capitalizado. `vIntegerCount`
    NÃO tem prefixo `Int` válido — após `Int` vem `e` minúscula, indicando
    que `Int` é só substring de `Integer` (palavra), não prefixo de tipo.
    """
    if not rest.startswith(prefix):
        return False
    tail = rest[len(prefix):]
    if not tail:
        return True
    return tail[0].isupper() or tail[0].isdigit()


# Order matters: longer first so `inout_` matches before `in_`/`out_`.
_DIR_PREFIXES = ("inout_", "in_out_", "in_", "out_", "io_")


def _strip_direction(name: str):
    """Strip any leading direction prefix, including invalid ones like
    `inout_`/`in_out_` (canonical é `io_`)."""
    for d in sorted(_DIR_PREFIXES, key=len, reverse=True):
        if name.startswith(d):
            return name[len(d):]
    return name


def _strip_known_type_prefix(rest: str, all_type_prefixes):
    """Strip qualquer prefix de tipo conhecido (longest match), retornando
    (resto, prefix_strippado_ou_None). Só strip se prefix é seguido por
    UPPER/digit (convenção `[Prefix][Nome]`)."""
    for p in sorted({x for x in all_type_prefixes if x}, key=len, reverse=True):
        if rest.startswith(p):
            tail = rest[len(p):]
            if not tail or tail[0].isupper() or tail[0].isdigit():
                return rest[len(p):], p
    return rest, None


# Direção embedded no meio do nome: `Inout_X`, `In_X`, `Out_X`. Underscores
# em CamelCase são anomalia — sempre indicam corrupção por fixer/template.
_RE_EMBEDDED_DIRECTION = re.compile(r'(In_?Out_|InOut_|Inout_|In_|Out_)')


def _strip_embedded_direction(rest: str) -> str:
    """Remove primeira direção residual encontrada no meio do nome."""
    m = _RE_EMBEDDED_DIRECTION.search(rest)
    if not m:
        return rest
    return rest[:m.start()] + rest[m.end():]


def _normalize_rest(rest: str, expected_prefix: str, wrong_map: dict, all_type_prefixes):
    """Aplica todas as estriparias possíveis até estabilizar:
      - leading `v` (var bleed)
      - direction leftover (`out_X` que sobrou de `inout_X[3:]`)
      - wrong_map prefix (Bool→Bl, etc.)
      - prefix de outro tipo conhecido (St quando expected é SSt, etc.)
    Loop até não haver mais mudança. Depois prepend `expected_prefix`
    se ainda não está presente.
    """
    prev = None
    while prev != rest:
        prev = rest
        # Strip leading underscore (Hungarian legacy separator residual após
        # remover wrong-prefix `Dt_X` → strip `Dt` → `_X` → strip `_` → `X`).
        if rest.startswith("_") and len(rest) > 1:
            rest = rest[1:]
            continue
        if rest.startswith("v") and len(rest) > 1 and rest[1].isupper():
            rest = rest[1:]
            continue
        stripped_dir = _strip_direction(rest)
        if stripped_dir != rest:
            rest = stripped_dir
            continue
        # Direção embedded no meio (`Foo + Inout_X` → `FooX`)
        stripped_embed = _strip_embedded_direction(rest)
        if stripped_embed != rest:
            rest = stripped_embed
            continue
        wrong = _detect_wrong_prefix(rest, wrong_map)
        if wrong is not None:
            rest = rest[len(wrong):]
            continue
        rest2, found_p = _strip_known_type_prefix(rest, all_type_prefixes)
        if found_p and found_p != expected_prefix:
            rest = rest2
            continue
    if _has_valid_prefix(rest, expected_prefix):
        # Double-stack guard restrito a pares de prefixos com confusão
        # comum (subset substring): expected é "extensão" de outro válido.
        # Ex.: SSt = SecureString (deriva de String/St); DTab = DataTable
        # (substring DT, Tab); Dict (substring Dt). Nesses casos é seguro
        # strip um prefix válido subsequente. Para outros, NÃO strip pois
        # pode ser parte do nome semântico (ex.: `St + Dt + HrExpiracao`
        # onde `Dt` é "Data" e não prefix de tipo).
        confusion_supersets = {
            "SSt": ("St",),
            "DTab": ("Dt", "Tab", "DT"),
            # Dict não inclui Dt — `DictDtX` é improvável (Dict é
            # substring "Dic" + "t", não tem Dt aninhado natural).
        }
        peers = confusion_supersets.get(expected_prefix, ())
        prev_tail = None
        # Loop sempre roda: precisa pegar redundância pura
        # (expected + wrong→expected, ex.: Dict + Dic → Dict).
        while True:
            tail = rest[len(expected_prefix):]
            if tail == prev_tail:
                break
            prev_tail = tail
            wrong_in_tail = _detect_wrong_prefix(tail, wrong_map)
            if wrong_in_tail is not None and (
                wrong_map[wrong_in_tail] == expected_prefix
                or wrong_map[wrong_in_tail] in peers
            ):
                # Strip redundância pura (Dict + Dic → Dict) ou peer confusível.
                # Plus: strip leading `_` (Hungarian legacy separator).
                new_tail = tail[len(wrong_in_tail):]
                while new_tail.startswith("_"):
                    new_tail = new_tail[1:]
                rest = f"{expected_prefix}{new_tail}"
                continue
            tail_stripped, found_in_tail = _strip_known_type_prefix(tail, all_type_prefixes)
            if found_in_tail and found_in_tail in peers:
                while tail_stripped.startswith("_"):
                    tail_stripped = tail_stripped[1:]
                rest = f"{expected_prefix}{tail_stripped}"
                continue
            break
        return rest
    return f"{expected_prefix}{rest}"


def _compute_var_fix(name, expected_prefix, wrong_map, all_type_prefixes=None):
    if all_type_prefixes is None:
        all_type_prefixes = ()
    if not name.startswith("v"):
        cap = name[0].upper() + name[1:] if name else ""
        rest = _normalize_rest(cap, expected_prefix, wrong_map, all_type_prefixes)
        return f"v{rest}"
    rest = name[1:]
    rest_fixed = _normalize_rest(rest, expected_prefix, wrong_map, all_type_prefixes)
    candidate = f"v{rest_fixed}"
    return None if candidate == name else candidate


def _compute_arg_rest_fix(rest, expected_prefix, wrong_map, all_type_prefixes=None):
    if all_type_prefixes is None:
        all_type_prefixes = ()
    return _normalize_rest(rest, expected_prefix, wrong_map, all_type_prefixes)


def _compute_arg_fix(name, direction, expected_prefix, wrong_map, all_type_prefixes=None):
    if all_type_prefixes is None:
        all_type_prefixes = ()
    dir_prefix = f"{direction}_"
    # Strip whatever direction was present (canonical or invalid like inout_).
    stripped = _strip_direction(name)
    if stripped == name:
        # Sem direction — capitalizar primeira letra.
        stripped = name[0].upper() + name[1:] if name else ""
    rest_fixed = _normalize_rest(stripped, expected_prefix, wrong_map, all_type_prefixes)
    candidate = f"{dir_prefix}{rest_fixed}"
    # Already correct AND wasn't broken to begin with
    if name == candidate:
        return None
    return candidate


def _outer_type(type_str):
    s = type_str.strip()
    s = re.split(r'[(\[]', s, maxsplit=1)[0]
    if ":" in s:
        s = s.split(":", 1)[1]
    return s


def _inner_generic_type(type_str: str) -> str | None:
    """Extrai T de `List(T)` ou `List(scg:Dictionary(...))`. Para tipos generic
    aninhados, retorna o outer do parâmetro: List(scg:Dictionary(...)) → Dictionary."""
    m = re.match(r'\s*[\w:]*List\s*\(\s*(.+)\s*\)\s*$', type_str.strip(), re.DOTALL)
    if not m:
        return None
    inner = m.group(1).strip()
    # outer of inner
    s = re.split(r'[(\[]', inner, maxsplit=1)[0]
    if ":" in s:
        s = s.split(":", 1)[1]
    return s.strip()


def _array_inner_type(type_str: str) -> str | None:
    """Extrai T de `T[]` ou `prefix:T[]`. Retorna outer local de T."""
    s = type_str.rstrip()
    if not s.endswith("[]"):
        return None
    base = s[:-2].strip()
    if ":" in base:
        base = base.split(":", 1)[1]
    return base.strip()


def _expected_prefix(type_str, type_pairs):
    outer = _outer_type(type_str)
    # List<T> → Lst + prefix(T). Convenção Sicoob: List é prefixo Lst
    # composto com prefix do tipo interno (LstSt, LstObj, LstDict, LstRow).
    if outer == "List":
        inner = _inner_generic_type(type_str)
        if inner:
            for needle, prefix in type_pairs:
                if inner == needle:
                    return f"Lst{prefix}" if prefix else "Lst"
        return "Lst"
    # Array nativo `T[]` → Arr + prefix(T). Ex.: String[]→ArrSt, Object[]→ArrObj.
    inner_arr = _array_inner_type(type_str)
    if inner_arr is not None:
        for needle, prefix in type_pairs:
            if inner_arr == needle:
                return f"Arr{prefix}" if prefix else "Arr"
        return "Arr"
    for needle, prefix in type_pairs:
        if outer == needle:
            return prefix
    return None


def _is_bare_special(name, type_str, bare_rules, reframework_vars):
    """name allowed-bare per declared rules."""
    for rule_def in bare_rules:
        sub = rule_def.get("type_substring")
        if not sub or sub not in type_str:
            continue
        names_in = rule_def.get("name_in") or []
        starts = rule_def.get("name_starts_with") or []
        if name in names_in:
            return True
        if any(name.startswith(p) for p in starts):
            return True
    if name in reframework_vars:
        return True
    return False


def detect_n1_variable_prefix(rule, fc, pc):
    """N-1: Variable name `v[Prefix][Nome]`."""
    p = _params(rule)
    type_pairs = _type_prefix_pairs(p)
    wrong_map = _wrong_prefix_map(p)
    bare_rules = _bare_special_rules(p)
    refrwk_vars = _reframework_main_vars(p)
    if not type_pairs:
        return []

    content = fc.active_content
    seen = set()
    findings = []

    for m in _RE_VARIABLE.finditer(content):
        name, type_str = m.group(1), m.group(2)
        seen.add((m.start(), name))
        f = _check_variable(rule, fc, content, name, type_str, m.start(),
                            type_pairs, wrong_map, bare_rules, refrwk_vars)
        if f:
            findings.append(f)
    for m in _RE_VARIABLE_ALT.finditer(content):
        if (m.start(), m.group(2)) in seen:
            continue
        name, type_str = m.group(2), m.group(1)
        f = _check_variable(rule, fc, content, name, type_str, m.start(),
                            type_pairs, wrong_map, bare_rules, refrwk_vars)
        if f:
            findings.append(f)
    return findings


def _check_variable(rule, fc, content, name, type_str, offset,
                    type_pairs, wrong_map, bare_rules, refrwk_vars):
    if _is_bare_special(name, type_str, bare_rules, refrwk_vars):
        return None
    expected = _expected_prefix(type_str, type_pairs)
    if expected is None:
        return None

    bad = False
    if not name.startswith("v"):
        bad = True
    else:
        rest = name[1:]
        if not _has_valid_prefix(rest, expected):
            bad = True
        else:
            # Double-stack check: prefix válido + cauda começa com wrong-prefix
            # mapped pra mesmo expected (caso `vDTabDt_X` = `DTab` + `Dt_X` onde
            # `Dt → DTab` no map). Sinal de rename anterior incompleto / legacy.
            tail = rest[len(expected):]
            if tail:
                _confusion = {"SSt": ("St",), "DTab": ("Dt", "Tab", "DT")}
                peers = _confusion.get(expected, ())
                wrong_t = _detect_wrong_prefix(tail, wrong_map)
                if wrong_t and (
                    wrong_map.get(wrong_t) == expected or wrong_t in peers
                ):
                    bad = True
    if not bad:
        return None

    all_type_prefixes = [p for _, p in type_pairs if p]
    suggested = _compute_var_fix(name, expected, wrong_map, all_type_prefixes)
    mech = None
    if suggested and suggested != name:
        mech = {
            "type": "rename_attribute",
            "from": name,
            "to": suggested,
        }
    return Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=_line_for(content, offset),
        message=f"{rule.title}: '{name}' → '{suggested or '<manual>'}' ({type_str})",
        fix_mechanical=mech,
        fix_prose=(rule.fix or {}).get("prose"),
    )


# --- N-11 (ERROR/breaking): direção de argumento inválida.
#
# Convenção Sicoob: argumento sempre `in_<Nome>`, `out_<Nome>`, `io_<Nome>`.
# Qualquer outra forma é ERRO:
#   inout_X, in_out_X (canonical é io_)
#   IN_X, OUT_X, IO_X (caps wrong)
#   In_X, Out_X (PascalCase wrong)
#   Sem direction prefix em x:Property

# Direction prefix válido EXATO (case-sensitive)
_VALID_DIRECTIONS = ("in_", "out_", "io_")

# Inválidos comuns
_INVALID_DIRECTION_PATTERNS = (
    re.compile(r"^(inout_|in_out_|InOut_|Inout_|inOut_)"),
    re.compile(r"^(IN|OUT|IO)_"),
    re.compile(r"^(In|Out|Io)_(?=[A-Z])"),
)


def _has_valid_direction(name: str) -> bool:
    return any(name.startswith(d) for d in _VALID_DIRECTIONS)


def detect_n11_argument_direction(rule, fc, pc):
    """N-11: x:Property com direção inválida.

    Convenção: `in_`, `out_`, `io_` somente. Qualquer outra forma é erro.
    Bare-args permitidos via params.bare_arg_names (Config, TransactionItem, etc.).
    """
    p = _params(rule)
    bare_args = _bare_arg_names(p)
    bare_rules = _bare_special_rules(p)
    refrwk_vars = _reframework_main_vars(p)

    content = fc.active_content
    findings = []
    seen = set()
    for re_pat in (_RE_PROPERTY, _RE_PROPERTY_ALT):
        for m in re_pat.finditer(content):
            if m.start() in seen:
                continue
            seen.add(m.start())
            if re_pat is _RE_PROPERTY:
                name, type_str = m.group(1), m.group(2)
            else:
                name, type_str = m.group(2), m.group(1)
            if not type_str.startswith(("InArgument", "OutArgument", "InOutArgument")):
                continue
            if name in bare_args:
                continue
            inner = re.search(r'\((.*)\)$', type_str)
            inner_type = inner.group(1) if inner else type_str
            if _is_bare_special(name, inner_type, bare_rules, refrwk_vars):
                continue
            if _has_valid_direction(name):
                continue
            # invalid — find which pattern
            invalid = None
            for pat in _INVALID_DIRECTION_PATTERNS:
                im = pat.match(name)
                if im:
                    invalid = im.group(0)
                    break
            # Compute suggested rename
            type_dir = "io" if type_str.startswith("InOutArgument") else (
                "out" if type_str.startswith("OutArgument") else "in"
            )
            if invalid:
                stripped = name[len(invalid):]
                cap = stripped[0].upper() + stripped[1:] if stripped else ""
                suggested = f"{type_dir}_{cap}"
            else:
                cap = name[0].upper() + name[1:] if name else ""
                suggested = f"{type_dir}_{cap}"
            mech = None
            if suggested != name:
                mech = {
                    "type": "rename_argument",
                    "from": name,
                    "to": suggested,
                    "target_workflow": fc.path.name,
                }
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, m.start()),
                message=(
                    f"{rule.title}: '{name}' usa direção inválida "
                    f"(canonical: in_/out_/io_) → '{suggested}'"
                ),
                fix_mechanical=mech,
                fix_prose=(rule.fix or {}).get("prose"),
            ))
    return findings


def detect_n2_argument_prefix(rule, fc, pc):
    """N-2: Argument name `(in_|out_|io_)[Prefix][Nome]`."""
    p = _params(rule)
    type_pairs = _type_prefix_pairs(p)
    wrong_map = _wrong_prefix_map(p)
    bare_rules = _bare_special_rules(p)
    refrwk_vars = _reframework_main_vars(p)
    bare_args = _bare_arg_names(p)
    if not type_pairs:
        return []

    content = fc.active_content
    findings = []
    seen = set()

    for m in _RE_PROPERTY.finditer(content):
        seen.add(m.start())
        f = _check_argument(rule, fc, content, m.group(1), m.group(2), m.start(),
                            type_pairs, wrong_map, bare_rules, refrwk_vars, bare_args)
        if f:
            findings.append(f)
    for m in _RE_PROPERTY_ALT.finditer(content):
        if m.start() in seen:
            continue
        f = _check_argument(rule, fc, content, m.group(2), m.group(1), m.start(),
                            type_pairs, wrong_map, bare_rules, refrwk_vars, bare_args)
        if f:
            findings.append(f)
    return findings


def _check_argument(rule, fc, content, name, type_str, offset,
                    type_pairs, wrong_map, bare_rules, refrwk_vars, bare_args):
    if type_str.startswith("InArgument"):
        direction = "in"
    elif type_str.startswith("OutArgument"):
        direction = "out"
    elif type_str.startswith("InOutArgument"):
        direction = "io"
    else:
        return None

    expected_dir = f"{direction}_"
    inner = re.search(r'\((.*)\)$', type_str)
    inner_type = inner.group(1) if inner else ""
    if _is_bare_special(name, inner_type or type_str, bare_rules, refrwk_vars):
        return None
    if name in bare_args:
        return None

    bad = False
    if not name.startswith(expected_dir):
        bad = True
    elif inner_type:
        expected_prefix = _expected_prefix(inner_type, type_pairs)
        if expected_prefix and not _has_valid_prefix(name[len(expected_dir):], expected_prefix):
            bad = True
        elif expected_prefix:
            # Sintomas de corrupção mesmo com prefix válido:
            rest_after_dir = name[len(expected_dir):]
            # 1) Direção embedded no meio (Inout_, In_, Out_)
            if _RE_EMBEDDED_DIRECTION.search(rest_after_dir):
                bad = True
            else:
                # 2) Double-stack: expected + outro_prefix(peer)|wrong→expected + Name
                tail = rest_after_dir[len(expected_prefix):]
                if tail:
                    wrong_t = _detect_wrong_prefix(tail, wrong_map)
                    if wrong_t and wrong_map[wrong_t] == expected_prefix:
                        bad = True
                    else:
                        confusion = {"SSt": ("St",), "DTab": ("Dt", "Tab", "DT")}
                        peers = confusion.get(expected_prefix, ())
                        _, found_t = _strip_known_type_prefix(
                            tail, [p for _, p in type_pairs if p]
                        )
                        if found_t and found_t in peers:
                            bad = True
    if not bad:
        return None

    expected_prefix = _expected_prefix(inner_type, type_pairs) if inner_type else None
    if expected_prefix is None:
        return None

    all_type_prefixes = [p for _, p in type_pairs if p]
    suggested = _compute_arg_fix(name, direction, expected_prefix, wrong_map, all_type_prefixes)
    mech = None
    if suggested and suggested != name:
        mech = {
            "type": "rename_argument",
            "from": name,
            "to": suggested,
            "target_workflow": fc.path.name,
        }
    return Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=_line_for(content, offset),
        message=f"{rule.title}: '{name}' → '{suggested or '<manual>'}' ({inner_type})",
        fix_mechanical=mech,
        fix_prose=(rule.fix or {}).get("prose"),
    )


def detect_n8_name_length(rule, fc, pc):
    """N-8: Variable/Property name length ≤ threshold (default 30)."""
    threshold = _params(rule).get("threshold", 30)
    content = fc.active_content
    findings = []
    seen_var = set()
    seen_prop = set()

    for m in _RE_VARIABLE.finditer(content):
        name = m.group(1)
        seen_var.add((m.start(), name))
        if len(name) > threshold:
            findings.append(_n8_finding(rule, fc, content, name, "Variable", m.start(), threshold))
    for m in _RE_VARIABLE_ALT.finditer(content):
        if (m.start(), m.group(2)) in seen_var:
            continue
        name = m.group(2)
        if len(name) > threshold:
            findings.append(_n8_finding(rule, fc, content, name, "Variable", m.start(), threshold))

    for m in _RE_PROPERTY.finditer(content):
        seen_prop.add(m.start())
        name = m.group(1)
        if len(name) > threshold:
            findings.append(_n8_finding(rule, fc, content, name, "Property", m.start(), threshold))
    for m in _RE_PROPERTY_ALT.finditer(content):
        if m.start() in seen_prop:
            continue
        name = m.group(2)
        if len(name) > threshold:
            findings.append(_n8_finding(rule, fc, content, name, "Property", m.start(), threshold))

    return findings


def _n8_finding(rule, fc, content, name, kind, offset, threshold):
    return Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=_line_for(content, offset),
        message=f"{rule.title}: {kind} '{name}' ({len(name)} chars > {threshold})",
        fix_mechanical=None,
        fix_prose=(rule.fix or {}).get("prose"),
    )


def detect_n4_arg_count(rule, fc, pc):
    """N-4: > threshold argumentos = sinal pra agrupar Dict/DataTable.

    Heurística refinada: args ja-agrupados (Dictionary, DataTable, KeyValuePair,
    Tuple, ICollection, Array, List) ja sao agrupamentos arquiteturais — contam
    com peso 0.4. Tipos simples (String, Int, Bool, etc.) contam peso 1.0.

    Total = sum_weights. Se total > threshold → finding.
    Justificativa: workflow com 8 args sendo 3 deles Dictionary nao tem mesma
    pressao arquitetural que workflow com 8 String/Int simples.
    """
    content = fc.active_content
    members_match = re.search(
        r'<x:Members\s*>(.*?)</x:Members>', content, re.DOTALL
    )
    if not members_match:
        return []
    block = members_match.group(1)
    threshold = _params(rule).get("threshold", 7)

    # Identify each x:Property + its Type
    prop_re = re.compile(
        r'<x:Property\b[^>]*\bType="((?:In|Out|InOut)Argument\(([^)]*(?:\([^)]*\)[^)]*)*)\))"',
        re.DOTALL,
    )
    grouped_marker_re = re.compile(
        r'(?:Dictionary|DataTable|KeyValuePair|Tuple|ICollection|IList|IEnumerable|List|HashSet|Stack|Queue|String\[\]|Int32\[\]|Object\[\]|Boolean\[\])',
        re.IGNORECASE,
    )

    weighted_total = 0.0
    n_simple = 0
    n_grouped = 0
    for m in prop_re.finditer(block):
        inner_type = m.group(2)
        if grouped_marker_re.search(inner_type):
            n_grouped += 1
            weighted_total += 0.4
        else:
            n_simple += 1
            weighted_total += 1.0
    # Also handle properties whose Type attr regex misses (complex nested):
    # count raw <x:Property> matches as fallback weight 1 if not captured above.
    total_raw = len(re.findall(r'<x:Property\b', block))
    accounted = n_simple + n_grouped
    weighted_total += max(0, total_raw - accounted) * 1.0
    n_raw = total_raw

    if weighted_total <= threshold:
        return []
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=_line_for(content, members_match.start()),
        message=(
            f"{rule.title}: {n_raw} argumentos "
            f"(simples={n_simple}, agrupados={n_grouped}, peso={weighted_total:.1f}, "
            f"threshold {threshold})"
        ),
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )]
