"""Heuristics for U-* rules — unused/undeclared identifiers in XAML.

U-1: variables declared in `<*.Variables>` never referenced in scope.
U-2: arguments declared in `<x:Members>` never read in callee body and
     never bound by any caller (cross-file, scoped to project).
U-3: identifiers used in expressions but not resolvable in scope chain
     (variables, arguments, delegate args, system globals, namespaces).

Sprint 1: detect-only. Fixers in sprint 2.
"""
from __future__ import annotations

import re
from html import unescape as _xml_unescape
from pathlib import Path
from typing import Iterable

from uip_engine._types import Finding


# ---------- Common helpers ----------

# Word-boundary identifier pattern, used for whole-word case-insensitive matches.
def _ident_re(name: str) -> re.Pattern:
    return re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


# Strip annotation text + property attributes (these are documentation,
# not real uses). Replace with whitespace of same length so offsets stay
# stable for line lookup.
_RE_ANNOTATION = re.compile(
    r'<sap2010:Annotation\.AnnotationText>.*?</sap2010:Annotation\.AnnotationText>',
    re.DOTALL,
)
_RE_ANNOTATION_ATTR = re.compile(
    r'sap2010:Annotation\.AnnotationText\s*=\s*"[^"]*"'
)
_RE_PROPERTY_ATTRS = re.compile(
    r'<x:Property\.Attributes>.*?</x:Property\.Attributes>',
    re.DOTALL,
)


def _scrub_doc_regions(content: str) -> str:
    """Replace annotation/property-attribute regions with spaces so identifier
    matches in those regions are ignored."""
    def _blank(m: re.Match) -> str:
        return " " * len(m.group(0))
    out = _RE_ANNOTATION.sub(_blank, content)
    out = _RE_ANNOTATION_ATTR.sub(_blank, out)
    out = _RE_PROPERTY_ATTRS.sub(_blank, out)
    return out


# ---------- U-1: Unused variables ----------

# Matches `<Variable ... Name="X" .../>` or open-tag form. Captures Name.
_RE_VARIABLE = re.compile(
    r'<Variable\b[^>]*\bName="([^"]+)"[^>]*/?>'
)


_RE_VARIABLES_BLOCK = re.compile(
    r'<(\w+)\.Variables\b[^>]*?>(.*?)</\1\.Variables>',
    re.DOTALL,
)


def _scope_offset_for(content: str, var_offset: int) -> int:
    """Retorna offset do `<*.Variables>` enclosing block. -1 se var não está
    dentro de bloco Variables (rare). Identifica scope por offset do block."""
    for m in _RE_VARIABLES_BLOCK.finditer(content):
        if m.start() < var_offset < m.end():
            return m.start()
    return -1


def detect_duplicate_variable_names(rule, fc, pc):
    """U-4: Variable declarations com mesmo Name no mesmo file.

    Distingue:
      - **Same-scope duplicate** (mesmo `<*.Variables>` block): redundante,
        XAML inválido. Auto-delete extras (mantém primeira).
      - **Cross-scope duplicate** (scopes diferentes): shadowing legit OU
        risco. Alert contextual, sem auto-fix.
    """
    content = fc.active_content
    findings: list[Finding] = []

    # (scope_offset, name_lc) → list of (offset, decl_text)
    by_scope_name: dict[tuple[int, str], list[tuple[int, str]]] = {}
    by_name_global: dict[str, list[int]] = {}

    for m in _RE_VARIABLE.finditer(content):
        name = m.group(1)
        scope = _scope_offset_for(content, m.start())
        by_scope_name.setdefault((scope, name.lower()), []).append(
            (m.start(), m.group(0))
        )
        by_name_global.setdefault(name.lower(), []).append(m.start())

    # Pass 1: same-scope duplicates → deterministic delete
    for (scope, name_lc), entries in by_scope_name.items():
        if len(entries) <= 1:
            continue
        first_offset = entries[0][0]
        m0 = re.search(r'<Variable\b[^>]*\bName="([^"]+)"', content[first_offset:first_offset+200])
        original_name = m0.group(1) if m0 else name_lc
        # Emit 1 finding per extra (entries[1:])
        for offset, decl_text in entries[1:]:
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, offset),
                message=(
                    f"{rule.title}: '{original_name}' duplicate same-scope — "
                    f"removendo extra (mantém first em line {_line_for(content, first_offset)})"
                ),
                fix_mechanical={
                    "type": "regex_replace",
                    "pattern": re.escape(decl_text),
                    "replacement": "",
                },
                fix_prose=(rule.fix or {}).get("prose"),
            ))

    # Pass 2: cross-scope duplicates (scopes diferentes mesmo name) → contextual
    same_scope_seen = {(s, n) for (s, n), e in by_scope_name.items() if len(e) > 1}
    for name_lc, offsets in by_name_global.items():
        if len(offsets) <= 1:
            continue
        scopes = {_scope_offset_for(content, o) for o in offsets}
        if len(scopes) <= 1:
            continue  # all in same scope (handled above)
        m0 = re.search(r'<Variable\b[^>]*\bName="([^"]+)"', content[offsets[0]:offsets[0]+200])
        original_name = m0.group(1) if m0 else name_lc
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, offsets[0]),
            message=(
                f"{rule.title}: '{original_name}' declarado {len(offsets)}× "
                f"em {len(scopes)} scopes diferentes — review manual (shadowing OK; "
                f"se intencional silenciar via supressão)"
            ),
            fix_mechanical=None,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


def detect_unused_variables(rule, fc, pc):
    content = fc.active_content
    scrubbed = _scrub_doc_regions(content)
    findings: list[Finding] = []

    rule_mech = (rule.fix or {}).get("mechanical")

    for m in _RE_VARIABLE.finditer(content):
        name = m.group(1)
        # Build a scrubbed copy with the declaration itself blanked, so the
        # declaration line doesn't count as a "use".
        decl_start, decl_end = m.start(), m.end()
        haystack = (
            scrubbed[:decl_start]
            + (" " * (decl_end - decl_start))
            + scrubbed[decl_end:]
        )
        if _ident_re(name).search(haystack):
            continue
        # Per-finding mechanical: inject `name` no spec do delete_variable.
        mech = None
        if rule_mech and rule_mech.get("type") == "delete_variable":
            mech = dict(rule_mech)
            mech["name"] = name
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: '{name}'",
            fix_mechanical=mech,
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# ---------- U-2: Unused arguments (cross-file) ----------

_RE_PROPERTY = re.compile(
    r'<x:Property\b[^>]*\bName="([^"]+)"[^>]*\bType="([^"]+)"',
)
# Detects `WorkflowFileName="..."` literal vs dynamic `[expr]`.
_RE_INVOKE_LITERAL = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*\bWorkflowFileName="([^"\[][^"]*)"',
)
_RE_INVOKE_DYNAMIC = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*\bWorkflowFileName="\[',
)
_RE_INVOKE_BLOCK = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*WorkflowFileName="([^"]+)"[^>]*>(.*?)</ui:InvokeWorkflowFile>',
    re.DOTALL,
)
_RE_BINDING_KEY = re.compile(r'x:Key="([^"]+)"')


# Project-level cache: {project_root: {"unsafe": bool, "callers_by_target": dict}}
_PROJECT_CACHE: dict[Path, dict] = {}


def _build_project_index(project_root: Path) -> dict:
    """Scan project once: map each callee xaml to list of (caller_path, bindings).

    Returns {"unsafe": bool, "by_target": {Path: [(caller_path, set_of_keys), ...]}}
    `unsafe=True` if any dynamic InvokeWorkflowFile found.
    """
    cached = _PROJECT_CACHE.get(project_root)
    if cached is not None:
        return cached

    by_target: dict[Path, list[tuple[Path, set[str]]]] = {}
    unsafe = False

    for xaml in project_root.rglob("*.xaml"):
        try:
            text = xaml.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        if "InvokeWorkflowFile" not in text:
            continue
        if _RE_INVOKE_DYNAMIC.search(text):
            unsafe = True
        for inv in _RE_INVOKE_BLOCK.finditer(text):
            target_str = inv.group(1)
            block = inv.group(2)
            if target_str.startswith("["):
                continue
            normalized = target_str.replace("\\", "/").lstrip("./")
            target_path = (project_root / normalized).resolve()
            keys = set(_RE_BINDING_KEY.findall(block))
            by_target.setdefault(target_path, []).append((xaml.resolve(), keys))

    cached = {"unsafe": unsafe, "by_target": by_target}
    _PROJECT_CACHE[project_root] = cached
    return cached


def _is_library_public(pc, fc) -> bool:
    """Return True if project is Library and current xaml is public."""
    if pc is None:
        return False
    if pc.project_type != "Library":
        return False
    pj = pc.project_json or {}
    lib = pj.get("libraryOptions", {}) or {}
    private_list = lib.get("privateWorkflows") or []
    rel = fc.path.resolve().relative_to(pc.root.resolve()).as_posix()
    return rel not in {p.replace("\\", "/") for p in private_list}


def _is_passthrough(arg_name: str, callee_content: str) -> bool:
    """Heuristic: callee has an InvokeWorkflowFile that passes the same arg
    name as binding key — chain, not unused."""
    for inv in _RE_INVOKE_BLOCK.finditer(callee_content):
        block = inv.group(2)
        for k in _RE_BINDING_KEY.findall(block):
            if k.lower() == arg_name.lower():
                return True
    return False


def detect_unused_arguments(rule, fc, pc):
    if pc is None:
        return []
    if _is_library_public(pc, fc):
        return []

    project_root = pc.root.resolve()
    index = _build_project_index(project_root)
    if index["unsafe"]:
        return []  # detect-only abort: dynamic invokes in project

    content = fc.active_content
    scrubbed = _scrub_doc_regions(content)
    findings: list[Finding] = []

    callee_path = fc.path.resolve()
    callers = index["by_target"].get(callee_path, [])

    for m in _RE_PROPERTY.finditer(content):
        name = m.group(1)
        type_str = m.group(2)
        # Phase 1: only in_ and io_
        if not (name.startswith("in_") or name.startswith("io_")):
            continue
        # Skip OutArgument / InOutArgument typed for outbound use; only
        # skip InArgument-style read checks. The naming prefix is the
        # primary signal in this codebase.
        # Body usage scan — exclude declaration itself.
        decl_start, decl_end = m.start(), m.end()
        haystack = (
            scrubbed[:decl_start]
            + (" " * (decl_end - decl_start))
            + scrubbed[decl_end:]
        )
        if _ident_re(name).search(haystack):
            continue
        # Passthrough: callee invokes other xaml passing same arg
        if _is_passthrough(name, content):
            continue
        # Caller side: any caller binding the key?
        bound_anywhere = any(name in keys for _caller, keys in callers)
        if bound_anywhere:
            # Caller passes value — used externally, not unused.
            continue
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, m.start()),
            message=f"{rule.title}: '{name}' ({type_str})",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# ---------- U-3: Undeclared identifiers ----------

# Match VB expressions wrapped in `[...]` inside attribute values
# (e.g., To="[vStrFoo]") and InvokeCode bodies.
_RE_VB_EXPR_IN_ATTR = re.compile(r'"\[([^"\]]*?)\]"')
_RE_INVOKECODE_BODY = re.compile(
    r'<ui:InvokeCode\b[^>]*>(.*?)</ui:InvokeCode>',
    re.DOTALL,
)
_RE_CDATA_BODY = re.compile(r'<!\[CDATA\[(.*?)\]\]>', re.DOTALL)
_RE_CODE_TAG = re.compile(r'<Code>(.*?)</Code>', re.DOTALL)

# Identifier in VB code: starts with letter or _, no keyword filtering yet.
_RE_VB_IDENT = re.compile(r'\b([A-Za-z_][A-Za-z_0-9]*)\b')

# VB string literals — skip identifier scan inside.
_RE_VB_STRING = re.compile(r'"(?:[^"]|"")*"')
# VB comment line `' ...` until end of segment (we operate on isolated chunks).
_RE_VB_LINE_COMMENT = re.compile(r"'[^\r\n]*")

# Common VB keywords + system globals we never flag as undeclared.
_VB_KEYWORDS = frozenset(s.lower() for s in [
    "And", "AndAlso", "Or", "OrElse", "Not", "Xor", "Mod",
    "If", "Then", "Else", "ElseIf", "End", "True", "False", "Nothing",
    "Is", "IsNot", "Like", "TypeOf", "GetType", "AddressOf",
    "New", "As", "Of", "Function", "Sub", "Return", "Dim",
    "ByVal", "ByRef", "Optional", "ParamArray",
    "For", "Each", "In", "To", "Step", "Next", "While", "Wend", "Do", "Loop",
    "Until", "Exit", "Continue", "Select", "Case", "When", "With",
    "Try", "Catch", "Finally", "Throw", "Using",
    "Me", "MyBase", "MyClass", "Imports",
    "CBool", "CByte", "CChar", "CDate", "CDbl", "CDec", "CInt", "CLng",
    "CObj", "CSByte", "CShort", "CSng", "CStr", "CType", "CUInt", "CULng",
    "CUShort", "DirectCast", "TryCast",
])

_SYSTEM_GLOBALS = frozenset(s.lower() for s in [
    "DateTime", "Now", "Today", "TimeSpan", "DateTimeOffset", "Date",
    "String", "Char", "Boolean", "Integer", "Long", "Short", "Byte", "SByte",
    "Decimal", "Double", "Single", "Object", "Math", "Convert", "Environment",
    "Exception", "SystemException", "ArgumentException",
    "ArgumentNullException", "InvalidOperationException", "NullReferenceException",
    "Console", "IO", "File", "Directory", "Path", "Encoding", "Guid",
    "Regex", "List", "Dictionary", "HashSet", "Queue", "Stack",
    "Array", "Enumerable", "Linq", "Tuple",
    "Newtonsoft", "JObject", "JArray", "JToken", "JsonConvert",
    "vbCrLf", "vbTab", "vbNewLine", "vbCr", "vbLf",
    # Common UiPath delegate arg names from system templates
    "exception", "row", "item",
])


# Captures variable declarations (any nesting).
_RE_VAR_DECL = re.compile(r'<Variable\b[^>]*\bName="([^"]+)"')
# Captures arguments declared in <x:Members>.
_RE_PROPERTY_NAME = re.compile(r'<x:Property\b[^>]*\bName="([^"]+)"')
# Captures DelegateInArgument names (ForEachRow CurrentRow, Catch exception, etc).
_RE_DELEGATE_ARG = re.compile(r'<DelegateInArgument\b[^>]*\bName="([^"]+)"')
# Captures imported namespaces.
_RE_NS_IMPORT = re.compile(
    r'<TextExpression\.NamespacesForImplementation>(.*?)</TextExpression\.NamespacesForImplementation>',
    re.DOTALL,
)
_RE_NS_STRING = re.compile(r'<x:String>([^<]+)</x:String>')


def _collect_declared_names(content: str) -> set[str]:
    """All identifiers we accept as declared in this xaml (lowercased)."""
    names: set[str] = set()
    names.update(s.lower() for s in _RE_VAR_DECL.findall(content))
    names.update(s.lower() for s in _RE_PROPERTY_NAME.findall(content))
    names.update(s.lower() for s in _RE_DELEGATE_ARG.findall(content))
    # Imported namespaces — last segment becomes a usable identifier.
    ns_block_match = _RE_NS_IMPORT.search(content)
    if ns_block_match:
        for ns in _RE_NS_STRING.findall(ns_block_match.group(1)):
            ns = ns.strip()
            if not ns:
                continue
            # last segment, plus full ns first segment (System.Linq → System)
            names.add(ns.rsplit(".", 1)[-1].lower())
            names.add(ns.split(".", 1)[0].lower())
    return names


def _strip_vb_strings_and_comments(text: str) -> str:
    out = _RE_VB_STRING.sub(lambda m: " " * len(m.group(0)), text)
    out = _RE_VB_LINE_COMMENT.sub(lambda m: " " * len(m.group(0)), out)
    return out


# Sicoob naming convention: variables start with `v` + uppercase type prefix,
# arguments use `in_`/`out_`/`io_`. Restricting U-3 to this pattern avoids the
# unbounded false-positive surface of BCL/UiPath types (BusinessRuleException,
# SecureString, CultureInfo, etc.) that resolve via imported namespaces or
# referenced assemblies — out of reach for static text scan.
_RE_USER_IDENT = re.compile(
    r'^(?:v[A-Z][A-Za-z0-9]*|(?:in|out|io)_[A-Za-z0-9_]+)$'
)


def _is_user_identifier(name: str) -> bool:
    return bool(_RE_USER_IDENT.match(name))


def _expr_identifiers(expr: str) -> Iterable[str]:
    """Yield identifier tokens that are NOT preceded by '.' (member access).

    Restricted to Sicoob user-defined identifiers (`vXxx`, `in_*`, `out_*`,
    `io_*`). Type names from BCL/UiPath are not considered here.
    """
    # Decode XML entities first (`&quot;` → `"`, `&amp;` → `&`, `&#xA;` → `\n`).
    # Without this, VB string literals encoded as `&quot;...&quot;` fail the
    # string-strip step and their contents leak into the identifier scan.
    decoded = _xml_unescape(expr)
    cleaned = _strip_vb_strings_and_comments(decoded)
    for m in _RE_VB_IDENT.finditer(cleaned):
        # Skip member access — only flag root identifiers.
        prev = cleaned[m.start() - 1] if m.start() > 0 else ""
        if prev == ".":
            continue
        ident = m.group(1)
        if not _is_user_identifier(ident):
            continue
        if ident.lower() in _VB_KEYWORDS:
            continue
        if ident.lower() in _SYSTEM_GLOBALS:
            continue
        yield ident


def detect_undeclared_identifiers(rule, fc, pc):
    content = fc.active_content
    scrubbed = _scrub_doc_regions(content)
    declared = _collect_declared_names(content)

    findings: list[Finding] = []
    seen: set[tuple[str, int]] = set()  # (name, line) dedup

    # 1. Identifiers inside attribute expressions `[expr]`
    for m in _RE_VB_EXPR_IN_ATTR.finditer(scrubbed):
        expr = m.group(1)
        if not expr.strip():
            continue
        line = _line_for(scrubbed, m.start())
        for ident in _expr_identifiers(expr):
            if ident.lower() in declared:
                continue
            key = (ident.lower(), line)
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=line,
                message=f"{rule.title}: '{ident}'",
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))

    # 2. Identifiers inside InvokeCode <Code> bodies (CDATA-aware).
    # Skip surrounding XAML markup like <ui:InvokeCode.Arguments> children.
    for code_m in _RE_CODE_TAG.finditer(scrubbed):
        body = code_m.group(1)
        cdata = _RE_CDATA_BODY.search(body)
        code_text = cdata.group(1) if cdata else body
        if not code_text.strip():
            continue
        base_offset = code_m.start()
        for ident in _expr_identifiers(code_text):
            if ident.lower() in declared:
                continue
            line = _line_for(scrubbed, base_offset)
            key = (ident.lower(), line)
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=line,
                message=f"{rule.title} (InvokeCode): '{ident}'",
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))

    return findings


# ---------------------------------------------------------------------------
# U-5 — Variáveis com mesma origem/Default — alias provável
# ---------------------------------------------------------------------------

_RE_VARIABLE_FULL = re.compile(
    r'<Variable\b([^>]*?)/?>',
)
_RE_VARIABLE_TYPE = re.compile(r'x:TypeArguments="([^"]+)"')
_RE_VARIABLE_NAME = re.compile(r'\bName="([^"]+)"')
_RE_VARIABLE_DEFAULT = re.compile(r'\bDefault="([^"]*)"')

_RE_ASSIGN_BLOCK = re.compile(
    r'<Assign\b[^>]*?>(.*?)</Assign>',
    re.DOTALL,
)
_RE_ASSIGN_TO_VAR = re.compile(
    r'<Assign\.To>\s*<OutArgument[^>]*>\[([A-Za-z_][\w]*)\]</OutArgument>\s*</Assign\.To>',
    re.DOTALL,
)
_RE_ASSIGN_VALUE = re.compile(
    r'<Assign\.Value>\s*<InArgument[^>]*>\[([^<]*)\]</InArgument>\s*</Assign\.Value>',
    re.DOTALL,
)


def _normalize_expr(s: str) -> str:
    """Normalize whitespace + decode entities for value comparison."""
    s = s.replace('&quot;', '"').replace('&amp;', '&').replace('&apos;', "'")
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def detect_u5_variable_aliases(rule, fc, pc):
    """U-5: variáveis com Default literal idêntico OU mesma expressão de Assign.

    Caso 1: 2+ <Variable> com mesmo (type, default) onde default ∉ trivial_defaults.
    Caso 2: 2+ <Assign> targets distintos populados com expressão textualmente igual.
    """
    p = (rule.detect.get("params", {}) or {})
    trivial = set(_normalize_expr(s) for s in (p.get("trivial_defaults") or ()))
    skip_types = tuple(p.get("skip_types") or ())
    min_dup = int(p.get("min_duplicate_assigns") or 2)
    normalize_ws = bool(p.get("normalize_whitespace", True))

    content = fc.active_content
    findings = []

    # ---------- Caso 1: Defaults idênticos ----------
    by_type_default: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for m in _RE_VARIABLE_FULL.finditer(content):
        attrs = m.group(1)
        nm = _RE_VARIABLE_NAME.search(attrs)
        tm = _RE_VARIABLE_TYPE.search(attrs)
        dm = _RE_VARIABLE_DEFAULT.search(attrs)
        if not (nm and tm and dm):
            continue
        name = nm.group(1)
        typ = tm.group(1)
        default = dm.group(1)
        if any(typ.startswith(skip) for skip in skip_types):
            continue
        norm = _normalize_expr(default) if normalize_ws else default.strip()
        if norm in trivial:
            continue
        key = (typ, norm)
        by_type_default.setdefault(key, []).append((name, m.start()))

    def _name_tokens(n: str) -> set[str]:
        # Strip Hungarian prefix (v/in/io/out + type marker) then CamelCase split
        stripped = re.sub(r'^(?:in|io|out|v)(?:St|Int|Bl|Dt|DTab|Arr|Dict|Lst)?', '', n)
        return {t.lower() for t in re.findall(r'[A-Z][a-z0-9]*|[a-z0-9]+', stripped) if t}

    for (typ, default), entries in by_type_default.items():
        if len(entries) < 2:
            continue
        names = [e[0] for e in entries]
        # Aliases share name tokens (e.g. vDTabUsuariosA / vDTabUsuariosB).
        # Names with distinct semantic stems (vDTabOperadoresEAprovadores
        # vs vDTabUsuariosRPA) NAO sao aliases — heurística agressiva.
        # Skip se intersection de tokens semanticos < 1 entre TODOS pares.
        token_sets = [_name_tokens(n) for n in names]
        any_overlap = False
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                if token_sets[i] & token_sets[j]:
                    any_overlap = True
                    break
            if any_overlap:
                break
        if not any_overlap:
            continue  # semantically distinct names — not alias
        first_offset = entries[0][1]
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(content, first_offset),
            message=f"{rule.title}: {len(entries)} <Variable> com mesmo Type+Default — vars={names}, type='{typ}', default='{default}' (consolidar em uma)",
            fix_mechanical=None,
            fix_prose=(rule.fix or {}).get("prose"),
        ))

    # ---------- Caso 2: Assigns com mesma expressão ----------
    by_value: dict[str, list[tuple[str, int]]] = {}
    for am in _RE_ASSIGN_BLOCK.finditer(content):
        body = am.group(1)
        to_m = _RE_ASSIGN_TO_VAR.search(body)
        val_m = _RE_ASSIGN_VALUE.search(body)
        if not (to_m and val_m):
            continue
        target_var = to_m.group(1)
        expr = val_m.group(1)
        norm = _normalize_expr(expr) if normalize_ws else expr.strip()
        if not norm or norm in trivial:
            continue
        # Skip too-short trivial expressions
        if len(norm) <= 3:
            continue
        by_value.setdefault(norm, []).append((target_var, am.start()))

    for expr, entries in by_value.items():
        # Different target vars receiving same expr
        unique_targets = list({e[0] for e in entries})
        if len(unique_targets) >= min_dup:
            # Skip if expression is a variable reference (`[vX]`) — likely
            # legitimate fan-out (1 source var → multiple destinations for
            # different downstream uses). True alias requires literal/computed
            # expression value, not variable propagation.
            expr_stripped = expr.strip()
            if re.fullmatch(r'\[?\s*v[A-Za-z][A-Za-z0-9_]*\s*\]?', expr_stripped):
                continue
            first_offset = entries[0][1]
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, first_offset),
                message=f"{rule.title}: vars {sorted(unique_targets)} recebem mesma expressão '[{expr[:80]}]' — alias provável",
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))

    return findings


# ---------------------------------------------------------------------------
# U-6 — Variable hoisting: scope estreito → preferir scope mais externo
# ---------------------------------------------------------------------------

_RE_VARIABLES_BLOCK_NS = re.compile(
    r'<([A-Za-z_][\w.\-:]*?)\.Variables\b',
)


def _scope_offset_for_ns(content: str, var_offset: int) -> tuple[int, str]:
    """NS-aware scope locator. Returns (offset, parent_tag) of enclosing
    `<TAG.Variables>` block where TAG may include `:`/namespace prefix.
    Returns (-1, '') if not in any block.
    """
    best_offset = -1
    best_tag = ''
    for m in _RE_VARIABLES_BLOCK_NS.finditer(content):
        if m.start() > var_offset:
            break
        # find matching </TAG.Variables>
        tag = m.group(1)
        close = content.find(f'</{tag}.Variables>', m.end())
        if close < 0:
            continue
        if m.start() < var_offset < close:
            # most-specific (innermost) wins via outermost-of-enclosing tracking
            if m.start() > best_offset:
                best_offset = m.start()
                best_tag = tag
    return best_offset, best_tag


def _is_loop_scope(parent_tag: str, loop_tags: tuple[str, ...]) -> bool:
    if not parent_tag:
        return False
    for lt in loop_tags:
        if parent_tag == lt or parent_tag.endswith(':' + lt) or parent_tag.endswith(lt):
            return True
    return False


def _is_exception_scope(content: str, scope_offset: int) -> bool:
    """Check if scope is inside <Catch> / <TryCatch.Catches> ancestor."""
    if scope_offset <= 0:
        return False
    prefix = content[:scope_offset]
    # walk back: any open <Catch ...> or <TryCatch.Catches> without intervening close?
    # crude heuristic: nearest preceding match wins
    last_catch_open = max(prefix.rfind('<Catch '), prefix.rfind('<Catch>'),
                          prefix.rfind('<TryCatch.Catches'))
    last_catch_close = max(prefix.rfind('</Catch>'), prefix.rfind('</TryCatch.Catches>'))
    return last_catch_open > last_catch_close >= 0 or (last_catch_open >= 0 and last_catch_close < 0)


def detect_u6_variable_hoist(rule, fc, pc):
    """U-6: Variable em scope estreito quando poderia viver em scope mais amplo.

    Caso A (default): mesma <Variable Name=X Type=T> em 2+ scopes diferentes
    no mesmo arquivo, NENHUM dos scopes sendo loop/exception → hoist candidate.

    Skip:
      - Loops (ForEach iterators, While body): scope-local intencional.
      - Exception scopes (Catch): exception locals.
    """
    p = (rule.detect.get("params", {}) or {})
    loop_tags = tuple(p.get("loop_parents") or ())
    only_cross_scope = bool(p.get("only_cross_scope_dup", True))

    content = fc.active_content
    findings: list[Finding] = []

    # Group declarations by (name_lower, type_signature)
    decls: dict[tuple[str, str], list[tuple[int, int, str, str, str]]] = {}
    type_re = re.compile(r'x:TypeArguments="([^"]+)"')
    for m in _RE_VARIABLE.finditer(content):
        name = m.group(1)
        attrs = m.group(0)
        tm = type_re.search(attrs)
        type_sig = tm.group(1) if tm else ''
        scope_off, parent_tag = _scope_offset_for_ns(content, m.start())
        decls.setdefault((name.lower(), type_sig), []).append(
            (m.start(), scope_off, name, attrs, parent_tag)
        )

    if only_cross_scope:
        for (name_lc, type_sig), entries in decls.items():
            scopes = {e[1] for e in entries}
            if len(scopes) < 2:
                continue
            skip = False
            for off, scope, _, _, parent_tag in entries:
                if _is_loop_scope(parent_tag, loop_tags):
                    skip = True; break
                if _is_exception_scope(content, scope):
                    skip = True; break
            if skip:
                continue
            original_name = entries[0][2]
            first_off = entries[0][0]
            scope_lines = sorted({_line_for(content, e[1]) for e in entries if e[1] >= 0})
            findings.append(Finding(
                rule_id=rule.id, severity=rule.severity, category=rule.category,
                file=str(fc.path), line=_line_for(content, first_off),
                message=(
                    f"{rule.title}: '{original_name}' (type='{type_sig}') "
                    f"declarado em {len(scopes)} scopes irmãos/aninhados "
                    f"(linhas Variables: {scope_lines}) — hoist para ancestral comum"
                ),
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))

    return findings
