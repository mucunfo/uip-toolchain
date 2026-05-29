"""selector_audit — detectors pra S-HEALCHAIN + S-SEMANTIC-LEAK.

Parse XAML, extrai TargetAnchorable.SearchSteps bitflag. Emite findings quando
bitflag inclui:
  - Image | TextOcr | TextNative | CV (S-HEALCHAIN — brittleness)
  - Semantic | SemanticSelector (S-SEMANTIC-LEAK — cloud LLM phone-home)

Bitflag values per Stream E dossier sicoob-studio-research/02-healing-agent.md
linha 22:

  None              = 0
  Selector          = 1
  FuzzySelector     = 2
  Image             = 4
  TextFindAll       = 8       (obsolete)
  TextOcr           = 0x10
  TextNative        = 0x20
  CV                = 0x40
  Semantic          = 0x80
  SemanticSelector  = 0x100

Parser tolerance:
  - Accept attribute or child-element forms of SearchSteps.
  - Accept namespace prefix `ui:` OR namespaced `{http://schemas.uipath.com/workflow/activities}TargetAnchorable`.
  - SearchSteps value may be:
      * decimal int            "4"
      * hex int                "0x10"  or "0X10"
      * pipe-separated enum    "Selector | FuzzySelector | Image"
      * combo / whitespace variants
  - Malformed XAML -> emit nothing (be conservative).
  - SearchSteps absent -> assume default (Selector | FuzzySelector) -> no finding.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

from .._types import Finding


# ---------------------------------------------------------------------------
# Bitflag constants — keep in sync with dossier sicoob-studio-research §02 L22.
# ---------------------------------------------------------------------------
SS_NONE = 0
SS_SELECTOR = 1
SS_FUZZY_SELECTOR = 2
SS_IMAGE = 4
SS_TEXT_FIND_ALL = 8        # obsolete per dossier
SS_TEXT_OCR = 0x10
SS_TEXT_NATIVE = 0x20
SS_CV = 0x40
SS_SEMANTIC = 0x80
SS_SEMANTIC_SELECTOR = 0x100

# Default when SearchSteps absent in XAML = Selector | FuzzySelector (standard
# UiPath Modern UI behavior). Used to skip "implicit" cases.
SS_DEFAULT = SS_SELECTOR | SS_FUZZY_SELECTOR

# Masks the two rules care about.
HEALCHAIN_MASK = SS_IMAGE | SS_TEXT_OCR | SS_TEXT_NATIVE | SS_CV
SEMANTIC_LEAK_MASK = SS_SEMANTIC | SS_SEMANTIC_SELECTOR

# Enum-name -> bitflag map (case-insensitive). Used to parse pipe-separated
# attribute values like "Selector | FuzzySelector | Image".
_ENUM_BY_NAME: dict[str, int] = {
    "none": SS_NONE,
    "selector": SS_SELECTOR,
    "fuzzyselector": SS_FUZZY_SELECTOR,
    "image": SS_IMAGE,
    "textfindall": SS_TEXT_FIND_ALL,
    "textocr": SS_TEXT_OCR,
    "textnative": SS_TEXT_NATIVE,
    "cv": SS_CV,
    "semantic": SS_SEMANTIC,
    "semanticselector": SS_SEMANTIC_SELECTOR,
}

# UiPath activities XAML namespaces. Real Sicoob XAMLs use BOTH:
#   ui  -> http://schemas.uipath.com/workflow/activities           (classic)
#   uix -> http://schemas.uipath.com/workflow/activities/uix       (Modern UI)
# TargetAnchorable lives in the `uix` ns in real projects but we accept either
# for tolerance — bare elements (no namespace) also accepted.
_UIPATH_NS_CANDIDATES = (
    "http://schemas.uipath.com/workflow/activities",
    "http://schemas.uipath.com/workflow/activities/uix",
)
_TA_LOCALNAME = "TargetAnchorable"
_SS_LOCALNAME = "SearchSteps"


def _parse_search_steps_value(raw: str | None) -> int:
    """Parse a SearchSteps attribute value into the integer bitflag.

    Accepts decimal ("4"), hex ("0x10"), or pipe-separated enum names
    ("Selector | FuzzySelector | Image"). Unknown tokens are ignored
    (best-effort parse). Empty/None -> 0.
    """
    if raw is None:
        return 0
    s = raw.strip()
    if not s:
        return 0

    # Hex prefix
    if s.lower().startswith("0x"):
        try:
            return int(s, 16)
        except ValueError:
            return 0

    # Pure decimal int
    if s.lstrip("+-").isdigit():
        try:
            return int(s)
        except ValueError:
            return 0

    # Pipe-separated enum names (with optional whitespace + comma alternation)
    bitmask = 0
    for token in re.split(r"[|,\s]+", s):
        if not token:
            continue
        key = token.strip().lower()
        if key in _ENUM_BY_NAME:
            bitmask |= _ENUM_BY_NAME[key]
        # Unknown enum names silently ignored — conservative.
    return bitmask


def _scan_serialized_search_steps(elem: ET.Element) -> int:
    """Recover a SearchSteps bitflag from a property element whose value is
    non-text markup (e.g. `<x:Static Member="...SemanticSelector"/>`).

    The text-only parser cannot decode this form (child.text is empty), which
    would silently under-match the breaking cloud-leak rule. We serialize the
    element's inner XML and scan it for the enum NAMES as whole words. This is
    deliberately conservative: it only recovers the enum names the engine cares
    about (Semantic / SemanticSelector and the brittle healing strategies), so
    a hand-edited / static-reference SearchSteps still triggers the compliance
    check instead of passing silently.

    Returns 0 when no known enum name is found (safe no-op).
    """
    try:
        serialized = ET.tostring(elem, encoding="unicode")
    except (TypeError, ValueError):
        return 0

    bitmask = 0
    # Longer names first so "SemanticSelector" is not double-counted via the
    # word-boundary match on "Semantic" (word boundaries make them distinct
    # tokens anyway, but ordering keeps intent explicit).
    for name, flag in (
        ("SemanticSelector", SS_SEMANTIC_SELECTOR),
        ("Semantic", SS_SEMANTIC),
        ("Image", SS_IMAGE),
        ("TextOcr", SS_TEXT_OCR),
        ("TextNative", SS_TEXT_NATIVE),
        ("CV", SS_CV),
    ):
        if re.search(r"\b" + re.escape(name) + r"\b", serialized):
            bitmask |= flag
    return bitmask


def _localname(tag: str) -> str:
    """Return localname stripping `{namespace}` prefix from ElementTree tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _ns_matches_uipath(tag: str) -> bool:
    """True when the tag's namespace is one of the UiPath workflow activities
    namespaces (classic `ui` ns OR Modern UI `uix` ns), OR when there's no
    namespace (best-effort for fragments without xmlns)."""
    if not tag.startswith("{"):
        return True  # no namespace info — accept by localname
    for ns in _UIPATH_NS_CANDIDATES:
        if tag.startswith("{" + ns + "}"):
            return True
    return False


def _line_of_element_in_text(content: str, localname: str, ns_prefixes: list[str],
                             occurrence: int) -> int:
    """Best-effort line number for the Nth occurrence of `<prefix:localname` or
    `<localname` in the raw content. ElementTree drops sourceline info in stdlib,
    so we re-scan the original text.

    `occurrence` is 0-indexed.
    """
    patterns = [r"<" + re.escape(p) + r":" + re.escape(localname) + r"\b"
                for p in ns_prefixes if p]
    patterns.append(r"<" + re.escape(localname) + r"\b")
    combined = re.compile("|".join(patterns))
    for i, m in enumerate(combined.finditer(content)):
        if i == occurrence:
            return content[: m.start()].count("\n") + 1
    return 1


def _find_uipath_prefixes(content: str) -> list[str]:
    """Scan xmlns declarations for prefixes mapped to ANY of the UiPath ns
    candidates. Returns the list of prefixes."""
    prefixes: list[str] = []
    ns_alt = "|".join(re.escape(ns) for ns in _UIPATH_NS_CANDIDATES)
    for m in re.finditer(
        r'xmlns:([A-Za-z_][\w.-]*)\s*=\s*["\'](?:' + ns_alt + r')["\']',
        content,
    ):
        prefixes.append(m.group(1))
    # Fallback: also accept common `ui:`/`uix:` prefixes if xmlns parse failed.
    for fallback in ("ui", "uix"):
        if fallback not in prefixes:
            prefixes.append(fallback)
    return prefixes


def _iter_target_anchorables(xaml_path: Path) -> Iterator[tuple[int, str, int]]:
    """Yield (line_no, search_steps_raw, value_int) for each TargetAnchorable.

    SearchSteps may live as an attribute on TargetAnchorable, or as a child
    `<ui:TargetAnchorable.SearchSteps>` element. Both shapes are handled.

    Malformed XML -> yields nothing (conservative).
    """
    try:
        content = xaml_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return

    ns_prefixes = _find_uipath_prefixes(content)

    # Walk every element. ElementTree iter() is depth-first.
    ta_seen = 0
    for elem in root.iter():
        if _localname(elem.tag) != _TA_LOCALNAME:
            continue
        if not _ns_matches_uipath(elem.tag):
            continue

        raw_value: str | None = None

        # Attribute form: <ui:TargetAnchorable SearchSteps="Selector|Image"/>
        # Attribute may itself be namespaced or bare.
        for attr_name, attr_val in elem.attrib.items():
            if _localname(attr_name) == _SS_LOCALNAME:
                raw_value = attr_val
                break

        # Child element form: <ui:TargetAnchorable.SearchSteps>...</...> would
        # be parsed by ElementTree as the .NET property-element pattern. In
        # XAML that's `<ui:TargetAnchorable><ui:TargetAnchorable.SearchSteps>...`
        # We look at children for that pattern.
        ss_child: ET.Element | None = None
        if raw_value is None:
            for child in elem:
                if _localname(child.tag).endswith("." + _SS_LOCALNAME):
                    raw_value = (child.text or "").strip()
                    ss_child = child
                    break
                if _localname(child.tag) == _SS_LOCALNAME:
                    raw_value = (child.text or "").strip()
                    ss_child = child
                    break

        line_no = _line_of_element_in_text(content, _TA_LOCALNAME,
                                           ns_prefixes, ta_seen)
        ta_seen += 1

        # Conservative: SearchSteps absent -> assume default, skip.
        if raw_value is None:
            continue

        value_int = _parse_search_steps_value(raw_value)

        # Property-element form where the value is non-text markup (e.g.
        # `<uix:TargetAnchorable.SearchSteps><x:Static Member="...SemanticSelector"/>`)
        # yields empty child.text -> value_int == 0, a silent under-match for a
        # breaking compliance rule. When the SearchSteps element actually has
        # child element(s) we could not parse as text, scan its serialized inner
        # XML for the enum names so the cloud-leak check is not silently bypassed.
        if value_int == 0 and ss_child is not None and len(ss_child) > 0:
            value_int = _scan_serialized_search_steps(ss_child)
            if value_int and not raw_value:
                raw_value = "<unparsed markup>"

        yield (line_no, raw_value, value_int)


def _mask_to_names(mask_value: int, mask_filter: int) -> list[str]:
    """Return the human-readable enum names of bits in `mask_value & mask_filter`."""
    bits = mask_value & mask_filter
    names = []
    for name, flag in [
        ("Image", SS_IMAGE),
        ("TextOcr", SS_TEXT_OCR),
        ("TextNative", SS_TEXT_NATIVE),
        ("CV", SS_CV),
        ("Semantic", SS_SEMANTIC),
        ("SemanticSelector", SS_SEMANTIC_SELECTOR),
    ]:
        if bits & flag:
            names.append(name)
    return names


# ---------------------------------------------------------------------------
# Public detectors — engine calls them as detect(rule, fc, pc).
# Also callable directly with a Path for tests / standalone use.
# ---------------------------------------------------------------------------

def _normalize_args(*args, **kwargs) -> tuple[Path, object, object]:
    """Accept BOTH calling conventions:
      detect(xaml_path)                 — direct/test usage
      detect(rule, fc, pc)              — engine usage (fc has `.path`)
    Returns (path, rule_or_none, file_context_or_none).
    """
    if len(args) == 1:
        a = args[0]
        if isinstance(a, Path):
            return a, None, None
        # Maybe a FileContext with .path
        path_attr = getattr(a, "path", None)
        if path_attr is not None:
            return Path(path_attr), None, a
        # str path
        return Path(a), None, None
    if len(args) >= 2:
        rule, fc = args[0], args[1]
        path = Path(getattr(fc, "path", fc))
        return path, rule, fc
    raise TypeError("detector requires (xaml_path) or (rule, fc, pc)")


def detect_healchain(*args, **kwargs) -> list[Finding]:
    """S-HEALCHAIN — flag SearchSteps including Image/OCR/TextNative/CV."""
    path, rule, fc = _normalize_args(*args, **kwargs)
    rule_id = getattr(rule, "id", "S-HEALCHAIN") if rule is not None else "S-HEALCHAIN"
    from .._types import Severity as _S
    severity = getattr(rule, "severity", _S.ERROR) if rule is not None else _S.ERROR
    category = getattr(rule, "category", "breaking") if rule is not None else "breaking"
    fix_prose = ((rule.fix or {}).get("prose")
                 if rule is not None and getattr(rule, "fix", None) else None)

    findings: list[Finding] = []
    for line_no, raw_value, value_int in _iter_target_anchorables(path):
        hit_names = _mask_to_names(value_int, HEALCHAIN_MASK)
        if not hit_names:
            continue
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=severity,
                category=category,
                file=str(path),
                line=line_no,
                message=(
                    f"TargetAnchorable SearchSteps inclui fallback brittle "
                    f"({', '.join(hit_names)}). Healing chain depende de "
                    f"Image/OCR/CV — runtime cost + silent failure em UI changes. "
                    f"Raw: '{raw_value}'."
                ),
                fix_mechanical=None,
                fix_prose=fix_prose,
            )
        )
    return findings


def detect_semantic_leak(*args, **kwargs) -> list[Finding]:
    """S-SEMANTIC-LEAK — flag SearchSteps including Semantic / SemanticSelector.

    These steps phone home to UiPath cloud LLM (dossier §02 linha 118). Sicoob
    compliance: dados internos NAO podem sair pra cloud externa.
    """
    path, rule, fc = _normalize_args(*args, **kwargs)
    rule_id = getattr(rule, "id", "S-SEMANTIC_LEAK") if rule is not None else "S-SEMANTIC_LEAK"
    from .._types import Severity as _S
    severity = getattr(rule, "severity", _S.ERROR) if rule is not None else _S.ERROR
    category = getattr(rule, "category", "breaking") if rule is not None else "breaking"
    fix_prose = ((rule.fix or {}).get("prose")
                 if rule is not None and getattr(rule, "fix", None) else None)

    findings: list[Finding] = []
    for line_no, raw_value, value_int in _iter_target_anchorables(path):
        hit_names = _mask_to_names(value_int, SEMANTIC_LEAK_MASK)
        if not hit_names:
            continue
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=severity,
                category=category,
                file=str(path),
                line=line_no,
                message=(
                    f"TargetAnchorable SearchSteps inclui {', '.join(hit_names)} "
                    f"— estes steps chamam UiPath cloud LLM com selector text + "
                    f"screenshot. VIOLA POLICY SICOOB (dados internos para cloud "
                    f"externa). Raw: '{raw_value}'."
                ),
                fix_mechanical=None,
                fix_prose=fix_prose,
            )
        )
    return findings
