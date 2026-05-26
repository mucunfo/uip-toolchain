"""fuzzy_matcher — UiPath FuzzyMatcher.Matches() port Python offline.

Reproduz algoritmo dossier sicoob-studio-research/02-healing-agent.md (Stream E):
  - Levenshtein DP com substitution cost = 2 (NAO textbook 1) — dossier linha 90
  - Levenshtein ratio + token-sort ratio
  - Score = max(both), threshold check

Permite pre-flight selector validation offline (sem driver UiAutomation).
Stage 9+: usar contra UI-tree snapshot.

Algoritmo (dossier linhas 76-89):
  1. null/null -> match (score 1.0).
  2. null XOR -> no match.
  3. Normalize newlines (optional).
  4. Literal equality -> 1.0.
  5. Pre-process: lowercase invariant, keep letters/digits/whitespace only,
     collapse runs, trim.
  6. Levenshtein ratio: (L1 + L2 - editDistance) / (L1 + L2), scale * 0.999.
  7. Token-sort ratio: sort whitespace-words alphabetically + Levenshtein-ratio,
     scale * 0.95.
  8. Score = max(step 6, step 7).
  9. Return MatchResult(score >= threshold, score).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# UiPath constants — see dossier sicoob-studio-research/02-healing-agent.md linhas 83-87.
# Step 6 produces a slightly-discounted ratio for "imperfect" matches even when
# the edit distance is 0 in the post-processed form (literal equality is checked
# earlier and returns 1.0 directly). Step 7 uses a heavier discount because
# token-sort is a coarser signal than literal Levenshtein.
_IMPERFECT_SCALE = 0.999
_UNBASE_SCALE = 0.95

# Substitution cost in the Levenshtein DP. UiPath uses 2 (dossier linha 90).
# This makes a substitution equivalent to delete+insert cost, but the textbook
# variant uses 1 — the higher cost rewards character preservation over swaps.
_SUBST_COST = 2


@dataclass(frozen=True)
class MatchResult:
    """Output of FuzzyMatcher.Matches() — score in [0, 1] and threshold flag."""
    matched: bool
    score: float


def levenshtein_distance(a: str, b: str, *, subst_cost: int = _SUBST_COST) -> int:
    """Edit distance with custom substitution cost. UiPath uses subst_cost=2.

    Standard DP, row-rolling for O(min(L1, L2)) memory.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    # Ensure b is the shorter one to minimize memory in the row buffer.
    if len(a) < len(b):
        a, b = b, a

    prev_row = list(range(len(b) + 1))
    cur_row = [0] * (len(b) + 1)

    for i, ca in enumerate(a, 1):
        cur_row[0] = i
        for j, cb in enumerate(b, 1):
            if ca == cb:
                cur_row[j] = prev_row[j - 1]
            else:
                cur_row[j] = min(
                    prev_row[j] + 1,                 # deletion
                    cur_row[j - 1] + 1,              # insertion
                    prev_row[j - 1] + subst_cost,    # substitution
                )
        prev_row, cur_row = cur_row, prev_row

    return prev_row[len(b)]


def levenshtein_ratio(a: str, b: str, *, subst_cost: int = _SUBST_COST) -> float:
    """Compute (L1 + L2 - editDistance) / (L1 + L2). Range [0, 1].

    Both-empty returns 1.0 (perfect match). When subst_cost=2 the maximum
    edit-distance is L1+L2 (delete-all + insert-all), so the ratio stays in
    [0, 1] even with all-substitution paths.
    """
    total = len(a) + len(b)
    if total == 0:
        return 1.0
    dist = levenshtein_distance(a, b, subst_cost=subst_cost)
    if dist >= total:
        return 0.0
    return (total - dist) / total


# Regex: keep ASCII/Unicode letters, digits, whitespace. Discard everything else.
# `re.UNICODE` is default in Python 3 for `\w`/`\d`/`\s`. We strip non-(letter|digit|space).
_RE_KEEP = re.compile(r"[^\w\s]", re.UNICODE)
_RE_COLLAPSE_WS = re.compile(r"\s+", re.UNICODE)
_RE_NEWLINES = re.compile(r"\r\n|\r|\n")


def _normalize_newlines(s: str) -> str:
    """Step 3 — collapse \\r\\n/\\r/\\n to single space (matches UiPath behavior)."""
    return _RE_NEWLINES.sub(" ", s)


def _preprocess(s: str, *, case_sensitive: bool = False) -> str:
    """Step 5 — lowercase invariant + keep letters/digits/whitespace + collapse + trim.

    Underscores survive because `\\w` includes `_` in regex. UiPath's invariant
    lowercase is implemented here as Python `str.casefold()` (closer to the
    .NET "invariant culture" lowercase than naive `.lower()` for non-ASCII).
    """
    if not case_sensitive:
        s = s.casefold()
    s = _RE_KEEP.sub("", s)
    s = _RE_COLLAPSE_WS.sub(" ", s)
    return s.strip()


def _token_sort_ratio(a: str, b: str, *, subst_cost: int = _SUBST_COST) -> float:
    """Step 7 — split on whitespace, sort tokens alphabetically, rejoin, ratio.

    Operates on the already-preprocessed strings.
    """
    a_sorted = " ".join(sorted(a.split()))
    b_sorted = " ".join(sorted(b.split()))
    return levenshtein_ratio(a_sorted, b_sorted, subst_cost=subst_cost)


def matches(pattern: str | None, value: str | None, *,
            case_sensitive: bool = False,
            fuzzy_level: float = 0.7,
            normalize_newlines: bool = False) -> MatchResult:
    """Reproduz FuzzyMatcher.Matches() do UiPath.UIAutomationNext.Services.

    Args:
      pattern: expected text from the selector / activity. None = wildcard.
      value: actual text observed in the UI tree. None = nothing-found.
      case_sensitive: if False (default), apply invariant lowercase pre-process.
      fuzzy_level: threshold in [0, 1]. UiPath default is 0.7.
      normalize_newlines: collapse \\r\\n/\\r/\\n to space before comparing.

    Returns:
      MatchResult(matched, score). `matched = score >= fuzzy_level`.
    """
    # Step 1 — both null match perfectly (used when both sides explicitly opt-out).
    if pattern is None and value is None:
        return MatchResult(matched=True, score=1.0)

    # Step 2 — XOR null = no match (one side has an expectation, the other doesn't).
    if pattern is None or value is None:
        return MatchResult(matched=False, score=0.0)

    # Step 3 — newline normalization (optional, opt-in).
    if normalize_newlines:
        pattern = _normalize_newlines(pattern)
        value = _normalize_newlines(value)

    # Step 4 — literal equality returns 1.0 unconditionally (skips preprocess).
    if pattern == value:
        return MatchResult(matched=True, score=1.0)

    # Step 5 — preprocess both sides.
    p_norm = _preprocess(pattern, case_sensitive=case_sensitive)
    v_norm = _preprocess(value, case_sensitive=case_sensitive)

    # Step 6 — Levenshtein ratio on preprocessed strings, * 0.999.
    raw_ratio = levenshtein_ratio(p_norm, v_norm) * _IMPERFECT_SCALE

    # Step 7 — token-sort ratio, * 0.95.
    token_ratio = _token_sort_ratio(p_norm, v_norm) * _UNBASE_SCALE

    # Step 8 — score = max(step 6, step 7).
    score = max(raw_ratio, token_ratio)

    # Step 9 — threshold check.
    return MatchResult(matched=score >= fuzzy_level, score=score)
