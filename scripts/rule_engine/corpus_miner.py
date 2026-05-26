"""corpus_miner -- extract canonical arg declarations from Sicoob XAMLs.

Scan multiple roots (.nupkgs/, Desktop/temp/, OneDrive Sicoob projects).
For each XAML, parse <x:Members><x:Property Name="..." Type="..."> declarations.
Aggregate: arg_name -> Counter[type]. Output highest-confidence canonical map.

Used by apply_inject_missing_args fixer (Phase 9E) as Layer 1 lookup, replacing
the previously hand-coded canonical args table. Statistical, data-driven, and
auto-refreshable from any corpus snapshot.

Public API:
    iter_xaml_files(root)            -> Iterable[Path]
    iter_nupkg_xamls(nupkg)          -> Iterable[tuple[str, bytes]]
    extract_property_declarations()  -> Iterable[tuple[str, str]]
    mine(roots, ...)                 -> dict[str, ArgSpec]
    generate_python_module(...)      -> None
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import traceback
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

# XAML namespaces
XAML_NS = "{http://schemas.microsoft.com/winfx/2006/xaml}"
PROPERTY_TAG = f"{XAML_NS}Property"
MEMBERS_TAG = f"{XAML_NS}Members"

# Direction prefixes (Sicoob/REFramework Hungarian convention)
DIRECTION_PREFIXES = ("in_", "io_", "out_")

# Min occurrences for inclusion (filter noise)
MIN_OCCURRENCES = 3

# Skip patterns -- directories/files we never want to traverse
_SKIP_DIR_NAMES = {
    ".git",
    ".local",
    ".tmp",
    ".vscode",
    ".idea",
    "__pycache__",
    "node_modules",
    ".uipath-rules",
    ".scripts",
    ".docs",
    ".claude",
    ".nupkgs",  # explicitly handle via --roots when desired (nupkgs branch)
    ".cache",
    "bin",
    "obj",
}

# Regex on directory name (case-insensitive)
_SKIP_DIR_RE = re.compile(r"^_BeforeMigration_", re.IGNORECASE)

# Regex on file stems to exclude (case-insensitive)
_SKIP_FILE_RE = re.compile(r"^_BeforeMigration_", re.IGNORECASE)

# Type values containing locally-scoped namespaces or unresolved references
# are treated as non-CLR and excluded from the canonical map.
_LOCAL_NS_PREFIXES = re.compile(r"\b(local|this|sys|temp|debug|wf):", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArgSpec:
    """Canonical type declaration for an argument name.

    Attributes:
        canonical_type:  the most-common type string seen for this arg.
        confidence:      fraction in [0, 1] of dominant type vs all occurrences.
        occurrences:     total times the arg name was seen across corpus.
        alternatives:    sorted (type, count) for non-dominant declarations.
    """
    canonical_type: str
    confidence: float
    occurrences: int
    alternatives: tuple[tuple[str, int], ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Filesystem traversal
# ---------------------------------------------------------------------------

def _should_skip_dir(name: str) -> bool:
    if name in _SKIP_DIR_NAMES:
        return True
    if name.startswith("."):
        # Hidden directories generically (covers .tmp, .local, .git, etc.)
        return True
    if _SKIP_DIR_RE.match(name):
        return True
    return False


def _should_skip_file(name: str) -> bool:
    if _SKIP_FILE_RE.match(name):
        return True
    return False


def iter_xaml_files(root: Path) -> Iterator[Path]:
    """Yield every *.xaml file under root, skipping non-corpus dirs/files.

    Skips:
        - Hidden directories (anything starting with ".")
        - `.tmp/`, `.local/`, `_BeforeMigration_*` siblings
        - `bin/`, `obj/` build outputs
        - Files named `_BeforeMigration_*.xaml`
    """
    root = Path(root)
    if not root.exists():
        return

    if root.is_file():
        if root.suffix.lower() == ".xaml" and not _should_skip_file(root.name):
            yield root
        return

    # Manual walk so we can prune skip dirs cheaply.
    import os
    for current, dirs, files in os.walk(root):
        # Prune dirs in-place
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fname in files:
            if not fname.lower().endswith(".xaml"):
                continue
            if _should_skip_file(fname):
                continue
            yield Path(current) / fname


def iter_nupkg_xamls(nupkg: Path) -> Iterator[tuple[str, bytes]]:
    """Yield (member_name, raw_bytes) for *.xaml inside a .nupkg.

    Tolerates malformed nupkgs (returns nothing on error).
    """
    nupkg = Path(nupkg)
    try:
        with zipfile.ZipFile(nupkg) as zf:
            for member in zf.namelist():
                if not member.lower().endswith(".xaml"):
                    continue
                # nupkgs may contain lib/, content/, tools/ etc. Skip
                # _BeforeMigration_* inside if it ever shows up.
                base = member.rsplit("/", 1)[-1]
                if _should_skip_file(base):
                    continue
                try:
                    yield member, zf.read(member)
                except (zipfile.BadZipFile, KeyError, OSError) as exc:
                    print(
                        f"[corpus_miner] warn: cannot read {member} in {nupkg.name}: {exc}",
                        file=sys.stderr,
                    )
    except (zipfile.BadZipFile, OSError) as exc:
        print(
            f"[corpus_miner] warn: not a valid zip/nupkg: {nupkg} ({exc})",
            file=sys.stderr,
        )


def iter_nupkgs(root: Path) -> Iterator[Path]:
    """Yield .nupkg files under root (non-recursive into hidden dirs)."""
    root = Path(root)
    if not root.exists():
        return
    if root.is_file():
        if root.suffix.lower() == ".nupkg":
            yield root
        return
    import os
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fname in files:
            if fname.lower().endswith(".nupkg"):
                yield Path(current) / fname


# ---------------------------------------------------------------------------
# XAML parsing
# ---------------------------------------------------------------------------

def _decode_xaml_bytes(data: bytes) -> str:
    """Decode bytes to text, stripping any UTF BOM and tolerating encodings."""
    # BOM-aware decode: lets ET.fromstring work even when file starts with BOM.
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace")
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        try:
            return data.decode("utf-16", errors="replace")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")
    # Default: assume UTF-8
    return data.decode("utf-8", errors="replace")


def _is_canonical_type(type_str: str) -> bool:
    """Reject Type values that reference locally-defined namespaces only.

    Canonical args in corpus use CLR-rooted types like InArgument(x:String) or
    InArgument(scg:Dictionary(x:String, x:String)). Types using `local:` (XAML
    file-local namespaces) refer to project-private classes and are not
    portable -- they MUST be excluded from the canonical map.
    """
    if not type_str:
        return False
    if _LOCAL_NS_PREFIXES.search(type_str):
        return False
    return True


def extract_property_declarations(xaml_bytes: bytes) -> Iterator[tuple[str, str]]:
    """Yield (arg_name, type_str) for each `<x:Property>` matching direction prefix.

    Only walks the top-level `<x:Members>` of the activity (children-property
    declarations on Activity root). Tolerates malformed XML.
    """
    text = _decode_xaml_bytes(xaml_bytes)
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return

    # Find Members element among direct children (or anywhere — XAML keeps it
    # as a direct child of <Activity>, but we accept slightly deeper for safety).
    members_elems = list(root.iter(MEMBERS_TAG))
    if not members_elems:
        return

    for members in members_elems:
        for prop in members.findall(PROPERTY_TAG):
            name = prop.get("Name") or ""
            type_str = prop.get("Type") or ""
            if not name or not type_str:
                continue
            if not name.startswith(DIRECTION_PREFIXES):
                continue
            if not _is_canonical_type(type_str):
                continue
            yield name, type_str.strip()


# ---------------------------------------------------------------------------
# Mining orchestration
# ---------------------------------------------------------------------------

@dataclass
class MineStats:
    roots: list[Path]
    nupkgs_scanned: int = 0
    nupkg_xamls: int = 0
    fs_xamls: int = 0
    parse_errors: int = 0
    raw_declarations: int = 0
    unique_args: int = 0
    canonical_args_after_filter: int = 0


def mine(
    roots: list[Path],
    *,
    include_nupkgs: bool = True,
    min_occurrences: int = MIN_OCCURRENCES,
    stats: MineStats | None = None,
) -> dict[str, ArgSpec]:
    """Scan roots, return canonical arg map.

    Args:
        roots: list of dirs/files to scan. .nupkg files anywhere inside are
            extracted if `include_nupkgs=True`.
        include_nupkgs: whether to expand .nupkg archives into in-memory XAMLs.
        min_occurrences: discard args with fewer total occurrences.
        stats: optional MineStats to fill in.

    Returns:
        dict mapping arg_name -> ArgSpec, sorted by descending occurrences.
    """
    type_counters: dict[str, Counter[str]] = {}

    if stats is None:
        stats = MineStats(roots=list(roots))
    else:
        stats.roots = list(roots)

    seen_nupkg_paths: set[Path] = set()
    seen_xaml_paths: set[Path] = set()

    for root in roots:
        root = Path(root)

        # Nupkg archives in this root
        if include_nupkgs:
            for nupkg_path in iter_nupkgs(root):
                if nupkg_path in seen_nupkg_paths:
                    continue
                seen_nupkg_paths.add(nupkg_path)
                stats.nupkgs_scanned += 1
                for member_name, data in iter_nupkg_xamls(nupkg_path):
                    stats.nupkg_xamls += 1
                    try:
                        for arg, typ in extract_property_declarations(data):
                            type_counters.setdefault(arg, Counter())[typ] += 1
                            stats.raw_declarations += 1
                    except Exception as exc:  # noqa: BLE001
                        stats.parse_errors += 1
                        print(
                            f"[corpus_miner] warn: parse error in {nupkg_path.name}!{member_name}: {exc}",
                            file=sys.stderr,
                        )

        # Filesystem XAMLs
        for xaml_path in iter_xaml_files(root):
            if xaml_path in seen_xaml_paths:
                continue
            seen_xaml_paths.add(xaml_path)
            stats.fs_xamls += 1
            try:
                data = xaml_path.read_bytes()
            except OSError as exc:
                stats.parse_errors += 1
                print(
                    f"[corpus_miner] warn: cannot read {xaml_path}: {exc}",
                    file=sys.stderr,
                )
                continue
            try:
                for arg, typ in extract_property_declarations(data):
                    type_counters.setdefault(arg, Counter())[typ] += 1
                    stats.raw_declarations += 1
            except Exception as exc:  # noqa: BLE001
                stats.parse_errors += 1
                print(
                    f"[corpus_miner] warn: parse error in {xaml_path}: {exc}",
                    file=sys.stderr,
                )

    stats.unique_args = len(type_counters)

    canonical: dict[str, ArgSpec] = {}
    for arg_name, counter in type_counters.items():
        total = sum(counter.values())
        if total < min_occurrences:
            continue
        ordered = counter.most_common()
        dominant_type, dominant_count = ordered[0]
        confidence = dominant_count / total if total else 0.0
        alternatives = tuple((t, c) for t, c in ordered[1:])
        canonical[arg_name] = ArgSpec(
            canonical_type=dominant_type,
            confidence=confidence,
            occurrences=total,
            alternatives=alternatives,
        )

    stats.canonical_args_after_filter = len(canonical)

    # Sort by descending occurrences, then alphabetical for tie-break stability.
    return dict(
        sorted(
            canonical.items(),
            key=lambda kv: (-kv[1].occurrences, kv[0]),
        )
    )


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

_GEN_HEADER = '''"""AUTO-GENERATED by scripts/rule_engine/corpus_miner.py -- do not edit manually.

Generated: {generated_at}
Source roots:
{roots_block}
Corpus stats: {fs_xamls} filesystem XAMLs + {nupkg_xamls} nupkg XAMLs
              ({nupkgs_scanned} nupkgs scanned)
Raw declarations: {raw_declarations}
Unique args:      {unique_args}
After filter (>= {min_occurrences} occurrences): {canonical_args_after_filter}

Used by apply_inject_missing_args fixer as Layer 1 canonical lookup. Regenerate
periodically as the corpus grows; this module is committed for reproducibility.
"""
from __future__ import annotations

from typing import NamedTuple


class ArgSpec(NamedTuple):
    canonical_type: str
    confidence: float
    occurrences: int


CANONICAL_ARGS: dict[str, ArgSpec] = {{
{entries}
}}


def lookup(arg_name: str, *, min_confidence: float = 0.85) -> str | None:
    """Return canonical type for arg_name, or None if below confidence threshold.

    Used by the inject_missing_args fixer to decide whether to auto-declare a
    missing argument. Below ``min_confidence``, the fixer should defer to
    structural inference or escalate to a contextual finding.
    """
    spec = CANONICAL_ARGS.get(arg_name)
    if spec is None:
        return None
    if spec.confidence < min_confidence:
        return None
    return spec.canonical_type
'''


def _format_entry(name: str, spec: ArgSpec) -> str:
    # Escape the type string with repr to handle any unusual characters safely.
    return (
        f"    {name!r:<40s}: "
        f"ArgSpec({spec.canonical_type!r}, "
        f"{round(spec.confidence, 4)}, "
        f"{spec.occurrences}),"
    )


def generate_python_module(
    canonical_map: dict[str, ArgSpec],
    output_path: Path,
    *,
    stats: MineStats | None = None,
    min_occurrences: int = MIN_OCCURRENCES,
) -> None:
    """Write an auto-generated `_canonical_args.py` with literal CANONICAL_ARGS dict."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if stats is None:
        stats = MineStats(roots=[])

    # Escape backslashes so Windows paths in docstring do not look like
    # unicode escape sequences (e.g., `\Users` -> `\\Users`). The triple-quoted
    # string is still treated by Python as containing escape sequences -- a
    # path like `C:\Users\...` would trigger SyntaxError 'truncated \UXXXX
    # escape'. Backslash doubling keeps the docstring purely literal.
    roots_block_lines = [f"    - {str(p).replace(chr(92), chr(92)*2)}" for p in stats.roots] or ["    - (none)"]
    roots_block = "\n".join(roots_block_lines)

    entries = "\n".join(_format_entry(n, s) for n, s in canonical_map.items())
    if not entries:
        entries = "    # (no canonical args mined -- corpus empty?)"

    body = _GEN_HEADER.format(
        generated_at=generated_at,
        roots_block=roots_block,
        fs_xamls=stats.fs_xamls,
        nupkg_xamls=stats.nupkg_xamls,
        nupkgs_scanned=stats.nupkgs_scanned,
        raw_declarations=stats.raw_declarations,
        unique_args=stats.unique_args,
        canonical_args_after_filter=stats.canonical_args_after_filter,
        min_occurrences=min_occurrences,
        entries=entries,
    )

    output_path.write_text(body, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent / "_canonical_args.py"
)


def _build_default_roots() -> list[Path]:
    """Best-effort default roots when none are passed on the CLI."""
    user_home = Path.home()
    candidates = [
        user_home / "OneDrive - Sicoob" / "Projects" / ".nupkgs",
        user_home / "Desktop" / "temp",
        user_home / "OneDrive - Sicoob" / "Projects",
    ]
    return [c for c in candidates if c.exists()]


def _print_dry_run(canonical_map: dict[str, ArgSpec], stats: MineStats) -> None:
    print("=" * 78)
    print(f"corpus_miner dry-run -- {stats.canonical_args_after_filter} canonical args")
    print("=" * 78)
    print(
        f"Sources:          {stats.fs_xamls} fs XAMLs + "
        f"{stats.nupkg_xamls} nupkg XAMLs ({stats.nupkgs_scanned} nupkgs)"
    )
    print(f"Raw declarations: {stats.raw_declarations}")
    print(f"Unique args:      {stats.unique_args}")
    print(f"Parse errors:     {stats.parse_errors}")
    print("-" * 78)
    for name, spec in canonical_map.items():
        alt = ""
        if spec.alternatives:
            alt = "  alt=" + ", ".join(f"{t}({c})" for t, c in spec.alternatives[:3])
        print(
            f"  {name:<40s}  occ={spec.occurrences:<5d}  "
            f"conf={spec.confidence:.3f}  type={spec.canonical_type}{alt}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="corpus_miner",
        description="Mine canonical argument declarations from Sicoob XAML corpus.",
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        type=Path,
        default=None,
        help="Directories (or .nupkg files) to scan. Defaults to .nupkgs, "
             "Desktop\\temp, and OneDrive Sicoob Projects.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Path to generated _canonical_args.py (default: in-package).",
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=MIN_OCCURRENCES,
        help=f"Minimum occurrences to include an arg (default: {MIN_OCCURRENCES}).",
    )
    parser.add_argument(
        "--no-nupkgs",
        action="store_true",
        help="Skip .nupkg archives even if found under roots.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print canonical map to stdout instead of writing the module.",
    )
    args = parser.parse_args(argv)

    roots = args.roots if args.roots else _build_default_roots()
    if not roots:
        print(
            "[corpus_miner] error: no roots provided and no default roots exist.",
            file=sys.stderr,
        )
        return 2

    stats = MineStats(roots=list(roots))
    try:
        canonical_map = mine(
            roots,
            include_nupkgs=not args.no_nupkgs,
            min_occurrences=args.min_occurrences,
            stats=stats,
        )
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 10

    if args.dry_run:
        _print_dry_run(canonical_map, stats)
        return 0

    generate_python_module(
        canonical_map,
        args.output,
        stats=stats,
        min_occurrences=args.min_occurrences,
    )
    print(
        f"[corpus_miner] wrote {args.output} -- "
        f"{stats.canonical_args_after_filter} canonical args "
        f"(scanned {stats.fs_xamls} fs + {stats.nupkg_xamls} nupkg XAMLs)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
