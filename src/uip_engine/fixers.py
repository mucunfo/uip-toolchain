"""Fixer registry — type → callable. Apply mechanical fixes."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable


REGISTRY: dict[str, Callable] = {}


def register(name: str):
    def decorator(fn):
        REGISTRY[name] = fn
        return fn
    return decorator


_BOM = b"\xef\xbb\xbf"


def _file_has_bom(path: Path) -> bool:
    """True se arquivo começa com UTF-8 BOM. Studio gera XAML com BOM
    e re-adiciona BOM no save — write sem BOM dispara churn no git +
    diff noise no Studio. Helper preserva estado original."""
    try:
        with open(path, "rb") as fh:
            return fh.read(3) == _BOM
    except OSError:
        return False


def _write_preserving_bom(path: Path, content: str, had_bom: bool) -> None:
    """Write `content` (utf-8) preservando BOM se `had_bom`."""
    if had_bom:
        path.write_bytes(_BOM + content.encode("utf-8"))
    else:
        path.write_text(content, encoding="utf-8")


_COMMON_XMLNS_FOR_TYPEARGS = {
    "sd": "clr-namespace:System.Data;assembly=System.Data.Common",
    "scg": "clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib",
    "s": "clr-namespace:System;assembly=System.Private.CoreLib",
    "ui": "http://schemas.uipath.com/workflow/activities",
}


def _ensure_common_xmlns_for_typeargs(content: str, typeargs: str | None) -> str:
    """Declare common prefixes used by injected x:TypeArguments."""
    if not typeargs:
        return content

    missing: list[tuple[str, str]] = []
    for prefix, uri in _COMMON_XMLNS_FOR_TYPEARGS.items():
        if re.search(rf'(?<![A-Za-z0-9_]){re.escape(prefix)}:', typeargs):
            if not re.search(rf'\bxmlns:{re.escape(prefix)}\s*=', content):
                missing.append((prefix, uri))
    if not missing:
        return content

    root = re.search(r'<Activity\b[^>]*>', content)
    if not root:
        return content
    additions = "".join(f' xmlns:{prefix}="{uri}"' for prefix, uri in missing)
    return content[:root.end() - 1] + additions + content[root.end() - 1:]


def _format_property_element_value(prop_type: str | None, default,
                                    direction: str = "In") -> str:
    """Generate `<{In|Out|InOut}Argument x:TypeArguments="T">{default}</...>` content.

    M-2 contract:
      - direction selects the argument wrapper element:
            In    -> <InArgument>    (default; preserves historical behavior)
            Out   -> <OutArgument>
            InOut -> <InOutArgument>
      - Out/InOut emit NO default literal (an Out/InOut target must bind to a
        variable reference, not a seeded literal). They always self-close.
      - The x:TypeArguments value is XML-escaped (a generic type containing a
        literal `<`, e.g. `IList<T>`, must be escaped or the attribute is not
        well-formed XML and the safety gate silently rolls back the fix).

    For unknown types, wraps in raw argument element. Default value (In only) is
    template-only; runtime XAML parser converts string to target type if
    compatible.
    """
    bare = (prop_type or "x:Object").split("`")[0]
    if not bare.startswith("System.") and bare != "x:Object":
        bare_full = "System." + bare
    else:
        bare_full = bare
    type_alias = {
        "System.String": "x:String",
        "System.Int32": "x:Int32",
        "System.Int64": "x:Int64",
        "System.Boolean": "x:Boolean",
        "System.Double": "x:Double",
        "System.Decimal": "x:Decimal",
        "System.DateTime": "x:DateTime",
        "x:Object": "x:Object",
    }.get(bare_full, bare_full)
    # XML-escape the TypeArguments value (generics with literal `<`/`>`/`&`).
    type_safe = (type_alias.replace("&", "&amp;")
                           .replace("<", "&lt;").replace(">", "&gt;"))

    wrapper = {
        "In": "InArgument",
        "Out": "OutArgument",
        "InOut": "InOutArgument",
    }.get(direction or "In", "InArgument")

    # Out/InOut never seed a literal default — emit self-closed wrapper.
    if wrapper != "InArgument":
        return f'<{wrapper} x:TypeArguments="{type_safe}" />'

    if default is None or default == "":
        return f'<{wrapper} x:TypeArguments="{type_safe}" />'
    # Escape XML
    safe = str(default).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<{wrapper} x:TypeArguments="{type_safe}">{safe}</{wrapper}>'


def _arg_already_provided(open_tag: str, content: str, tag_start: int, tag_end: int,
                          prefix: str, activity: str, prop_name: str) -> bool:
    """Check if prop is provided as attribute OR property element scoped to this tag."""
    # Attribute form within open tag body
    if re.search(rf'(?:(?<=\s)|(?<=^))(?<!\.){re.escape(prop_name)}\s*=', open_tag):
        return True
    # Property element form: <prefix:Activity.PropName ...> anywhere in file
    # (best-effort; XAML structure makes scope hard without full parse)
    pe_pattern = rf'<{re.escape(prefix)}:{re.escape(activity)}\.{re.escape(prop_name)}\b'
    if re.search(pe_pattern, content):
        return True
    return False


@register("add_property_element")
def apply_add_property_element(file: Path, spec: dict[str, Any], dry_run: bool = True) -> bool:
    """Insert property element form for a missing required arg.

    Spec:
        prefix         : XAML prefix (e.g. "ui")
        activity_local : activity local name (e.g. "WriteRange")
        prop_name      : missing arg name (e.g. "WorkbookPath")
        prop_type      : .NET type (e.g. "System.String")
        default        : optional default value to seed
        tag_line       : approximate line where finding emitted (used to disambiguate)

    Edits FIRST occurrence of <prefix:activity_local ...> that does not yet
    have prop_name set. Subsequent occurrences handled by fixpoint loop on
    re-detection.

    Self-close `<ui:WriteRange ... />` is expanded to `<ui:WriteRange ...>
    <ui:WriteRange.Foo>...</ui:WriteRange.Foo></ui:WriteRange>`.
    """
    prefix = spec.get("prefix")
    activity = spec.get("activity_local")
    prop_name = spec.get("prop_name")
    prop_type = spec.get("prop_type")
    default = spec.get("default")
    direction = spec.get("direction") or "In"
    if not (prefix and activity and prop_name):
        return False

    content = file.read_text(encoding="utf-8-sig")

    # Match opening tag (self-close or not). Capture name, body, terminator.
    open_tag_re = re.compile(
        rf'<{re.escape(prefix)}:{re.escape(activity)}\b([^>]*?)(/?)>',
        re.DOTALL,
    )

    new_content = None
    for m in open_tag_re.finditer(content):
        body = m.group(1) or ""
        is_self_close = m.group(2) == "/"
        full_tag = m.group(0)
        if _arg_already_provided(full_tag, content, m.start(), m.end(),
                                  prefix, activity, prop_name):
            continue

        pe_inner = _format_property_element_value(prop_type, default, direction)
        pe_block = (f'<{prefix}:{activity}.{prop_name}>'
                    f'{pe_inner}'
                    f'</{prefix}:{activity}.{prop_name}>')

        if is_self_close:
            # Replace `<ui:Activity ... />` with
            # `<ui:Activity ...>\n  <PE/>\n</ui:Activity>`
            new_open = f'<{prefix}:{activity}{body}>'
            new_close = f'</{prefix}:{activity}>'
            replacement = f'{new_open}{pe_block}{new_close}'
            new_content = content[:m.start()] + replacement + content[m.end():]
        else:
            # Find matching close tag. Scan forward respecting nesting.
            close_start = _find_matching_close(content, m.end(), prefix, activity)
            if close_start < 0:
                continue
            new_content = (content[:close_start]
                           + pe_block
                           + content[close_start:])
        break

    if new_content is None or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


def _find_matching_close(content: str, start: int, prefix: str, activity: str) -> int:
    """Find offset of matching </prefix:activity> respecting nesting.
    Returns -1 if not found."""
    open_pat = re.compile(rf'<{re.escape(prefix)}:{re.escape(activity)}(?=[\s/>])[^>]*?(/?)>')
    close_pat = re.compile(rf'</{re.escape(prefix)}:{re.escape(activity)}\s*>')
    depth = 1
    pos = start
    while depth > 0 and pos < len(content):
        nxt_open = open_pat.search(content, pos)
        nxt_close = close_pat.search(content, pos)
        if nxt_close is None:
            return -1
        if nxt_open is not None and nxt_open.start() < nxt_close.start():
            if nxt_open.group(1) != "/":
                depth += 1
            pos = nxt_open.end()
        else:
            depth -= 1
            if depth == 0:
                return nxt_close.start()
            pos = nxt_close.end()
    return -1


def _has_property_element_for_attr(content: str, tag: str, attr: str,
                                   open_end: int) -> bool:
    """True when `<tag>` already sets `attr` through `<tag.attr>...`."""
    if ":" not in tag:
        return False
    prefix, local = tag.split(":", 1)
    close_start = _find_matching_close(content, open_end, prefix, local)
    if close_start < 0:
        return False
    body = content[open_end:close_start]
    prop_re = re.compile(
        rf'<{re.escape(tag)}\.{re.escape(attr)}(?=[\s/>])',
        re.DOTALL,
    )
    return bool(prop_re.search(body))


@register("regex_replace")
def apply_regex_replace(file: Path, spec: dict[str, Any], dry_run: bool = True) -> bool:
    """Apply regex replacement. Returns True if file would change."""
    pattern = spec.get("pattern")
    replacement = spec.get("replacement", "")
    if not pattern:
        return False
    content = file.read_text(encoding="utf-8-sig")
    new_content, n = re.subn(pattern, replacement, content)
    if n == 0 or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


_RE_ELEMENT_NAME_CTX = re.compile(r'</?[A-Za-z_][\w.\-]*:?$')


def _is_element_name_context(content: str, s: int) -> bool:
    """True se posição `s` em `content` é início de nome-de-elemento XML
    (precedido por `<`, `</`, ou `<prefix:`).

    Busca para trás até encontrar `<` ou `>`. Janela fixa anterior (64 chars)
    falhava quando atributo precedente era longo (>64 chars de DisplayName,
    Annotation.AnnotationText, etc) — `<` ficava fora do scope, match dentro
    de attribute value pulado erroneamente E (mais grave) match dentro de
    nome de element era renomeado, corrompendo XML.
    """
    # Boundary: até primeiro < ou > anterior, OU início de file.
    lt = content.rfind("<", 0, s)
    gt = content.rfind(">", 0, s)
    if lt < 0 or lt < gt:
        # Estamos dentro de text/attribute-value content, não em element name.
        return False
    # Há `<` mais recente que `>`. Se substring de lt até s casa com regex de
    # element-name-prefix (`<NAME` ou `</NAME` ou `<NAME:`), é element ctx.
    fragment = content[lt:s]
    return bool(_RE_ELEMENT_NAME_CTX.match(fragment))


def _is_attribute_name_context(content: str, s: int, name_len: int) -> bool:
    """True se posição `s` é nome de attribute XML dentro de tag aberta
    (ex.: `<ui:RemoveDataColumn ColumnIndex="...">` — `ColumnIndex` aqui é
    PROPERTY da activity, NÃO ref de variable).

    Critério:
      1. Há `<` sem `>` fechando antes de `s` (estamos dentro de open-tag).
      2. Char(s) imediatamente após `s+name_len` é `=` (com optional `:` antes
         pra namespace, ex.: `xmlns:`).
      3. Precedido por whitespace (delimita attribute name).

    Bug histórico (2026-05-25): rename N-1 de var `ColumnIndex` →
    `vIntColumnIndex` cascateava p/ property name de RemoveDataColumn,
    quebrando Studio load (`Não é possível definir o associado
    desconhecido 'UiPath.Core.Activities.RemoveDataColumn.vIntColumnIndex'`).
    """
    # Boundary: open-tag detection (mesmo critério de _is_element_name_context
    # mas precisa estar APÓS o nome do element, não no início).
    lt = content.rfind("<", 0, s)
    gt = content.rfind(">", 0, s)
    if lt < 0 or lt < gt:
        return False  # fora de tag
    # Preceded by whitespace (attribute name delimiter).
    if s == 0 or not content[s - 1].isspace():
        return False
    # Followed by `=` (attribute assignment) — tolera `:` namespace separator.
    after = content[s + name_len : s + name_len + 2]
    return after.startswith("=") or after.startswith(":")


def _whole_word_sub_skip_tags(
    content: str, from_name: str, to_name: str,
    case_insensitive: bool = True,
) -> tuple[str, int]:
    """Whole-word rename, mas pula matches que são nomes de element XML
    (precedidos por `<` ou `</` ou `<prefix:`). Renames dentro de attribute
    values, expressões VB, x:Key, Name="...", etc. continuam normais.

    Default `case_insensitive=True`: VB é case-insensitive, então refs como
    `[Dt_X]` para declaração `dt_X` precisam ser renomeadas. UiPath/VB não
    permite duas declarações case-distinct no mesmo escopo, então rename
    case-insensitive é seguro.

    2026-05-01: regression fix — antes era case-sensitive, deixando refs VB
    com case diferente da declaração órfãs (Studio: BC30451 var não declarada).
    2026-05-07: element-context detection passou de janela 64-char para
    busca-até-`<` (atributos longos quebravam detecção).
    """
    flags = re.IGNORECASE if case_insensitive else 0
    pattern = re.compile(rf"\b{re.escape(from_name)}\b", flags)
    out_parts: list[str] = []
    last = 0
    count = 0
    name_len = len(from_name)
    for m in pattern.finditer(content):
        s = m.start()
        if _is_element_name_context(content, s):
            continue  # skip — match é nome de element/tag
        if _is_attribute_name_context(content, s, name_len):
            continue  # skip — match é nome de attribute (property da activity)
        out_parts.append(content[last:s])
        out_parts.append(to_name)
        last = m.end()
        count += 1
    out_parts.append(content[last:])
    return ("".join(out_parts), count)


def _has_orphan_ref(content: str, name: str, exclude: str | None = None) -> bool:
    """True se houver match case-insensitive whole-word de `name` fora de
    contexto element-name. Usado pós-rename para detectar refs órfãs que
    não foram alcançadas pela substituição.

    `exclude` (case-sensitive): match exato deste valor é considerado
    rename ok, não orphan. Necessário pra case-only renames
    (`in_StCpfCnpj` → `in_StCPFCNPJ`) onde new name é case-insensitive
    igual ao old name — sem `exclude` daria false positive.
    """
    pattern = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
    name_len = len(name)
    for m in pattern.finditer(content):
        s = m.start()
        if _is_element_name_context(content, s):
            continue
        if _is_attribute_name_context(content, s, name_len):
            continue  # attribute name (activity property) ≠ orphan ref
        if exclude is not None and m.group(0) == exclude:
            continue
        return True
    return False


def _has_duplicate_invoke_arg_keys(content: str) -> bool:
    args_block_re = re.compile(
        r'<ui:InvokeWorkflowFile\.Arguments\s*>(.*?)</ui:InvokeWorkflowFile\.Arguments\s*>',
        re.DOTALL,
    )
    for block in args_block_re.finditer(content):
        keys = re.findall(r'\bx:Key="([^"]+)"', block.group(1))
        if len(keys) != len(set(keys)):
            return True
    return False


@register("rename_attribute")
def apply_rename_attribute(file: Path, spec: dict, dry_run: bool = True) -> bool:
    from_name = spec.get("from")
    to_name = spec.get("to")
    if not from_name or not to_name:
        return False
    content = file.read_text(encoding="utf-8-sig")
    new_content, n = _whole_word_sub_skip_tags(content, from_name, to_name)
    if n == 0 or new_content == content:
        return False
    # Safety check — orphan ref detection (caso `to_name` colida case-insensitive
    # com outro identifier não relacionado). Se sobra match de `from_name`
    # fora de contexto element-name, abortar pra evitar quebra silenciosa.
    if _has_orphan_ref(new_content, from_name, exclude=to_name):
        print(f"  [NEEDS_REVIEW] rename_attribute: orphan refs '{from_name}' em {file.name} — fix abortado")
        return False
    if _has_duplicate_invoke_arg_keys(new_content):
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("rename_attribute_name_in_tag")
def apply_rename_attribute_name_in_tag(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """CCS-1 fixer: rename the attribute NAME (case-correction) inside the open
    tag(s) of a specific invocation element.

    Unlike `rename_attribute` (which skips attribute-name contexts by design —
    see `_is_attribute_name_context` — so it would no-op on the very attribute
    CCS-1 targets), this fixer rewrites the attribute NAME within the matched
    `<element ...>` open tag only. Scoped to the element to avoid touching
    homonym attributes on unrelated activities.

    Spec:
        from    : current (wrong-cased) attribute name (e.g. 'out_UiESipagDirect')
        to      : correct attribute name (e.g. 'out_UIESipagDirect')
        element : qualified invocation element name (e.g. 'c:Login'). Required —
                  without it we would risk a file-wide attribute rename.

    Safety:
      - Only rewrites within `<element ...>` / `<element ... />` OPEN tags.
      - Whole-word attribute-name match (`\\bfrom=`) so substrings/values are
        never touched.
      - Idempotent: no-op if `from` not present as an attribute name in any
        matched open tag.
      - Preserves BOM.
    """
    from_name = spec.get("from")
    to_name = spec.get("to")
    element = spec.get("element")
    if not from_name or not to_name or not element:
        return False
    if from_name == to_name:
        return False
    # Validate identifiers (XML attribute names + qualified element local).
    if not re.fullmatch(r"[A-Za-z_][\w.\-]*(?::[A-Za-z_][\w.\-]*)?", element):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.\-]*", from_name):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.\-]*", to_name):
        return False

    content = file.read_text(encoding="utf-8-sig")

    # Match open tags (self-close or paired) of exactly this element.
    open_tag_re = re.compile(
        rf'<{re.escape(element)}\b(?P<body>[^>]*?)(?P<sc>/?)>',
        re.DOTALL,
    )
    # Attribute-name occurrence inside a tag body: whitespace-led, followed by `=`.
    attr_name_re = re.compile(
        rf'(?P<lead>\s){re.escape(from_name)}(?P<eq>\s*=)'
    )

    changed = [False]

    def _rewrite_tag(m: re.Match) -> str:
        body = m.group("body")
        sc = m.group("sc")
        new_body, n = attr_name_re.subn(
            lambda am: f'{am.group("lead")}{to_name}{am.group("eq")}', body
        )
        if n == 0 or new_body == body:
            return m.group(0)
        changed[0] = True
        return f'<{element}{new_body}{sc}>'

    new_content = open_tag_re.sub(_rewrite_tag, content)
    if not changed[0] or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("rename_argument")
def apply_rename_argument(
    file: Path, spec: dict, dry_run: bool = True, project_root: Path | None = None
) -> bool:
    """Rename arg `from_name` → `to_name`.

    Callee (file): rename `Name="<from>"` declaração + whole-word `\\b<from>\\b`
    em todo body (cobre uses em expressões `[in_OldArg.ToString]`).

    Callers (project_root): localizam `WorkflowFileName="...<basename>"` (qualquer
    separator), trocam `x:Key="<from>"` + `\\b<from>\\b` whole-word.
    """
    from_name = spec.get("from")
    to_name = spec.get("to")
    if not from_name or not to_name:
        return False
    target_wf = spec.get("target_workflow")

    content = file.read_text(encoding="utf-8-sig")
    # Name="..." declaração é case-sensitive (XML attr value identifies a
    # specific declaration). Rename só do exact-case match.
    new_content = re.sub(
        rf'Name="{re.escape(from_name)}"', f'Name="{to_name}"', content
    )
    # Body refs (VB expressions, [argname], etc.) case-insensitive.
    new_content, _ = _whole_word_sub_skip_tags(new_content, from_name, to_name)
    changed = new_content != content
    if changed and _has_orphan_ref(new_content, from_name, exclude=to_name):
        print(f"  [NEEDS_REVIEW] rename_argument (callee): orphan refs '{from_name}' em {file.name} — fix abortado")
        return False
    if changed and _has_duplicate_invoke_arg_keys(new_content):
        return False
    if changed and not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))

    if project_root is None or not target_wf:
        return changed

    # Match callers via WorkflowFileName attribute, accepting both `\` and `/`.
    basename = target_wf.replace("\\", "/").split("/")[-1]
    callee_pattern = re.compile(
        rf'WorkflowFileName="(?:[^"]*[\\/])?{re.escape(basename)}"'
    )
    # Class name = stem of basename. Cross-file PropertyElement default-value
    # syntax uses `this:<ClassName>.<arg>` — present quando caller seta default
    # via xmlns:this (CLR namespace vazio compartilhado dentro do projeto).
    target_class = basename.rsplit(".", 1)[0] if "." in basename else basename
    this_arg_pattern = re.compile(
        rf'\bthis:{re.escape(target_class)}\.{re.escape(from_name)}\b'
    )
    invoke_block_re = re.compile(
        r'<ui:InvokeWorkflowFile\b[^>]*>.*?</ui:InvokeWorkflowFile>',
        re.DOTALL,
    )

    for xaml in project_root.rglob("*.xaml"):
        if xaml.resolve() == file.resolve():
            continue
        try:
            c = xaml.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        has_invoke = bool(callee_pattern.search(c))
        has_this_arg = bool(this_arg_pattern.search(c))
        if not (has_invoke or has_this_arg):
            continue

        new_c = c

        # 1. <ui:InvokeWorkflowFile> blocks: rename x:Key + body refs.
        if has_invoke:
            def _maybe_rename_block(match):
                block = match.group(0)
                if not callee_pattern.search(block):
                    return block
                new_block = re.sub(
                    rf'x:Key="{re.escape(from_name)}"', f'x:Key="{to_name}"', block
                )
                new_block, _ = _whole_word_sub_skip_tags(new_block, from_name, to_name)
                if _has_duplicate_invoke_arg_keys(new_block):
                    return block
                return new_block
            new_c = invoke_block_re.sub(_maybe_rename_block, new_c)

        # 2. PropertyElement default-value cross-file: `this:<Class>.<arg>` em
        #    attribute form (`this:Class.OldArg="..."`) e element form
        #    (`<this:Class.OldArg>...</this:Class.OldArg>`). Single sub cobre
        #    todas ocorrências (regex word-boundary).
        if has_this_arg or this_arg_pattern.search(new_c):
            new_c = this_arg_pattern.sub(
                f'this:{target_class}.{to_name}', new_c
            )

        if new_c != c:
            # Orphan check 1 — escopo de InvokeWorkflowFile blocks que apontam
            # pro callee.
            orphan_in_callee_blocks = False
            for blk in invoke_block_re.findall(new_c):
                if not callee_pattern.search(blk):
                    continue
                if _has_orphan_ref(blk, from_name, exclude=to_name):
                    orphan_in_callee_blocks = True
                    break
            if orphan_in_callee_blocks:
                print(f"  [NEEDS_REVIEW] rename_argument (caller): orphan refs '{from_name}' em {xaml.name} — caller skip")
                continue
            # Orphan check 2 — sobrou `this:<Class>.<from>` em algum lugar.
            if this_arg_pattern.search(new_c):
                print(f"  [NEEDS_REVIEW] rename_argument (caller): orphan this:{target_class}.{from_name} em {xaml.name} — caller skip")
                continue
            changed = True
            if not dry_run:
                _write_preserving_bom(xaml, new_c, _file_has_bom(xaml))

    return changed


@register("rename_xclass")
def apply_rename_xclass(
    file: Path, spec: dict, dry_run: bool = True, project_root: Path | None = None
) -> bool:
    """Rename `x:Class` to match filename and propagate `this:` references.

    Side-effects of an x:Class rename that callers must NOT miss:
      1. PropertyElement default-value blocks in the same file:
         `<this:OldClass.argName>...</this:OldClass.argName>` → uses `this:`
         prefix bound to own x:Class. Stale prefix → Studio compile error
         "Cannot set unknown member".
      2. Cross-project callers may reference `<this:OldClass.*` or
         `x:Key="OldClass.*"` (rare, but happens with PropertyElement defaults
         passed at invocation). Scan project_root and rewrite.

    Spec:
      to: new class name (default: file.stem)
      from: old class name (default: detected from current x:Class attr)
    """
    content = file.read_text(encoding="utf-8-sig")
    xclass_re = re.compile(r'(<Activity\b[^>]*\sx:Class=")([^"]+)(")')
    m = xclass_re.search(content[:5000])
    if not m:
        return False
    current = m.group(2)
    from_name = spec.get("from") or current
    to_name = spec.get("to") or file.stem
    if from_name == to_name:
        return False
    # GUARD: to_name precisa ser identificador XAML valido. Filenames numerados/
    # com espaco (ex: "1.1 ObtemEstrutura") gerariam `<this:1.1 ...>` = XML
    # nao-well-formed. Nesse caso o rename de x:Class nao se aplica (o fix real
    # e' renomear o arquivo) — skip em vez de produzir XML invalido (rollback).
    if not re.match(r"^[A-Za-z_]\w*$", to_name):
        return False

    # 1. x:Class attribute itself
    new_content = xclass_re.sub(
        lambda mm: f"{mm.group(1)}{to_name}{mm.group(3)}" if mm.group(2) == from_name else mm.group(0),
        content,
    )
    # 2. Same-file `this:Old.` → `this:New.`
    this_ref_re = re.compile(rf'\bthis:{re.escape(from_name)}\.')
    new_content = this_ref_re.sub(f'this:{to_name}.', new_content)

    changed = new_content != content
    if changed and not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))

    if project_root is None:
        return changed

    # 3. Cross-project: callers referencing `this:Old.` ou `x:Key="Old.*"`.
    # COLLISION CHECK: se outros files também têm `x:Class="<from_name>"`,
    # este rename NÃO pode propagar cross-project — `this:Old.X` em outro
    # caller pode estar bindando em qualquer dos files que compartilham
    # x:Class (Sicoob template antipattern: muitos files começam com
    # `x:Class="API"`). Auto-rename cross-project bagunçaria refs alheias.
    # Same-file rename (step 2) é seguro e suficiente.
    other_files_same_class = []
    xclass_collision_re = re.compile(
        rf'<Activity\b[^>]*\sx:Class="{re.escape(from_name)}"'
    )
    for xaml in project_root.rglob("*.xaml"):
        if xaml.resolve() == file.resolve():
            continue
        try:
            head = xaml.read_text(encoding="utf-8-sig")[:5000]
        except Exception:
            continue
        if xclass_collision_re.search(head):
            other_files_same_class.append(xaml.name)
    if other_files_same_class:
        print(
            f"  [SKIP cross-project this:{from_name}] {file.name}: "
            f"x:Class=\"{from_name}\" também em {len(other_files_same_class)} "
            f"outros files ({', '.join(other_files_same_class[:3])}...). "
            f"Não propaga cross-project."
        )
        return changed

    cross_this_re = re.compile(rf'\bthis:{re.escape(from_name)}\.')
    cross_key_re = re.compile(rf'x:Key="{re.escape(from_name)}\.')
    for xaml in project_root.rglob("*.xaml"):
        if xaml.resolve() == file.resolve():
            continue
        try:
            c = xaml.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        new = cross_this_re.sub(f'this:{to_name}.', c)
        new = cross_key_re.sub(f'x:Key="{to_name}.', new)
        if new != c:
            changed = True
            if not dry_run:
                _write_preserving_bom(xaml, new, _file_has_bom(xaml))

    return changed


@register("dedupe_idref")
def apply_dedupe_idref(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Renomeia IdRef duplicados dentro de um XAML. Mantém primeira ocorrência;
    subsequentes recebem suffix `_dedup_<n>`. Atualiza refs no mesmo arquivo
    (qualquer attribute value contendo o IdRef antigo via `\\b<id>\\b`).

    Idempotente: 2ª chamada não encontra duplicatas, no-op.
    """
    content = file.read_text(encoding="utf-8-sig")
    # Match attr `IdRef="X"` em qualquer namespace (sap2010, sap, etc.)
    idref_re = re.compile(r'\b(?:[\w]+:)?IdRef="([^"]+)"')
    seen: dict[str, int] = {}
    duplicates: list[tuple[int, int, str, str]] = []  # (start, end, old, new)
    for m in idref_re.finditer(content):
        val = m.group(1)
        seen[val] = seen.get(val, 0) + 1
        if seen[val] > 1:
            new_val = f"{val}_dedup_{seen[val]}"
            duplicates.append((m.start(1), m.end(1), val, new_val))
    if not duplicates:
        return False
    # Apply replacements in REVERSE order (preserve offsets).
    new_content = content
    for start, end, old, new in reversed(duplicates):
        new_content = new_content[:start] + new + new_content[end:]
    # Não atualizar refs cross-element — IdRef em XAML 2010 é só identifier
    # do próprio element, não chave de lookup global. ViewState dict pode
    # conter IdRef como key — handled implicit (ViewState entry permanece com
    # old value, mas é só rendering hint; orphan key tolerado por Studio).
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return new_content != content


@register("xmlns_assembly_resolve")
def apply_xmlns_assembly_resolve(file: Path, spec: dict, dry_run: bool = True,
                                  project_root: Path | None = None) -> bool:
    """Resolve xmlns prefix com assembly não declarado.

    Spec:
      assembly: nome do assembly (ex: 'UiPath.Testing.Activities')
      action: 'add_package' | 'remove'
      package: nome do pacote a adicionar (se action=add_package)
      version: versão (se action=add_package)
      prefix: nome do xmlns prefix (se action=remove, ex: 'uta')
    """
    action = spec.get("action")
    if action == "add_package":
        package = spec.get("package")
        version = spec.get("version")
        if not package or not version or project_root is None:
            return False
        proj_json = project_root / "project.json"
        if not proj_json.exists():
            return False
        import json as _json
        raw = proj_json.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        try:
            data = _json.loads(raw.decode("utf-8-sig"))
        except _json.JSONDecodeError:
            return False
        deps = data.setdefault("dependencies", {})
        pinned = f"[{version}]"
        if deps.get(package) == pinned:
            return False
        deps[package] = pinned
        new_text = _json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if not dry_run:
            out = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
            proj_json.write_bytes(out)
        return True

    if action == "remove":
        prefix = spec.get("prefix")
        if not prefix:
            return False
        content = file.read_text(encoding="utf-8-sig")
        # Remove xmlns:<prefix>="..." attr from <Activity> root
        new_content = re.sub(
            rf'\s+xmlns:{re.escape(prefix)}="[^"]+"', "", content, count=1
        )
        # Remove all <prefix:Activity ...> ... </prefix:Activity> blocks
        # (open+close form)
        new_content = re.sub(
            rf'<{re.escape(prefix)}:[^>\s]+\b[^>]*>.*?</{re.escape(prefix)}:[^>]+>',
            "", new_content, flags=re.DOTALL,
        )
        # Remove self-close <prefix:Activity ... />
        new_content = re.sub(
            rf'<{re.escape(prefix)}:[^>\s]+\b[^>]*?/>', "", new_content,
        )
        if new_content == content:
            return False
        if not dry_run:
            _write_preserving_bom(file, new_content, _file_has_bom(file))
        return True
    return False


@register("arg_default_to_element_form")
def apply_arg_default_to_element_form(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Convert root attribute `this:Class.<arg>="value"` em element form
    `<this:Class.<arg>>...InArgument...</this:Class.<arg>>`.

    Spec:
      class_name: nome do x:Class (ex: 'PlataformaDeCredito')
      arg_name: nome do argumento (ex: 'in_StCpfCnpj')
      arg_type: type pulled from <x:Property> (ex: 'x:String', 'x:Int32')
      value: literal/expression como aparece no attr (ex: '03567879000146' ou '[expr]')
    """
    class_name = spec.get("class_name")
    arg_name = spec.get("arg_name")
    arg_type = spec.get("arg_type")
    value = spec.get("value")
    if not all([class_name, arg_name, arg_type, value is not None]):
        return False
    content = file.read_text(encoding="utf-8-sig")
    # Remove attr from <Activity> root
    attr_re = re.compile(
        rf'\s+this:{re.escape(class_name)}\.{re.escape(arg_name)}="[^"]*"'
    )
    if not attr_re.search(content):
        return False
    new_content = attr_re.sub("", content, count=1)
    # Build element form. VB expression `[expr]` vs literal.
    is_expr = value.startswith("[") and value.endswith("]")
    inner_expr = value if is_expr else f"[&quot;{value}&quot;]"
    element_block = (
        f'\n  <this:{class_name}.{arg_name}>'
        f'<InArgument x:TypeArguments="{arg_type}">'
        f'{inner_expr}</InArgument>'
        f'</this:{class_name}.{arg_name}>'
    )
    # Insert after </x:Members> tag (or before <Sequence> if no members)
    if "</x:Members>" in new_content:
        new_content = new_content.replace(
            "</x:Members>", "</x:Members>" + element_block, 1
        )
    else:
        # Fallback: insert after first <Activity ...> opening tag
        m = re.search(r"<Activity\b[^>]*>", new_content)
        if m:
            new_content = new_content[:m.end()] + element_block + new_content[m.end():]
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("delete_empty_element")
def apply_delete_empty_element(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Remove element vazio (open+close apenas whitespace, ou self-close).
    Idempotente. Suporta:
      - `<Tag>\\s*</Tag>` (open+close empty)
      - `<Tag\\s*/>` (self-close)
      - `<Tag attrs="..."\\s*/>` (self-close com attrs)

    Spec:
      tag: nome local da tag (ex: `Sequence.Variables`, `Sequence`)
    """
    tag = spec.get("tag")
    if not tag:
        return False
    content = file.read_text(encoding="utf-8-sig")
    # Open+close empty (whitespace-only inside)
    oc = re.compile(
        rf'\s*<{re.escape(tag)}\b[^>]*?>\s*</{re.escape(tag)}>\s*'
    )
    new_content, n_oc = oc.subn("\n", content)
    # Self-close (sem content por definição)
    sc = re.compile(rf'\s*<{re.escape(tag)}\b[^>]*?/>\s*')
    new_content, n_sc = sc.subn("\n", new_content)
    if (n_oc + n_sc) == 0 or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("delete_variable")
def apply_delete_variable(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Remove `<Variable Name="X">` declaration. Suporta self-close
    e open+close forms. Idempotente. Match case-sensitive em XML attr,
    case-insensitive seria perigoso (variável `vX` e `VX` em mesmo escopo
    são tecnicamente VB-equivalent mas XML-distinct — manter strict)."""
    name = spec.get("name")
    if not name:
        return False
    content = file.read_text(encoding="utf-8-sig")
    # Self-close: <Variable ... Name="X" .../>
    sc = re.compile(
        rf'\s*<Variable\b[^>]*?\bName="{re.escape(name)}"[^>]*?/>\s*'
    )
    new_content, n_sc = sc.subn("\n", content)
    if n_sc == 0:
        # Open+close: <Variable ... Name="X" ...>...</Variable>
        oc = re.compile(
            rf'\s*<Variable\b[^>]*?\bName="{re.escape(name)}"[^>]*?>.*?</Variable>\s*',
            re.DOTALL,
        )
        new_content, n_oc = oc.subn("\n", content)
        if n_oc == 0:
            return False
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("set_json_field")
def apply_set_json_field(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Set JSON field at dot-path to canonical value. Idempotent.

    Spec:
      path: dot-separated key path (ex: 'studioVersion', 'foo.bar.baz')
      value: scalar value (string/number/bool/null) ou dict/list (full replace)
    """
    import json as _json
    path = spec.get("path")
    value = spec.get("value")
    if not path or value is None:
        return False
    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return False
    keys = path.split(".")
    cur = data
    for k in keys[:-1]:
        if not isinstance(cur, dict):
            return False
        cur = cur.setdefault(k, {})
    last = keys[-1]
    if isinstance(cur, dict) and cur.get(last) == value:
        return False
    if isinstance(cur, dict):
        cur[last] = value
    else:
        return False
    new_text = _json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
        file.write_bytes(out)
    return True


@register("json_array_ensure")
def apply_json_array_ensure(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Ensure JSON array at dot-path contains required values. Append missing.
    Idempotente; case-insensitive match.

    Spec:
      path: dot-separated key path (ex: 'runtimeOptions.excludedLoggedData')
      values: list of required string values to ensure present
    """
    import json as _json
    path = spec.get("path")
    values = spec.get("values") or []
    if not path or not values:
        return False
    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return False
    keys = path.split(".")
    cur = data
    for k in keys[:-1]:
        if not isinstance(cur, dict):
            return False
        cur = cur.setdefault(k, {})
    last = keys[-1]
    if not isinstance(cur, dict):
        return False
    arr = cur.get(last)
    if arr is None:
        arr = []
    elif not isinstance(arr, list):
        return False
    existing_lower = {str(x).lower() for x in arr}
    missing = [v for v in values if str(v).lower() not in existing_lower]
    if not missing:
        return False
    arr = list(arr) + missing
    cur[last] = arr
    new_text = _json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
        file.write_bytes(out)
    return True


@register("set_dependency_pin")
def apply_set_dependency_pin(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Pin package version em project.json. Idempotente.

    Spec:
      package: nome exato do pacote (ex: 'UiPath.System.Activities')
      version: versão pinada formato `[X.Y.Z]` (canonical Sicoob)

    Diferença vs set_json_field: dot-path quebraria em
    `dependencies.UiPath.System.Activities` (split por `.`). Aqui acessa
    `data['dependencies'][package]` direto.
    """
    import json as _json
    package = spec.get("package")
    version = spec.get("version")
    if not package or not version:
        return False
    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return False
    deps = data.get("dependencies")
    if not isinstance(deps, dict):
        return False
    existing_key = None
    for key in deps:
        if str(key).lower() == str(package).lower():
            existing_key = key
            break
    if existing_key == package and deps.get(package) == version:
        return False
    if existing_key is not None and existing_key != package:
        deps.pop(existing_key, None)
    deps[package] = version
    new_text = _json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
        file.write_bytes(out)
    return True


@register("force_attribute")
def apply_force_attribute(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Set tag attr to canonical value. Replace se presente com valor diferente,
    add se ausente. Idempotente.

    Diff vs `set_attribute`:
      - `set_attribute`: SKIP se attr presente (qualquer valor).
      - `force_attribute`: REPLACE se attr presente com valor != target.

    Usa pattern lazy `[^>]*?` + grupo opcional `(/?)` (mesma técnica de
    set_attribute) p/ preservar self-close.
    """
    tag = spec.get("tag")
    attr = spec.get("attribute")
    value = spec.get("value")
    if not all([tag, attr, value is not None]):
        return False
    content = file.read_text(encoding="utf-8-sig")
    pattern = re.compile(rf"<{re.escape(tag)}(?=[\s/>])([^>]*?)(/?)>", re.DOTALL)
    attr_in_existing = re.compile(rf'(\s){re.escape(attr)}="([^"]*)"')

    def replace(m):
        existing = m.group(1)
        self_close = m.group(2)
        existing_attr = attr_in_existing.search(existing)
        if existing_attr:
            if existing_attr.group(2) == value:
                return m.group(0)
            new_existing = attr_in_existing.sub(
                rf'\g<1>{attr}="{value}"', existing, count=1
            )
            return f'<{tag}{new_existing}{self_close}>'
        if not self_close and _has_property_element_for_attr(content, tag, attr, m.end()):
            return m.group(0)
        sep = '' if existing.endswith(' ') else ' '
        return f'<{tag}{existing}{sep}{attr}="{value}"{self_close}>'

    new_content = pattern.sub(replace, content)
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("set_attribute")
def apply_set_attribute(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Insere attr em opening tag se ausente. Suporta `<X attrs>` e `<X attrs/>`
    em uma única pass — pattern lazy `[^>]*?` + grupo opcional `(/?)` captura
    self-close marker corretamente. Bug histórico (corrupção em self-close
    quando tratado em duas passes) corrigido aqui.
    """
    tag = spec.get("tag")
    attr = spec.get("attribute")
    value = spec.get("value")
    if not all([tag, attr, value is not None]):
        return False
    content = file.read_text(encoding="utf-8-sig")
    pattern = re.compile(rf"<{re.escape(tag)}(?=[\s/>])([^>]*?)(/?)>", re.DOTALL)

    def replace(m):
        existing = m.group(1)
        self_close = m.group(2)
        if re.search(rf'\b{re.escape(attr)}\s*=', existing):
            return m.group(0)
        if not self_close and _has_property_element_for_attr(content, tag, attr, m.end()):
            return m.group(0)
        sep = '' if existing.endswith(' ') else ' '
        return f'<{tag}{existing}{sep}{attr}="{value}"{self_close}>'

    new_content = pattern.sub(replace, content)

    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("delete_element")
def apply_delete_element(file: Path, spec: dict, dry_run: bool = True) -> bool:
    pattern = spec.get("pattern")
    if not pattern:
        return False
    content = file.read_text(encoding="utf-8-sig")
    new_content, n = re.subn(pattern, "", content)
    if n == 0 or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("rename_invoke_arg_key")
def apply_rename_invoke_arg_key(
    file: Path, spec: dict, dry_run: bool = True
) -> bool:
    """Rename `x:Key="from_key"` → `x:Key="to_key"` SOMENTE dentro do
    `<ui:InvokeWorkflowFile>` que aponta para `workflow_basename` (e
    opcionalmente identificado por `invoke_idref` quando há múltiplos
    callers ao mesmo callee no caller).
    """
    basename = spec.get("workflow_basename")
    from_key = spec.get("from_key")
    to_key = spec.get("to_key")
    idref = spec.get("invoke_idref")
    if not basename or not from_key or not to_key:
        return False
    content = file.read_text(encoding="utf-8-sig")

    invoke_block_re = re.compile(
        r'<ui:InvokeWorkflowFile\b(?P<attrs>[^>]*)>(?P<inner>.*?)</ui:InvokeWorkflowFile>',
        re.DOTALL,
    )
    name_re = re.compile(
        rf'WorkflowFileName="(?:[^"]*[\\/])?{re.escape(basename)}"'
    )
    idref_re = re.compile(rf'sap2010:WorkflowViewState\.IdRef="{re.escape(idref)}"') if idref else None
    key_re = re.compile(rf'(x:Key=")({re.escape(from_key)})(")')

    changed = [False]

    def _maybe_rename(match):
        attrs = match.group("attrs")
        inner = match.group("inner")
        if not name_re.search(attrs):
            return match.group(0)
        if idref_re is not None and not idref_re.search(attrs):
            return match.group(0)
        # Same fix iteration can first add `to_key` via A-19b and then process
        # a stale A-19c finding computed before that insertion. Renaming now
        # would create duplicate x:Key entries and Studio fails loading the
        # InvokeWorkflowFile.Arguments dictionary.
        if re.search(rf'\bx:Key="{re.escape(to_key)}"', inner):
            return match.group(0)
        new_inner = key_re.sub(rf'\1{to_key}\3', inner)
        if new_inner == inner:
            return match.group(0)
        changed[0] = True
        # Reconstruct
        return match.group(0).replace(inner, new_inner, 1)

    new_content = invoke_block_re.sub(_maybe_rename, content)
    if not changed[0]:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


_PRIMITIVE_LITERAL_DEFAULTS: dict[str, str] = {
    "x:String": "",
    "x:Boolean": "False",
    "x:Int32": "0",
    "x:Int64": "0",
    "x:Double": "0",
    "x:Decimal": "0",
    "x:Single": "0",
}


_SELF_CLOSED_INARG_RE = re.compile(
    r'<InArgument\s+(?P<attrs>[^/>]*?)\s*/>'
)


@register("expand_self_closed_inarg")
def apply_expand_self_closed_inarg(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """W-1: convert `<InArgument x:Key="X" />` self-closed em caller para
    forma expandida.

    - Tipos primitivos (`x:String`/`Boolean`/`Int32`/`Int64`/`Double`/
      `Decimal`/`Single`): emite `<Literal x:TypeArguments="<T>" Value="<default>"/>`
      com default conforme tipo.
    - Tipos não-primitivos (Tuple, Dict, classes custom, qualquer com `(` ou
      `:` que não sejam x:): emite `<x:Null />` — Literal Value="" quebra
      tipos complexos com 'Set property Value threw exception'.

    Idempotent. Sem-op se nenhum self-closed InArgument com x:Key.
    """
    content = file.read_text(encoding="utf-8-sig")

    def expand(m: re.Match) -> str:
        attrs = m.group("attrs")
        # only expand caller-side self-closed (must have x:Key)
        if 'x:Key="' not in attrs:
            return m.group(0)
        type_match = re.search(r'x:TypeArguments="([^"]+)"', attrs)
        if not type_match:
            return m.group(0)
        t = type_match.group(1)
        attrs_clean = attrs.strip()
        if t in _PRIMITIVE_LITERAL_DEFAULTS:
            val = _PRIMITIVE_LITERAL_DEFAULTS[t]
            return (
                f'<InArgument {attrs_clean}>'
                f'<Literal x:TypeArguments="{t}" Value="{val}" />'
                f'</InArgument>'
            )
        return f'<InArgument {attrs_clean}><x:Null /></InArgument>'

    new_content = _SELF_CLOSED_INARG_RE.sub(expand, content)
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


_NUM_TYPES_RE = r"x:(?:Int32|Int64|Boolean|Double|Decimal|Single)"
_NUM_DEFAULT_ELEM_RE = re.compile(
    rf'(<InArgument\s+x:TypeArguments="{_NUM_TYPES_RE}"\s*>)\[&quot;([^&\]]*)&quot;\](</InArgument>)'
)
_NUM_DEFAULT_ATTR_RE = re.compile(
    r'(this:[A-Za-z_][\w]*\.in_(?:Int|Bl|Db|Dec|Dbl)[A-Za-z]*=")\[&quot;([^&\]]*)&quot;\](")'
)


@register("strip_string_quotes_numeric_default")
def apply_strip_string_quotes_numeric_default(
    file: Path, spec: dict, dry_run: bool = True
) -> bool:
    """V-2: stripar `&quot;...&quot;` de Default literais numéricos/booleanos.

    Pattern element-form:
      <InArgument x:TypeArguments="x:Int32">[&quot;60&quot;]</InArgument>
      → <InArgument x:TypeArguments="x:Int32">[60]</InArgument>

    Pattern attr-form (raiz):
      this:Class.in_IntFoo="[&quot;60&quot;]"
      → this:Class.in_IntFoo="[60]"

    Validação: conteúdo deve ser parseável como número (int/float) ou bool.
    Senão preserva (não é só questão de aspas).
    """
    content = file.read_text(encoding="utf-8-sig")

    def _is_numeric_or_bool(v: str) -> bool:
        s = v.strip()
        if s.lower() in ("true", "false"):
            return True
        try:
            float(s.replace(",", "."))
            return True
        except ValueError:
            return False

    def fix_elem(m: re.Match) -> str:
        prefix, val, suffix = m.groups()
        if not _is_numeric_or_bool(val):
            return m.group(0)
        v = val.strip()
        if v.lower() in ("true", "false"):
            v = v.capitalize()
        return f"{prefix}[{v}]{suffix}"

    def fix_attr(m: re.Match) -> str:
        prefix, val, suffix = m.groups()
        if not _is_numeric_or_bool(val):
            return m.group(0)
        v = val.strip()
        if v.lower() in ("true", "false"):
            v = v.capitalize()
        return f"{prefix}[{v}]{suffix}"

    new_content = _NUM_DEFAULT_ELEM_RE.sub(fix_elem, content)
    new_content = _NUM_DEFAULT_ATTR_RE.sub(fix_attr, new_content)
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


# ---------------------------------------------------------------------------
# N-5 fixer: insert <ui:LogMessage Level="Trace" .../> after a flagged activity.
#
# Key invariants:
#   - Walker compares FULL tag names (e.g. `Assign` vs `Assign.To` are
#     distinct). Bug histórico (regex `<Assign\b` casava com `<Assign.To>`)
#     levou a inserção dentro de `<Assign>` quebrando compile Studio.
#   - Parent restritivo (single-child / collection-typed / qualified-property
#     que aceita só specific children) → skip.
#   - IdRef único: counter scaneado de IdRefs existentes no arquivo, +offset.
#   - Idempotência: detector re-run não re-emite finding pra mesma activity
#     porque Trace já estará dentro de proximity_window.
# ---------------------------------------------------------------------------

# Tag name pattern: prefix:Local with optional `.SubProp` qualified-property
# part. NOTE: `.` is NOT a word char, so `\b` after the name doesn't work
# uniformly. Use explicit terminator chars.
_FULLTAG_RE = re.compile(
    r'<(?P<slash>/?)\s*(?P<name>[A-Za-z_][\w.\-]*(?::[\w.\-]+)?)(?=[\s/>])'
    r'(?P<attrs>[^>]*?)(?P<self>/?)>',
    re.DOTALL,
)

# Parents que NÃO aceitam sibling LogMessage extra. Inserir Trace ali quebra
# compile Studio.
#
# COBERTURA EM CAMADAS (defesa em profundidade):
#   1. Heurística `.` em parent_local → rejeita TODOS qualified-property
#      elements (Assign.To, If.Then, ui:HttpClient.Headers, etc.). Sem
#      precisar enumerar caso a caso.
#   2. `_COLLECTION_LOCAL_NAMES` → rejeita typed collections.
#   3. Esta lista (mínima): non-dot, non-collection special parents que
#      rejeitam activities mas precisam ser nomeados explicitamente.
#   4. Layer 2 (Studio Analyzer gate) → ground truth final. Pega o que
#      escapar das camadas 1-3.
#
# Itens removidos desta lista (cobertos pela camada 1 ou 2):
#   - Todas entries com `.` (Assign.To, ui:HttpClient.Headers, etc.)
#   - Typed collections (movidas pra _COLLECTION_LOCAL_NAMES)
#   - Long tail de qualified-property singletons (Layer 2 captura)
# Parents non-qualified que rejeitam LogMessage E NÃO são wrap-able
# (tipos com signature/shape específica).
_N5_RESTRICTIVE_PARENT_NAMES = frozenset({
    # ActivityFunc: generic signature (Func<T1, ..., TN, TResult>) — wrap
    # quebraria type contract.
    "ActivityFunc",
    # Argument shapes — wrapper elements que não comportam activities
    "InArgument", "OutArgument", "InOutArgument", "Literal",
    # Variable/Property/Member containers — accept declarations, not activities
    "Variable", "Variables", "Property", "Members",
})

# Parents non-qualified que aceitam single Activity child — wrap em Sequence
# converte em multi-child container, mantém type contract.
_N5_WRAP_ABLE_NON_QUALIFIED = frozenset({
    # ActivityAction: delegate body — accept single Activity. Sequence é
    # Activity-shape, wrap legítimo.
    "ActivityAction",
    # FlowStep: System.Activities.Statements — single-Activity slot (implicit
    # `Action` property). Schema não cobre WF base types → cai em "unknown".
    # Insert direto como sibling causa Studio error `'Action' property has
    # already been set on 'FlowStep'`. Wrap em Sequence é safe: Sequence é
    # Activity → FlowStep Action aceita → 1 child Activity preserved.
    "FlowStep",
})


# Pattern pra detectar parent qualname tipo collection (sufixo `:List`,
# `:Dictionary`, etc.) — defesa adicional caso prefix aliasing varie.
_COLLECTION_LOCAL_NAMES = frozenset({
    "BindingList", "List", "Dictionary", "Collection",
    "HashSet", "Queue", "Stack", "ObservableCollection",
    "ReadOnlyCollection",
})


def _n5_walk_to_element_end(content: str, opening_offset: int):
    """Return offset just after closing tag of element at opening_offset.
    Tag name comparison is EXACT — `Assign` and `Assign.To` are distinct.
    Returns (end_offset, tag_name) or (None, None)."""
    m = _FULLTAG_RE.match(content, opening_offset)
    if not m or m.group("slash") == "/":
        return None, None
    name = m.group("name")
    if m.group("self") == "/":
        return m.end(), name
    depth = 1
    pos = m.end()
    while pos < len(content):
        m2 = _FULLTAG_RE.search(content, pos)
        if m2 is None:
            return None, None
        n2 = m2.group("name")
        if n2 != name:
            pos = m2.end()
            continue
        if m2.group("slash") == "/":
            depth -= 1
            pos = m2.end()
            if depth == 0:
                return pos, name
        elif m2.group("self") == "/":
            pos = m2.end()
        else:
            depth += 1
            pos = m2.end()
    return None, None


def _n5_find_immediate_parent_via_lxml(content: bytes, target_line: int,
                                         target_local: str):
    """Use lxml to find target activity at given line, return parent's full
    qualified name (prefix:Local or just Local). Returns None if not found
    or activity has no parent."""
    try:
        from lxml import etree
    except ImportError:
        return None
    parser = etree.XMLParser(remove_blank_text=False, recover=False,
                              huge_tree=True)
    try:
        root = etree.fromstring(content, parser)
    except etree.XMLSyntaxError:
        return None
    # Walk all elements; match by sourceline + localname/qname
    for elem in root.iter():
        if elem.sourceline != target_line:
            continue
        qn = etree.QName(elem.tag)
        local = qn.localname
        prefix = elem.prefix
        qual = f"{prefix}:{local}" if prefix else local
        # target_local may be "Assign" or "ui:HttpClient" — match either form
        if local != target_local and qual != target_local:
            continue
        parent = elem.getparent()
        if parent is None:
            return None
        pqn = etree.QName(parent.tag)
        plocal = pqn.localname
        pprefix = parent.prefix
        return f"{pprefix}:{plocal}" if pprefix else plocal
    return None


_IDREF_RE = re.compile(r'\b(?:[\w]+:)?IdRef="([^"]+)"')
_DISPLAYNAME_RE = re.compile(r'\bDisplayName="([^"]*)"')


def _n5_next_idref(content: str, base: str = "LogMessage_Auto") -> str:
    """Return next unused IdRef of form `<base>_<n>`. Scans existing IdRefs."""
    used = set(_IDREF_RE.findall(content))
    n = 1
    while f"{base}_{n}" in used:
        n += 1
    return f"{base}_{n}"


def _n5_unique_display_name(content: str, base: str) -> str:
    """Return unique DisplayName based on `base`. Se `base` já usado no arquivo,
    appenda ` #<n>` até virar único.

    Evita ST-NMG-004 (DisplayName repetido > limite 1 por workflow). Activity
    original com DisplayName duplicado já viola — Trace inserido com mesmo
    DisplayName amplifica. Usar suffix garante uniqueness do INSERT mesmo se
    o source duplicava.
    """
    used = set(_DISPLAYNAME_RE.findall(content))
    if base not in used:
        return base
    n = 2
    while True:
        candidate = f"{base} #{n}"
        if candidate not in used:
            return candidate
        n += 1


_INVOKE_ARGUMENTS_BLOCK_RE = re.compile(
    r'(<ui:InvokeWorkflowFile\.Arguments\s*>)(.*?)(</ui:InvokeWorkflowFile\.Arguments\s*>)',
    re.DOTALL,
)
_INVOKE_ARGUMENTS_SELF_CLOSING_RE = re.compile(
    r'(?P<indent>[ \t]*)<ui:InvokeWorkflowFile\.Arguments\s*/>'
)
_EMPTY_INVOKE_ARGUMENTS_DICT_RE = re.compile(
    r'\n?[ \t]*<scg:Dictionary\b'
    r'(?=[^>]*\bx:TypeArguments\s*=\s*"x:String,\s*(?:Argument|System\.Activities\.Argument)")'
    r'(?=[^>]*\s/>)'
    r'[^>]*/>',
    re.DOTALL,
)
_NULL_ARGUMENTS_VARIABLE_ATTR_RE = re.compile(
    r'\s+ArgumentsVariable\s*=\s*"\{x:Null\}"'
)
_INVOKE_WORKFLOW_FILE_BLOCK_RE = re.compile(
    r'(<(?P<prefix>[A-Za-z_]\w*):InvokeWorkflowFile(?=[\s/>])[^>]*>)'
    r'(?P<body>.*?)'
    r'(</(?P=prefix):InvokeWorkflowFile>)',
    re.DOTALL,
)


def _count_invoke_arguments_properties(body: str) -> int:
    return len(re.findall(r'<ui:InvokeWorkflowFile\.Arguments(?=[\s/>])', body))


def _insert_invoke_workflow_argument(body: str, new_arg: str) -> str:
    """Insert into InvokeWorkflowFile.Arguments, including self-closing form."""
    am = _INVOKE_ARGUMENTS_BLOCK_RE.search(body)
    if am:
        inner = _strip_empty_invoke_arguments_dictionary(am.group(2))
        return (
            body[:am.start()]
            + am.group(1)
            + inner
            + new_arg
            + "\n        "
            + am.group(3)
            + body[am.end():]
        )

    sm = _INVOKE_ARGUMENTS_SELF_CLOSING_RE.search(body)
    if sm:
        indent = sm.group("indent")
        replacement = (
            f'{indent}<ui:InvokeWorkflowFile.Arguments>'
            f'{new_arg}\n{indent}</ui:InvokeWorkflowFile.Arguments>'
        )
        return body[:sm.start()] + replacement + body[sm.end():]

    return body + (
        f'\n        <ui:InvokeWorkflowFile.Arguments>'
        f'{new_arg}\n        </ui:InvokeWorkflowFile.Arguments>\n      '
    )


def _strip_null_arguments_variable_attr(opening: str) -> str:
    return _NULL_ARGUMENTS_VARIABLE_ATTR_RE.sub("", opening, count=1)


def _strip_empty_invoke_arguments_dictionary(inner: str) -> str:
    """Drop legacy empty dictionary placeholders once real args are present."""
    if not re.search(r'<(?:In|Out|InOut)Argument\b', inner):
        return inner
    return _EMPTY_INVOKE_ARGUMENTS_DICT_RE.sub("", inner)


def strip_empty_invoke_arguments_dictionary_placeholders(
    content: str,
) -> tuple[str, int]:
    """Remove empty Arguments dictionary placeholders with real arg siblings.

    Some migrated projects contain:

    `<ui:InvokeWorkflowFile.Arguments><scg:Dictionary ... /><InArgument ...>`

    Studio's Windows XAML loader can treat the empty dictionary as an extra
    assignment to `InvokeWorkflowFile.Arguments`. If concrete argument entries
    exist, the empty dictionary is just a legacy placeholder and is safe to drop.
    """
    removals = 0

    def _rewrite(m: "re.Match[str]") -> str:
        nonlocal removals
        inner = m.group(2)
        if not re.search(r'<(?:In|Out|InOut)Argument\b', inner):
            return m.group(0)
        new_inner, count = _EMPTY_INVOKE_ARGUMENTS_DICT_RE.subn("", inner)
        if count <= 0:
            return m.group(0)
        removals += count
        return m.group(1) + new_inner + m.group(3)

    return _INVOKE_ARGUMENTS_BLOCK_RE.sub(_rewrite, content), removals


def strip_null_arguments_variable_conflicts(content: str) -> tuple[str, int]:
    """Remove null ArgumentsVariable only when an Arguments property exists."""
    removals = 0

    def _rewrite(m: "re.Match[str]") -> str:
        nonlocal removals
        opening = m.group(1)
        prefix = m.group("prefix")
        body = m.group("body")
        if not _NULL_ARGUMENTS_VARIABLE_ATTR_RE.search(opening):
            return m.group(0)
        if not re.search(
            rf'<{re.escape(prefix)}:InvokeWorkflowFile\.Arguments(?=[\s/>])',
            body,
        ):
            return m.group(0)
        new_opening, n = _NULL_ARGUMENTS_VARIABLE_ATTR_RE.subn("", opening, count=1)
        if not n:
            return m.group(0)
        removals += n
        return new_opening + body + m.group(4)

    return _INVOKE_WORKFLOW_FILE_BLOCK_RE.sub(_rewrite, content), removals


def sanitize_invoke_arguments_variable_conflicts(project_root: Path) -> tuple[int, int]:
    """Strip analyzer-breaking null ArgumentsVariable conflicts project-wide."""
    import os as _os

    skip_dirs = {
        ".git", ".hg", ".svn", "bin", "obj", ".local", ".nuget",
        ".uipath", ".tmp", "__pycache__", "node_modules",
    }
    changed_files = 0
    removals = 0
    for root, dirs, files in _os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            if not name.lower().endswith(".xaml"):
                continue
            path = Path(root) / name
            try:
                content = path.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            new_content, count = strip_null_arguments_variable_conflicts(content)
            if count <= 0 or new_content == content:
                continue
            changed_files += 1
            removals += count
            _write_preserving_bom(path, new_content, _file_has_bom(path))
    return changed_files, removals


def sanitize_invoke_arguments_dictionary_placeholders(
    project_root: Path,
) -> tuple[int, int]:
    """Strip empty `Arguments` dictionary placeholders project-wide."""
    import os as _os

    skip_dirs = {
        ".git", ".hg", ".svn", "bin", "obj", ".local", ".nuget",
        ".uipath", ".tmp", "__pycache__", "node_modules",
    }
    changed_files = 0
    removals = 0
    for root, dirs, files in _os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            if not name.lower().endswith(".xaml"):
                continue
            path = Path(root) / name
            try:
                content = path.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            new_content, count = strip_empty_invoke_arguments_dictionary_placeholders(
                content
            )
            if count <= 0 or new_content == content:
                continue
            changed_files += 1
            removals += count
            _write_preserving_bom(path, new_content, _file_has_bom(path))
    return changed_files, removals



def _cascade_arg_to_callers(project_root: Path, callee_file: Path,
                             arg_name: str, default_expr: str = '""',
                             dry_run: bool = True,
                             transaction_var_name: str = "TransactionItem",
                             transaction_arg_name: str = "in_TransactionItem") -> int:
    """Cross-file cascade: scan all XAMLs in project_root that invoke
    callee_file via <ui:InvokeWorkflowFile WorkflowFileName="..."/> and
    insert `<InArgument x:Key="<arg_name>">...</InArgument>` se ausente.

    Heurística do default expression no caller:
      1. Se caller declara x:Property `<arg_name>` → usa `[<arg_name>]`
      2. Senão se caller tem Variable `v<ArgNameWithoutPrefix>` → `[v<...>]`
      3. Senão fallback: `default_expr` (default `""`)

    Returns: number of callers modified.

    Idempotent: callers que já passam o arg são pulados.
    """
    if project_root is None or not project_root.exists():
        return 0

    # N-3 derivação: callee que recebe in_TransactionItem permite que o caller
    # (tipicamente Main, com Variable TransactionItem) semeie o prefixo de
    # TransactionItem.Reference no binding. Sem o arg de transação no callee,
    # não há de onde derivar → cai na propagação/fallback.
    try:
        callee_content = callee_file.read_text(encoding="utf-8-sig")
    except OSError:
        callee_content = ""
    callee_has_txn_arg = bool(
        re.search(rf'<x:Property\b[^>]*Name="{re.escape(transaction_arg_name)}"',
                  callee_content)
    )

    callee_basename = callee_file.name  # e.g. PreProcessamento.xaml
    # Path patterns a procurar em WorkflowFileName — / ou \\ separator
    # Stripping project_root prefix, normalize.
    try:
        rel = callee_file.relative_to(project_root)
        rel_posix = rel.as_posix()  # forward slashes
        rel_winsep = rel_posix.replace("/", "\\")
    except Exception:
        rel_posix = callee_basename
        rel_winsep = callee_basename

    modified = 0
    for caller in project_root.rglob("*.xaml"):
        if caller == callee_file:
            continue
        try:
            ctext = caller.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        # Find all <ui:InvokeWorkflowFile ...WorkflowFileName="...callee..."...>...</ui:InvokeWorkflowFile>
        # Process each Invoke block independently.
        new_ctext = ctext
        # Determine default-expr para esse caller (uma vez). Ordem de precedência:
        # 0. Derivação transação (Main→Process): callee tem arg in_TransactionItem
        #    E caller tem Variable TransactionItem. Sem guard — REFramework só roda
        #    o Process state após TransactionItem recebido (Reference non-null).
        # 1. caller declara <arg_name> (in_StPrefixoLog) → propaga [<arg_name>].
        # 2. caller tem Variable v<Short> → [v<Short>].
        # 3. fallback default_expr ("").
        if callee_has_txn_arg and re.search(
            rf'<Variable\b[^>]*\bName="{re.escape(transaction_var_name)}"', ctext
        ):
            caller_default = f'[{transaction_var_name}.Reference + " - "]'
        elif re.search(rf'<x:Property\b[^>]*Name="{re.escape(arg_name)}"', ctext):
            caller_default = f"[{arg_name}]"
        else:
            # Variable v + capitalized arg_name without leading prefix
            # e.g. in_StPrefixoLog → vStPrefixoLog
            short = re.sub(r'^(in|out|io)_', '', arg_name)
            var_candidate = f"v{short}"
            if re.search(rf'<Variable\b[^>]*\bName="{re.escape(var_candidate)}"', ctext):
                caller_default = f"[{var_candidate}]"
            else:
                caller_default = default_expr

        # Pattern InvokeWorkflowFile block (non-greedy)
        invoke_re = re.compile(
            r'(<ui:InvokeWorkflowFile(?=[\s/>])[^>]*?\bWorkflowFileName="([^"]+)"[^>]*>)'
            r'(.*?)'
            r'(</ui:InvokeWorkflowFile>)',
            re.DOTALL,
        )
        def _rewrite_invoke(m):
            opening, wf_name, body, closing = m.group(1), m.group(2), m.group(3), m.group(4)
            # Match callee?
            wf_norm = wf_name.replace("\\", "/")
            wf_basename = wf_norm.split("/")[-1]
            if wf_basename.lower() != callee_basename.lower():
                return m.group(0)
            # Idempotent: já passa?
            if re.search(rf'\bx:Key="{re.escape(arg_name)}"', body):
                return m.group(0)
            if re.search(r'\bArguments\s*=', opening):
                return m.group(0)
            # Encontra <ui:InvokeWorkflowFile.Arguments> ... </ui:InvokeWorkflowFile.Arguments>
            args_re = re.compile(
                r'(<ui:InvokeWorkflowFile\.Arguments\s*>)(.*?)(</ui:InvokeWorkflowFile\.Arguments\s*>)',
                re.DOTALL,
            )
            am = args_re.search(body)
            asm = _INVOKE_ARGUMENTS_SELF_CLOSING_RE.search(body)
            new_in_arg = (
                f'\n          <InArgument x:TypeArguments="x:String" '
                f'x:Key="{arg_name}">{caller_default}</InArgument>'
            )
            if am:
                # Insert before closing </ui:InvokeWorkflowFile.Arguments>
                new_body = body[:am.start()] + am.group(1) + am.group(2) + new_in_arg + "\n        " + am.group(3) + body[am.end():]
            elif asm:
                indent = asm.group("indent")
                replacement = (
                    f'{indent}<ui:InvokeWorkflowFile.Arguments>'
                    f'{new_in_arg}\n{indent}</ui:InvokeWorkflowFile.Arguments>'
                )
                new_body = body[:asm.start()] + replacement + body[asm.end():]
            else:
                # No Arguments block — add one before </ui:InvokeWorkflowFile>
                new_body = body + (
                    f'\n        <ui:InvokeWorkflowFile.Arguments>'
                    f'{new_in_arg}\n        </ui:InvokeWorkflowFile.Arguments>\n      '
                )
            # Defesa pós-insert: se key apareceu >1× na args block resultante,
            # rollback. Cobre race/regex-miss (Studio load-fail: dict bind
            # exception em Dictionary(String, Argument)).
            if _count_invoke_arguments_properties(new_body) > 1:
                return m.group(0)
            check_re = re.compile(
                r'<ui:InvokeWorkflowFile\.Arguments\s*>(.*?)</ui:InvokeWorkflowFile\.Arguments\s*>',
                re.DOTALL,
            )
            check_m = check_re.search(new_body)
            if check_m:
                key_count = len(re.findall(
                    rf'\bx:Key="{re.escape(arg_name)}"', check_m.group(1)
                ))
                if key_count > 1:
                    return m.group(0)
            return _strip_null_arguments_variable_attr(opening) + new_body + closing

        new_ctext = invoke_re.sub(_rewrite_invoke, new_ctext)
        if new_ctext != ctext:
            modified += 1
            if not dry_run:
                _write_preserving_bom(caller, new_ctext, _file_has_bom(caller))
    return modified


@register("strip_invoke_arguments_variable_when_args_element")
def apply_strip_invoke_arguments_variable_when_args_element(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """Strip legacy ArgumentsVariable={x:Null} when Arguments element exists.

    Windows target can treat `ArgumentsVariable` as a duplicate assignment when
    the same InvokeWorkflowFile also has `<ui:InvokeWorkflowFile.Arguments>`.
    Only the null legacy placeholder is removed; non-null values are preserved.
    """
    content = file.read_text(encoding="utf-8-sig")
    new_content, count = strip_null_arguments_variable_conflicts(content)
    if count <= 0 or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("add_prefixo_arg")
def apply_add_prefixo_arg(file: Path, spec: dict, dry_run: bool = True,
                           project_root: Path | None = None) -> bool:
    """Declare `in_StPrefixoLog` arg + rewrite literal LogMessage Messages
    pra usar prefixo (N-3 path 1) + **cascade callers** (cross-file).

    Spec:
        prefixo_arg : nome do arg (default "in_StPrefixoLog")

    Behavior:
      1. Adiciona `<x:Property Name="<prefixo_arg>" Type="InArgument(x:String)" />`
         em `<x:Members>` (idempotent — skip se já existe).
      2. Adiciona default-value block `<this:<Class>.<prefixo_arg>>` com Literal
         vazio APÓS `</x:Members>`. Cobre callers que não bindam.
      3. Reescreve Messages literais `Message="[&quot;X&quot;]"` para
         `Message="[<prefixo_arg> + &quot;X&quot;]"`. Limita a literal-string
         expressions — não toca expressions complexas.
      4. **Cascade**: scan callers que invocam este callee via
         `<ui:InvokeWorkflowFile WorkflowFileName="...callee.xaml"/>` e
         insere `<InArgument x:Key="<prefixo_arg>">[expr]</InArgument>`
         em cada `<ui:InvokeWorkflowFile.Arguments>` que ainda não passa.
         Default expr heurístico (caller's own arg, var, ou "").

    Cuidado: Path 2 N-3 (Messages com expressões complexas que não usam
    prefixo) NÃO é coberto aqui — cascade via re-detect próxima iter.
    """
    prefixo_arg = spec.get("prefixo_arg") or "in_StPrefixoLog"
    txn_var = spec.get("transaction_var_name") or "TransactionItem"
    txn_arg = spec.get("transaction_arg_name") or "in_TransactionItem"
    content = file.read_text(encoding="utf-8-sig")

    # Idempotent: se já declara, **ainda assim cascade nos callers** (defesa).
    already_declared = bool(
        re.search(rf'<x:Property\b[^>]*Name="{re.escape(prefixo_arg)}"', content)
    )
    if already_declared:
        # Skip Step 1-3, mas cascade Step 4.
        if project_root:
            modified = _cascade_arg_to_callers(
                project_root, file, prefixo_arg, default_expr='""',
                dry_run=dry_run,
                transaction_var_name=txn_var, transaction_arg_name=txn_arg,
            )
            return modified > 0
        return False

    new_content = content

    # Step 1: x:Property declaration. Insere depois da última <x:Property> em
    # <x:Members>, ou imediatamente após `<x:Members>` (sem properties existentes).
    members_open = re.search(r'<x:Members\b[^>]*>', new_content)
    if members_open is None:
        activity_open = re.search(r'<Activity\b[^>]*>', new_content)
        if activity_open is not None:
            members_block = (
                f'\n  <x:Members>\n'
                f'  </x:Members>'
            )
            new_content = (
                new_content[:activity_open.end()]
                + members_block
                + new_content[activity_open.end():]
            )
            members_open = re.search(r'<x:Members\b[^>]*>', new_content)
    if members_open is None:
        # No <x:Members> block — workflow malformed for our purposes.
        return False
    members_end_close = re.search(r'</x:Members\s*>', new_content)
    if members_end_close is None:
        return False
    # Indentation hint: use indentation of last property line, or 4 spaces.
    members_text = new_content[members_open.end():members_end_close.start()]
    last_prop = list(re.finditer(r'(\s*)<x:Property\b', members_text))
    if last_prop:
        indent = last_prop[-1].group(1).lstrip("\n")
        if not indent.strip():
            # whitespace-only — keep
            pass
        else:
            indent = "    "
    else:
        indent = "    "
    insert_str = f'\n{indent}<x:Property Name="{prefixo_arg}" Type="InArgument(x:String)" />'
    insertion_point = members_end_close.start()
    # Strip trailing whitespace before </x:Members> to preserve clean format
    new_content = (new_content[:insertion_point].rstrip(" \t\n") + insert_str + "\n  "
                   + new_content[insertion_point:])

    # Step 2a: garantir xmlns:this declarado no <Activity> root. Sem isso,
    # `<this:<Class>.<arg>>` quebra XML (unbound prefix).
    if 'xmlns:this=' not in new_content[:5000]:
        # Insert antes do `>` que fecha <Activity ...>
        activity_open_re = re.compile(r'(<Activity\b[^>]*?)(>)', re.DOTALL)
        am = activity_open_re.search(new_content)
        if am is None:
            return False
        new_content = (new_content[:am.start()]
                       + am.group(1)
                       + ' xmlns:this="clr-namespace:"'
                       + am.group(2)
                       + new_content[am.end():])

    # Step 2b: default-value block após </x:Members>. Class name extraído do
    # <Activity x:Class="<Name>"> — Sicoob convention this:<Class>.<arg>.
    cls_m = re.search(r'<Activity\b[^>]*\bx:Class="([^"]+)"', new_content)
    if cls_m is None:
        return False
    class_name = cls_m.group(1)
    # Insert depois do </x:Members> recém-emitido. Encontrar nova posição.
    members_close_re = re.compile(r'</x:Members\s*>')
    mc = members_close_re.search(new_content)
    if mc is None:
        return False
    default_tag_local = f"{class_name}.{prefixo_arg}"
    # Legacy UiPath workflows sometimes use x:Class values such as
    # "1.2.UpdateExecutionEndDB2". That is not a valid XML local-name for a
    # `<this:...>` property element. In that case, the x:Property declaration is
    # still valid and is the deploy-safe mechanical fix; skip the default block.
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", default_tag_local):
        default_block = (
            f'\n  <this:{default_tag_local}>'
            f'<InArgument x:TypeArguments="x:String">'
            f'<Literal x:TypeArguments="x:String" Value="" />'
            f'</InArgument>'
            f'</this:{default_tag_local}>'
        )
        # Idempotent check
        if f'this:{default_tag_local}' not in new_content:
            new_content = (new_content[:mc.end()] + default_block
                           + new_content[mc.end():])

    # Step 3: rewrite literal Messages `[&quot;X&quot;]` →
    # `[<prefixo_arg> + &quot;X&quot;]`. Cobre só literal-string form.
    msg_re = re.compile(r'(<ui:LogMessage\b[^>]*\bMessage=")\[&quot;([^"]*)&quot;\](")')
    def _rewrite(m):
        return f'{m.group(1)}[{prefixo_arg} + &quot;{m.group(2)}&quot;]{m.group(3)}'
    new_content = msg_re.sub(_rewrite, new_content)

    callee_changed = (new_content != content)
    if callee_changed and not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))

    # Step 4: cascade callers (cross-file). Sempre roda quando project_root
    # presente, mesmo se callee não mudou (defensivo p/ idempotência).
    cascade_changed = False
    if project_root:
        modified = _cascade_arg_to_callers(
            project_root, file, prefixo_arg, default_expr='""',
            dry_run=dry_run,
            transaction_var_name=txn_var, transaction_arg_name=txn_arg,
        )
        cascade_changed = (modified > 0)

    return callee_changed or cascade_changed


@register("seed_prefixo_binding")
def apply_seed_prefixo_binding(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """N-3B fixer: UPGRADE empty in_StPrefixoLog invoke-bindings to value_expr.

    Spec:
        arg_name   : binding key (default "in_StPrefixoLog")
        value_expr : computed value, e.g. '[in_TransactionItem.Reference + " - "]'
                     (DERIVE) or '[in_StPrefixoLog]' (INHERIT). Policy lives in
                     o detector (detect_n3_prefixo_binding); este fixer é mecânico.

    Scope: reescreve SÓ o VALOR de bindings in_StPrefixoLog dentro de
    <ui:InvokeWorkflowFile.Arguments> cujo valor atual é vazio ("" / whitespace
    / self-closed / <Literal Value=""/>). NUNCA sobrescreve valor não-vazio
    hand-set. Idempotente: binding já == value_expr fica intocado;
    `new_content == content` => return False.

    Output sempre element-content form preservando o attrs blob original
    (x:TypeArguments, x:Key, ordem). value_expr é XML-escapado p/ element content
    (& < >); `"` raw é legal em element text e casa com a serialização do repo.
    """
    arg_name = spec.get("arg_name") or "in_StPrefixoLog"
    value_expr = spec.get("value_expr")
    if not value_expr:
        return False
    # overwrite=True (N-3B cadeia): só há um valor legítimo de prefixo a jusante
    # do seed — [in_StPrefixoLog]. Autoriza sobrescrever binding NÃO-vazio errado
    # (ex.: re-derivação `[*.Reference + " - "]` no Process). overwrite ausente/
    # False mantém o guard clássico (só preenche vazio) — protege seeds hand-set.
    overwrite = bool(spec.get("overwrite", False))

    content = file.read_text(encoding="utf-8-sig")
    if "InvokeWorkflowFile" not in content or arg_name not in content:
        return False

    # XML-escape p/ element-content. Mantém `"` raw (legal em element text,
    # casa com serialização existente). Ordem importa: & primeiro.
    safe_value = (
        value_expr.replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;")
    )

    binding_re = re.compile(
        r'<InArgument\b(?P<attrs>[^>]*?\bx:Key="' + re.escape(arg_name) + r'"[^>]*?)'
        r'(?:/>|>(?P<value>.*?)</InArgument>)',
        re.DOTALL,
    )
    args_block_re = re.compile(
        r'<ui:InvokeWorkflowFile\.Arguments\s*>.*?</ui:InvokeWorkflowFile\.Arguments\s*>',
        re.DOTALL,
    )

    def _value_is_empty(value):
        if value is None:
            return True
        stripped = value.strip()
        if stripped in ("", '""', '&quot;&quot;', '[""]', '[&quot;&quot;]'):
            return True
        if re.fullmatch(r'<Literal\b[^>]*\bValue=""[^>]*/>', stripped):
            return True
        return False

    def _rewrite_binding(bm):
        attrs = bm.group("attrs")
        value = bm.group("value")
        # Idempotente: já correto → no-op.
        if value is not None and value.strip() in (safe_value, value_expr):
            return bm.group(0)
        # Guard "nunca clobber valor não-vazio hand-set" — relaxado só com
        # overwrite=True (cadeia: valor único legítimo é a herança).
        if not overwrite and not _value_is_empty(value):
            return bm.group(0)
        # attrs.strip() (ambos lados) + single space no template → exatamente
        # `<InArgument x:... >` sem double-space (byte-clean diff).
        return f'<InArgument {attrs.strip()}>{safe_value}</InArgument>'

    def _rewrite_block(block_m):
        return binding_re.sub(_rewrite_binding, block_m.group(0))

    new_content = args_block_re.sub(_rewrite_block, content)

    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("strip_prefixo_from_main")
def apply_strip_prefixo_from_main(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """N-3C fixer: remove a POSSE do prefixo de log do Main (entry).

    O prefixo só pertence a Process + filhos (regra 3 Sicoob). No Main remove:
      1. a declaração `<x:Property Name="<prefixo_arg>" .../>`;
      2. o bloco default `<this:<Class>.<prefixo_arg>> ... </this:<Class>.<prefixo_arg>>`;
      3. o prefixo das LogMessages do Main (`[<prefixo_arg> + ` → `[`).

    NÃO toca em bindings `x:Key="<prefixo_arg>"` dentro de
    <ui:InvokeWorkflowFile.Arguments> — esse é o SEED que o Main passa pro Process
    (mantido). Idempotente. Preserva BOM/encoding.
    """
    prefixo_arg = spec.get("prefixo_arg") or "in_StPrefixoLog"
    content = file.read_text(encoding="utf-8-sig")
    new_content = content

    # 1. Remove a declaração x:Property (linha + newline à esquerda).
    new_content = re.sub(
        rf'\n[ \t]*<x:Property\b[^>]*\bName="{re.escape(prefixo_arg)}"[^>]*/>',
        "", new_content, count=1,
    )
    # 2. Remove o bloco default <this:<Class>.<arg>> ... </this:<Class>.<arg>>.
    new_content = re.sub(
        rf'\n[ \t]*<this:[A-Za-z0-9_]+\.{re.escape(prefixo_arg)}>.*?'
        rf'</this:[A-Za-z0-9_]+\.{re.escape(prefixo_arg)}>',
        "", new_content, count=1, flags=re.DOTALL,
    )
    # 3. Strip do prefixo nas mensagens do Main. O literal `[<arg> + ` só ocorre
    #    em expressões de LogMessage (o seed usa x:Key=, não esse literal). Cobre
    #    forma literal `[arg + "X"]` e parentizada `[arg + (X)]` — ambas viram `[`.
    new_content = new_content.replace(f"[{prefixo_arg} + ", "[")

    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("guard_linq_arg_ref")
def apply_guard_linq_arg_ref(file: Path, spec: dict, dry_run: bool = True,
                              project_root: Path | None = None) -> bool:
    """W-2 fixer: wrap LINQ over arg reference com null guard.

    Patterns:
      `in_X.Contains(y)` → `If(in_X Is Nothing, False, in_X.Contains(y))`
      `in_X.Any(...)`    → `If(in_X Is Nothing, False, in_X.Any(...))`
      `in_X.Where(...)`  → `If(in_X Is Nothing, Enumerable.Empty(Of T)(), in_X.Where(...))`  ← SKIP (type-dependent)
      `in_X.Select(...)` → idem SKIP
      `in_X.First`       → SKIP (typed return)

    Heuristic: so wrap Contains/Any (Boolean return — default False).
    Outros = skip pra evitar type mismatch.

    File-level: aplica em todas LINQ ocorrências num só call.
    Idempotent: skip se already guarded (`Is Nothing` preceding).
    """
    content = file.read_text(encoding="utf-8-sig")

    # Pattern: (in|io)_<Name>.<Method>(<args>)
    # Type heurística via Hungarian prefix do argumento:
    #   in_BlX, in_ArrStX, in_DTabX, in_StX, in_IntX, in_DictX ...
    pat = re.compile(
        r'\b((?:in|io)_[A-Za-z_][A-Za-z0-9_]*)\.(Contains|Any|Select|Where|First|Single|All|AsEnumerable)\(([^()]*(?:\([^()]*\)[^()]*)*)\)'
    )

    def _default_for(arg: str, meth: str) -> str | None:
        """Pick a sensible default Nothing fallback by Hungarian prefix + method."""
        # Boolean-return methods (always safe to default False)
        if meth in ("Contains", "Any", "All"):
            return "False"
        # Strip 'in_'/'io_' prefix to inspect type marker
        bare = re.sub(r'^(in|io)_', '', arg)
        # DataTable: DTab → SKIP — guard sozinho no Select e enganoso. Caller
        # frequentemente faz `.Select(...)(0)("Field")` — wrap parcial troca NRE
        # por IndexOutOfRange (array vazio + indexing). Caller deve manualmente
        # wrappar a chain COMPLETA com `If(dt Is Nothing OrElse dt.Select(...).Length = 0, default, ...)`.
        # Historico: 47 ocorrencias quebradas em 19 XAMLs (sustentacao 2026-05).
        if bare.startswith('DTab'):
            return None
        if meth == 'AsEnumerable':
            return None
        # Array: ArrSt/ArrInt/etc → Select/Where return IEnumerable
        if bare.startswith('Arr'):
            if meth in ('Select', 'Where'):
                return f'{arg}'  # idem self (already empty if Nothing → conceptually OK but unsafe)
            return None
        # Dict / List — type-dependent — skip
        if bare.startswith(('Dict', 'Lst')):
            return None
        return None

    changed = 0

    def _rewrite(m):
        arg, meth, args = m.group(1), m.group(2), m.group(3)
        full = m.group(0)
        return _wrap_or_keep(content, m, arg, meth, args, full)

    def _wrap_or_keep(ct, m, arg, meth, args, full):
        nonlocal changed
        pos = m.start()
        window_before = ct[max(0, pos - 100):pos]
        if f"{arg} Is Nothing" in window_before or f"If({arg} " in window_before:
            return full  # already guarded
        default = _default_for(arg, meth)
        if default is None:
            return full  # type-dependent, skip
        changed += 1
        return f"If({arg} Is Nothing, {default}, {arg}.{meth}({args}))"

    new_content = pat.sub(_rewrite, content)
    if changed == 0 or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


_POOR_DN_PREFIXES = ("Trace: ", "Trace:", "Log - ", "Log -", "Log:")
_POOR_DN_DEFAULTS = {"Log Message", "Log", "LogMessage", "Message", "Write Line"}


def _is_poor_log_displayname(dn: str) -> bool:
    if not dn:
        return True
    if dn.strip() in _POOR_DN_DEFAULTS:
        return True
    for p in _POOR_DN_PREFIXES:
        if dn.startswith(p):
            return True
    # "Log - TX_END", "Log Message", "Log X" — first word "Log" plain
    if dn.lower().startswith("log "):
        return True
    return False


def _improve_log_displayname(old: str, message: str) -> str:
    """Generate replacement DisplayName from old DN + Message body.

    Heuristics:
      1. Strip known bad prefixes from old DN → keep tail context
      2. If tail empty, try first 5 words from Message body (strip [..]/&quot;)
      3. Fallback: "Registrar evento de log"
    """
    tail = old.strip()
    for p in _POOR_DN_PREFIXES:
        if tail.startswith(p):
            tail = tail[len(p):].strip()
            break
    if tail in _POOR_DN_DEFAULTS or not tail or tail.lower() == "log":
        tail = ""
    if not tail and message:
        # Extract literal between &quot;...&quot; or between "..."
        m = re.search(r'&quot;([^&]+?)&quot;', message)
        if not m:
            m = re.search(r'"([^"]+)"', message)
        if m:
            words = re.findall(r"[A-Za-zÀ-ÿ0-9_]+", m.group(1))[:5]
            tail = " ".join(words)
    if not tail:
        return "Log Message - evento generico"
    return f"Log Message - {tail}"[:120]


@register("rename_poor_log_displayname")
def apply_rename_poor_log_displayname(file: Path, spec: dict, dry_run: bool = True,
                                        project_root: Path | None = None) -> bool:
    """N-17 fixer: renomeia DisplayName pobre em <ui:LogMessage>.

    Pobre = começa com 'Trace:', 'Log -', 'Log:' ou é default 'Log Message'/'Log'.
    Padrão Sicoob: verbo infinitivo + descrição. Replace por 'Registrar - <tail>'.
    """
    content = file.read_text(encoding="utf-8-sig")
    pat = re.compile(r'(<ui:LogMessage\b[^>]*\bDisplayName=")([^"]*)("[^>]*?\bMessage=")([^"]*)(")')
    changed = 0

    def _rewrite(m):
        nonlocal changed
        dn_open, dn_val, mid, msg_val, end = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if not _is_poor_log_displayname(dn_val):
            return m.group(0)
        new_dn = _improve_log_displayname(dn_val, msg_val)
        if new_dn == dn_val:
            return m.group(0)
        changed += 1
        safe = (new_dn.replace("&", "&amp;").replace("<", "&lt;")
                     .replace(">", "&gt;").replace('"', "&quot;"))
        return f'{dn_open}{safe}{mid}{msg_val}{end}'

    new_content = pat.sub(_rewrite, content)
    # Also handle LogMessages where Message is BEFORE DisplayName (less common)
    pat2 = re.compile(r'(<ui:LogMessage\b[^>]*\bMessage=")([^"]*)("[^>]*?\bDisplayName=")([^"]*)(")')

    def _rewrite2(m):
        nonlocal changed
        msg_open, msg_val, mid, dn_val, end = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if not _is_poor_log_displayname(dn_val):
            return m.group(0)
        new_dn = _improve_log_displayname(dn_val, msg_val)
        if new_dn == dn_val:
            return m.group(0)
        changed += 1
        safe = (new_dn.replace("&", "&amp;").replace("<", "&lt;")
                     .replace(">", "&gt;").replace('"', "&quot;"))
        return f'{msg_open}{msg_val}{mid}{safe}{end}'

    new_content = pat2.sub(_rewrite2, new_content)

    # N-17 (audit): pass 3 — rewrite the poor DisplayName INDEPENDENTLY of
    # whether Message is an attribute. The detector flags a LogMessage purely on
    # a poor DisplayName attribute and does NOT require a Message attribute;
    # passes 1/2 only fire when BOTH are attributes, so a LogMessage whose
    # Message is in property-ELEMENT form (`<ui:LogMessage.Message>...</...>`,
    # the traceable form Sicoob prefers) was previously a deterministic no-op.
    # Here we rewrite the DisplayName attribute alone, pulling context from the
    # element-form Message when available. Poor-detection mirrors the detector
    # EXACTLY (_POOR_DN_EXACT + _POOR_DN_PATTERNS surrogate) to stay idempotent.
    dn_only_re = re.compile(r'<ui:LogMessage\b[^>]*\bDisplayName="([^"]*)"', re.DOTALL)

    def _detector_poor(dn: str) -> bool:
        d = dn.strip()
        if not d:
            return False
        if d in {"Log Message", "Log", "LogMessage", "Message"}:
            return True
        for rx in (r'^\s*Trace\s*:', r'^\s*Log\s*:', r'^\s*Log Message\s*-\s*$'):
            if re.match(rx, d):
                return True
        return False

    pass3_src = new_content

    def _rewrite_dn_only(m):
        nonlocal changed
        full = m.group(0)
        dn_val = m.group(1)
        if not _detector_poor(dn_val):
            return full
        # Locate element-form Message context after this open tag, if present.
        # Index into the SAME string the regex iterated (pass3_src), not the
        # original content — offsets are relative to pass3_src.
        msg_ctx = ""
        tail = pass3_src[m.end():m.end() + 2000]
        em = re.search(
            r'<ui:LogMessage\.Message\b[^>]*>(.*?)</ui:LogMessage\.Message>',
            tail, re.DOTALL,
        )
        if em:
            inner = em.group(1)
            lit = re.search(r'\[([^\]]+)\]', inner)
            msg_ctx = lit.group(1) if lit else inner
        new_dn = _improve_log_displayname(dn_val, msg_ctx)
        if new_dn == dn_val or _detector_poor(new_dn):
            return full
        changed += 1
        safe = (new_dn.replace("&", "&amp;").replace("<", "&lt;")
                     .replace(">", "&gt;").replace('"', "&quot;"))
        # Replace ONLY the DisplayName attribute value inside this open tag.
        return full.replace(f'DisplayName="{dn_val}"', f'DisplayName="{safe}"', 1)

    new_content = dn_only_re.sub(_rewrite_dn_only, new_content)

    if changed == 0 or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("strip_annotation_text")
def apply_strip_annotation_text(file: Path, spec: dict, dry_run: bool = True,
                                 project_root: Path | None = None) -> bool:
    """S-5 / S-5b fixer: remove `sap2010:Annotation.AnnotationText="..."` attrs.

    Sicoob policy: codigo auto-explicativo via DisplayName + variable names.
    AnnotationText so quando absolutamente imprescindivel. Migrator-injected
    annotations sao TODOs nao-resolvidos — strip apos review.

    Spec params (opcionais):
        text_prefix : substring que deve aparecer no INICIO do texto pra
                      remover. Quando ausente, remove TODOS annotations
                      (comportamento S-5). Quando presente, remove SOMENTE
                      annotations cujo texto começa por esse prefixo
                      (comportamento S-5b, restrito a markers do Migrator).

    Forms cobertas (S-5 audit):
      - ATTRIBUTE: `sap2010:Annotation.AnnotationText="..."`
      - ELEMENT  : `<sap2010:Annotation.AnnotationText>...</sap2010:Annotation.AnnotationText>`
        (Studio/Migrator emite element-form pra texto longo/multiline). Antes do
        fix S-5, o detector flagava element-form mas o fixer só removia attr-form
        → no-op silencioso (deterministic não convergia). text_prefix gating
        (S-5b) aplica às DUAS formas.

    Idempotent: file unchanged if no annotation present.
    Cross-file scope: NO. Local-only file edit.
    """
    params = spec.get("params") if isinstance(spec.get("params"), dict) else {}
    text_prefix = params.get("text_prefix")

    content = file.read_text(encoding="utf-8-sig")
    # Match attribute (with surrounding whitespace) — works for single and
    # multi-line annotation text (XML preserves newlines as &#xA;).
    attr_re = re.compile(r'\s+sap2010:Annotation\.AnnotationText="([^"]*)"')
    # Match property-ELEMENT form (open+close, with surrounding whitespace).
    # Inner text captured for text_prefix gating (raw, no unescape).
    elem_re = re.compile(
        r'\s*<sap2010:Annotation\.AnnotationText\b[^>]*>(.*?)'
        r'</sap2010:Annotation\.AnnotationText>',
        re.DOTALL,
    )

    if text_prefix:
        # XML attributes têm `[` literal; comparamos contra texto cru do
        # atributo (sem unescape — `[PostMigration Action Required]` aparece
        # literal porque colchetes não precisam escape em XML attribute).
        def _replace(m: re.Match) -> str:
            attr_text = m.group(1)
            return "" if attr_text.startswith(text_prefix) else m.group(0)

        def _replace_elem(m: re.Match) -> str:
            inner = m.group(1).lstrip()
            return "" if inner.startswith(text_prefix) else m.group(0)
        new = attr_re.sub(_replace, content)
        new = elem_re.sub(_replace_elem, new)
    else:
        new = attr_re.sub("", content)
        new = elem_re.sub("", new)

    if new == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new, _file_has_bom(file))
    return True


@register("prefix_complex_log_message")
def apply_prefix_complex_log_message(file: Path, spec: dict, dry_run: bool = True,
                                       project_root: Path | None = None) -> bool:
    """N-3 path 2 fixer: prepend `in_StPrefixoLog &` em LogMessage Messages
    com expressões complexas (que NÃO usam o arg de prefixo).

    Safety:
      - Wrap só se expr contém literal string (`&quot;...&quot;`) OU `.ToString`
        OU operadores de concat string (`&` ou `+` com strings). Se expr é puro
        numeric/boolean, skip (poderia mudar tipo).
      - Idempotent: skip se `in_StPrefixoLog` já presente.
      - File-level: aplica em TODAS LogMessages elegíveis num só call.

    Spec:
        prefixo_arg : nome do arg (default "in_StPrefixoLog")

    Não toca path 1 (literal-only `[&quot;X&quot;]`) — coberto por
    `apply_add_prefixo_arg`.
    """
    params = spec.get("params") if isinstance(spec.get("params"), dict) else spec
    prefixo_arg = params.get("prefixo_arg") or spec.get("prefixo_arg") or "in_StPrefixoLog"

    content = file.read_text(encoding="utf-8-sig")

    # Requer prefixo_arg declarado no workflow — senão path 1 deve rodar antes.
    if not re.search(rf'<x:Property\b[^>]*Name="{re.escape(prefixo_arg)}"', content):
        return False

    msg_re = re.compile(r'(<ui:LogMessage\b[^>]*\bMessage=")\[([^"]+)\]"')

    def _is_safe_to_wrap(expr: str) -> bool:
        # Already uses prefixo_arg
        if prefixo_arg in expr:
            return False
        # Has string literal
        if "&quot;" in expr:
            return True
        # Has ToString
        if ".ToString" in expr:
            return True
        # Has vbLf (line break literal)
        if "vbLf" in expr or "vbCrLf" in expr:
            return True
        return False

    changed_count = 0

    def _rewrite(m):
        nonlocal changed_count
        opening = m.group(1)
        expr = m.group(2)
        if not _is_safe_to_wrap(expr):
            return m.group(0)
        changed_count += 1
        # Wrap com `+` (string concat, evita VB validator FP em `&amp;`→`amp`).
        return f'{opening}[{prefixo_arg} + ({expr})]"'

    new_content = msg_re.sub(_rewrite, content)
    if changed_count == 0 or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("cascade_caller_in_args")
def apply_cascade_caller_in_args(file: Path, spec: dict, dry_run: bool = True,
                                  project_root: Path | None = None) -> bool:
    """Cascade fixer for A-19b: caller falta argumento In declarado pelo callee.

    Cross-file: file aqui = CALLER (não callee). Spec contém info do callee
    + arg ausente. Add `<InArgument x:Key="<arg>">[default]</InArgument>`
    no bloco InvokeWorkflowFile.Arguments do caller.

    Spec:
        callee_path : path relativo do callee (ex: 'Processamento/PreProcessamento.xaml')
        arg_name    : nome do argumento ausente
        invoke_idref: opcional, IdRef do InvokeWorkflowFile a desambiguar
        default_expr: opcional, expressão default (heurística se omitido)

    Idempotente: se caller já passa arg, no-op.
    """
    # spec may be {"params": {...}} or flat. Accept both.
    params = spec.get("params") if isinstance(spec.get("params"), dict) else spec
    callee_path = params.get("callee_path", "") or spec.get("callee_path", "")
    arg_name = params.get("arg_name", "") or spec.get("arg_name", "")
    if not arg_name:
        return False
    target_invoke_idref = params.get("invoke_idref") or spec.get("invoke_idref")
    default_expr = params.get("default_expr") or spec.get("default_expr")
    # A-19b contract: detector forwards the callee arg's declared DIRECTION
    # ("In"/"Out"/"InOut") and INNER_TYPE (the x:TypeArguments value, e.g.
    # 'ui:QueueItem', 'x:Int32', 'sd:DataTable'). When absent (older detector /
    # irresolvable type), FALL BACK to the historical hardcoded
    # `<InArgument x:TypeArguments="x:String">` so this fixer stays safe in
    # isolation.
    direction = params.get("direction") or spec.get("direction")
    inner_type = params.get("inner_type") or spec.get("inner_type")

    callee_basename = Path(callee_path).name if callee_path else None
    content = file.read_text(encoding="utf-8-sig")

    # Heurística default-expr: usa arg do próprio caller, var local, ou "".
    if default_expr is None:
        if re.search(rf'<x:Property\b[^>]*Name="{re.escape(arg_name)}"', content):
            default_expr = f"[{arg_name}]"
        else:
            short = re.sub(r'^(in|out|io)_', '', arg_name)
            var_candidate = f"v{short}"
            if re.search(rf'<Variable\b[^>]*\bName="{re.escape(var_candidate)}"', content):
                default_expr = f"[{var_candidate}]"
            else:
                type_hint = str(inner_type or "x:String")
                if type_hint in {"x:String", "System.String", "String"}:
                    default_expr = '[&quot;&quot;]'
                else:
                    default_expr = "[Nothing]"

    invoke_re = re.compile(
        r'(<ui:InvokeWorkflowFile(?=[\s/>])[^>]*?\bWorkflowFileName="([^"]+)"[^>]*?>)'
        r'(.*?)'
        r'(</ui:InvokeWorkflowFile>)',
        re.DOTALL,
    )

    def _rewrite(m):
        opening, wf_name, body, closing = m.group(1), m.group(2), m.group(3), m.group(4)
        if callee_basename:
            wf_norm = wf_name.replace("\\", "/")
            wf_basename = wf_norm.split("/")[-1]
            if wf_basename.lower() != callee_basename.lower():
                return m.group(0)
        if target_invoke_idref:
            idref_m = re.search(r'IdRef="([^"]+)"', opening)
            if not idref_m or idref_m.group(1) != target_invoke_idref:
                return m.group(0)
        if re.search(rf'\bx:Key="{re.escape(arg_name)}"', body):
            return m.group(0)
        if re.search(r'\bArguments\s*=', opening):
            return m.group(0)
        # Direction-aware emission (A-19b contract). Fallback = legacy
        # <InArgument x:TypeArguments="x:String">[default] when direction/
        # inner_type absent (keeps fixer safe if detector did not forward them).
        if direction and inner_type:
            wrapper = {
                "In": "InArgument",
                "Out": "OutArgument",
                "InOut": "InOutArgument",
            }.get(direction, "InArgument")
            type_safe = (str(inner_type).replace("&", "&amp;")
                         .replace("<", "&lt;").replace(">", "&gt;"))
            if wrapper == "InArgument":
                new_in_arg = (
                    f'\n          <InArgument x:TypeArguments="{type_safe}" '
                    f'x:Key="{arg_name}">{default_expr}</InArgument>'
                )
            else:
                # Out/InOut: no default literal — target binds to a variable.
                new_in_arg = (
                    f'\n          <{wrapper} x:TypeArguments="{type_safe}" '
                    f'x:Key="{arg_name}" />'
                )
        else:
            new_in_arg = (
                f'\n          <InArgument x:TypeArguments="x:String" '
                f'x:Key="{arg_name}">{default_expr}</InArgument>'
            )
        new_body = _insert_invoke_workflow_argument(body, new_in_arg)
        if _count_invoke_arguments_properties(new_body) > 1:
            return m.group(0)
        # Defesa pós-insert: x:Key duplicado na args block → rollback
        # (cobre race/regex-miss; Studio load-fails: dict bind exception).
        check_re = re.compile(
            r'<ui:InvokeWorkflowFile\.Arguments\s*>(.*?)</ui:InvokeWorkflowFile\.Arguments\s*>',
            re.DOTALL,
        )
        check_m = check_re.search(new_body)
        if check_m:
            keys = re.findall(r'\bx:Key="([^"]+)"', check_m.group(1))
            if len(keys) != len(set(keys)):
                return m.group(0)
        return _strip_null_arguments_variable_attr(opening) + new_body + closing

    new_content = invoke_re.sub(_rewrite, content)
    if new_content == content:
        return False
    new_content = _ensure_common_xmlns_for_typeargs(new_content, str(inner_type or ""))
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("remove_anticipatory_log")
def apply_remove_anticipatory_log(file: Path, spec: dict, dry_run: bool = True,
                                    project_root: Path | None = None) -> bool:
    """Remove `<ui:LogMessage>` antecipatório (N-10).

    Spec (from heuristics.logs.detect_n10_log_anticipatory):
        log_line     : 1-based line number of LogMessage opening tag
        parent_name  : qualified parent name (validation guard)

    Behavior:
      1. Locate `<ui:LogMessage` opening at log_line (or nearby ±1 lines).
      2. Walk to element end via name-aware walker (paired or self-close).
      3. Remove element + leading whitespace of the line (clean line removal).
      4. Idempotente: skip se line não tem mais LogMessage.

    Cuidado: remoção pode amplificar N-5 (log que cobria activity próxima).
    Layer 2 analyzer-gate captura compile errors. N-5 fixer próxima iter
    re-insere Trace dentro do window (engine self-heals via fixpoint loop).
    """
    log_line = spec.get("log_line")
    if not log_line:
        return False
    content = file.read_text(encoding="utf-8-sig")
    lines = content.splitlines(keepends=True)
    n_lines = len(lines)
    if log_line < 1 or log_line > n_lines:
        return False

    # Locate <ui:LogMessage opening at log_line ±1.
    log_offset = None
    for delta in (0, -1, 1):
        ln = log_line - 1 + delta
        if ln < 0 or ln >= n_lines:
            continue
        ln_offset = sum(len(s) for s in lines[:ln])
        ln_text = lines[ln]
        idx = ln_text.find("<ui:LogMessage")
        if idx >= 0:
            cand_offset = ln_offset + idx
            mc = _FULLTAG_RE.match(content, cand_offset)
            if mc and mc.group("name") == "ui:LogMessage" and mc.group("slash") != "/":
                log_offset = cand_offset
                break
    if log_offset is None:
        return False

    # Find element end (paired or self-close).
    end_offset, _ = _n5_walk_to_element_end(content, log_offset)
    if end_offset is None:
        return False

    # Determine line-start before log_offset (for clean line removal —
    # remove leading whitespace + trailing newline of the LogMessage line block).
    line_start = content.rfind("\n", 0, log_offset) + 1
    # If preceding chars are whitespace only, drop them.
    leading = content[line_start:log_offset]
    if leading and leading.strip() == "":
        snip_start = line_start
    else:
        snip_start = log_offset
    # Drop trailing newline after end_offset if present (avoid double blank line).
    snip_end = end_offset
    if snip_end < len(content) and content[snip_end] == "\n":
        snip_end += 1

    new_content = content[:snip_start] + content[snip_end:]
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("insert_trace_log")
def apply_insert_trace_log(file: Path, spec: dict, dry_run: bool = True,
                            project_root: Path | None = None) -> bool:
    """Insert <ui:LogMessage Level="Trace" .../> as next sibling after a
    flagged activity (N-5).

    Spec (from heuristics.logs.detect_n5_trace_log_significant):
        activity_offset    : byte offset of activity opening tag
        activity_name      : fully-qualified tag name (e.g. "Assign", "ui:HttpClient")
        activity_line      : 1-based line number for lxml lookup
        trace_level        : "Trace" (typically)
        has_prefixo        : True if workflow declares in_StPrefixoLog arg
        proximity_window   : detector window size (used for safety check)

    Behavior:
      1. Parse via lxml to find IMMEDIATE PARENT of target activity.
      2. If parent in restrictive list → skip (returns False).
      3. Else walk forward via name-aware regex to find activity end offset.
      4. Skip if Trace already exists within proximity_window after activity.
      5. Insert LogMessage tag with matching indentation as next sibling.
      6. Return True if changed.
    """
    activity_name = spec.get("activity_name")
    activity_line = spec.get("activity_line")
    trace_level = spec.get("trace_level") or "Trace"
    has_prefixo = bool(spec.get("has_prefixo"))
    window = int(spec.get("proximity_window") or 600)
    if not activity_name or not activity_line:
        return False

    content = file.read_text(encoding="utf-8-sig")

    # Locate activity by line + name match. Detector offsets reference
    # `active_content` (CommentOut stripped) — não mapeiam direto ao raw file.
    # Resolver via line é robusto: scan a linha apontada e linhas próximas
    # procurando primeiro `<<activity_name>` que casa.
    lines = content.splitlines(keepends=True)
    n_lines = len(lines)
    if activity_line < 1 or activity_line > n_lines:
        return False
    # Search within a small window of lines (line ±2) — CommentOut stripping
    # rarely shifts more than a couple lines but be safe.
    activity_offset = None
    m = None
    for delta in (0, -1, 1, -2, 2):
        ln = activity_line - 1 + delta
        if ln < 0 or ln >= n_lines:
            continue
        ln_offset = sum(len(s) for s in lines[:ln])
        ln_text = lines[ln]
        # Find each `<` in line_text and try to match
        for col_idx in range(len(ln_text)):
            if ln_text[col_idx] != "<":
                continue
            cand_offset = ln_offset + col_idx
            mc = _FULLTAG_RE.match(content, cand_offset)
            if mc is None:
                continue
            if mc.group("slash") == "/":
                continue
            if mc.group("name") == activity_name:
                activity_offset = cand_offset
                m = mc
                break
        if m is not None:
            break
    if m is None:
        return False

    # 2. Detect parent via lxml — restrictive check.
    target_local_only = activity_name.split(":", 1)[-1]
    parent_qual = _n5_find_immediate_parent_via_lxml(
        content.encode("utf-8"), activity_line, target_local_only,
    )
    if parent_qual is None:
        # Couldn't resolve parent → conservative skip.
        return False
    # F34: schema-driven classification (authoritative). Hardcoded fallback
    # quando schema não cobre o parent (rare — UiPath core activities).
    try:
        from .heuristics.activity_meta import classify_parent_for_logmessage
        schema_class = classify_parent_for_logmessage(parent_qual)
    except Exception:
        schema_class = "unknown"
    parent_local = parent_qual.split(":", 1)[-1]
    if schema_class == "restrictive":
        return False
    if schema_class == "open":
        # Multi-child container — sem wrap necessário, insert direto.
        is_wrap_able_non_qualified = False
    elif schema_class == "wrap_able":
        is_wrap_able_non_qualified = True  # treat as wrap-able regardless suffix
    else:
        # Unknown — fallback hardcoded lists (legacy behavior).
        if parent_qual in _N5_RESTRICTIVE_PARENT_NAMES:
            return False
        if parent_local in _COLLECTION_LOCAL_NAMES:
            return False
        is_wrap_able_non_qualified = parent_local in _N5_WRAP_ABLE_NON_QUALIFIED
    # Qualified-property parents (`Foo.Bar`): tentamos wrap em Sequence se for
    # single-child slot conhecido. Outros = skip.
    #
    # Wrap-safe suffixes (parent property aceita 1 Activity-shape child):
    #   .Then, .Else      — If/IfElseIfBlock branches
    #   .Action           — Catch.Action, Transition.Action
    #   .Body             — generic body slot
    #   .ActivityBody     — RetryScope.ActivityBody (ActivityAction wrapper —
    #                       wrap-able pq Sequence implementa ActivityAction body)
    #   .RetryAction      — RetryScope.RetryAction (idem)
    #   .Entry, .Exit     — State.Entry, State.Exit
    #
    # Wrap-UNSAFE suffixes (parent property exige tipo specific NÃO Activity):
    #   .To, .Value       — Assign.To/.Value (InArgument/OutArgument shape)
    #   .Condition        — VB expression, não Activity
    #   .Variables        — Variable[] coleção
    #   .Arguments        — Dictionary
    #   .AssignOperations — collection tipada
    #   .Headers/.Cookies/.Parameters — collections
    is_wrap_able = False
    if "." in parent_local:
        suffix = parent_local.rsplit(".", 1)[-1]
        wrap_safe_suffixes = {
            "Then", "Else", "Action", "Body",
            "ActivityBody", "RetryAction",
            "Entry", "Exit",
            "Try", "Finally",  # TryCatch.Try / TryCatch.Finally — single-child Activity slot
            "Default",  # FlowSwitch.Default, Switch.Default — single-child
            "True", "False",  # FlowDecision.True / FlowDecision.False
        }
        if suffix in wrap_safe_suffixes:
            is_wrap_able = True
        else:
            return False
    if is_wrap_able_non_qualified:
        is_wrap_able = True

    # 3. Find activity end offset.
    end_offset, _ = _n5_walk_to_element_end(content, activity_offset)
    if end_offset is None:
        return False

    # 4. Safety: skip if a Trace already follows within proximity_window.
    look = content[end_offset:end_offset + window]
    if re.search(rf'<ui:LogMessage\b[^>]*\bLevel="{re.escape(trace_level)}"',
                  look):
        return False

    # 5. Build LogMessage. Indentation = same as activity's line.
    line_start = content.rfind("\n", 0, activity_offset) + 1
    line_prefix = content[line_start:activity_offset]
    indent = re.match(r"^(\s*)", line_prefix).group(1)
    display = ""
    m_dn = re.search(r'\bDisplayName="([^"]*)"', m.group(0))
    if m_dn:
        display = m_dn.group(1)
    if not display:
        display = activity_name
    # Sanitize for embedding inside attribute value (XML-escape).
    safe_disp = (display.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))
    idref = _n5_next_idref(content, base="LogMessage_Auto")
    # Message DEVE ser VB expression form `[...]` em Studio Windows target.
    # Literal sem brackets é parseado por VB compiler como código → erros
    # BC30109/BC30451 (`'Assign' is a class type`, identifiers undeclared).
    if has_prefixo:
        msg_attr = (
            f'Message="[in_StPrefixoLog + &quot;Concluído: '
            f'{safe_disp}&quot;]"'
        )
    else:
        msg_attr = f'Message="[&quot;Concluído: {safe_disp}&quot;]"'
    # DisplayName usa verbo infinitivo (Sicoob N-15) + sanitized activity context.
    # Strip prefixes ruins do source DisplayName (`Trace:`, `Log -`, `Log Message`).
    # Evita ST-MRD-002 (default "Log Message") + ST-NMG-004 (DisplayName repetido).
    _sanitized = display
    for _prefix in ("Trace: ", "Trace:", "Log - ", "Log -", "Log Message", "Log:", "Log "):
        if _sanitized.startswith(_prefix):
            _sanitized = _sanitized[len(_prefix):].strip()
            break
    if not _sanitized or _sanitized.lower() in ("log", "logmessage", "message"):
        _sanitized = activity_name.split(":", 1)[-1]
    base_display = f"Log Message - {_sanitized} concluido"[:120]
    trace_display = _n5_unique_display_name(content, base_display)
    safe_trace_disp = (trace_display.replace("&", "&amp;")
                       .replace("<", "&lt;").replace(">", "&gt;")
                       .replace('"', "&quot;"))
    log_tag = (
        f'<ui:LogMessage DisplayName="{safe_trace_disp}" '
        f'sap:VirtualizedContainerService.HintSize="334,91" '
        f'sap2010:WorkflowViewState.IdRef="{idref}" '
        f'Level="{trace_level}" '
        f'{msg_attr} />'
    )
    insert_block = "\n" + indent + log_tag

    if is_wrap_able:
        # Wrap: substituir activity por <Sequence>activity\n+log</Sequence>.
        # Parent é qualified-property single-child slot (.Then/.Else/.Action/
        # .Body). Sequence é Activity-shape — aceita pelo slot.
        original_activity = content[activity_offset:end_offset]
        # Re-indent activity dentro do Sequence (+2 chars).
        # Pra Sicoob convenção, mantém formatting original — wrap externo só.
        wrap_indent = indent
        inner_indent = wrap_indent + "  "
        # Re-indent activity body com inner_indent (linha-a-linha).
        activity_lines = original_activity.split("\n")
        re_indented = activity_lines[0]
        if len(activity_lines) > 1:
            re_indented += "\n" + "\n".join(
                (inner_indent + ln.lstrip(" \t")) if ln.strip() else ln
                for ln in activity_lines[1:]
            )
        # Build Sequence wrapper. DisplayName herda do activity ou usa "Sequence — Trace wrap".
        seq_disp = f"Sequence (wrap N-5: {display})"[:120]
        safe_seq = (seq_disp.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))
        wrapper = (
            f'<Sequence DisplayName="{safe_seq}">\n'
            f'{inner_indent}{re_indented}\n'
            f'{inner_indent}{log_tag}\n'
            f'{wrap_indent}</Sequence>'
        )
        new_content = (content[:activity_offset] + wrapper
                       + content[end_offset:])
    else:
        new_content = content[:end_offset] + insert_block + content[end_offset:]
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("remove_xml_comment_root")
def apply_remove_xml_comment_root(file: Path, spec: dict, dry_run: bool = True,
                                    project_root: Path | None = None) -> bool:
    """S-17 fixer: remove XmlComment as direct child of <Activity> root.

    Studio compiler aborta com 'Unable to cast XmlComment to XmlElement' quando
    comment esta entre <Activity> open tag e o primeiro child element.

    Remove ALL XmlComments na regiao entre Activity-open e first-element.
    """
    content = file.read_text(encoding="utf-8-sig")
    activity_re = re.compile(r'<Activity\b[^>]*?>', re.DOTALL)
    m = activity_re.search(content)
    if m is None:
        return False
    activity_end = m.end()
    first_elem_re = re.compile(r'<(?!!|\?)[A-Za-z]')
    fe = first_elem_re.search(content, activity_end)
    if fe is None:
        return False
    first_elem_start = fe.start()
    gap = content[activity_end:first_elem_start]
    comment_re = re.compile(r'\n?\s*<!--.*?-->\n?', re.DOTALL)
    new_gap, n = comment_re.subn('\n', gap)
    if n == 0:
        return False
    new_gap = re.sub(r'\n\s*\n+', '\n', new_gap)
    new_content = content[:activity_end] + new_gap + content[first_elem_start:]
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("project_manifest_remove_stale_entries")
def apply_project_manifest_remove_stale_entries(
    file: Path, spec: dict, dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """J-8 fixer: remove entries from a project.json array (`key_path`)
    whose `filename_field` references a file that does not exist on disk.

    Spec:
      key_path: dot-separated path do array
                (default: 'designOptions.fileInfoCollection')
      filename_field: nome do campo dentro de cada entry (default: 'fileName')

    Idempotente; no-op se array faltando/vazio ou todos arquivos existem.
    Preserva BOM. Mantém indent=2 + trailing newline (mesmo padrão dos
    fixers JSON existentes).
    """
    import json as _json
    key_path = spec.get("key_path", "designOptions.fileInfoCollection")
    filename_field = spec.get("filename_field", "fileName")
    if not key_path or not filename_field:
        return False
    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return False

    keys = key_path.split(".")
    cur = data
    for k in keys[:-1]:
        if not isinstance(cur, dict):
            return False
        cur = cur.get(k)
        if cur is None:
            return False
    if not isinstance(cur, dict):
        return False
    last = keys[-1]
    arr = cur.get(last)
    if not isinstance(arr, list) or not arr:
        return False

    root = Path(project_root) if project_root is not None else file.parent
    kept = []
    for entry in arr:
        if not isinstance(entry, dict):
            kept.append(entry)
            continue
        fname = entry.get(filename_field)
        if not fname or not isinstance(fname, str):
            kept.append(entry)
            continue
        rel = fname.replace("\\", "/")
        target = (root / rel).resolve()
        if target.exists():
            kept.append(entry)
        # else: drop entry

    if len(kept) == len(arr):
        return False  # no-op

    cur[last] = kept
    new_text = _json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
        file.write_bytes(out)
    return True


@register("project_manifest_set_keys")
def apply_project_manifest_set_keys(
    file: Path, spec: dict, dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """ENV-1 fixer: set/override múltiplas keys em project.json via paths dotted.

    Spec:
      keys: dict[str, Any] — path dotted → valor desejado.
            Ex: {"runtimeOptions.mustRestoreAllDependencies": True,
                 "designOptions.modernBehavior": False}
            Cria sub-objects intermediários se ausentes. Sobrescreve valores
            divergentes. Type-check estrito por leaf — só aceita primitivo
            (bool/int/str/None) na folha pra evitar mutações estruturais
            acidentais.

    Idempotente: skip se todos keys já têm valor desejado. Preserva BOM +
    indent=2 + trailing newline (mesmo padrão J-8/J-12).
    """
    import json as _json
    keys = spec.get("keys") or {}
    if not keys or not isinstance(keys, dict):
        return False
    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False

    _ALLOWED_LEAF = (bool, int, float, str, type(None))
    changed = False
    for dotted, desired in keys.items():
        if not isinstance(desired, _ALLOWED_LEAF):
            continue  # safety: skip non-primitive leaf
        parts = dotted.split(".")
        cur = data
        for k in parts[:-1]:
            nxt = cur.get(k)
            if not isinstance(nxt, dict):
                if nxt is not None:
                    # collision com tipo não-dict → skip esse key (não
                    # sobrescrever array/scalar com object).
                    cur = None
                    break
                nxt = {}
                cur[k] = nxt
            cur = nxt
        if cur is None:
            continue
        leaf = parts[-1]
        existing = cur.get(leaf, _SENTINEL)
        if existing == desired:
            continue
        cur[leaf] = desired
        changed = True

    if not changed:
        return False
    new_text = _json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
        file.write_bytes(out)
    return True


_SENTINEL = object()


@register("gitignore_append_lines")
def apply_gitignore_append_lines(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """HY-4 fixer: garante entries obrigatórios em .gitignore.

    Spec:
      target: path do .gitignore (injetado pelo detector). Permite que
              `file` permaneça anchor em project.json (sempre existe →
              safety snapshot funciona) e fixer escreve no path correto.
      missing: list[str] de linhas faltando (injetadas pela heuristic).
      defaults: list[str] de entries obrigatórios (fallback se missing ausente).
    Idempotente; cria .gitignore se ausente. Preserva CRLF se já existente,
    senão LF. Append no fim com bloco separador.
    """
    missing = spec.get("missing") or spec.get("defaults") or []
    if not missing:
        return False
    target_raw = spec.get("target")
    if target_raw:
        file = Path(target_raw)
    if file.exists():
        try:
            existing_bytes = file.read_bytes()
        except OSError:
            return False
        eol = b"\r\n" if b"\r\n" in existing_bytes else b"\n"
        existing_text = existing_bytes.decode("utf-8", errors="replace")
        existing_lines = {ln.strip() for ln in existing_text.splitlines() if ln.strip()}
        to_add = [m for m in missing if m not in existing_lines]
        if not to_add:
            return False
        new_block = (eol.decode("ascii")).join(
            ["", "# Engine rule-engine HY-4 — required entries"] + to_add + [""]
        )
        if not existing_text.endswith("\n") and not existing_text.endswith("\r\n"):
            new_block = (eol.decode("ascii")) + new_block
        new_text = existing_text + new_block
    else:
        new_text = "\n".join(
            ["# Generated by rule-engine HY-4"] + list(missing) + [""]
        )
    if not dry_run:
        file.write_text(new_text, encoding="utf-8", newline="")
    return True


@register("normalize_eol_crlf")
def apply_normalize_eol_crlf(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """HY-5 fixer: normaliza EOL → CRLF (Windows + XAML Studio std).
    Idempotente; preserva BOM. Re-encode UTF-8 igual ao read.
    """
    try:
        raw = file.read_bytes()
    except OSError:
        return False
    bom = raw.startswith(b"\xef\xbb\xbf")
    body = raw[3:] if bom else raw
    # Normalize: CRLF → LF first, depois LF → CRLF
    normalized = body.replace(b"\r\n", b"\n").replace(b"\r", b"\n").replace(b"\n", b"\r\n")
    new_raw = (b"\xef\xbb\xbf" if bom else b"") + normalized
    if new_raw == raw:
        return False
    if not dry_run:
        file.write_bytes(new_raw)
    return True


@register("strip_bom")
def apply_strip_bom(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """HY-6 fixer: strip UTF-8 BOM. JSON convention sem BOM.
    Idempotente; no-op se já sem BOM.
    """
    try:
        raw = file.read_bytes()
    except OSError:
        return False
    if not raw.startswith(b"\xef\xbb\xbf"):
        return False
    if not dry_run:
        file.write_bytes(raw[3:])
    return True


@register("wrap_arrayrow_object")
def apply_wrap_arrayrow_object(file: Path, spec: dict, dry_run: bool = True,
                                project_root: Path | None = None) -> bool:
    """W-12 fixer: `ArrayRow="[{a, b}]"` → `ArrayRow="[New Object() {a, b}]"`.

    AddDataRow.ArrayRow target Object(). Sem type explícito, compiler infere
    do conteúdo (Integer/String/etc); quando heterogêneo OU value type, falha
    BC30333. Wrap Object() é safe — todos types convertem upward.

    Idempotente: skip se já `New ` prefixed.
    """
    content = file.read_text(encoding="utf-8-sig")
    pat = re.compile(r'ArrayRow="\[\{(?!New\s)([^"]*)\}\]"')
    def _wrap(m):
        return f'ArrayRow="[New Object() {{{m.group(1)}}}]"'
    new_content, n = pat.subn(_wrap, content)
    if n == 0 or new_content == content:
        return False
    if not dry_run:
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("wrap_typed_empty_array_literal")
def apply_wrap_typed_empty_array_literal(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """W-12 fixer: `[{...}]` in `x:TypeArguments="T[]"` -> `[New T() {...}]`.

    VB array literals often cannot infer an element type under Option Strict.
    When XAML declares the array type locally, the conversion is mechanical:
    `s:String[]` becomes `New String() {...}` and
    `umm:Office365Message[]` becomes `New UiPath...Office365Message() {...}`.
    """
    content = file.read_text(encoding="utf-8-sig")

    primitive_aliases = {
        "String": "String",
        "Boolean": "Boolean",
        "Int16": "Short",
        "Int32": "Integer",
        "Int64": "Long",
        "Double": "Double",
        "Decimal": "Decimal",
        "DateTime": "Date",
        "Object": "Object",
    }

    def vb_type(array_type: str) -> str:
        element_type = array_type.strip()[:-2].strip()
        if ":" not in element_type:
            return primitive_aliases.get(element_type, element_type)

        prefix, name = element_type.split(":", 1)
        if prefix in {"x", "s"} and name in primitive_aliases:
            return primitive_aliases[name]

        ns_m = re.search(
            rf'\bxmlns:{re.escape(prefix)}="clr-namespace:([^;"]+)',
            content,
        )
        if ns_m:
            return f"{ns_m.group(1)}.{name}"
        return element_type

    def expr(array_type: str, items: str = "") -> str:
        element_type = vb_type(array_type)
        return f"[New {element_type}() {{{items}}}]"

    def expr_inner(array_type: str, items: str = "") -> str:
        return expr(array_type, items)[1:-1]

    tag_pat = re.compile(
        r"<[^<>]*\bDefault=\"\[\{(?P<items>[^\"<>]*?)\}\]\"[^<>]*>"
    )

    def repl_default(m: re.Match) -> str:
        tag = m.group(0)
        type_m = re.search(r'\bx:TypeArguments="([^"]+\[\])"', tag)
        if not type_m:
            return tag
        items = m.group("items")
        if items.lstrip().startswith("New "):
            return tag
        return tag.replace(
            f'Default="[{{{items}}}]"',
            f'Default="{expr(type_m.group(1), items)}"',
        )

    vbvalue_pat = re.compile(
        r"<[^<>]*\bx:TypeArguments=\"(?P<type>[^\"]+\[\])\""
        r"[^<>]*\bExpressionText=\"\{\}\{\}\"[^<>]*>"
    )

    def repl_vbvalue(m: re.Match) -> str:
        tag = m.group(0)
        return tag.replace(
            'ExpressionText="{}{}"',
            f'ExpressionText="{expr_inner(m.group("type"))}"',
        )

    elem_pat = re.compile(
        r'(<(?P<tag>[A-Za-z_][\w:.-]*)\b[^>]*'
        r'\bx:TypeArguments="(?P<type>[^"]+\[\])"[^>]*>)'
        r'\[\{(?P<items>[^<>\r\n]*?)\}\]'
        r'(</(?P=tag)>)'
    )

    def repl_element(m: re.Match) -> str:
        if m.group("items").lstrip().startswith("New "):
            return m.group(0)
        return f"{m.group(1)}{expr(m.group('type'), m.group('items'))}{m.group(5)}"

    new_content = tag_pat.sub(repl_default, content)
    new_content = vbvalue_pat.sub(repl_vbvalue, new_content)
    new_content = elem_pat.sub(repl_element, new_content)

    if new_content == content:
        return False
    if not dry_run:
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("strip_terminal_vb_line_continuation")
def apply_strip_terminal_vb_line_continuation(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """W-35 fixer: remove terminal VB line-continuation `_` before `]`.

    Example:
      `Condition="[(foo) _]"` -> `Condition="[(foo) ]"`

    The matcher requires whitespace or encoded XML whitespace before `_`, so
    identifiers ending with underscore are preserved.
    """
    content = file.read_text(encoding="utf-8-sig")
    pat = re.compile(
        r'(?P<prefix>(?:[ \t\r\n]|&#x(?:A|D|9);|&#(?:10|13|9);)+)'
        r'_'
        r'(?P<suffix>(?:[ \t\r\n]|&#x(?:A|D|9);|&#(?:10|13|9);)*)'
        r'\]'
    )
    new_content, n = pat.subn(r'\g<prefix>\g<suffix>]', content)
    if n == 0 or new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("strip_string_format_tostring_with_delimiter")
def apply_strip_string_format_tostring_with_delimiter(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """W-36 fixer: remove legacy `.ToStringWithDelimiter()` after String.Format.

    The Windows compiler sees the receiver as String and raises BC30456. In
    selector attributes generated as `String.Format(...).ToStringWithDelimiter()`
    the delimiter call is a legacy no-op.
    """
    content = file.read_text(encoding="utf-8-sig")
    pat = re.compile(
        r'(?P<receiver>\(?[sS]tring\.Format\([^]]*?\)\)?)'
        r'\.ToStringWithDelimiter\(\)'
    )
    lines = content.splitlines(keepends=True)
    changed = False
    new_lines: list[str] = []
    for line in lines:
        if "ToStringWithDelimiter()" in line and re.search(r'(?i)string\.format\(', line):
            new_line = pat.sub(r'\g<receiver>', line)
            changed = changed or new_line != line
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    if not changed:
        return False
    if not dry_run:
        _write_preserving_bom(file, "".join(new_lines), _file_has_bom(file))
    return True


@register("expand_read_as_datatable_signature")
def apply_expand_read_as_datatable_signature(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """W-37 fixer: `.ReadAsDataTable(a,b,c)` -> 5-argument Excel 3.x call."""
    content = file.read_text(encoding="utf-8-sig")
    pat = re.compile(
        r'\.ReadAsDataTable\('
        r'(?P<a1>[^(),\r\n]+),'
        r'(?P<a2>[^(),\r\n]+),'
        r'(?P<a3>[^(),\r\n]+)'
        r'\)'
    )

    def repl(m: re.Match) -> str:
        return (
            ".ReadAsDataTable("
            f"{m.group('a1')},{m.group('a2')},{m.group('a3')},False,Nothing)"
        )

    new_content = pat.sub(repl, content)
    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("rewrite_ccs_sipagdirect_legacy_login")
def apply_rewrite_ccs_sipagdirect_legacy_login(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """W-38 fixer: CCS_SipagDirect.Sessão.LoginSipagDirect -> CCS_SipagDirect.Login."""
    content = file.read_text(encoding="utf-8-sig")
    new_content = content
    new_content = new_content.replace(
        "clr-namespace:CCS_SipagDirect.Sessão;assembly=CCS_SipagDirect",
        "clr-namespace:CCS_SipagDirect;assembly=CCS_SipagDirect",
    )
    new_content = new_content.replace(
        "clr-namespace:CCS_SipagDirect.Sessao;assembly=CCS_SipagDirect",
        "clr-namespace:CCS_SipagDirect;assembly=CCS_SipagDirect",
    )
    new_content = new_content.replace(
        "<x:String>CCS_SipagDirect.Sessão</x:String>",
        "<x:String>CCS_SipagDirect</x:String>",
    )
    new_content = new_content.replace(
        "<x:String>CCS_SipagDirect.Sessao</x:String>",
        "<x:String>CCS_SipagDirect</x:String>",
    )
    new_content = re.sub(
        r'<(?P<prefix>[A-Za-z_]\w*):LoginSipagDirect(?=[\s/>])',
        r'<\g<prefix>:Login',
        new_content,
    )
    new_content = re.sub(
        r'</(?P<prefix>[A-Za-z_]\w*):LoginSipagDirect>',
        r'</\g<prefix>:Login>',
        new_content,
    )
    arg_map = {
        "in_StUrlSipagDirect": "in_URL",
        "in_StUsuario": "in_Usuario",
        "in_SSSenha": "in_Senha",
    }
    for old, new in arg_map.items():
        new_content = re.sub(rf'\b{re.escape(old)}=', f"{new}=", new_content)

    if new_content == content:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, _file_has_bom(file))
    return True


@register("strip_empty_ocrengine_block")
def apply_strip_empty_ocrengine_block(file: Path, spec: dict, dry_run: bool = True,
                                       project_root: Path | None = None) -> bool:
    """OCR-1 fixer: remove `<uix:NApplicationCard.OCREngine>...</...>` quando
    ActivityFunc body é vazio (só Argument declarations).

    Regex precisão garante engines concretos (com ui:UiPathScreenOcr etc dentro)
    NÃO matcham — fixer preserva workflows OCR legítimos.

    Idempotente: skip se nenhum bloco vazio.

    Trailing whitespace incluído pra cleanup limpo (não deixa linha vazia).
    """
    content = file.read_text(encoding="utf-8-sig")
    pat = re.compile(
        r'\s*<uix:NApplicationCard\.OCREngine>\s*'
        r'<ActivityFunc\b[^>]*>\s*'
        r'(?:<ActivityFunc\.Argument>\s*<DelegateInArgument\b[^>]*/?>\s*</ActivityFunc\.Argument>\s*)*'
        r'</ActivityFunc>\s*'
        r'</uix:NApplicationCard\.OCREngine>',
        re.DOTALL,
    )
    new_content, n = pat.subn("", content)
    if n == 0 or new_content == content:
        return False
    if not dry_run:
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("retarget_project_argument_types")
def apply_retarget_project_argument_types(file: Path, spec: dict, dry_run: bool = True,
                                            project_root: Path | None = None) -> bool:
    """J-12 fixer: project.json arguments[input/output][*].type rewrite.

    Activity Migrator switches targetFramework Legacy→Windows mas deixa
    `project.json::arguments.input[*].type` apontando pra .NET Framework
    assemblies (`mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089`).

    Studio analyzer compila project com .NET 6 mas vê argument types declarados
    com mscorlib v4 (incompatível) — gera cascade BC31424/BC30652 quando workflow
    usa esses arguments.

    Fix: rewrite assembly-qualified type string pra short type name (sem
    assembly clause). Studio resolve via project deps + AssemblyReferences.

      "System.String, mscorlib, Version=4.0.0.0, ..." → "System.String"

    Cobre input + output args. Idempotente: skip se já short form.
    """
    if file.name != "project.json":
        return False
    import json
    content = file.read_text(encoding="utf-8-sig")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return False

    changed = False
    # Trailing OUTERMOST legacy assembly clause, e.g.
    #   ", mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089"
    # Anchored at end-of-string ($). For a non-generic type the bare name is left.
    # For a generic type the bracketed `[[...]]` generic args (which contain
    # their OWN inner assembly clauses) are preserved — only the top-level
    # trailing clause after the final `]]` is stripped.
    _LEGACY_ASMS = (
        r'mscorlib|System|System\.Core|System\.Drawing|System\.Xml|System\.Data'
    )
    legacy_tail_pat = re.compile(
        rf',\s*(?:{_LEGACY_ASMS}),\s*Version=4\.\d+\.\d+\.\d+'
        r'(?:,\s*Culture=[^,\]]+)?(?:,\s*PublicKeyToken=[^,\]]+)?\s*$'
    )

    def _strip_outer_assembly_clause(tp: str) -> str | None:
        """Strip the outermost trailing legacy assembly clause, preserving any
        bracketed generic type arguments. Returns the rewritten short type, or
        None if no top-level legacy clause is present.

        Generic types serialize as `Outer`N[[arg1, asm, Version=...],[arg2, ...]],
        asm, Version=...`. The `^(\\S+),` approach truncated at the first comma
        (inside the first generic arg). Here we only remove the trailing clause
        that sits OUTSIDE the bracketed args.
        """
        m = legacy_tail_pat.search(tp)
        if not m:
            return None
        # Guard: the match must be at the TOP level, i.e. not inside `[[...]]`.
        # Since the pattern is anchored at `$` and the generic args close with
        # `]]`, the only way the tail follows balanced brackets is if every `[`
        # before m.start() is matched by a `]`. Verify bracket balance of the
        # prefix to avoid stripping inside an unbalanced (malformed) generic.
        prefix = tp[: m.start()]
        if prefix.count("[") != prefix.count("]"):
            return None
        return prefix

    def _rewrite_items(items):
        nonlocal changed
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            tp = item.get("type")
            if not isinstance(tp, str):
                continue
            short = _strip_outer_assembly_clause(tp)
            if short is not None and short != tp:
                item["type"] = short
                changed = True

    # Top-level `arguments.input/output`
    args = data.get("arguments")
    if isinstance(args, dict):
        _rewrite_items(args.get("input"))
        _rewrite_items(args.get("output"))

    # Per-entry-point `entryPoints[].input/output` (Migrator deixa stale)
    entry_points = data.get("entryPoints")
    if isinstance(entry_points, list):
        for ep in entry_points:
            if isinstance(ep, dict):
                _rewrite_items(ep.get("input"))
                _rewrite_items(ep.get("output"))

    if not changed:
        return False
    if not dry_run:
        new_text = json.dumps(data, indent=2, ensure_ascii=False)
        # Preserve trailing newline if original had it
        if content.endswith("\n") and not new_text.endswith("\n"):
            new_text += "\n"
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_text.encode("utf-8"))
    return True


@register("queue_item_indexer_to_item")
def apply_queue_item_indexer_to_item(file: Path, spec: dict, dry_run: bool = True,
                                       project_root: Path | None = None) -> bool:
    """W-14 fixer: disambiguate `.SpecificContent("key")` / `.Output("key")` calls.

    VB compiler em alguns contextos (UIA 25.x QueueItem ABI shift) interpreta
    `qi.SpecificContent("X")` como property call com arg, gerando
    `BC30057: Too many arguments to 'Public Overloads Property SpecificContent'`.

    Fix: rewrite usando `.Item("X")` explícito — força resolução como
    Dictionary indexer method call vs property invocation:

      `.SpecificContent("X")` → `.SpecificContent.Item("X")`
      `.Output("X")`          → `.Output.Item("X")`

    Cobre forma XAML-escaped (`&quot;`) e raw quote (`"`). Single key arg
    apenas — multi-arg seria semântica diferente.

    Idempotente: regex match exige args dentro de parens, `.Item(` post-fix
    não re-matcha porque `.Item` não está na lista.
    """
    content = file.read_text(encoding="utf-8-sig")
    # XAML-escaped quote form (mais comum dentro Default="...")
    pat_xaml = re.compile(
        r'\.(SpecificContent|Output)\s*\(\s*(&quot;[^&]+&quot;)\s*\)'
    )
    pat_raw = re.compile(
        r'\.(SpecificContent|Output)\s*\(\s*("[^"]+")\s*\)'
    )

    new_content = pat_xaml.sub(r'.\1.Item(\2)', content)
    new_content = pat_raw.sub(r'.\1.Item(\2)', new_content)
    if new_content == content:
        return False
    if not dry_run:
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("strip_orphan_xmlns")
def apply_strip_orphan_xmlns(file: Path, spec: dict, dry_run: bool = True,
                              project_root: Path | None = None) -> bool:
    """W-15 fixer: strip `xmlns:PREFIX="..."` declarações cujo prefix NÃO é
    usado no resto do XAML.

    Activity Migrator deixa muitas xmlns aliases cruft após migração
    Legacy→Windows. Alguns referenciam `.NET Framework 4` assemblies
    (`mscorlib, Version=4.0.0.0`) que conflitam com `.NET 6` resolution
    — Studio analyzer pode gerar BC31424/BC30652 confusos por ambiguidade
    de type forwarder paths.

    Strip:
      - Find todos `xmlns:PREFIX="..."` no Activity root
      - Pra cada PREFIX, conta usages `PREFIX:` no resto do document
        (exclui própria xmlns declaration)
      - Se 0 usages → strip declaration

    Safety:
      - NÃO strip prefixes XAML core: `x`, `mc`, `xmlns` (default)
      - Considera `mc:Ignorable="sap sap2010"` style atribute-value usage
      - Idempotente: skip se nada removido

    Risk: se algum tool externo (test runner, custom analyzer) depender
    de xmlns alias específica sem usar prefix:, esse cleanup pode quebrar.
    Empiricamente baixo risco — XAML standard só USA prefixes via
    `prefix:Element` ou `prefix:Attribute=`.
    """
    content = file.read_text(encoding="utf-8-sig")

    # Find all xmlns:PREFIX="VALUE" declarations
    xmlns_pat = re.compile(r'\s+xmlns:([A-Za-z_][\w]*)="[^"]*"')
    declarations = list(xmlns_pat.finditer(content))
    if not declarations:
        return False

    # Core prefixes NEVER strip (mesmo se não tiver usage textual — Studio
    # gera implicitamente)
    _CORE_PREFIXES = frozenset({"x", "mc", "xml"})

    orphan_decls: list[re.Match] = []
    for decl in declarations:
        prefix = decl.group(1)
        if prefix in _CORE_PREFIXES:
            continue
        # Count usage of `prefix:` outside its own xmlns declaration
        # Pattern: `\bPREFIX:` mas NÃO `xmlns:PREFIX=`
        usage_pat = re.compile(rf'(?<!xmlns:)\b{re.escape(prefix)}:')
        usage_count = len(usage_pat.findall(content))
        # Subtract count of own xmlns declaration matches (where xmlns: prefix
        # is preceded by xmlns: — the lookbehind already excludes those, but
        # double-check)
        if usage_count == 0:
            orphan_decls.append(decl)

    if not orphan_decls:
        return False

    # Strip orphan declarations from END to START (preserve positions)
    new_content = content
    for decl in reversed(orphan_decls):
        new_content = new_content[: decl.start()] + new_content[decl.end():]

    if new_content == content:
        return False
    if not dry_run:
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("strip_nwindow_operation")
def apply_strip_nwindow_operation(file: Path, spec: dict, dry_run: bool = True,
                                    project_root: Path | None = None) -> bool:
    r"""D-PINALERT NWindowOperation fixer: strip activity + força CloseMode="Always"
    nos NApplicationCard que continham NWindowOperation.

    NWindowOperation foi introduzida em UIA 25.10.21. Pin canonical Sicoob (D-1b
    em `assets/canonical_pins.yaml`) é anterior — API não existe nessa versão. Activity geralmente vive aninhada dentro de `<uix:NApplicationCard>`
    pra controlar close lifecycle quando default `CloseMode="IfOpenedByThisCard"`
    ou explícito `CloseMode="Never"` foi escolhido.

    Strategy:
      1. Pra cada NWindowOperation, identifica NApplicationCard pai mais próximo
         (text search backward).
      2. Strip TODOS NWindowOperation blocks (open+close, self-closed).
      3. Pra cada NApplicationCard pai tracked, força `CloseMode="Always"`:
         - Se CloseMode= ausente → injeta
         - Se CloseMode="<qualquer>" → replace pra "Always"
      4. NApplicationCards NÃO tracked (sem NWindow dentro) → leave intact.

    Safety:
      - Negative lookahead `(?!\.)` evita matchar property elements
        (`<uix:NApplicationCard.Body>` etc).
      - Idempotente: se já não tem NWindow, return False.
      - Se NApplicationCard pai não encontrado pra algum NWindow → strip
        mesmo assim (CloseMode default ou orphan, raro).
    """
    content = file.read_text(encoding="utf-8-sig")

    # Patterns NWindowOperation block (pair + self-closed)
    nwo_pair_pat = re.compile(
        r'<uix:NWindowOperation(?!\.)\b[^>]*(?<!/)>.*?</uix:NWindowOperation>',
        re.DOTALL,
    )
    nwo_self_pat = re.compile(
        r'<uix:NWindowOperation(?!\.)\b[^>]*/>',
    )

    # Coleta posições start de cada NWindow
    nwo_positions = [m.start() for m in nwo_pair_pat.finditer(content)]
    nwo_positions += [m.start() for m in nwo_self_pat.finditer(content)]
    if not nwo_positions:
        return False

    # Pra cada NWindow, encontra NApplicationCard ancestor mais próximo backward.
    # Pattern: `<uix:NApplicationCard\b(?!\.)` — activity instance, não property.
    nac_open_pat = re.compile(r'<uix:NApplicationCard\b(?!\.)')
    # Tracked NApplicationCard open tag start positions (deduped)
    tracked_nac_starts: set[int] = set()
    for nwo_pos in nwo_positions:
        # All NApplicationCard opens before this NWindow position
        nac_starts = [m.start() for m in nac_open_pat.finditer(content[:nwo_pos])]
        if nac_starts:
            tracked_nac_starts.add(nac_starts[-1])  # closest ancestor

    # Strip todos NWindowOperation blocks (com whitespace prefix pra cleanup)
    pat_pair_ws = re.compile(
        r'\s*<uix:NWindowOperation(?!\.)\b[^>]*(?<!/)>.*?</uix:NWindowOperation>\s*',
        re.DOTALL,
    )
    pat_self_ws = re.compile(
        r'\s*<uix:NWindowOperation(?!\.)\b[^>]*/>\s*',
    )
    new_content, n_pair = pat_pair_ws.subn('\n', content)
    new_content, n_self = pat_self_ws.subn('\n', new_content)
    n_total = n_pair + n_self
    if n_total == 0:
        return False

    # Pra cada tracked NApplicationCard, force CloseMode="Always".
    # Note: posições mudaram pós-strip — precisamos re-localizar via regex.
    # Cada NApplicationCard pode ser identificada por algum attr único; vou
    # usar approach mais simples: substitui TODOS NApplicationCards (não-property
    # element) que estão na lista de "originalmente continha NWindow" via
    # identificador único.
    #
    # Heurística simples: identifica NACs por seu sap2010:WorkflowViewState.IdRef
    # ou ScopeGuid (presentes na maioria) — atributos únicos. Captura essas IDs
    # ANTES do strip, depois aplica force_closemode nas NACs com matching ID.

    # Extract ID per tracked NAC (pre-strip content)
    nac_full_open_pat = re.compile(r'<uix:NApplicationCard\b(?!\.)[^>]*?/?>')
    tracked_ids: set[str] = set()
    for nac_start in tracked_nac_starts:
        m = nac_full_open_pat.search(content, nac_start)
        if not m:
            continue
        open_tag = m.group(0)
        # Try ScopeGuid first (unique per scope), then IdRef
        id_m = re.search(r'ScopeGuid="([^"]+)"', open_tag)
        if not id_m:
            id_m = re.search(r'sap2010:WorkflowViewState\.IdRef="([^"]+)"', open_tag)
        if id_m:
            tracked_ids.add(id_m.group(1))

    if not tracked_ids:
        # Sem IDs trackable — apply force_closemode em TODOS NACs (fallback comportamento agressivo)
        # Conservador: skip CloseMode injection nesse caso, só strip
        pass
    else:
        def _force_closemode(m):
            open_tag = m.group(0)
            # Verify essa NAC está tracked
            id_m = re.search(r'ScopeGuid="([^"]+)"', open_tag) or re.search(
                r'sap2010:WorkflowViewState\.IdRef="([^"]+)"', open_tag
            )
            if not id_m or id_m.group(1) not in tracked_ids:
                return open_tag
            # Force CloseMode="Always"
            if re.search(r'\bCloseMode\s*=\s*"[^"]*"', open_tag):
                return re.sub(
                    r'\bCloseMode\s*=\s*"[^"]*"',
                    'CloseMode="Always"',
                    open_tag,
                )
            # Inject CloseMode antes do `>` ou `/>` final
            if open_tag.rstrip().endswith('/>'):
                return open_tag.rstrip()[:-2].rstrip() + ' CloseMode="Always" />'
            return open_tag.rstrip()[:-1].rstrip() + ' CloseMode="Always">'

        new_content = nac_full_open_pat.sub(_force_closemode, new_content)

    if new_content == content:
        return False
    if not dry_run:
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("insert_assembly_reference")
def apply_insert_assembly_reference(file: Path, spec: dict, dry_run: bool = True,
                                     project_root: Path | None = None) -> bool:
    """W-11* fixer: insere `<AssemblyReference>X</AssemblyReference>` dentro do
    bloco `<sco:Collection x:TypeArguments="AssemblyReference">` antes da close
    tag, preservando indent existente.

    spec.name = nome do assembly (string simples, sem version/culture).

    Idempotente: skip se ref já presente.

    Safety:
      - Validate name pattern (sem espaços/aspas).
      - Requer bloco `<sco:Collection x:TypeArguments="AssemblyReference">`
        existir (XAML standard). Sem ele, no-op (XAML provavelmente é fragment
        ou library workflow).
      - Studio re-sorta refs no save — não tentamos preservar alfabético aqui.
    """
    name = (spec or {}).get("name")
    if not name or not isinstance(name, str):
        return False
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\-]*", name):
        return False

    content = file.read_text(encoding="utf-8-sig")

    # Idempotent: já presente
    if re.search(rf"<AssemblyReference>{re.escape(name)}</AssemblyReference>", content):
        return False

    # Match bloco AssemblyReference Collection + close tag. Cobre as duas formas
    # do Studio:
    #   <sco:Collection x:TypeArguments="AssemblyReference">...</sco:Collection>
    #   <scg:List x:TypeArguments="AssemblyReference" Capacity="N">...</scg:List>
    # Studio numera prefixes (sco, sco1, sco2, scg, scg1...) conforme ordem de
    # namespace declaration — aceita qualquer sufixo numérico.
    block_pat = re.compile(
        r'(<((?:scg|sco)\d*:(?:List|Collection))\s+x:TypeArguments="AssemblyReference"[^>]*>.*?)(\n[ \t]*)(</\2>)',
        re.DOTALL,
    )
    m = block_pat.search(content)
    if not m:
        return False

    body = m.group(1)
    close_indent = m.group(3)  # newline + spaces preceding close tag
    close_tag = m.group(4)

    # Indent dos AssemblyReference: pega do primeiro existente; fallback close_indent + 2 spaces
    ref_indent_m = re.search(r"\n([ \t]*)<AssemblyReference>", body)
    if ref_indent_m:
        indent = "\n" + ref_indent_m.group(1)
    else:
        indent = close_indent + "  "

    insert = f"{indent}<AssemblyReference>{name}</AssemblyReference>"
    new_content = content[:m.start(3)] + insert + close_indent + close_tag + content[m.end():]

    if new_content == content:
        return False
    if not dry_run:
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("insert_namespace_import")
def apply_insert_namespace_import(file: Path, spec: dict, dry_run: bool = True,
                                    project_root: Path | None = None) -> bool:
    """ENV-3 fixer: insere `<x:String>NS</x:String>` dentro do bloco
    `<TextExpression.NamespacesForImplementation>` antes da close tag,
    preservando indent existente.

    spec.name = nome namespace (ex: 'System.Net').

    Idempotente: skip se namespace já presente. Sem bloco refs → no-op
    (XAML não-workflow).

    Studio 23.10 precisa imports explícitos no NamespacesForImplementation
    pra VB resolver types em assemblies forwarded chain (NetworkCredential
    via System.Net → System.Net.Primitives, etc.).
    """
    name = (spec or {}).get("name")
    if not name or not isinstance(name, str):
        return False
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name):
        return False

    content = file.read_text(encoding="utf-8-sig")

    # Idempotent: já presente
    if re.search(rf"<x:String>{re.escape(name)}</x:String>", content):
        return False

    # Match bloco NamespacesForImplementation. Studio escreve via
    # <scg:List x:TypeArguments="x:String" Capacity="N"> ... </scg:List>.
    # Bloco específico — precisa estar dentro de NamespacesForImplementation
    ns_block_pat = re.compile(
        r'(<TextExpression\.NamespacesForImplementation>.*?)'
        r'(<scg:List\s+x:TypeArguments="x:String"[^>]*>)(.*?)(\n[ \t]*)(</scg:List>)'
        r'(.*?</TextExpression\.NamespacesForImplementation>)',
        re.DOTALL,
    )
    m = ns_block_pat.search(content)
    if m:
        body = m.group(3)
        close_indent = m.group(4)

        # Indent dos x:String: pega do primeiro existente; fallback close_indent + 2 spaces
        str_indent_m = re.search(r"\n([ \t]*)<x:String>", body)
        if str_indent_m:
            indent = "\n" + str_indent_m.group(1)
        else:
            indent = close_indent + "  "

        insert = f"{indent}<x:String>{name}</x:String>"
        new_content = (
            content[:m.start(4)] + insert + close_indent
            + m.group(5) + m.group(6) + content[m.end():]
        )
    else:
        # ENV-3 fallback (audit): the scg:List wrapper shape varies (different
        # collection prefix/attr ordering, no newline before </scg:List>, etc.).
        # The detector only requires the NamespacesForImplementation block, so
        # fail-safe by inserting an <x:String> just before its close tag using
        # the same surface the detector inspects. Fail-safe: only act if the
        # block exists AND contains at least one collection wrapper (so we don't
        # inject into a malformed/empty block).
        block_re = re.compile(
            r'<TextExpression\.NamespacesForImplementation>'
            r'(?P<body>.*?)'
            r'(?P<close>\s*</TextExpression\.NamespacesForImplementation>)',
            re.DOTALL,
        )
        bm = block_re.search(content)
        if not bm:
            return False
        body = bm.group("body")
        # Indent: derive from an existing <x:String>, else default 2-space bump
        # from the close-tag indent.
        str_indent_m = re.search(r"\n([ \t]*)<x:String>", body)
        if str_indent_m:
            indent = "\n" + str_indent_m.group(1)
        else:
            close_indent_m = re.search(r'(\n[ \t]*)</TextExpression\.NamespacesForImplementation>', content)
            close_indent = close_indent_m.group(1) if close_indent_m else "\n  "
            indent = close_indent + "  "
        insert = f"{indent}<x:String>{name}</x:String>"
        # Insert before any trailing collection close + the block close.
        # Locate the last </...List>/</...Collection> close inside the block,
        # if present, to keep the new entry inside the collection; else insert
        # right before the block close tag.
        coll_close_m = None
        for cm in re.finditer(r'</[A-Za-z_][\w]*:[A-Za-z_][\w]*>', body):
            coll_close_m = cm
        if coll_close_m is not None:
            abs_pos = bm.start() + len("<TextExpression.NamespacesForImplementation>") + coll_close_m.start()
            new_content = content[:abs_pos] + insert + content[abs_pos:]
        else:
            insert_pos = bm.start("close")
            new_content = content[:insert_pos] + insert + content[insert_pos:]

    if new_content == content:
        return False
    if not dry_run:
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("strip_xml_attribute")
def apply_strip_xml_attribute(file: Path, spec: dict, dry_run: bool = True,
                               project_root: Path | None = None) -> bool:
    """D-PINALERT fixer: strip XAML attribute introduzido em versão > pin.

    spec.attribute = nome atributo (sem namespace prefix). Remove ocorrências
    `<prefix:>?<Attribute>="<value>"` mantendo whitespace mínimo. Cobre
    namespaced (`ui:Foo`) e plain (`Foo`).

    Idempotente: skip se attribute não presente.

    Casos cobertos:
        LogRetriedExceptions, RetriedExceptionsLogLevel,
        DestinationResource, PathResource (UIA 25.10.21+).

    Spec opcional:
        element : nome qualificado da activity (ex: 'uma:Office365ApplicationScope').
                  Quando presente, o strip é restrito às OPEN TAGS desse element
                  — atributos homônimos (ex: `Folder=` genérico em CreateDirectory,
                  MoveFile, mail, FTP) em activities NÃO relacionadas ficam
                  INTACTOS. Quando ausente, mantém comportamento file-wide
                  (compat legado).

    Safety: regex limita match a attribute pattern legítimo XAML — quoted
    value, palavra-completa antes do `=`. Não toca substrings.
    """
    attr = (spec or {}).get("attribute")
    if not attr:
        return False
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\-]*", attr):
        return False  # safety: nome atributo malformado

    element = (spec or {}).get("element")
    if element is not None and not re.fullmatch(
        r"[A-Za-z_][\w.\-]*(?::[A-Za-z_][\w.\-]*)?", element
    ):
        return False  # safety: nome de element malformado

    content = file.read_text(encoding="utf-8-sig")

    # Pattern: opt namespace prefix + opt dotted owner + attribute name + ="..."
    # UiPath load errors report dotted names (RetryScope.LogRetriedExceptions)
    # while the catalog keeps the reusable leaf name (LogRetriedExceptions).
    # Captura prefixed whitespace pra cleanup limpo.
    pat = re.compile(
        rf'(\s+)(?:[A-Za-z_][\w]*:)?(?:[A-Za-z_][\w]*\.)*'
        rf'{re.escape(attr)}\s*=\s*"[^"]*"'
    )

    if element:
        # Element-scoped: só remove o atributo dentro das open tags do element.
        # Evita data loss em activities homônimas (ver D-PINALERT audit Folder=).
        open_tag_re = re.compile(
            rf'<{re.escape(element)}\b[^>]*?/?>', re.DOTALL
        )
        n_total = 0

        def _strip_in_tag(mm: re.Match) -> str:
            nonlocal n_total
            tag = mm.group(0)
            new_tag, n = pat.subn("", tag)
            n_total += n
            return new_tag

        new_content = open_tag_re.sub(_strip_in_tag, content)
        n = n_total
    else:
        new_content, n = pat.subn("", content)
    if n == 0 or new_content == content:
        return False
    if not dry_run:
        # Preservar BOM se original tinha
        raw = file.read_bytes()
        prefix = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        file.write_bytes(prefix + new_content.encode("utf-8"))
    return True


@register("remove_sharepoint_2x_current_user_probe")
def apply_remove_sharepoint_2x_current_user_probe(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """SP-7: remove legacy CSOM current-user probe left by SharePoint 1.x."""
    var = (spec or {}).get("variable")
    if not var or not re.fullmatch(r"[A-Za-z_]\w*", var):
        return False
    content = file.read_text(encoding="utf-8-sig")
    original = content

    content = re.sub(
        rf'\s*<Variable\b(?=[^>]*\bx:TypeArguments="msc:User")'
        rf'(?=[^>]*\bName="{re.escape(var)}")[^>]*/>\s*',
        "\n",
        content,
        count=1,
    )
    content = re.sub(
        rf'\s*<usa:GetWebLoginUser\b'
        rf'(?=[^>]*\bSharePointUser="\[{re.escape(var)}\]")[^>]*/>\s*',
        "\n",
        content,
        count=1,
    )
    content = re.sub(
        rf'\+If\(\s*{re.escape(var)}\s+IsNot\s+Nothing,'
        rf'\s*[^]]*?{re.escape(var)}\.Email[^]]*?\)',
        "",
        content,
        count=1,
        flags=re.DOTALL,
    )
    content = re.sub(
        r'\s*<Sequence\.Variables>\s*</Sequence\.Variables>\s*',
        "\n",
        content,
        count=1,
    )

    if content == original:
        return False
    if re.search(rf"(?<![A-Za-z0-9_]){re.escape(var)}(?![A-Za-z0-9_])", content):
        return False
    if not dry_run:
        _write_preserving_bom(file, content, _file_has_bom(file))
    return True


def _has_msc_runtime_usage(content: str) -> bool:
    without_xmlns = re.sub(r'\s+xmlns:msc="[^"]+"', "", content, count=1)
    return "msc:" in without_xmlns


@register("remove_stale_csom_imports_and_refs")
def apply_remove_stale_csom_imports_and_refs(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """SP-8: remove stale Microsoft.SharePoint.Client imports/refs."""
    content = file.read_text(encoding="utf-8-sig")
    if _has_msc_runtime_usage(content):
        return False
    original = content
    content = re.sub(
        r'\s+xmlns:msc="clr-namespace:Microsoft\.SharePoint\.Client;'
        r'assembly=Microsoft\.SharePoint\.Client"',
        "",
        content,
        count=1,
    )
    content = re.sub(
        r'\s*<x:String>Microsoft\.SharePoint\.Client(?:\.Runtime)?</x:String>\s*',
        "\n",
        content,
    )
    content = re.sub(
        r'\s*<AssemblyReference>Microsoft\.SharePoint\.Client(?:\.Runtime)?'
        r'</AssemblyReference>\s*',
        "\n",
        content,
    )
    if content == original:
        return False
    if not dry_run:
        _write_preserving_bom(file, content, _file_has_bom(file))
    return True


_XAML_ATTR_RE = re.compile(r'([A-Za-z_][\w:.-]*)\s*=\s*"([^"]*)"')


def _xaml_attrs(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _XAML_ATTR_RE.finditer(text)}


def _classic_target_from_ntake(attrs: dict[str, str], body: str, indent: str) -> str:
    element = attrs.get("InUiElement")
    target_attrs: list[str] = []
    if element:
        target_attrs.append(f'Element="{element}"')
    else:
        target_match = re.search(
            r'<uix:TargetAnchorable\b(?P<attrs>[^>]*)/?>',
            body,
            flags=re.DOTALL,
        )
        if target_match:
            tattrs = _xaml_attrs(target_match.group("attrs"))
            full = tattrs.get("FullSelectorArgument")
            scope = tattrs.get("ScopeSelectorArgument")
            selector = ""
            if full and not full.startswith("["):
                selector = (scope or "") + full if scope and not scope.startswith("[") else full
            if selector:
                target_attrs.append(f'Selector="{selector}"')
            for old, new in (
                ("InformativeScreenshot", "InformativeScreenshot"),
                ("Reference", "Reference"),
                ("ContentHash", "ContentHash"),
            ):
                if old in tattrs:
                    target_attrs.append(f'{new}="{tattrs[old]}"')
    if not target_attrs:
        return ""
    inner = indent + "  "
    return (
        ">\n"
        f"{inner}<ui:TakeScreenshot.Target>\n"
        f"{inner}  <ui:Target {' '.join(target_attrs)} />\n"
        f"{inner}</ui:TakeScreenshot.Target>\n"
        f"{indent}</ui:TakeScreenshot>"
    )


def _rewrite_ntake_match(match: re.Match) -> str:
    indent = match.group("indent") or ""
    attrs = _xaml_attrs(match.group("attrs") or "")
    body = match.groupdict().get("body") or ""
    keep: list[str] = []
    for attr in (
        "DisplayName",
        "sap:VirtualizedContainerService.HintSize",
        "sap2010:WorkflowViewState.IdRef",
        "ContinueOnError",
    ):
        if attr in attrs:
            keep.append(f'{attr}="{attrs[attr]}"')
    if attrs.get("OutImage"):
        keep.append(f'Screenshot="{attrs["OutImage"]}"')
    keep.append('WaitBefore="{x:Null}"')
    target = _classic_target_from_ntake(attrs, body, indent)
    open_tag = f"{indent}<ui:TakeScreenshot {' '.join(keep)}"
    if target:
        return open_tag + target
    return open_tag + " />"


@register("rewrite_ntake_screenshot_to_classic")
def apply_rewrite_ntake_screenshot_to_classic(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """D-PINALERT: downgrade UIA Next NTakeScreenshot to classic screenshot."""
    content = file.read_text(encoding="utf-8-sig")
    original = content
    pair_re = re.compile(
        r'(?P<indent>[ \t]*)<uix:NTakeScreenshot(?!\.)\b'
        r'(?P<attrs>[^>]*?)(?<!/)>(?P<body>.*?)</uix:NTakeScreenshot>',
        flags=re.DOTALL,
    )
    self_re = re.compile(
        r'(?P<indent>[ \t]*)<uix:NTakeScreenshot(?!\.)\b'
        r'(?P<attrs>[^>]*)/>',
        flags=re.DOTALL,
    )
    content = pair_re.sub(_rewrite_ntake_match, content)
    content = self_re.sub(_rewrite_ntake_match, content)
    if content == original:
        return False
    if not dry_run:
        _write_preserving_bom(file, content, _file_has_bom(file))
    return True


@register("normalize_visualbasic_settings")
def apply_normalize_visualbasic_settings(
    file: Path,
    spec: dict,
    dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """ENV-4 fixer: normalize legacy `<mva:VisualBasic.Settings>text</...>`
    para canonical `<VisualBasic.Settings><x:Null /></VisualBasic.Settings>`.

    ROOT CAUSE BC30652/BC31424 (isolated 2026-05-22): text-content em
    `<mva:VisualBasic.Settings>` ativa VB compiler resolução legacy mode →
    Dictionary/NetworkCredential resolvem via facades v4 → mismatch com
    forwarders v6. `<x:Null />` = modern empty marker → default .NET 6
    resolver → BC clears. Studio "Import References" valida mecanismo.

    Cobre:
      - Forma A: `<mva:VisualBasic.Settings>...text...</mva:VisualBasic.Settings>`
      - Forma B: `<mva:VisualBasic.Settings />` (self-closing)

    Pós-replace, se `xmlns:mva="...System.Activities"` não tem outras
    referências `mva:` no body, drop attribute do root.

    Idempotente: skip se já normalizado.

    Safety:
      - Preserva BOM original (Studio padrão).
      - Não toca instances dentro de `<!-- -->` (regex padrão não match).
      - mva: usage check é case-sensitive, conservador (preserva xmlns se
        qualquer mva: ocorre — ex: `mva:VisualBasicValue`).
    """
    had_bom = _file_has_bom(file)
    content = file.read_text(encoding="utf-8-sig")

    # ENV-4 (audit): leading newline+indent capture is OPTIONAL so a settings
    # element NOT at line-start (e.g. inline after a sibling on the same line)
    # still normalizes. When absent, the replacement derives indent defensively
    # and omits the leading newline.
    pat_text = re.compile(
        r"(?:(\n)([ \t]*))?<mva:VisualBasic\.Settings>[^<]*</mva:VisualBasic\.Settings>"
    )
    pat_self_closing = re.compile(
        r"(?:(\n)([ \t]*))?<mva:VisualBasic\.Settings\s*/>"
    )

    def _canonical_replacement(m: "re.Match[str]") -> str:
        nl = m.group(1)  # "\n" when at line-start, else None
        indent = m.group(2) or ""
        leading = (nl + indent) if nl is not None else ""
        child_indent = indent + "  "
        if nl is not None:
            return (
                f"{leading}<VisualBasic.Settings>"
                f"\n{child_indent}<x:Null />"
                f"\n{indent}</VisualBasic.Settings>"
            )
        # Not at line-start: keep it compact (no synthetic leading newline that
        # would shift a sibling onto its own malformed indent).
        return "<VisualBasic.Settings><x:Null /></VisualBasic.Settings>"

    new_content, n1 = pat_text.subn(_canonical_replacement, content)
    new_content, n2 = pat_self_closing.subn(_canonical_replacement, new_content)

    if n1 + n2 == 0:
        return False

    # Drop `xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;..."` se
    # mva: prefix não usado em outros lugares (após replacement).
    candidate = re.sub(
        r"\s+xmlns:mva\s*=\s*\"clr-namespace:Microsoft\.VisualBasic\.Activities[^\"]*\"",
        "",
        new_content,
        count=1,
    )
    if candidate != new_content and not re.search(r"\bmva:", candidate):
        new_content = candidate

    if not dry_run:
        _write_preserving_bom(file, new_content, had_bom)
    return True


@register("strip_assembly_reference")
def apply_strip_assembly_reference(file: Path, spec: dict, dry_run: bool = True,
                                    project_root: Path | None = None) -> bool:
    """W-26 fixer: remove `<AssemblyReference>X</AssemblyReference>` line do
    bloco refs. Complementa `insert_assembly_reference` (W-11g et al).

    spec.name = nome do assembly (string simples, sem version/culture).

    Idempotente: skip se ref já ausente.

    Safety:
      - Validate name pattern (sem espaços/aspas).
      - Match exato `<AssemblyReference>NAME</AssemblyReference>` precedido
        de newline+indent — remove linha inteira atomicamente.
      - Preserva BOM original.
      - Não toca AssemblyReference em comentários (regex padrão XML não
        match dentro de `<!-- -->`).
    """
    name = (spec or {}).get("name")
    if not name or not isinstance(name, str):
        return False
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\-]*", name):
        return False

    raw = file.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        bom = b"\xef\xbb\xbf"
        content_bytes = raw[3:]
    else:
        bom = b""
        content_bytes = raw
    content = content_bytes.decode("utf-8")

    # Match leading newline + indent + tag (com ou sem trailing whitespace).
    # Remove a linha inteira atomicamente preservando o newline da próxima ref.
    pat = re.compile(
        rf"\n[ \t]*<AssemblyReference>{re.escape(name)}</AssemblyReference>"
    )
    new_content, n = pat.subn("", content, count=1)
    if n == 0 or new_content == content:
        return False
    if not dry_run:
        file.write_bytes(bom + new_content.encode("utf-8"))
    return True


@register("rename_element")
def apply_rename_element(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """Generic fixer: rename activity local name em todas 4 formas:
       <prefix:OldLocal ...>       → <prefix:NewLocal ...>
       <prefix:OldLocal .../>      → <prefix:NewLocal .../>
       </prefix:OldLocal>          → </prefix:NewLocal>
       <prefix:OldLocal.Foo>...    → <prefix:NewLocal.Foo>...
       </prefix:OldLocal.Foo>      → </prefix:NewLocal.Foo>

    Spec:
      prefix:    xmlns prefix (ex: 'ui')
      old_local: nome local atual (ex: 'HashText')
      new_local: nome local novo (ex: 'KeyedHashText')

    Safety:
      - Idempotente: skip se old_local não presente OU já renomeado.
      - Whitelist regex chars (letras/dígitos/_).
      - Word-boundary: NÃO match `<ui:HashTextExtended>` quando renomeando
        HashText.
      - Preserva BOM.
      - Args (attrs) preservados inteiramente — só nome muda.
    """
    prefix = (spec or {}).get("prefix") or ""
    old_local = (spec or {}).get("old_local") or ""
    new_local = (spec or {}).get("new_local") or ""
    if not all([prefix, old_local, new_local]) or old_local == new_local:
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", prefix):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w]*", old_local):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w]*", new_local):
        return False

    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    content = raw.decode("utf-8-sig")

    p = re.escape(prefix)
    ol = re.escape(old_local)
    # Open: `<prefix:OldLocal` seguido por space, `/`, ou `>` (word boundary)
    open_re = re.compile(rf'<{p}:{ol}(?=[\s/>.])')
    # Close: `</prefix:OldLocal>` ou property close `</prefix:OldLocal.Foo>`
    close_re = re.compile(rf'</{p}:{ol}(?=[.>])')

    new_content, n_open = open_re.subn(f'<{prefix}:{new_local}', content)
    new_content, n_close = close_re.subn(f'</{prefix}:{new_local}', new_content)
    if (n_open + n_close) == 0 or new_content == content:
        return False
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_content.encode("utf-8")
        file.write_bytes(out)
    return True


@register("force_attribute_in_activity_with_guard")
def apply_force_attribute_in_activity_with_guard(
    file: Path, spec: dict, dry_run: bool = True
) -> bool:
    """UI-7 fixer: force attr=value DENTRO de activity guardada por outro attr.

    Spec (per-finding):
      prefix:          xmlns prefix da activity (ex: 'uix')
      activity_local:  nome local (ex: 'NTypeInto')
      guard_attr:      attr usado pra match scope (ex: 'InteractionMode')
      guard_value:     valor exato do guard (ex: 'Simulate')
      attr_name:       attr alvo a forçar (ex: 'DelayBefore')
      target_value:    valor final (ex: '0')
      tag_line:        linha 1-based (informativo; fixer scaneia tudo)

    Logic:
      1. Encontra todos open-tags `<prefix:local ...>`
      2. Para cada, verifica se contém `guard_attr="guard_value"` exato
      3. Se sim: replace `attr_name="..."` por `attr_name="target_value"` OU
         adiciona o attr se ausente
      4. Skip tags sem guard match — protege outras activities (HardwareEvents,
         ChromiumAPI, etc.) de pollution

    Safety:
      - Idempotente: skip se attr já = target_value.
      - Scope-strict: guard impede polluir activities diferentes mesmo
        com mesmo (prefix, local).
      - Whitelist regex chars em todos campos.
      - Preserva BOM, self-close marker.
    """
    prefix = (spec or {}).get("prefix") or ""
    local = (spec or {}).get("activity_local") or ""
    guard_attr = (spec or {}).get("guard_attr") or ""
    guard_value = (spec or {}).get("guard_value")
    attr = (spec or {}).get("attr_name") or ""
    target = (spec or {}).get("target_value")
    if not all([prefix, local, guard_attr, attr]) or guard_value is None or target is None:
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", prefix):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", local):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w]*", guard_attr):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w]*", attr):
        return False

    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    content = raw.decode("utf-8-sig")

    tag_open_re = re.compile(
        rf'<{re.escape(prefix)}:{re.escape(local)}\b([^>]*?)(/?>)'
    )
    guard_re = re.compile(
        rf'\b{re.escape(guard_attr)}="{re.escape(str(guard_value))}"'
    )
    attr_re = re.compile(rf'(\s){re.escape(attr)}="([^"]*)"')

    changed = False
    target_str = str(target)

    def _patch_tag(m: re.Match) -> str:
        nonlocal changed
        attrs_blob = m.group(1)
        closer = m.group(2)
        # Skip se guard não match — protege scope
        if not guard_re.search(attrs_blob):
            return m.group(0)
        existing = attr_re.search(attrs_blob)
        if existing:
            if existing.group(2) == target_str:
                return m.group(0)  # idempotent
            new_blob = attr_re.sub(rf'\1{attr}="{target_str}"', attrs_blob, count=1)
        else:
            sep = "" if (attrs_blob == "" or attrs_blob.endswith(" ")) else " "
            new_blob = f'{attrs_blob}{sep}{attr}="{target_str}"'
        if new_blob == attrs_blob:
            return m.group(0)
        changed = True
        return f'<{prefix}:{local}{new_blob}{closer}'

    new_content = tag_open_re.sub(_patch_tag, content)
    if not changed or new_content == content:
        return False
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_content.encode("utf-8")
        file.write_bytes(out)
    return True


@register("xmlns_declare")
def apply_xmlns_declare(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """M-6 fixer: adiciona `xmlns:<prefix>="<uri>"` no <Activity> root.

    Spec (per-finding, emitido por detect_m6_xmlns_missing):
      prefix:    xmlns prefix (ex: 'ui')
      xmlns_uri: URI canônica resolvida via schema (ex:
                 'http://schemas.uipath.com/workflow/activities')

    Safety:
      - Idempotente: skip se xmlns:<prefix> já declarado em qualquer tag.
      - Inject único: somente no PRIMEIRO `<Activity ...>` (root).
      - Não toca xmlns existentes nem reordena atributos.
      - Whitelist prefix chars (letras/dígitos/_) — evita injection em regex.
      - Preserva BOM.
      - Não declara dependência em project.json — se assembly faltar,
        S-11 dispara como finding separado (escopo fora de M-6).
    """
    prefix = (spec or {}).get("prefix") or ""
    xmlns_uri = (spec or {}).get("xmlns_uri") or ""
    if not prefix or not xmlns_uri:
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", prefix):
        return False
    # URI sanity: sem quotes/newlines que quebrariam o XML.
    if '"' in xmlns_uri or "\n" in xmlns_uri or "\r" in xmlns_uri:
        return False

    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    content = raw.decode("utf-8-sig")

    # Idempotente: se já existe declaração xmlns:<prefix>="..." em qualquer
    # parte do arquivo (mais comum: root), skip.
    if re.search(rf'\bxmlns:{re.escape(prefix)}\s*=\s*"', content):
        return False

    # Inject no PRIMEIRO open-tag de <Activity ...>. Match não-greedy do attrs
    # blob até o `>` final (ou `/>` em raros casos de Activity vazio).
    root_re = re.compile(r'(<Activity\b)([^>]*?)(/?>)', flags=re.DOTALL)
    m = root_re.search(content)
    if m is None:
        return False
    head, attrs_blob, closer = m.group(1), m.group(2), m.group(3)
    # Determina indent: usa newline+spaces se attrs_blob multi-line, senão space.
    if "\n" in attrs_blob:
        # mesma indent dos xmlns existentes — procura padrão `\n<spaces>xmlns:`
        indent_match = re.search(r'\n([ \t]+)xmlns:', attrs_blob)
        sep = f'\n{indent_match.group(1)}' if indent_match else "\n          "
    else:
        sep = " "
    new_attrs = f'{attrs_blob}{sep}xmlns:{prefix}="{xmlns_uri}"'
    new_content = content[:m.start()] + head + new_attrs + closer + content[m.end():]
    if new_content == content:
        return False
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_content.encode("utf-8")
        file.write_bytes(out)
    return True


@register("strip_redundant_default")
def apply_strip_redundant_default(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """M-7 fixer: remove `attr="<value>"` quando valor == schema default.

    Spec (per-finding, emitido por detect_m7_redundant_default):
      prefix:         xmlns prefix da activity (ex: 'ui')
      activity_local: nome local (ex: 'WriteRange')
      attr_name:      arg redundante (ex: 'StartingCell')
      expected_value: valor exato emitido pelo detector (ex: 'A1')
      tag_line:       linha 1-based do open-tag

    Safety:
      - Scope: replace acontece SOMENTE dentro do open-tag de uma activity
        específica (prefix:local) + match exato (attr, value).
      - Idempotente: skip se attr já ausente OU valor != expected.
      - Whole-word match em attr_name (não match em substring).
      - Não toca outros atributos.
      - Preserva BOM.
    """
    prefix = (spec or {}).get("prefix") or ""
    local = (spec or {}).get("activity_local") or ""
    attr = (spec or {}).get("attr_name") or ""
    expected_value = (spec or {}).get("expected_value")
    if not all([prefix, local, attr]) or expected_value is None:
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", prefix):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", local):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w]*", attr):
        return False

    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    content = raw.decode("utf-8-sig")

    tag_open_re = re.compile(
        rf'<{re.escape(prefix)}:{re.escape(local)}\b([^>]*?)(/?>)'
    )
    # Strip ` attr="expected_value"` (leading space removed too, idempotent
    # space cleanup). re.escape escapa eventuais `<`, `&`, etc no valor.
    attr_re = re.compile(
        rf'(\s+){re.escape(attr)}="{re.escape(str(expected_value))}"'
    )

    changed = False

    def _patch_tag(m: re.Match) -> str:
        nonlocal changed
        attrs_blob = m.group(1)
        closer = m.group(2)
        new_blob, n = attr_re.subn("", attrs_blob)
        if n > 0 and new_blob != attrs_blob:
            changed = True
            return f'<{prefix}:{local}{new_blob}{closer}'
        return m.group(0)

    new_content = tag_open_re.sub(_patch_tag, content)
    if not changed or new_content == content:
        return False
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_content.encode("utf-8")
        file.write_bytes(out)
    return True


@register("replace_nothing_value_type")
def apply_replace_nothing_value_type(file: Path, spec: dict, dry_run: bool = True) -> bool:
    """M-8 fixer: substitui `attr="[Nothing]"` por default VB do tipo de valor.

    Spec (per-finding, emitido por detect_m8_nothing_in_value_type):
      prefix:          xmlns prefix da activity (ex: 'ui')
      activity_local:  nome local (ex: 'WriteRange')
      attr_name:       arg do tipo valor (ex: 'AddHeaders')
      tag_line:        linha 1-based do open-tag no XAML
      default_expr:    VB bind expression substituta (ex: '[False]', '[0]')

    Safety:
      - Scope: replace acontece dentro do open-tag de uma activity específica
        (delimitado por `<prefix:Local` até `>` ou `/>`).
      - Idempotente: skip se attr já não é `[Nothing]`.
      - Whole-word match em attr_name (não match em substring).
      - Preserva BOM.
      - Não toca outros atributos da mesma tag nem outras tags.
    """
    prefix = (spec or {}).get("prefix") or ""
    local = (spec or {}).get("activity_local") or ""
    attr = (spec or {}).get("attr_name") or ""
    default_expr = (spec or {}).get("default_expr") or ""
    if not all([prefix, local, attr, default_expr]):
        return False
    # Whitelist chars pra evitar injection em regex
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", prefix):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", local):
        return False
    if not re.fullmatch(r"[A-Za-z_][\w]*", attr):
        return False

    raw = file.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    content = raw.decode("utf-8-sig")

    # Match open-tag completo: <prefix:Local ...> ou <prefix:Local .../>
    # Captura conteúdo entre `<prefix:Local` e o `>` final do open-tag.
    # Não-greedy + lookahead pra parar no primeiro `>` que não esteja dentro
    # de attr quoted value.
    tag_open_re = re.compile(
        rf'<{re.escape(prefix)}:{re.escape(local)}\b([^>]*?)(/?>)'
    )

    nothing_re = re.compile(
        rf'(\s){re.escape(attr)}="\s*\[\s*Nothing\s*\]\s*"',
        flags=re.IGNORECASE,
    )

    changed = False

    def _patch_tag(m: re.Match) -> str:
        nonlocal changed
        attrs_blob = m.group(1)
        closer = m.group(2)
        new_blob, n = nothing_re.subn(rf'\1{attr}="{default_expr}"', attrs_blob)
        if n > 0 and new_blob != attrs_blob:
            changed = True
            return f'<{prefix}:{local}{new_blob}{closer}'
        return m.group(0)

    new_content = tag_open_re.sub(_patch_tag, content)
    if not changed or new_content == content:
        return False
    if not dry_run:
        out = (b"\xef\xbb\xbf" if bom else b"") + new_content.encode("utf-8")
        file.write_bytes(out)
    return True


_PROPELEM_HYBRID_RE = re.compile(
    r'<(?P<elem>[A-Za-z_][\w]*:[A-Za-z_][\w]*\.[A-Za-z_][\w]*)'
    r'(?P<attrs>(?:\s+[A-Za-z_][\w:]*="[^"]*")+)\s*>'
    r'(?P<inner>.*?)'
    r'</(?P=elem)\s*>',
    re.DOTALL,
)


_HOSTILE_UNICODE_MAP = {
    "“": "&quot;",   # LEFT DOUBLE QUOTATION MARK
    "”": "&quot;",   # RIGHT DOUBLE QUOTATION MARK
    "‘": "&apos;",   # LEFT SINGLE QUOTATION MARK
    "’": "&apos;",   # RIGHT SINGLE QUOTATION MARK
    " ": " ",        # NBSP → space
    "​": "",         # ZERO WIDTH SPACE
    "‌": "",         # ZERO WIDTH NON-JOINER
    "‍": "",         # ZERO WIDTH JOINER
}


@register("replace_hostile_unicode_chars")
def apply_replace_hostile_unicode_chars(
    file: Path, spec: dict, dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """W-30 fixer: replace HARD hostile Unicode chars por ASCII equivalent.

    Catalog (sempre wrong em VB Roslyn .NET 6 runtime):
      U+201C/U+201D smart-double-quote → &quot;
      U+2018/U+2019 smart-single-quote → &apos;
      U+00A0 NBSP → space
      U+200B/C/D zero-width → strip
      U+FEFF zero-width no-break (mid-file BOM) → strip

    Preserva BOM original do file (pos 0). Strip apenas U+FEFF interno.

    Idempotente: skip se nenhum char hostil.

    Scope guard (W-30 audit): NÃO muta texto dentro de attribute values
    user-facing — `DisplayName`, `Annotation`, `AnnotationText` e
    `sap2010:Annotation*` (incl. `sap2010:Annotation.AnnotationText`). Smart
    quotes (curly) são legítimas nesses textos exibidos/logados; reescrevê-las
    pra &quot;/&apos; é perda silenciosa de dado user-facing. Normalização HARD
    aplica somente fora desses spans (expressões VB, código, etc.).

    Safety: XML well-formedness validada pós-write.
    """
    bom = _file_has_bom(file)
    content = file.read_text(encoding="utf-8-sig")

    # Compute protected spans = attribute values of user-facing attributes that
    # must keep their original (possibly smart-quoted) text. Match the attribute
    # NAME (whole-word, optional namespace prefix) followed by ="...". We protect
    # the VALUE region (chars between the quotes) only.
    _PROTECTED_ATTR_RE = re.compile(
        r'(?:[A-Za-z_][\w]*:)?'
        r'(?:DisplayName|AnnotationText|Annotation)\s*=\s*"([^"]*)"'
    )
    protected: list[tuple[int, int]] = [
        (m.start(1), m.end(1)) for m in _PROTECTED_ATTR_RE.finditer(content)
    ]

    def _in_protected(idx: int) -> bool:
        for s, e in protected:
            if s <= idx < e:
                return True
        return False

    # Build the new content char-by-char span-wise: apply replacements only to
    # the non-protected regions; copy protected regions verbatim.
    _SUBST_MAP = dict(_HOSTILE_UNICODE_MAP)
    _SUBST_MAP["﻿"] = ""  # mid-file BOM strip (folded into same pass)

    out: list[str] = []
    for i, ch in enumerate(content):
        if ch in _SUBST_MAP and not _in_protected(i):
            out.append(_SUBST_MAP[ch])
        else:
            out.append(ch)
    new_content = "".join(out)

    if new_content == content:
        return False
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(new_content)
    except ET.ParseError:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, bom)
    return True


@register("strip_property_element_with_attribute")
def apply_strip_property_element_with_attribute(
    file: Path, spec: dict, dry_run: bool = True,
    project_root: Path | None = None,
) -> bool:
    """X-2 fixer: cleanup pos-Migrator regression.

    Pattern: `<NS:Activity.Prop Attr="v">...</NS:Activity.Prop>` (property
    element c/ attribute = XAML invalido).

    Estrategia:
      A. Se parent activity (`<NS:Activity ... Attr="v" ...>` anterior)
         ja tem `Attr="v"` inline => remove o bloco property element
         inteiro (redundante).
      B. Senao => strip apenas a(s) attribute(s) da tag de abertura do
         property element. Preserva inner content.

    Spec opcional: `{'elem': 'ui:LogMessage.Level'}` restringe target.
    """
    target_elem = (spec or {}).get("elem")
    bom = _file_has_bom(file)
    content = file.read_text(encoding="utf-8-sig")
    changed = False
    out_parts: list[str] = []
    last = 0
    for m in _PROPELEM_HYBRID_RE.finditer(content):
        elem = m.group("elem")
        if target_elem and elem != target_elem:
            continue
        attrs_blob = m.group("attrs")
        inner = m.group("inner")
        if "." not in elem:
            continue
        parent_act, prop = elem.rsplit(".", 1)
        # Keep fixer scope identical to X-2 detector: only Migrator's invalid
        # hybrid shape, where the property element carries an attribute with the
        # same local-name as the property (`<ui:LogMessage.Level Level="...">`).
        # Generic property elements with directive attrs (`x:TypeArguments`,
        # `x:Key`, `xml:space`) are intentionally out of scope.
        if not re.search(rf'\s{re.escape(prop)}\s*=\s*"', attrs_blob):
            continue
        before = content[:m.start()]
        parent_open_re = re.compile(rf'<{re.escape(parent_act)}\b[^>]*?>')
        parent_opens = list(parent_open_re.finditer(before))
        parent_has_inline = False
        if parent_opens:
            last_open = parent_opens[-1].group(0)
            if re.search(rf'\b{re.escape(prop)}\s*=\s*"', last_open):
                parent_has_inline = True
        out_parts.append(content[last:m.start()])
        if parent_has_inline:
            tail_ws = re.search(r'[ \t]*\n?[ \t]*$', out_parts[-1])
            if tail_ws and tail_ws.group(0):
                out_parts[-1] = out_parts[-1][: -len(tail_ws.group(0))]
        else:
            # Case B: strip only the redundant activity-property attributes,
            # PRESERVING XAML directive attributes (x:/xml:-prefixed) such as
            # x:TypeArguments / x:Key. Dropping x:TypeArguments off a generic
            # property element (e.g. <scg:List.Items x:TypeArguments="x:String">)
            # produces well-formed-but-broken XAML that the ET.fromstring gate
            # cannot catch (X-2 audit).
            directive_attrs = "".join(
                am.group(0)
                for am in re.finditer(
                    r'\s+(?:x|xml):[A-Za-z_][\w]*="[^"]*"', attrs_blob
                )
            )
            out_parts.append(f'<{elem}{directive_attrs}>{inner}</{elem}>')
        last = m.end()
        changed = True
    if not changed:
        return False
    out_parts.append(content[last:])
    new_content = "".join(out_parts)
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(new_content)
    except ET.ParseError:
        return False
    if not dry_run:
        _write_preserving_bom(file, new_content, bom)
    return True


# Phase 9E: inject missing arg declaration in <x:Members> block.
# Pre-resolved type passed em spec; inference já feita upstream pelo
# runtime_loadtest gate. Fixer = pure write-time mecânico.
_MEMBERS_CLOSE_RE = re.compile(r"</x:Members>")
_MEMBERS_OPEN_RE = re.compile(r"<x:Members\s*>")
_ACTIVITY_OPEN_RE = re.compile(r"<Activity\b[^>]*?>", re.DOTALL)


@register("inject_missing_args")
def apply_inject_missing_args(file: Path, spec: dict[str, Any], dry_run: bool = True,
                                project_root: Path | None = None) -> bool:
    """Phase 9E fixer: inject missing `<x:Property Name="X" Type="Y"/>` em
    <x:Members> block.

    Spec (emitido por runtime_loadtest._parse_output após 3-layer inference):
      arg_name      : nome do arg (ex: 'in_Config')
      inferred_type : tipo wrapped (ex: 'InArgument(scg:Dictionary(...))')
      source        : 'canonical' | 'invocation_xref' | 'hungarian' (debug)

    Algoritmo (raw-string surgical edit pra preservar 100% format XAML
    incluindo namespace prefixes — ET.write não preserva ns0/ns1):

      1. Read file (preserve BOM).
      2. Idempotência: se `<x:Property Name="<arg>"` já existe no Members,
         skip silencioso (no-op).
      3. Se <x:Members> tag existe: insert <x:Property/> antes do </x:Members>,
         preservando indent.
      4. Se <x:Members> ausente: cria block + property após root <Activity ...>
         open tag. Raro pra workflows reais (Studio sempre emite block, mesmo
         vazio — ver rule S-1 self-close `<x:Members/>`).

    Safety:
      - Idempotente: re-run não duplica property.
      - Preserva BOM.
      - Sanitiza arg_name/inferred_type contra XML injection (whitelist chars).
      - Post-write é validado por apply_with_gate → XML well-form gate +
        VB orphan gate. Se invalid, rollback automático.
    """
    if not isinstance(spec, dict):
        return False
    arg_name = (spec.get("arg_name") or "").strip()
    inferred_type = (spec.get("inferred_type") or "").strip()
    if not arg_name or not inferred_type:
        return False
    # Whitelist arg_name: identifier ASCII. UiPath Members aceita basicamente
    # qualquer identifier VB válido, mas Sicoob padrão é ASCII puro.
    if not re.fullmatch(r"[A-Za-z_][\w]*", arg_name):
        return False
    # inferred_type pode conter `(`, `)`, `:`, `,`, espaços, `[`, `]`, ponto.
    # Bloqueia chars que quebram XML attribute (<, >, ", &, control chars).
    if any(c in inferred_type for c in '"<>&\n\r\t'):
        return False

    if not file.exists():
        return False

    had_bom = _file_has_bom(file)
    content = file.read_text(encoding="utf-8-sig")

    # Idempotência: já declarado?
    # Match `<x:Property ... Name="<arg>" ...` em qualquer atributo-position.
    # Tolera prefixos como `sap2010:Annotation.AnnotationText="..."` ou ordem
    # arbitrária (Name antes/depois de Type). Single regex cobre todas as
    # variações Studio emite. Regression test: pilot contestacao-de-compras
    # (5/27) — `\b` trailing falhava em property annotada porque `"` e ` `
    # ambos não-word chars não formam word boundary. Fix: terminator literal
    # `"` já garante match exato; word boundary trailing era redundante e
    # incorreto. Apenas `\b` LEADING permanece pra impedir match em prefixo
    # (`SomeOtherName="X"` ≠ `Name="X"`).
    if re.search(rf'<x:Property\s+[^>]*\bName="{re.escape(arg_name)}"', content):
        return False

    # Build new property line. Single-line, self-closed.
    new_prop = f'<x:Property Name="{arg_name}" Type="{inferred_type}" />'

    # Path 1: <x:Members>...</x:Members> exists.
    members_close = _MEMBERS_CLOSE_RE.search(content)
    if members_close is not None:
        # Find indent from existing property line se houver; senão, herda do
        # bloco. Default 4-space indent (Sicoob padrão Studio).
        # Look from <x:Members> open backwards/forwards pra encontrar indent.
        members_open = _MEMBERS_OPEN_RE.search(content)
        existing_prop = re.search(
            r"(\n[ \t]*)<x:Property\b", content[:members_close.start()],
        )
        if existing_prop:
            indent = existing_prop.group(1)
        elif members_open:
            # Indent do <x:Members> + 2 spaces
            members_line_start = content.rfind("\n", 0, members_open.start()) + 1
            members_indent = content[members_line_start:members_open.start()]
            indent = "\n" + members_indent + "  "
        else:
            indent = "\n    "

        # Insert antes do </x:Members>. Encontra linha-início da close tag pra
        # preservar indent original da close.
        close_line_start = content.rfind("\n", 0, members_close.start())
        if close_line_start == -1:
            insert_pos = members_close.start()
            new_content = (
                content[:insert_pos]
                + indent.lstrip("\n") + new_prop + "\n"
                + content[insert_pos:]
            )
        else:
            # insert: <indent><new_prop> antes do `\n<close_indent></x:Members>`
            insert_pos = close_line_start
            new_content = (
                content[:insert_pos]
                + indent + new_prop
                + content[insert_pos:]
            )
    else:
        # Path 2: no <x:Members> block. Inject `<x:Members>...<Property/>...</x:Members>`
        # após root <Activity ...> open tag.
        activity_open = _ACTIVITY_OPEN_RE.search(content)
        if activity_open is None:
            return False
        # Determine indent: 2 spaces após `\n` da root.
        insert_pos = activity_open.end()
        # Heuristic indent: 2 spaces (Sicoob/Studio default p/ Members)
        block = (
            "\n  <x:Members>"
            f"\n    {new_prop}"
            "\n  </x:Members>"
        )
        new_content = content[:insert_pos] + block + content[insert_pos:]

    if new_content == content:
        return False

    # Pre-flight XML well-form gate antes de write. apply_with_gate faz outro
    # check, mas validar local previne write inútil em casos malformados.
    try:
        import xml.etree.ElementTree as _ET
        _ET.fromstring(new_content)
    except _ET.ParseError:
        return False

    if not dry_run:
        _write_preserving_bom(file, new_content, had_bom)
    return True
