"""VB reference ↔ declaration consistency check (Layer C-lite).

Detecta refs órfãs em XAML: identifiers usados em VB-expression contexts
(`[ident]`, `<InArgument>...ident...</InArgument>`) sem declaração matching.

Cobre BC30451-class errors (var não declarada). NÃO cobre type checking,
AssemblyReference, schema-level activity attrs.

Heurística — não substitui compilador VB. False positives possíveis em casos
com sintaxe VB raríssima. Config via extra_whitelist.

Comparison é case-insensitive (VB é case-insensitive).
"""
from __future__ import annotations

import re
from pathlib import Path


# VB keywords
VB_KEYWORDS = frozenset({
    "new", "nothing", "true", "false", "me", "mybase", "myclass", "global",
    "if", "iif", "and", "or", "not", "xor", "mod", "like", "is", "isnot",
    "andalso", "orelse", "in", "of", "as", "by", "for", "each", "next",
    "while", "do", "loop", "until", "function", "sub", "return", "select",
    "case", "from", "where", "let", "join", "group", "into", "on",
    "ascending", "descending", "order", "with", "out", "byval", "byref",
    "ctype", "directcast", "trycast", "gettype", "typeof", "addressof",
    "addhandler", "removehandler", "raiseevent", "exit", "continue",
    "throw", "try", "catch", "finally", "when", "end", "then", "else",
    "elseif", "dim", "const", "static", "shared", "public", "private",
    "protected", "friend", "imports", "namespace", "class", "structure",
    "interface", "module", "property", "get", "set", "event", "delegate",
    "operator", "implements", "inherits", "overrides", "overloads",
    "narrowing", "widening", "shadows", "overridable", "mustinherit",
    "mustoverride", "notoverridable", "notinheritable", "partial",
    "readonly", "writeonly", "default", "optional", "paramarray",
    "step", "to", "stop", "error", "resume", "goto", "single", "double",
    "decimal", "boolean", "string", "char", "object", "long", "integer",
    "short", "byte", "sbyte", "ushort", "uinteger", "ulong", "date",
    "of", "rem",
})

# .NET BCL types (common ones used in UiPath)
NET_TYPES = frozenset({
    # Primitives
    "string", "integer", "int", "int16", "int32", "int64", "long", "short",
    "byte", "boolean", "bool", "double", "decimal", "single", "float",
    "datetime", "timespan", "object", "char", "guid", "uri",
    # Collections
    "list", "dictionary", "ienumerable", "icollection", "ilist",
    "hashset", "queue", "stack", "kvp", "keyvaluepair", "tuple",
    "array", "arraylist", "sortedlist", "sorteddictionary",
    # Common BCL
    "exception", "argumentexception", "argumentnullexception",
    "invalidoperationexception", "notimplementedexception",
    "math", "console", "convert", "environment", "regex",
    # IO
    "path", "file", "directory", "stream", "filestream", "streamreader",
    "streamwriter", "encoding", "fileinfo", "directoryinfo",
    # Linq
    "enumerable", "queryable",
    # Newtonsoft / JSON
    "jobject", "jarray", "jproperty", "jtoken", "jvalue", "jsonconvert",
    # Data
    "datatable", "datarow", "datacolumn", "dataset", "dataview",
    # Activities core
    "argument", "inargument", "outargument", "inoutargument",
    "delegateinargument", "delegateoutargument",
})

# Common namespaces / qualifiers
NET_NAMESPACES = frozenset({
    "system", "microsoft", "uipath", "newtonsoft", "this", "scg", "sco",
    "x", "ui", "uix", "njl", "s", "sd", "ss", "uia", "sap", "sap2010",
    "mva", "v", "av", "p",
})

# REFramework / convention-based identifiers (non-rename targets)
REFRAMEWORK_VARS = frozenset({
    "transactionitem", "transactionnumber", "retrynumber", "config",
    "credentials", "in_credentials", "in_credenciais",
    "transactionfield1", "transactionfield2", "transactionfield3",
    "businessexception", "systemexception", "in_businessexception",
    "in_systemexception", "in_exception", "consecutivesystemexceptions",
    "transactionid", "reference", "progress", "item", "row", "element",
    "queuename", "in_orchestratorqueuename", "in_orchestratorqueuefolder",
    "in_transactionfield1", "in_transactionfield2", "in_transactionfield3",
    # ForEach iterators / common loop vars
    "currentitem", "currentindex", "i", "j", "k", "n",
    "uiapp", "in_uiapp", "out_uiapp", "io_uiapp",
})

DEFAULT_WHITELIST = VB_KEYWORDS | NET_TYPES | NET_NAMESPACES | REFRAMEWORK_VARS


# ---- Declaration extraction ----

_RE_DECL = re.compile(
    r'<(?:\w+:)?(?:Variable|Property|DelegateInArgument|DelegateOutArgument)\b[^>]*\bName="([^"]+)"',
    re.DOTALL,
)


def extract_declarations(content: str) -> set[str]:
    """Names from <Variable>, <x:Property>, <DelegateInArgument>, etc.
    Lowercased for case-insensitive comparison."""
    return {m.group(1).lower() for m in _RE_DECL.finditer(content)}


# ---- Reference extraction ----

# VB expression contexts:
#   1. [ident...] — bracketed VB binding
#   2. <InArgument>...</InArgument> body, similar for Out/InOut
#   3. Expression="..." attribute value (in some activities)
_RE_BRACKET_EXPR = re.compile(r'\[([^\[\]]*?)\]')
_RE_ARG_BODY = re.compile(
    r'<(?:\w+:)?(?:In|Out|InOut)Argument\b[^>]*>([^<]+)</',
    re.DOTALL,
)
_RE_EXPRESSION_ATTR = re.compile(r'\bExpression="([^"]+)"', re.DOTALL)


def _strip_vb_strings(expr: str) -> str:
    """Remove VB string literals (`"..."` and `&quot;...&quot;`) so their
    contents aren't misidentified as identifiers."""
    expr = re.sub(r'&quot;.*?&quot;', '', expr, flags=re.DOTALL)
    expr = re.sub(r'"[^"]*"', '', expr)
    # Also: `&apos;` and `&amp;` escapes — pass through, harmless to ident scan.
    return expr


_RE_IDENT = re.compile(r'\b([A-Za-z_][A-Za-z_0-9]*)\b')


def _idents_in_expr(expr: str) -> set[str]:
    """Identifiers in expr, excluding member-access (preceded by `.`).
    Lowercased."""
    expr = _strip_vb_strings(expr)
    out: set[str] = set()
    for m in _RE_IDENT.finditer(expr):
        s = m.start()
        # Skip if preceded by `.` (member access)
        prev = expr[:s].rstrip()
        if prev.endswith('.'):
            continue
        out.add(m.group(1).lower())
    return out


def extract_references(content: str) -> set[str]:
    """Top-level identifiers used in VB-expression contexts."""
    refs: set[str] = set()
    for m in _RE_BRACKET_EXPR.finditer(content):
        refs |= _idents_in_expr(m.group(1))
    for m in _RE_ARG_BODY.finditer(content):
        body = m.group(1).strip()
        if body.startswith('[') and body.endswith(']'):
            body = body[1:-1]
        refs |= _idents_in_expr(body)
    for m in _RE_EXPRESSION_ATTR.finditer(content):
        refs |= _idents_in_expr(m.group(1))
    return refs


# ---- Orphan detection ----

def find_orphans(
    content: str,
    extra_whitelist: frozenset[str] | set[str] | None = None,
) -> set[str]:
    """Identifiers referenced em VB-expression contexts mas não declarados
    e não em whitelist. Lowercased."""
    decls = extract_declarations(content)
    refs = extract_references(content)
    whitelist = DEFAULT_WHITELIST
    if extra_whitelist:
        whitelist = whitelist | {x.lower() for x in extra_whitelist}
    return refs - decls - whitelist


def diff_orphans(
    pre_content: str,
    post_content: str,
    extra_whitelist: frozenset[str] | set[str] | None = None,
) -> set[str]:
    """Orphans introduzidas pelo fix (pos - pre)."""
    pre = find_orphans(pre_content, extra_whitelist)
    post = find_orphans(post_content, extra_whitelist)
    return post - pre
