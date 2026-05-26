#!/usr/bin/env python3
"""xaml_summary.py — compact structural summary of a UiPath XAML file.

Purpose: reduce token cost when Claude (or a human) needs to understand a
workflow without reading the whole verbose XML. Emits arguments, variables,
imports, invoked workflows, and the activity tree with DisplayNames and line
numbers.

Usage:
    python xaml_summary.py <file.xaml>
    python xaml_summary.py <file.xaml> --tree-depth 5
    python xaml_summary.py <file.xaml> --no-tree        # skeleton only
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

NS = {
    "x": "http://schemas.microsoft.com/winfx/2006/xaml",
    "ui": "http://schemas.uipath.com/workflow/activities",
    "sap": "http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation",
    "sap2010": "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation",
    "scg": "clr-namespace:System.Collections.Generic;assembly=mscorlib",
    "mva": "clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities",
}

# Noise tags to skip when rendering tree
_SKIP_TAGS = {
    "VirtualizedContainerService.HintSize",
    "WorkflowViewState.IdRef",
    "VisualBasic.Settings",
    "TextExpression.NamespacesForImplementation",
    "TextExpression.ReferencesForImplementation",
    "Annotation.AnnotationText",
    # Designer view-state data (positions, flags) — not real activities
    "Dictionary",
    "Point",
    "PointCollection",
    "Size",
    "Boolean",
    "Int32",
    "Double",
    "String",
    "Reference",
    "Variable",
    "OutArgument",
    "InArgument",
    "InOutArgument",
}

_TAG_RE = re.compile(r"^\{(?P<uri>[^}]+)\}(?P<name>.+)$")


def _strip_ns(tag: str) -> tuple[str, str]:
    """Return (prefix, localname) for an ET tag with namespace."""
    m = _TAG_RE.match(tag)
    if not m:
        return ("", tag)
    uri, name = m.group("uri"), m.group("name")
    if uri == NS["ui"]:
        return ("ui", name)
    if uri == NS["x"]:
        return ("x", name)
    if uri.startswith("http://schemas.microsoft.com/netfx/"):
        # sap / default activities ns
        if "presentation" in uri:
            return ("sap", name)
        return ("", name)
    if uri.startswith("clr-namespace:"):
        # use module prefix if recognizable, else raw
        for prefix, full in NS.items():
            if full == uri:
                return (prefix, name)
        return ("ns", name)
    return ("", name)


def _build_line_index(raw: str) -> dict[str, int]:
    """Map '<prefix:Tag ... sap2010:WorkflowViewState.IdRef="id">' to line num.

    Not every element has an IdRef. For those without, we fall back to a
    (DisplayName, nth-occurrence) lookup done at render time.
    """
    idx: dict[str, int] = {}
    for i, line in enumerate(raw.splitlines(), start=1):
        m = re.search(r'WorkflowViewState\.IdRef="([^"]+)"', line)
        if m:
            idx.setdefault(m.group(1), i)
    return idx


def _display_name_line_map(raw: str) -> dict[str, list[int]]:
    """Map DisplayName -> [line numbers] in document order."""
    out: dict[str, list[int]] = {}
    for i, line in enumerate(raw.splitlines(), start=1):
        for m in re.finditer(r'DisplayName="([^"]*)"', line):
            out.setdefault(m.group(1), []).append(i)
    return out


def _extract_arguments(root: ET.Element) -> list[tuple[str, str, str]]:
    """Return list of (name, direction, type) from <x:Members>."""
    members = root.find("x:Members", NS)
    if members is None:
        return []
    out = []
    for prop in members.findall("x:Property", NS):
        name = prop.get("Name", "?")
        type_ = prop.get("Type", "?")
        # Type looks like "InArgument(x:String)" / "OutArgument(...)" / "InOutArgument(...)"
        direction = "?"
        if type_.startswith("InArgument"):
            direction = "In"
        elif type_.startswith("OutArgument"):
            direction = "Out"
        elif type_.startswith("InOutArgument"):
            direction = "InOut"
        out.append((name, direction, type_))
    return out


def _extract_imports(root: ET.Element) -> list[str]:
    namespaces_elem = root.find(".//{*}NamespacesForImplementation", NS)
    # Fallback: search in any namespace
    if namespaces_elem is None:
        for el in root.iter():
            _, name = _strip_ns(el.tag)
            if name == "NamespacesForImplementation":
                namespaces_elem = el
                break
    if namespaces_elem is None:
        return []
    out = []
    for el in namespaces_elem.iter():
        _, name = _strip_ns(el.tag)
        if name == "String" and el.text:
            out.append(el.text.strip())
    return out


def _extract_invoked_workflows(root: ET.Element, raw: str) -> list[tuple[str, int]]:
    """Find InvokeWorkflowFile WorkflowFileName values + line numbers."""
    results: list[tuple[str, int]] = []
    for i, line in enumerate(raw.splitlines(), start=1):
        for m in re.finditer(r'WorkflowFileName="([^"]+)"', line):
            results.append((m.group(1), i))
    return results


def _walk_variables(root: ET.Element) -> list[tuple[str, str, str]]:
    """Find <Variable Name=... TypeArguments=... Default=...> at any depth.

    Returns (name, type_args, default). Type is best-effort — XAML Variable has
    TypeArguments as x:TypeArguments attribute on parent or as sub element.
    """
    out = []
    for el in root.iter():
        _, name = _strip_ns(el.tag)
        if name != "Variable":
            continue
        var_name = el.get("Name", "?")
        t = el.get("{%s}TypeArguments" % NS["x"], "") or el.get("TypeArguments", "")
        default = el.get("Default", "")
        out.append((var_name, t, default))
    return out


def _render_tree(
    root: ET.Element,
    raw: str,
    max_depth: int,
    line_idx: dict[str, int],
    dn_lines: dict[str, list[int]],
) -> list[str]:
    """Render activity tree as indented text. Returns list of lines."""
    dn_counter: dict[str, int] = {}
    lines: list[str] = []

    def _line_for(el: ET.Element, display_name: str) -> int | None:
        # 1) try IdRef
        idref = el.get("{%s}WorkflowViewState.IdRef" % NS["sap2010"]) or el.get(
            "WorkflowViewState.IdRef"
        )
        if idref and idref in line_idx:
            return line_idx[idref]
        # 2) match nth occurrence of DisplayName
        if display_name:
            n = dn_counter.get(display_name, 0)
            dn_counter[display_name] = n + 1
            occs = dn_lines.get(display_name, [])
            if n < len(occs):
                return occs[n]
        return None

    def walk(el: ET.Element, depth: int, prefix: str, is_last: bool) -> None:
        if depth > max_depth:
            return
        prefix_, local = _strip_ns(el.tag)
        if local in _SKIP_TAGS or local.endswith(".HintSize"):
            return
        if "." in local:
            # Property element like 'Sequence.Variables' — skip the wrapper but
            # descend to children
            for c in list(el):
                walk(c, depth, prefix, is_last)
            return

        dn = el.get("DisplayName", "")
        tag_repr = f"{prefix_}:{local}" if prefix_ else local
        line_no = _line_for(el, dn)
        loc = f"  [L.{line_no}]" if line_no else ""
        dn_repr = f' "{dn}"' if dn else ""

        connector = "└─ " if is_last else "├─ "
        lines.append(f"{prefix}{connector}{tag_repr}{dn_repr}{loc}")

        children = [
            c for c in list(el)
            if _strip_ns(c.tag)[1] not in _SKIP_TAGS
            and not _strip_ns(c.tag)[1].endswith(".HintSize")
        ]
        # Filter property-wrapper elements but keep their content
        real_children: list[ET.Element] = []
        for c in children:
            _, cname = _strip_ns(c.tag)
            if "." in cname:
                real_children.extend(list(c))
            else:
                real_children.append(c)

        for i, c in enumerate(real_children):
            last = i == len(real_children) - 1
            new_prefix = prefix + ("   " if is_last else "│  ")
            walk(c, depth + 1, new_prefix, last)

    # Root is the Activity element; find its single child that is the root activity
    body: ET.Element | None = None
    for c in list(root):
        _, local = _strip_ns(c.tag)
        if local in _SKIP_TAGS or "." in local or local == "Members":
            continue
        body = c
        break
    if body is None:
        return ["(no activity body found)"]
    walk(body, 0, "", True)
    return lines


def summarize(path: Path, tree_depth: int = 6, include_tree: bool = True) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        return f"PARSE ERROR: {e}"

    line_idx = _build_line_index(raw)
    dn_lines = _display_name_line_map(raw)

    total_lines = raw.count("\n") + 1
    out: list[str] = []
    out.append(f"FILE: {path.name} ({total_lines} lines, {len(raw)} bytes)")
    out.append(f"ROOT: {_strip_ns(root.tag)[1]} (x:Class={root.get('{%s}Class' % NS['x']) or '?'})")
    out.append("")

    args = _extract_arguments(root)
    if args:
        out.append(f"ARGUMENTS ({len(args)}):")
        pad = max(len(a[0]) for a in args)
        for name, direction, type_ in args:
            out.append(f"  {name.ljust(pad)}  {direction:5s}  {type_}")
        out.append("")

    variables = _walk_variables(root)
    if variables:
        out.append(f"VARIABLES ({len(variables)}):")
        pad = max(len(v[0]) for v in variables) if variables else 0
        for name, t, default in variables[:40]:
            suffix = f" = {default}" if default else ""
            type_repr = t if t else "?"
            out.append(f"  {name.ljust(pad)}  : {type_repr}{suffix}")
        if len(variables) > 40:
            out.append(f"  ... ({len(variables) - 40} more)")
        out.append("")

    imports = _extract_imports(root)
    if imports:
        out.append(f"IMPORTS ({len(imports)}): {', '.join(imports[:20])}"
                   + (f" ... (+{len(imports)-20})" if len(imports) > 20 else ""))
        out.append("")

    invoked = _extract_invoked_workflows(root, raw)
    if invoked:
        out.append(f"INVOKED WORKFLOWS ({len(invoked)}):")
        for wf, line in invoked[:30]:
            out.append(f"  L.{line}: {wf}")
        if len(invoked) > 30:
            out.append(f"  ... ({len(invoked) - 30} more)")
        out.append("")

    if include_tree:
        out.append(f"ACTIVITY TREE (depth={tree_depth}):")
        out.extend("  " + l for l in _render_tree(root, raw, tree_depth, line_idx, dn_lines))

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compact summary of a UiPath XAML file")
    ap.add_argument("file", help="path to .xaml file")
    ap.add_argument("--tree-depth", type=int, default=6)
    ap.add_argument("--no-tree", action="store_true", help="skip activity tree")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 2
    print(summarize(path, tree_depth=args.tree_depth, include_tree=not args.no_tree))
    return 0


if __name__ == "__main__":
    sys.exit(main())
