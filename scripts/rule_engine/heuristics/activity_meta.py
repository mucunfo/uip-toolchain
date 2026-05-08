"""Heuristic for activity metadata schema validation (M-* rules).

Loads `assets/activities/activities-compact.json` (built by
`scripts/activities_meta/build-schema.ps1`) and exposes lookups + per-check
detectors consumed by `detect_activity_signature` in `detectors.py`.

Schema regenerated offline (Mono.Cecil reflection over installed nuget
packages). See `scripts/activities_meta/README.md`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from scripts.rule_engine._types import Finding


SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "assets"
    / "activities"
    / "activities-compact.json"
)

# UiPath xmlns canônicos. Derivado dinamicamente do schema (F11) — não
# hardcoded. Acessar via `is_canonical_xmlns()` ou `get_canonical_xmlns_set()`.
# Fallback mínimo se schema não carrega (defensivo).
_FALLBACK_UIPATH_XMLNS = frozenset({
    "http://schemas.uipath.com/workflow/activities",
})

# Schema indexa DataObjects (Target, *Argument, *Modification etc) com
# Kind="DataObject". Lookup distingue via .kind. Whitelist hardcoded foi
# removida — fonte de verdade agora é o schema.


@dataclass(frozen=True)
class ArgDef:
    name: str
    type: str
    direction: str  # In | Out | InOut | Plain
    is_argument: bool  # True = InArgument/OutArgument; False = property pura
    required: bool
    overload_group: Optional[str]
    default: object
    label: Optional[str] = None  # human-readable derivado da DisplayName resource key
    collection_item_type: Optional[str] = None  # F34: tipo aceito em coleção


@dataclass(frozen=True)
class ActivityDef:
    fqn: str
    pkg: str
    kind: str  # "Activity" | "DataObject"
    xmlns: Optional[str]
    category: Optional[str]
    args: tuple[ArgDef, ...]
    # F34: parent-restrictive determination via schema
    content_property: Optional[str] = None  # nome da prop default-child (XAML)
    activity_shape: Optional[str] = None    # Activity|ActivityAction|ActivityFunc|...

    @property
    def required_args(self) -> tuple[ArgDef, ...]:
        return tuple(a for a in self.args if a.required)

    def arg_by_name(self, name: str) -> ArgDef | None:
        for a in self.args:
            if a.name == name:
                return a
        return None


class ActivitySchema:
    """Indexed view of activities-compact.json."""

    def __init__(self, entries: list[dict]):
        self._by_fqn: dict[str, ActivityDef] = {}
        self._by_xmlns_local: dict[tuple[str, str], list[ActivityDef]] = {}
        self._canonical_xmlns: set[str] = set()
        for e in entries:
            fqn = e["fqn"]
            args = tuple(
                ArgDef(
                    name=a["n"],
                    type=a.get("t") or "?",
                    direction=a.get("d") or "In",
                    is_argument=bool(a.get("a", True)),
                    required=bool(a.get("r")),
                    overload_group=a.get("g"),
                    default=a.get("v"),
                    label=a.get("l"),
                    collection_item_type=a.get("cit"),  # F34
                )
                for a in (e.get("args") or [])
            )
            ad = ActivityDef(
                fqn=fqn,
                pkg=e.get("pkg", ""),
                kind=e.get("kind", "Activity"),
                xmlns=e.get("xmlns"),
                category=e.get("category"),
                args=args,
                content_property=e.get("contentProperty"),  # F34
                activity_shape=e.get("activityShape"),       # F34
            )
            self._by_fqn[fqn] = ad
            local = fqn.rsplit(".", 1)[-1]
            local_clean = local.split("`")[0]
            xmlns = e.get("xmlns")
            if xmlns:
                self._canonical_xmlns.add(xmlns)
                self._by_xmlns_local.setdefault((xmlns, local_clean), []).append(ad)
                if local != local_clean:
                    self._by_xmlns_local.setdefault((xmlns, local), []).append(ad)

    def by_fqn(self, fqn: str) -> ActivityDef | None:
        return self._by_fqn.get(fqn)

    def candidates(self, xmlns: str, local_name: str) -> list[ActivityDef]:
        return list(self._by_xmlns_local.get((xmlns, local_name), []))

    def is_canonical_xmlns(self, uri: Optional[str]) -> bool:
        """True se URI aparece em pelo menos 1 entry do schema."""
        if not uri:
            return False
        return uri in self._canonical_xmlns

    def canonical_xmlns_set(self) -> frozenset[str]:
        return frozenset(self._canonical_xmlns) or _FALLBACK_UIPATH_XMLNS

    @property
    def size(self) -> int:
        return len(self._by_fqn)


_singleton: ActivitySchema | None = None
_singleton_mtime: float = 0.0


# F34: Parent-restrictive classification via schema.
#
# Resultado: ('open' | 'wrap_able' | 'restrictive' | 'unknown')
#   open       — multi-child accept (Sequence-like)
#   wrap_able  — single-child slot, accept Activity-shape (wrap em Sequence OK)
#   restrictive — argumented/typed shape, NÃO aceita LogMessage child
#   unknown    — schema não cobre; caller fallback hardcoded list

_RESTRICTIVE_ARG_DIRECTIONS = frozenset({"In", "Out", "InOut"})


def classify_parent_for_logmessage(
    parent_qual: str,
    schema: ActivitySchema | None = None,
) -> str:
    """Classifica parent (ex: 'ui:HttpClient', 'Assign.Value', 'ActivityAction')
    contra schema. Retorna 'open' | 'wrap_able' | 'restrictive' | 'unknown'.

    Decisões:
      1. Qualified-property `Owner.Prop`:
         - Se `Owner.Prop` corresponde a property `Prop` em `Owner` activity:
           - is_argument (InArgument/OutArgument/InOutArgument) → restrictive.
           - collection_item_type definido → restrictive (collection tipada).
           - Type contém "Activity" sem ser Argument → wrap_able.
           - Else → restrictive (default conservador).
         - Activity Owner desconhecida → unknown.
      2. Non-qualified `Owner` (top-level activity name):
         - activity_shape == "ActivityAction" → wrap_able.
         - activity_shape == "ActivityFunc" → restrictive (signature delegate).
         - activity_shape em Activity/NativeActivity/Sequence/Body — open.
         - Else → unknown (não Activity, ex: container genérico).
    """
    if schema is None:
        try:
            schema = get_schema()
        except FileNotFoundError:
            return "unknown"

    # Strip xmlns prefix
    bare = parent_qual.split(":", 1)[-1]

    if "." in bare:
        # Qualified property element
        owner_local, prop_name = bare.split(".", 1)
        # Lookup activity by local name (try multiple xmlns)
        owner = None
        for xmlns in schema.canonical_xmlns_set():
            cands = schema.candidates(xmlns, owner_local)
            if cands:
                owner = cands[0]
                break
        if owner is None:
            return "unknown"
        prop = owner.arg_by_name(prop_name)
        if prop is None:
            return "unknown"
        # is_argument (typed In/Out/InOut) é shape específica → restrictive
        if prop.is_argument and prop.direction in _RESTRICTIVE_ARG_DIRECTIONS:
            return "restrictive"
        # collection_item_type definido → coleção tipada
        if prop.collection_item_type:
            # Se item type é Activity-base, ainda restrictive (não pode misturar)
            return "restrictive"
        # Property type contém "Activity" → single Activity slot, wrap_able
        if prop.type and ("Activity" in prop.type
                           and "Argument" not in prop.type):
            return "wrap_able"
        # Default conservador: outras qualified-properties consideradas
        # restrictive até confirmação contrária.
        return "restrictive"

    # Non-qualified: top-level activity by local name
    owner = None
    for xmlns in schema.canonical_xmlns_set():
        cands = schema.candidates(xmlns, bare)
        if cands:
            owner = cands[0]
            break
    if owner is None:
        # Pode ser Sequence base type, ActivityAction, etc.
        if bare == "ActivityAction":
            return "wrap_able"
        if bare == "ActivityFunc":
            return "restrictive"
        if bare in ("Sequence", "Flowchart", "StateMachine", "State"):
            return "open"
        return "unknown"
    if owner.activity_shape == "ActivityAction":
        return "wrap_able"
    if owner.activity_shape == "ActivityFunc":
        return "restrictive"
    if owner.activity_shape in ("Activity", "NativeActivity",
                                  "AsyncCodeActivity", "CodeActivity",
                                  "Sequence"):
        return "open"
    return "unknown"


def get_schema() -> ActivitySchema:
    """Lazy-load schema; auto-reload if file mtime > singleton load time."""
    global _singleton, _singleton_mtime
    if not SCHEMA_PATH.exists():
        if _singleton is not None:
            return _singleton  # use stale if file disappeared mid-process
        raise FileNotFoundError(
            f"Activity schema não encontrado em {SCHEMA_PATH}. "
            "Rode scripts/activities_meta/batch-extract.ps1 + build-schema.ps1."
        )
    current_mtime = SCHEMA_PATH.stat().st_mtime
    if _singleton is None or current_mtime > _singleton_mtime:
        data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
        _singleton = ActivitySchema(data)
        _singleton_mtime = current_mtime
    return _singleton


# ---------------------------------------------------------------------------
# XAML parsing helpers (regex-based; mantém line numbers reais)
# ---------------------------------------------------------------------------

# Captura `xmlns:prefix="uri"` no XAML root. Não cobre default xmlns (usaremos
# em fase 2 se necessário; activities UiPath sempre usam prefixo).
_RE_XMLNS_DECL = re.compile(r'xmlns:(\w+)="([^"]+)"')

# Captura tag de abertura com prefixo qualificado: <ui:WriteRange ...>
# group(1)=prefixo, group(2)=local name, group(3)=corpo até `>` (atributos).
# `[^/>]` para impedir capturar property elements (`<ui:X.Foo>`).
_RE_QUALIFIED_TAG = re.compile(
    r'<(\w+):([A-Za-z][\w]*)((?:\s+[^>]*?)?)(/?>)',
    re.DOTALL,
)

# Atributos dentro do corpo de uma tag de abertura. Pega `Name="value"` ou
# `prefix:Name="value"`. Captura name (com prefix opcional) + value.
# Lookbehind exige whitespace ou inicio (impede capturar `IdRef` em
# `sap2010:WorkflowViewState.IdRef="..."`).
_RE_ATTR = re.compile(r'(?:(?<=\s)|(?<=^))(?:(\w+):)?(\w+)\s*=\s*"([^"]*)"')

# System/markup prefixes a ignorar quando não resolvem activity.
_SKIP_PREFIXES = frozenset({"x", "mc", "sap", "sap2010", "mva", "scg", "sco"})


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def _parse_xmlns_decls(content: str) -> dict[str, str]:
    """Returns prefix→uri for all xmlns:* declarations found in content."""
    return dict(_RE_XMLNS_DECL.findall(content))


@dataclass
class XamlActivityRef:
    """Activity element parsed from XAML."""
    prefix: str
    local_name: str
    xmlns: Optional[str]
    attrs: dict[str, str]
    line: int
    tag_start: int  # offset in content
    tag_end: int


def parse_activities(content: str) -> tuple[dict[str, str], list[XamlActivityRef]]:
    """Returns (xmlns_decls, activity_refs).

    Refs include qualified tags with non-system prefix and a non-property
    local name (i.e. without a `.` — `<ui:X.Foo>` is property element, skipped).
    """
    xmlns_decls = _parse_xmlns_decls(content)
    refs: list[XamlActivityRef] = []
    for m in _RE_QUALIFIED_TAG.finditer(content):
        prefix = m.group(1)
        local = m.group(2)
        body = m.group(3) or ""
        if prefix in _SKIP_PREFIXES:
            continue
        if "." in local:
            # property element <ui:X.Foo> — não é activity
            continue
        attrs = {}
        for am in _RE_ATTR.finditer(body):
            attr_prefix = am.group(1) or ""
            attr_name = am.group(2)
            attr_val = am.group(3)
            # `x:Class`, `x:TypeArguments` etc são metadados, mantém prefixados
            full_name = f"{attr_prefix}:{attr_name}" if attr_prefix else attr_name
            attrs[full_name] = attr_val
        refs.append(XamlActivityRef(
            prefix=prefix,
            local_name=local,
            xmlns=xmlns_decls.get(prefix),
            attrs=attrs,
            line=_line_for(content, m.start()),
            tag_start=m.start(),
            tag_end=m.end(),
        ))
    return xmlns_decls, refs


def resolve_activity_def(
    schema: ActivitySchema, ref: XamlActivityRef
) -> tuple[Optional[ActivityDef], list[ActivityDef]]:
    """Returns (resolved_def, candidates).

    If exactly 1 candidate matches xmlns+local_name → resolved.
    If multiple → returns None + candidates (caller pode desambiguar via args).
    If zero → returns None + [].
    """
    if not ref.xmlns:
        return None, []
    candidates = schema.candidates(ref.xmlns, ref.local_name)
    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


# ---------------------------------------------------------------------------
# Per-check functions (consumidos por detect_activity_signature)
# ---------------------------------------------------------------------------


def _emit(rule, fc, line: int, msg: str, fix_mechanical=None) -> Finding:
    return Finding(
        rule_id=rule.id,
        severity=rule.severity,
        category=rule.category,
        file=str(fc.path),
        line=line,
        message=f"{rule.title}: {msg}",
        fix_mechanical=fix_mechanical or (rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )


def _check_unknown(rule, fc, schema, refs) -> list[Finding]:
    """M-1: emite só para xmlns canônicos UiPath conhecidos.

    Custom packages (clr-namespace) ficam pra fase 2 quando engine cruzar
    com project.json. Hoje emitir sobre custom = false-positive em qualquer
    library proprietária.
    """
    findings = []
    for ref in refs:
        # Skip xmlns não-canônico (custom packages, clr-namespace, third-party)
        if not schema.is_canonical_xmlns(ref.xmlns):
            continue
        candidates = schema.candidates(ref.xmlns, ref.local_name)
        if not candidates:
            findings.append(_emit(
                rule, fc, ref.line,
                f"<{ref.prefix}:{ref.local_name}> não existe no schema (xmlns={ref.xmlns})"
            ))
    return findings


def _levenshtein(a: str, b: str, max_dist: int = 3) -> int:
    """Compute Levenshtein distance with early exit at max_dist+1."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > max_dist:
        return max_dist + 1
    if la == 0 or lb == 0:
        return la or lb
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * lb
        min_row = curr[0]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j-1] + 1, prev[j] + 1, prev[j-1] + cost)
            if curr[j] < min_row:
                min_row = curr[j]
        if min_row > max_dist:
            return max_dist + 1
        prev = curr
    return prev[lb]


def _suggest_arg(name: str, valid: list[str], max_dist: int = 2) -> str | None:
    """Returns closest valid name within max_dist edits, case-insensitive comparison.
    Returns None if no candidate ≤ max_dist."""
    best = None
    best_dist = max_dist + 1
    name_lower = name.lower()
    for v in valid:
        d = _levenshtein(name_lower, v.lower(), max_dist)
        if d < best_dist:
            best_dist = d
            best = v
    return best


def _check_unknown_arg(rule, fc, schema, refs) -> list[Finding]:
    """M-3: arg fornecido não existe em adef.args (typo / arg removida).

    Mensagem inclui sugestão Levenshtein quando match próximo (≤2 edits)
    existe no schema da activity. Sem mecânico (rename é judgment humano).
    """
    findings = []
    for ref in refs:
        adef, _ = resolve_activity_def(schema, ref)
        if adef is None:
            continue
        provided = _collect_provided_args(ref, fc.active_content)
        valid_names = sorted({a.name for a in adef.args})
        always_ok = {"DisplayName", "ContinueOnError", "TimeoutMS", "DelayBefore", "DelayAfter"}
        for name in provided:
            if name in valid_names or name in always_ok:
                continue
            suggestion = _suggest_arg(name, valid_names)
            hint = f" — você quis dizer '{suggestion}'?" if suggestion else ""
            findings.append(_emit(
                rule, fc, ref.line,
                f"<{ref.prefix}:{ref.local_name}> tem arg desconhecido '{name}'{hint} "
                f"(válidos: {', '.join(valid_names[:6])}{'...' if len(valid_names)>6 else ''})"
            ))
    return findings


def _check_overload_conflict(rule, fc, schema, refs) -> list[Finding]:
    """M-4: args required de OverloadGroups distintos preenchidos juntos."""
    findings = []
    for ref in refs:
        adef, _ = resolve_activity_def(schema, ref)
        if adef is None:
            continue
        provided = _collect_provided_args(ref, fc.active_content)
        groups_with_provided: dict[str, list[str]] = {}
        for a in adef.args:
            if a.overload_group and a.name in provided:
                groups_with_provided.setdefault(a.overload_group, []).append(a.name)
        if len(groups_with_provided) > 1:
            details = "; ".join(
                f"{g}=[{', '.join(names)}]" for g, names in groups_with_provided.items()
            )
            findings.append(_emit(
                rule, fc, ref.line,
                f"<{ref.prefix}:{ref.local_name}> mistura args de OverloadGroups "
                f"mutuamente exclusivos: {details}"
            ))
    return findings


def _check_xmlns_missing(rule, fc, schema, refs) -> list[Finding]:
    """M-6: usa prefix UiPath conhecido mas xmlns não declarado no root."""
    findings = []
    seen_prefixes = set()
    for ref in refs:
        if ref.xmlns is not None:
            continue
        if ref.prefix not in _UIPATH_PREFIX_ALIASES:
            continue
        if ref.prefix in seen_prefixes:
            continue  # 1 finding por prefix faltante
        seen_prefixes.add(ref.prefix)
        findings.append(_emit(
            rule, fc, ref.line,
            f"prefix '{ref.prefix}' usado em <{ref.prefix}:{ref.local_name}> "
            f"mas xmlns:{ref.prefix} não declarado no <Activity> root"
        ))
    return findings


# ---------------------------------------------------------------------------
# M-5 — type mismatch (literais)
# ---------------------------------------------------------------------------

# Tipos numéricos .NET aceitos como destino de literal numérico.
_NUMERIC_TYPES = frozenset({
    "System.Int16", "System.Int32", "System.Int64",
    "System.UInt16", "System.UInt32", "System.UInt64",
    "System.Single", "System.Double", "System.Decimal", "System.Byte",
})
_BOOLEAN_TYPES = frozenset({"System.Boolean"})
_STRING_TYPES = frozenset({"System.String"})
_DATETIME_TYPES = frozenset({"System.DateTime", "System.DateTimeOffset", "System.TimeSpan"})

# True se valor é expressão (bind, lambda, x:Null) — skip type check.
_RE_BIND = re.compile(r'^\s*\[.+\]\s*$', re.DOTALL)
_RE_NUMERIC_LITERAL = re.compile(r'^-?\d+(\.\d+)?$')
_RE_DATETIME_LITERAL = re.compile(r'^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?$')
# TimeSpan format: hh:mm:ss[.fffffff] ou d.hh:mm:ss
_RE_TIMESPAN_LITERAL = re.compile(r'^-?(\d+\.)?\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?$')

# VB cast helpers within bind expression. Map ao tipo inferido.
_VB_CAST_MAP = {
    "CInt": "int", "CLng": "int", "CShort": "int", "CByte": "int",
    "CDbl": "float", "CSng": "float", "CDec": "float",
    "CStr": "string",
    "CBool": "bool",
    "CDate": "datetime",
}
_RE_VB_CAST = re.compile(r'^\s*\[\s*(C(?:Int|Lng|Short|Byte|Dbl|Sng|Dec|Str|Bool|Date))\s*\(', re.IGNORECASE)
_RE_VB_CTYPE = re.compile(r'^\s*\[\s*CType\s*\(.+?,\s*(\w+)\s*\)\s*\]\s*$', re.DOTALL)
_RE_VB_NEW = re.compile(r'^\s*\[\s*New\s+(\w+(?:\.\w+)*)\b', re.IGNORECASE)
_RE_VB_STRING_CONCAT = re.compile(r'"[^"]*"\s*[&+]')
_RE_VB_TOSTRING = re.compile(r'\.ToString\s*\(', re.IGNORECASE)
_RE_VB_NOTHING = re.compile(r'^\s*Nothing\s*$', re.IGNORECASE)


def _is_bind_or_null(value: str) -> bool:
    if value is None:
        return True
    v = value.strip()
    if not v:
        return True
    if v == "{x:Null}":
        return True
    if _RE_BIND.match(v):
        return True
    # Markup extensions {Binding ...}, {StaticResource ...} etc.
    if v.startswith("{") and v.endswith("}"):
        return True
    return False


def _classify_literal(value: str) -> str:
    """Returns 'string' | 'int' | 'float' | 'bool' | 'datetime' | 'timespan'."""
    v = value.strip()
    if v.lower() in ("true", "false"):
        return "bool"
    if _RE_NUMERIC_LITERAL.match(v):
        return "float" if "." in v else "int"
    if _RE_DATETIME_LITERAL.match(v):
        return "datetime"
    if _RE_TIMESPAN_LITERAL.match(v):
        return "timespan"
    return "string"


def _infer_vb_bind_type(expr: str) -> Optional[str]:
    """Try to infer the type of a VB bind expression `[...]`.

    Returns 'int'|'float'|'string'|'bool'|'datetime' if confident, else None
    (means: skip type check; could be anything).
    """
    if not expr:
        return None
    e = expr.strip()
    # CType(x, T) — second arg is target type.
    m = _RE_VB_CTYPE.match(e)
    if m:
        target = m.group(1)
        if target in ("Integer", "Int32", "Int64", "Long", "Short"):
            return "int"
        if target in ("Double", "Single", "Decimal"):
            return "float"
        if target == "String":
            return "string"
        if target == "Boolean":
            return "bool"
        if target in ("Date", "DateTime"):
            return "datetime"
        return None
    # CInt(...), CStr(...), CBool(...), etc.
    m = _RE_VB_CAST.match(e)
    if m:
        cast_fn = m.group(1)
        # Normalize case (CInt or cint both valid in VB)
        for key, kind in _VB_CAST_MAP.items():
            if cast_fn.lower() == key.lower():
                return kind
    # New T(...) — inferr T
    m = _RE_VB_NEW.match(e)
    if m:
        target = m.group(1).rsplit(".", 1)[-1]
        if target in ("Integer", "Int32", "Int64", "Long"):
            return "int"
        if target == "String":
            return "string"
        if target == "Boolean":
            return "bool"
        if target in ("DateTime", "Date"):
            return "datetime"
        if target == "TimeSpan":
            return "timespan"
        return None
    # String concatenation `"abc" & x` → string
    if _RE_VB_STRING_CONCAT.search(e):
        return "string"
    # `.ToString()` → string
    if _RE_VB_TOSTRING.search(e):
        return "string"
    # Nothing → null (sinaliza separadamente)
    inner = e.strip("[]").strip()
    if _RE_VB_NOTHING.match(inner):
        return "null"
    return None


def _is_compatible(literal_kind: str, schema_type: Optional[str]) -> bool:
    """Conservative compat: only flag obvious mismatches."""
    if not schema_type:
        return True
    # Strip generic suffix; accept with or without "System." prefix (build-schema
    # normalizes types removing prefix).
    bare = schema_type.split("`")[0]
    if not bare.startswith("System."):
        bare_full = "System." + bare
    else:
        bare_full = bare
    if bare_full in _STRING_TYPES:
        return True
    if bare_full in _BOOLEAN_TYPES:
        return literal_kind == "bool"
    if bare_full in _NUMERIC_TYPES:
        return literal_kind in ("int", "float")
    if bare_full in _DATETIME_TYPES:
        return literal_kind in ("datetime", "timespan")
    return True


def _check_type_mismatch(rule, fc, schema, refs) -> list[Finding]:
    """M-5: literal/expressão incompatível com tipo do arg.

    Cobre 2 caminhos:
      1. Literal direto: classify_literal vs schema_type.
      2. Bind expression VB: tenta inferir tipo via _infer_vb_bind_type
         (CInt/CStr/CBool/CDate/CType/concat/.ToString/New). Se inferido
         e incompatível → flag. Se não conseguir inferir → skip.
    """
    findings = []
    for ref in refs:
        adef, _ = resolve_activity_def(schema, ref)
        if adef is None:
            continue
        for attr_name, attr_val in ref.attrs.items():
            if ":" in attr_name:
                continue
            if attr_val is None:
                continue
            v_strip = attr_val.strip()
            # markup extensions / x:Null = skip
            if v_strip == "{x:Null}" or (v_strip.startswith("{") and v_strip.endswith("}")):
                continue
            arg = adef.arg_by_name(attr_name)
            if arg is None or not arg.type:
                continue

            # Bind expression VB
            if _RE_BIND.match(v_strip):
                inferred = _infer_vb_bind_type(v_strip)
                if inferred is None or inferred == "null":
                    continue
                if not _is_compatible(inferred, arg.type):
                    expected = arg.type.replace("System.", "")
                    findings.append(_emit(
                        rule, fc, ref.line,
                        f"<{ref.prefix}:{ref.local_name}> arg '{attr_name}' = "
                        f"\"{v_strip[:40]}{'...' if len(v_strip)>40 else ''}\" "
                        f"(VB infere {inferred}) incompatível com tipo {expected}"
                    ))
                continue

            # Literal direto
            kind = _classify_literal(attr_val)
            if not _is_compatible(kind, arg.type):
                expected = arg.type.replace("System.", "")
                findings.append(_emit(
                    rule, fc, ref.line,
                    f"<{ref.prefix}:{ref.local_name}> arg '{attr_name}' = "
                    f"\"{attr_val[:40]}{'...' if len(attr_val)>40 else ''}\" "
                    f"(literal {kind}) incompatível com tipo {expected}"
                ))
    return findings


# Tipos valor .NET — não aceitam Nothing/null direto em VB sem nullable wrapper.
_VALUE_TYPES = (
    _NUMERIC_TYPES
    | _BOOLEAN_TYPES
    | _DATETIME_TYPES
    | frozenset({"System.Char", "System.Guid"})
)


def _check_nothing_in_value_type(rule, fc, schema, refs) -> list[Finding]:
    """M-8 (VB): bind expression `[Nothing]` em InArgument tipo valor.

    VB: `Integer`, `Boolean`, `DateTime`, etc não aceitam Nothing direto
    via expressão. Studio runtime joga InvalidOperationException quando
    Expression resolve para Nothing em arg tipo valor.

    NÃO inclui `{x:Null}` em attribute form: isso significa "InArgument
    não fornecido" (activity usa default), não "Expression=Nothing".
    Só `[Nothing]` (bind expression) transmite null real.
    """
    findings = []
    for ref in refs:
        adef, _ = resolve_activity_def(schema, ref)
        if adef is None:
            continue
        for attr_name, attr_val in ref.attrs.items():
            if ":" in attr_name:
                continue
            if attr_val is None:
                continue
            v_strip = attr_val.strip()
            # Apenas bind expression `[Nothing]` (case-insensitive em VB).
            if not (v_strip.startswith("[") and v_strip.endswith("]")):
                continue
            inner = v_strip[1:-1].strip()
            if not _RE_VB_NOTHING.match(inner):
                continue
            arg = adef.arg_by_name(attr_name)
            if arg is None or not arg.type:
                continue
            bare = arg.type.split("`")[0]
            full = bare if bare.startswith("System.") else "System." + bare
            if "Nullable" in arg.type:
                continue
            if full not in _VALUE_TYPES:
                continue
            expected = bare
            findings.append(_emit(
                rule, fc, ref.line,
                f"<{ref.prefix}:{ref.local_name}> arg '{attr_name}' = "
                f"{v_strip} (VB Nothing) mas tipo é valor ({expected}) — "
                f"InvalidOperationException em runtime"
            ))
    return findings


def _check_redundant_default(rule, fc, schema, refs) -> list[Finding]:
    """M-7: arg explicitamente atribuído com valor igual ao default do schema."""
    findings = []
    for ref in refs:
        adef, _ = resolve_activity_def(schema, ref)
        if adef is None:
            continue
        for attr_name, attr_val in ref.attrs.items():
            if ":" in attr_name:
                continue
            arg = adef.arg_by_name(attr_name)
            if arg is None or arg.default is None:
                continue
            schema_default = str(arg.default)
            if attr_val == schema_default:
                findings.append(_emit(
                    rule, fc, ref.line,
                    f"<{ref.prefix}:{ref.local_name}> atribui '{attr_name}=\"{attr_val}\"' "
                    f"que é igual ao default do schema (omitir é equivalente)"
                ))
    return findings


def _check_required_missing(rule, fc, schema, refs) -> list[Finding]:
    """Required arg ausente.

    OverloadGroup semantics: cada activity tem N groups; cada group representa
    uma combinação válida. Se >=1 group teve TODOS seus required satisfeitos,
    os requireds dos outros groups NÃO precisam estar preenchidos.
    Args required sem group são sempre obrigatórios.
    """
    findings = []
    for ref in refs:
        adef, candidates = resolve_activity_def(schema, ref)
        if adef is None:
            continue  # resolvido por M-1
        # 1. Args fornecidos
        provided = _collect_provided_args(ref, fc.active_content)

        # 2. Particiona required args
        required_no_group: list[ArgDef] = []
        required_by_group: dict[str, list[ArgDef]] = {}
        for a in adef.required_args:
            if a.overload_group:
                required_by_group.setdefault(a.overload_group, []).append(a)
            else:
                required_no_group.append(a)

        # 3. Identifica groups completamente satisfeitos
        any_group_satisfied = False
        for group_name, args in required_by_group.items():
            if all(a.name in provided for a in args):
                any_group_satisfied = True
                break

        # 4. Emit findings
        # 4a. Args sem group: sempre required
        for a in required_no_group:
            if a.name not in provided:
                fix_mech = {
                    "type": "add_property_element",
                    "prefix": ref.prefix,
                    "activity_local": ref.local_name,
                    "prop_name": a.name,
                    "prop_type": a.type,
                    "default": a.default,
                    "tag_line": ref.line,
                }
                findings.append(_emit(
                    rule, fc, ref.line,
                    f"<{ref.prefix}:{ref.local_name}> falta arg required '{a.name}' (tipo {a.type})",
                    fix_mechanical=fix_mech,
                ))
        # 4b. Args com group: só emite se NENHUM group satisfeito
        if required_by_group and not any_group_satisfied:
            best_group = None
            best_score = -1
            for group_name, args in required_by_group.items():
                score = sum(1 for a in args if a.name in provided)
                if score > best_score:
                    best_score = score
                    best_group = group_name
            if best_group:
                for a in required_by_group[best_group]:
                    if a.name not in provided:
                        fix_mech = {
                            "type": "add_property_element",
                            "prefix": ref.prefix,
                            "activity_local": ref.local_name,
                            "prop_name": a.name,
                            "prop_type": a.type,
                            "default": a.default,
                            "tag_line": ref.line,
                        }
                        findings.append(_emit(
                            rule, fc, ref.line,
                            f"<{ref.prefix}:{ref.local_name}> falta arg required '{a.name}' "
                            f"(tipo {a.type}, group={best_group}; alternativas: "
                            f"{', '.join(g for g in required_by_group if g != best_group) or 'nenhuma'})",
                            fix_mechanical=fix_mech,
                        ))
    return findings


# Aliases comuns que projetos UiPath usam para xmlns canônicos. Se prefix
# bater mas xmlns não declarado, M-6 emite.
_UIPATH_PREFIX_ALIASES = frozenset({"ui", "uix", "cv", "isactr", "uitp"})


def _collect_provided_args(ref: XamlActivityRef, content: str) -> set[str]:
    """Args fornecidos via attribute form ou property element form.

    Atributos com valor literal `{x:Null}` são considerados não-providos
    (Studio salva placeholder). Atributos qualificados com prefix (sap:, etc)
    são metadata do designer, não args.
    """
    provided = {
        k for k, v in ref.attrs.items()
        if ":" not in k and v != "{x:Null}"
    }
    pe_pattern = re.compile(
        rf'<{re.escape(ref.prefix)}:{re.escape(ref.local_name)}\.(\w+)\b'
    )
    for pem in pe_pattern.finditer(content):
        provided.add(pem.group(1))
    return provided


def _xaml_pre(fc):
    """Returns (schema, refs) or None se XAML inválido / non-XAML / sem refs."""
    if not str(fc.path).lower().endswith(".xaml"):
        return None
    schema = get_schema()
    _, refs = parse_activities(fc.active_content)
    if not refs:
        return None
    return schema, refs


# ---------------------------------------------------------------------------
# Public detector entry points (consumidos via detect.type=python em rules.yaml)
# ---------------------------------------------------------------------------


def detect_m1_activity_unknown(rule, fc, pc):
    """M-1: activity FQN não existe em schema."""
    pre = _xaml_pre(fc)
    if pre is None:
        return []
    schema, refs = pre
    return _check_unknown(rule, fc, schema, refs)


def detect_m2_required_missing(rule, fc, pc):
    """M-2: required arg ausente (respeita OverloadGroups)."""
    pre = _xaml_pre(fc)
    if pre is None:
        return []
    schema, refs = pre
    return _check_required_missing(rule, fc, schema, refs)


def detect_m3_unknown_arg(rule, fc, pc):
    """M-3: arg fornecido não existe na activity."""
    pre = _xaml_pre(fc)
    if pre is None:
        return []
    schema, refs = pre
    return _check_unknown_arg(rule, fc, schema, refs)


def detect_m4_overload_conflict(rule, fc, pc):
    """M-4: args de OverloadGroups distintos preenchidos juntos."""
    pre = _xaml_pre(fc)
    if pre is None:
        return []
    schema, refs = pre
    return _check_overload_conflict(rule, fc, schema, refs)


def detect_m5_type_mismatch(rule, fc, pc):
    """M-5: literal em InArgument com tipo incompatível."""
    pre = _xaml_pre(fc)
    if pre is None:
        return []
    schema, refs = pre
    return _check_type_mismatch(rule, fc, schema, refs)


def detect_m8_nothing_in_value_type(rule, fc, pc):
    """M-8 (VB): Nothing/x:Null em InArgument tipo valor."""
    pre = _xaml_pre(fc)
    if pre is None:
        return []
    schema, refs = pre
    return _check_nothing_in_value_type(rule, fc, schema, refs)


def detect_m6_xmlns_missing(rule, fc, pc):
    """M-6: prefix UiPath usado sem xmlns declarado."""
    pre = _xaml_pre(fc)
    if pre is None:
        return []
    schema, refs = pre
    return _check_xmlns_missing(rule, fc, schema, refs)


def detect_m7_redundant_default(rule, fc, pc):
    """M-7: arg atribuído com valor igual ao default do schema."""
    pre = _xaml_pre(fc)
    if pre is None:
        return []
    schema, refs = pre
    return _check_redundant_default(rule, fc, schema, refs)
