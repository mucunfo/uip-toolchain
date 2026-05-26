"""invocation_xref — find InvokeWorkflowFile callers + extract arg types.

For target XAML, scan project root recursively, find all activities
`InvokeWorkflowFile WorkflowFileName="<target_rel_path>"`, extract
`<InvokeWorkflowFile.Arguments>` block, parse type declarations.

Used by apply_inject_missing_args fixer (Phase 9E) as Layer 2 lookup:
when a sub-workflow uses an identifier without declaring it in `<x:Members>`,
the engine inspects all caller invocation sites to infer the expected type
from the `x:TypeArguments` attribute on the `<InArgument>` / `<InOutArgument>` /
`<OutArgument>` child elements.

Pure stdlib (xml.etree, re, pathlib) — no lxml dependency in this module.

Public API:
  - normalize_workflow_ref(ref, caller_dir, project_root) -> Path
  - find_callers(target_xaml, project_root) -> list[CallerSite]
  - extract_invoke_args(invoke_element) -> tuple[InvocationArg, ...]
  - infer_arg_type_from_callers(arg_name, callers) -> str | None
  - dump_arg_to_xaml(arg) -> str

Data classes:
  - InvocationArg: single arg declared at invocation site
  - CallerSite: one invocation of target from a particular file/line

Robustness:
  - Malformed XAML files swallowed silently (try/except per file).
  - Tolerates `ui:` vs `uix:` (or other) prefix variants on InvokeWorkflowFile.
  - Tolerates `./` prefix, `\\` vs `/` mixing in `WorkflowFileName`.
  - Skips `_BeforeMigration_*` backup dirs and `.tmp/` dirs during scan.
  - Skips self-references (target invoking itself).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

UI_NS = "{http://schemas.uipath.com/workflow/activities}"
XAML_NS = "{http://schemas.microsoft.com/winfx/2006/xaml}"
INVOKE_LOCAL = "InvokeWorkflowFile"
ARGS_LOCAL = "InvokeWorkflowFile.Arguments"

# Dirs ignored when scanning project for callers.
# `_BeforeMigration_*` are backup snapshots left by Activity Migrator.
# `.tmp/` is engine intermediate artifacts (snapshots, baselines).
_SKIP_DIR_PATTERNS = (
    re.compile(r"^_BeforeMigration_"),
    re.compile(r"^\.tmp$"),
    re.compile(r"^\.git$"),
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvocationArg:
    """A single argument declared at an InvokeWorkflowFile site.

    Attributes
    ----------
    name : str
        Argument name (the `x:Key` attribute value on the child element).
    type_str : str
        Full wrapped type, e.g., ``InArgument(x:String)`` or
        ``InOutArgument(scg:Dictionary(x:String, x:Object))``.
    direction : str
        One of ``"In"``, ``"InOut"``, ``"Out"`` — derived from the
        element's local tag (``InArgument`` → ``In``, etc.).
    raw_value : str
        Text content of the element — typically a VB binding expression
        like ``[in_Config]`` or a literal like ``""``.
    """

    name: str
    type_str: str
    direction: str
    raw_value: str = ""


@dataclass(frozen=True)
class CallerSite:
    """One invocation of a target workflow.

    Attributes
    ----------
    file : Path
        Absolute path of the caller XAML.
    line : int
        1-indexed source line of the ``<ui:InvokeWorkflowFile>`` opening
        tag in the caller. Best-effort: matched via regex scan of the
        raw file because ``xml.etree.ElementTree`` does not preserve
        line numbers by default. Falls back to 0 if not locatable.
    target_workflow : str
        The raw ``WorkflowFileName`` attribute value (unnormalised) as it
        appears in the XAML.
    args : tuple[InvocationArg, ...]
        Ordered tuple of arguments declared at this invocation site.
    """

    file: Path
    line: int
    target_workflow: str
    args: tuple[InvocationArg, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Path normalisation
# ---------------------------------------------------------------------------


def normalize_workflow_ref(
    ref: str,
    caller_dir: Path,
    project_root: Path,
) -> Path:
    """Resolve a ``WorkflowFileName`` attribute to an absolute Path.

    UiPath ``WorkflowFileName`` values are *project-root-relative* paths.
    Confirmed by inspecting Studio-emitted XAMLs: a caller at
    ``Framework/Process.xaml`` referencing ``Arquivos\\CriaRelatorioSaida.xaml``
    resolves to ``<project_root>/Arquivos/CriaRelatorioSaida.xaml`` —
    NOT ``Framework/Arquivos/...``. The same project-root anchoring
    is used by ``project.json::ignoredFiles`` (see heuristic
    :mod:`invoke_refs`).

    May use either ``\\`` or ``/`` separators; may start with ``./``;
    may (defensively) start with ``\\``/``/`` (still project-rooted).

    The ``caller_dir`` parameter is accepted for API completeness and
    to allow a future ``..`` traversal fallback if a legacy project
    ever emits one — but Studio-generated XAML never does, and current
    resolution is purely project-root anchored.

    Parameters
    ----------
    ref : str
        Raw attribute value from the XAML.
    caller_dir : Path
        Directory of the caller XAML. Currently unused — kept in the
        signature so the API can evolve without breaking callers.
    project_root : Path
        Project root that anchors the resolution.

    Returns
    -------
    Path
        Resolved absolute path. Existence is NOT checked here; caller
        decides what to do with missing files.
    """
    if not ref:
        return Path()
    # Normalise separators: backslashes are Windows convention but XAML
    # is portable text and may contain either.
    cleaned = ref.replace("\\", "/").strip()
    # Strip leading `./` (any number).
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    # Strip leading `/` (defensive — Studio emits relative paths).
    cleaned = cleaned.lstrip("/")
    # `caller_dir` is accepted for API stability; the actual anchor is
    # always project_root.
    _ = caller_dir
    resolved = (project_root / cleaned).resolve()
    return resolved


def _normalize_for_compare(p: Path) -> str:
    """Lower-cased, forward-slash string used for case-insensitive
    Path comparisons (Windows filesystems are case-insensitive)."""
    try:
        s = str(p.resolve())
    except (OSError, RuntimeError):
        s = str(p)
    return s.replace("\\", "/").lower()


# ---------------------------------------------------------------------------
# Scan helpers
# ---------------------------------------------------------------------------


def _should_skip_dir(name: str) -> bool:
    return any(p.search(name) for p in _SKIP_DIR_PATTERNS)


def _iter_xaml_files(project_root: Path) -> Iterable[Path]:
    """Yield .xaml files under project_root, skipping backup/tmp dirs.

    Walks manually rather than using ``rglob`` so we can prune skipped
    directories early (e.g., a ``_BeforeMigration_2026-05-20T10/`` folder
    can contain hundreds of stale XAMLs we never want to scan).
    """
    if not project_root.is_dir():
        return
    stack = [project_root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            try:
                if entry.is_dir():
                    if _should_skip_dir(entry.name):
                        continue
                    stack.append(entry)
                elif entry.is_file() and entry.suffix.lower() == ".xaml":
                    yield entry
            except OSError:
                continue


# ---------------------------------------------------------------------------
# Element parsing
# ---------------------------------------------------------------------------


def _localname(tag: str) -> str:
    """Return local part of an ElementTree-style namespaced tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _direction_from_tag(local: str) -> str:
    """Map ``InArgument`` → ``In``, ``InOutArgument`` → ``InOut``, etc.

    Returns empty string if the tag is not a recognised argument kind.
    """
    if local == "InArgument":
        return "In"
    if local == "OutArgument":
        return "Out"
    if local == "InOutArgument":
        return "InOut"
    if local == "Property":  # rare: nested Property declarations
        return "Property"
    return ""


def extract_invoke_args(invoke_element: ET.Element) -> tuple[InvocationArg, ...]:
    """Parse the ``<ui:InvokeWorkflowFile.Arguments>`` child block.

    Walks immediate children looking for a tag whose localname is
    ``InvokeWorkflowFile.Arguments``. For each grandchild that looks
    like an ``InArgument`` / ``OutArgument`` / ``InOutArgument``, build
    an :class:`InvocationArg`.

    Robust to namespace prefix variations: the outer wrapper may use
    ``ui:`` or some other prefix; we match by *local name only*.

    Parameters
    ----------
    invoke_element : xml.etree.ElementTree.Element
        The ``<ui:InvokeWorkflowFile>`` element.

    Returns
    -------
    tuple[InvocationArg, ...]
        In document order. Empty if no arguments block present.
    """
    args: list[InvocationArg] = []
    for child in invoke_element:
        if _localname(child.tag) != ARGS_LOCAL:
            continue
        for arg_elem in child:
            local = _localname(arg_elem.tag)
            direction = _direction_from_tag(local)
            if not direction:
                continue
            # Argument name: `x:Key` attribute (xaml namespace).
            name = (
                arg_elem.get(f"{XAML_NS}Key")
                or arg_elem.get("Key")
                or ""
            )
            if not name:
                # Cannot infer arg without a Key.
                continue
            type_args = (
                arg_elem.get(f"{XAML_NS}TypeArguments")
                or arg_elem.get("TypeArguments")
                or ""
            )
            # Wrap in the direction's argument-kind container for
            # symmetry with `<x:Property Type="InArgument(x:String)">`
            # form used in `<x:Members>` declarations.
            if type_args:
                type_str = f"{local}({type_args})"
            else:
                type_str = local
            raw_value = (arg_elem.text or "").strip()
            args.append(
                InvocationArg(
                    name=name,
                    type_str=type_str,
                    direction=direction,
                    raw_value=raw_value,
                )
            )
    return tuple(args)


def _find_invoke_line_map(raw_text: str) -> list[tuple[int, str]]:
    """Locate each ``<{prefix}:InvokeWorkflowFile`` opening tag in raw text.

    Returns a list of ``(line_number, workflow_filename)`` tuples in
    document order. ElementTree does not preserve line numbers in the
    default pure-Python implementation, so we recover them via a regex
    scan and align by ordinal position (Nth ``<InvokeWorkflowFile>``
    found in the tree matches the Nth match here).
    """
    results: list[tuple[int, str]] = []
    for m in _RE_INVOKE_OPEN.finditer(raw_text):
        line = raw_text.count("\n", 0, m.start()) + 1
        wff = m.group("wff") or ""
        results.append((line, wff))
    return results


_RE_INVOKE_OPEN = re.compile(
    # Match `<prefix:InvokeWorkflowFile ...` where prefix is any identifier
    # (typically `ui` but defensively allow `uix` or others). Capture the
    # WorkflowFileName attribute (may appear in any order amongst attrs).
    r'<(?:[A-Za-z_][\w]*:)?InvokeWorkflowFile\b'
    r'(?P<attrs>[^>]*?)'
    r'(?:WorkflowFileName="(?P<wff>[^"]*)")?'
    r'(?P<rest>[^>]*?)>',
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Main entry: find callers of a target
# ---------------------------------------------------------------------------


def find_callers(
    target_xaml: Path,
    project_root: Path,
) -> list[CallerSite]:
    """Scan ``project_root`` for XAML files that invoke ``target_xaml``.

    For each candidate caller, parse the XAML, find all
    ``<InvokeWorkflowFile>`` elements, resolve their ``WorkflowFileName``
    relative to the caller's directory, and record a :class:`CallerSite`
    if it points at ``target_xaml``.

    Self-references are skipped (a workflow invoking itself).

    Malformed XAMLs are skipped silently.

    Parameters
    ----------
    target_xaml : Path
        The sub-workflow we're looking up callers for. Must exist.
    project_root : Path
        Project root to scan recursively.

    Returns
    -------
    list[CallerSite]
        One entry per invocation site (a single caller XAML may invoke
        the same target multiple times → multiple CallerSite entries).
    """
    target_norm = _normalize_for_compare(target_xaml)
    project_root = project_root.resolve()
    target_resolved = target_xaml.resolve()

    callers: list[CallerSite] = []

    for candidate in _iter_xaml_files(project_root):
        # Skip the target itself (self-references handled defensively
        # below too, in case of resolve() quirks).
        try:
            if candidate.resolve() == target_resolved:
                continue
        except OSError:
            pass

        try:
            raw_text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            try:
                raw_text = candidate.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeDecodeError):
                continue

        # Quick textual short-circuit: if the file does not even contain
        # `InvokeWorkflowFile`, skip the parse step entirely. Big win
        # on large projects with many leaf workflows.
        if "InvokeWorkflowFile" not in raw_text:
            continue

        try:
            tree = ET.fromstring(raw_text)
        except ET.ParseError:
            # Malformed XAML — engine elsewhere reports it via a separate
            # rule; here we just skip.
            continue

        # Build line map by regex scan (ElementTree doesn't preserve
        # source line numbers in pure-Python implementation).
        line_map = _find_invoke_line_map(raw_text)
        # Find every InvokeWorkflowFile element, in document order.
        invoke_elements = [
            elem for elem in tree.iter()
            if _localname(elem.tag) == INVOKE_LOCAL
        ]

        caller_dir = candidate.parent
        for idx, invoke in enumerate(invoke_elements):
            wff = invoke.get("WorkflowFileName", "")
            if not wff:
                continue
            # Skip dynamic expressions (VB binding or WPF markup
            # extension) — can't statically resolve.
            if wff.startswith("[") or wff.startswith("{"):
                continue
            try:
                resolved = normalize_workflow_ref(
                    wff, caller_dir, project_root,
                )
            except (OSError, ValueError):
                continue
            if _normalize_for_compare(resolved) != target_norm:
                continue

            line = 0
            if idx < len(line_map):
                line = line_map[idx][0]
            args = extract_invoke_args(invoke)
            callers.append(
                CallerSite(
                    file=candidate,
                    line=line,
                    target_workflow=wff,
                    args=args,
                )
            )

    return callers


# ---------------------------------------------------------------------------
# Type inference
# ---------------------------------------------------------------------------


def infer_arg_type_from_callers(
    arg_name: str,
    callers: list[CallerSite],
) -> Optional[str]:
    """Aggregate the declared type for ``arg_name`` across all callers.

    Uses a *majority vote* (>50%): if 2 of 3 callers declare the arg as
    ``InArgument(x:String)`` and 1 declares ``InArgument(x:Object)``,
    the answer is the String form. Ties or no-data return ``None``.

    Multiple invocation sites within a single caller file count as
    separate votes — they represent independent type declarations
    made by the developer.

    Parameters
    ----------
    arg_name : str
        Argument name to look up (compared case-sensitive, matching
        UiPath's ``x:Key`` convention).
    callers : list[CallerSite]
        Output of :func:`find_callers`.

    Returns
    -------
    str | None
        The most common ``type_str`` if it represents a strict majority
        (>50%) of declarations, else ``None``.
    """
    if not callers:
        return None
    type_counts: Counter[str] = Counter()
    for caller in callers:
        for arg in caller.args:
            if arg.name == arg_name:
                type_counts[arg.type_str] += 1
    if not type_counts:
        return None
    total = sum(type_counts.values())
    most_common, count = type_counts.most_common(1)[0]
    # Strict majority: must exceed half. With a single declaration
    # (count==1, total==1), 1 > 0.5 so a lone observation is accepted.
    if count * 2 > total:
        return most_common
    return None


# ---------------------------------------------------------------------------
# Emit XAML <x:Property> from an InvocationArg
# ---------------------------------------------------------------------------


def dump_arg_to_xaml(arg: InvocationArg) -> str:
    """Render an :class:`InvocationArg` as a ``<x:Property>`` element.

    Used by Phase 9E ``apply_inject_missing_args`` fixer to materialise
    inferred argument declarations into a sub-workflow's
    ``<x:Members>`` block.

    Output form::

        <x:Property Name="in_Config" Type="InArgument(scg:Dictionary(x:String, x:Object))" />

    Returns a single-line XML string with no trailing newline. The
    caller is responsible for indentation and surrounding whitespace.
    """
    # Escape attribute values defensively. Argument names are nearly
    # always plain identifiers; type strings may legitimately contain
    # `<`/`>`/`&` (e.g., generic types use `(` `)` in XAML, not `<` `>`,
    # so this is mostly defensive).
    name = (
        arg.name
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
    )
    type_str = (
        arg.type_str
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
    )
    return f'<x:Property Name="{name}" Type="{type_str}" />'


__all__ = [
    "InvocationArg",
    "CallerSite",
    "normalize_workflow_ref",
    "find_callers",
    "extract_invoke_args",
    "infer_arg_type_from_callers",
    "dump_arg_to_xaml",
]
