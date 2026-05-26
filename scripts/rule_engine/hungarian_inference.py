"""hungarian_inference -- Sicoob arg type inference via Hungarian convention.

Convention (per CLAUDE.md + N-1/N-2 rules):
  <direction>_<TypePrefix><Name>

  direction in {in, io, out} -> wrapper {InArgument, InOutArgument, OutArgument}
  TypePrefix in {St, Int, Lng, Bol, Dt, Dbl, Dec, Dtb, Dtr, Dict, Lst, Arr, Eml, Br, Ex, Q, Json, ...}
  Name = CamelCase identifier suffix.

Used by apply_inject_missing_args fixer (Phase 9E) as Layer 3 inference.

Aliases doc'd via W-33 migration:
  Bl -> Bol (legacy boolean)
  Ss -> SSt (legacy list-of-strings)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# (prefix, clr_type_str)  -- ORDER matters: longer prefixes first to avoid greedy match
# Sicoob aliases doc'd (W-33 migration): Bl is legacy for Bol, Ss for SSt.
HUNGARIAN_PREFIXES: tuple[tuple[str, str], ...] = (
    ("SSt",  "scg:List(x:String)"),       # Sicoob: list of strings
    ("Dtb",  "sd:DataTable"),
    ("Dtr",  "sd:DataRow"),
    ("Dict", "scg:Dictionary(x:String, x:Object)"),
    ("Json", "Newtonsoft.Json.Linq:JObject"),
    ("Lst",  "scg:List(x:Object)"),
    ("Arr",  "x:String[]"),
    ("Eml",  "smm:MailMessage"),
    ("Int",  "x:Int32"),
    ("Lng",  "x:Int64"),
    ("Bol",  "x:Boolean"),
    ("Bl",   "x:Boolean"),                # alias of Bol
    ("Ss",   "scg:List(x:String)"),       # alias of SSt
    ("Dbl",  "x:Double"),
    ("Dec",  "x:Decimal"),
    ("Dt",   "s:DateTime"),
    ("St",   "x:String"),
    ("Br",   "uipath:BusinessRuleException"),
    ("Ex",   "s:Exception"),
    ("Q",    "uipath:QueueItem"),
)

DIRECTION_WRAPPER = {
    "in":  "InArgument",
    "io":  "InOutArgument",
    "out": "OutArgument",
}

# Match direction prefix and capture the remainder for prefix scanning.
# Remainder must start with an uppercase letter (CamelCase convention).
_DIRECTION_RE = re.compile(r"^(in|io|out)_([A-Z]\w*)$")


@dataclass(frozen=True)
class HungarianMatch:
    """Result of parsing a Sicoob Hungarian arg name.

    Attributes:
        direction:         "in" | "io" | "out"
        type_prefix:       e.g. "St", "Int", "SSt", "Bol"
        inferred_clr_type: e.g. "x:String", "scg:List(x:String)"
        wrapped_type:      e.g. "InArgument(x:String)"
        rest:              suffix after type prefix (e.g. "PrefixoLog")
    """
    direction: str
    type_prefix: str
    inferred_clr_type: str
    wrapped_type: str
    rest: str


def _find_type_prefix(remainder: str) -> tuple[str, str, str] | None:
    """Return (prefix, clr_type, rest) for the longest matching Hungarian
    type prefix, or None if no prefix applies.

    The remainder must continue with either end-of-string or an uppercase
    letter -- this prevents 'Config' from matching 'C' (no such prefix) and
    keeps prefix boundaries on CamelCase humps.
    """
    for prefix, clr_type in HUNGARIAN_PREFIXES:
        if not remainder.startswith(prefix):
            continue
        rest = remainder[len(prefix):]
        # Boundary check: after the prefix we expect either nothing
        # or another CamelCase token starting with uppercase.
        if rest == "" or rest[0].isupper():
            return prefix, clr_type, rest
    return None


def parse(arg_name: str) -> HungarianMatch | None:
    """Parse a Hungarian-notation argument name.

    Returns HungarianMatch when the name conforms to
    `<direction>_<TypePrefix><Rest>`, else None.
    """
    if not isinstance(arg_name, str) or not arg_name:
        return None
    m = _DIRECTION_RE.match(arg_name)
    if not m:
        return None
    direction, remainder = m.group(1), m.group(2)
    pf = _find_type_prefix(remainder)
    if pf is None:
        return None
    prefix, clr_type, rest = pf
    wrapper = DIRECTION_WRAPPER[direction]
    return HungarianMatch(
        direction=direction,
        type_prefix=prefix,
        inferred_clr_type=clr_type,
        wrapped_type=f"{wrapper}({clr_type})",
        rest=rest,
    )


def infer(arg_name: str) -> str | None:
    """Convenience wrapper: return wrapped_type if parse succeeds, else None."""
    m = parse(arg_name)
    return m.wrapped_type if m is not None else None


def parse_all_known_prefixes() -> dict[str, str]:
    """Return dict mapping all known Hungarian prefixes to CLR types.

    Useful for documentation generation and debug output.
    """
    return {prefix: clr_type for prefix, clr_type in HUNGARIAN_PREFIXES}
