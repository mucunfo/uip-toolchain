"""Golden tests for fuzzy_matcher — UiPath FuzzyMatcher.Matches() port.

Refs: sicoob-studio-research/02-healing-agent.md linhas 76-90.
"""
from __future__ import annotations

import pytest

from scripts.rule_engine.fuzzy_matcher import (
    matches, levenshtein_distance, levenshtein_ratio, MatchResult,
    _preprocess, _token_sort_ratio,
)


# ---------------------------------------------------------------------------
# Step 1/2 — null handling
# ---------------------------------------------------------------------------

def test_null_null_matches():
    """Both null -> match with score 1.0."""
    r = matches(None, None)
    assert r.matched is True
    assert r.score == 1.0


def test_null_xor_no_match():
    """One side null, other not -> no match."""
    assert matches(None, "foo").matched is False
    assert matches(None, "foo").score == 0.0
    assert matches("foo", None).matched is False
    assert matches("foo", None).score == 0.0


# ---------------------------------------------------------------------------
# Step 4 — literal equality
# ---------------------------------------------------------------------------

def test_literal_equality():
    r = matches("foo", "foo")
    assert r.matched is True
    assert r.score == 1.0


def test_literal_equality_preserves_special_chars():
    """Step 4 happens BEFORE preprocess — special chars should still match 1.0."""
    r = matches("Salvar & Continuar!", "Salvar & Continuar!")
    assert r.matched is True
    assert r.score == 1.0


# ---------------------------------------------------------------------------
# Levenshtein primitive — subst cost = 2 (dossier linha 90)
# ---------------------------------------------------------------------------

def test_subst_cost_2():
    """foo -> fox: 1 substitution at cost 2 == delete+insert cost 2.
    UiPath subst_cost=2 makes both paths equivalent."""
    assert levenshtein_distance("foo", "fox") == 2


def test_identical_strings_distance_zero():
    assert levenshtein_distance("abc", "abc") == 0


def test_empty_string_distance():
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("abc", "") == 3
    assert levenshtein_distance("", "abc") == 3


def test_pure_insertion_cost_1_each():
    """Insertions cost 1 each. foo -> foofoo = 3 insertions = 3."""
    assert levenshtein_distance("foo", "foofoo") == 3


def test_pure_deletion_cost_1_each():
    assert levenshtein_distance("foofoo", "foo") == 3


# ---------------------------------------------------------------------------
# Levenshtein ratio
# ---------------------------------------------------------------------------

def test_levenshtein_ratio_identical():
    assert levenshtein_ratio("salvar", "salvar") == 1.0


def test_levenshtein_ratio_both_empty():
    assert levenshtein_ratio("", "") == 1.0


def test_levenshtein_ratio_in_unit_interval():
    """Ratio is always in [0, 1] even with subst_cost=2."""
    for a, b in [("a", "b"), ("hello", "world"), ("foo", "fbaroo"), ("xyz", "")]:
        r = levenshtein_ratio(a, b)
        assert 0.0 <= r <= 1.0, f"ratio({a!r}, {b!r}) = {r} out of range"


# ---------------------------------------------------------------------------
# Step 5 — preprocess (lowercase + keep letters/digits/whitespace + collapse + trim)
# ---------------------------------------------------------------------------

def test_preprocess_lowercases():
    assert _preprocess("SALVAR") == "salvar"


def test_preprocess_strips_punctuation():
    assert _preprocess("Salvar!") == "salvar"
    assert _preprocess("Salvar & Continuar.") == "salvar continuar"


def test_preprocess_collapses_whitespace():
    assert _preprocess("Salvar    e\t\t Continuar") == "salvar e continuar"


def test_preprocess_keeps_digits():
    assert _preprocess("Botao 123") == "botao 123"


def test_preprocess_trims():
    assert _preprocess("   Salvar   ") == "salvar"


# ---------------------------------------------------------------------------
# Step 7 — token-sort
# ---------------------------------------------------------------------------

def test_token_sort_reorders_words():
    """Sorted by word, joined by single space."""
    # After preprocess + sort, both produce same string -> ratio 1.0
    a = _preprocess("Salvar e Continuar")
    b = _preprocess("Continuar e Salvar")
    assert _token_sort_ratio(a, b) == 1.0


def test_token_sort_word_order_high_score():
    """Through `matches()` token-sort is scaled by 0.95, so we expect >= ~0.95."""
    r = matches("Salvar e Continuar", "Continuar e Salvar")
    # Token-sort gives 1.0 * 0.95 = 0.95. Levenshtein on raw gives lower.
    assert r.score >= 0.94
    assert r.matched is True


# ---------------------------------------------------------------------------
# Score = max(step 6, step 7)
# ---------------------------------------------------------------------------

def test_punct_noise_stripped_by_preprocess():
    """Step 5 strips non-letter/digit/space chars. `S@lv@r` -> `slvr` after
    preprocess. With subst_cost=2 the distance to `salvar` is 2 inserts = 2,
    total 10, ratio = 8/10 = 0.8 -> matches.

    This documents the surprising-but-correct UiPath behavior: punctuation
    noise is FORGIVEN (stripped) while length drift is PENALIZED (insert cost).
    """
    noise = matches("Salvar", "S@lv@r")
    assert noise.matched is True
    # Suffix drift inserts 12 chars worth of " e Continuar" -> heavy penalty.
    suffix = matches("Salvar", "Salvar e Continuar")
    # 6 + 18 = 24 total chars; 12 insertions cost 12; ratio = 12/24 = 0.5
    assert suffix.score < 0.6
    assert suffix.matched is False


def test_score_is_max_of_two_ratios():
    """When word-order differs but characters are identical, token-sort wins."""
    r = matches("alpha beta", "beta alpha")
    # Levenshtein on raw is mid; token-sort after preprocess produces identical
    # sorted strings -> ratio 1.0 * 0.95 = 0.95
    assert r.score >= 0.94


# ---------------------------------------------------------------------------
# Threshold default 0.7 / case insensitivity
# ---------------------------------------------------------------------------

def test_threshold_default_case_insensitive():
    """`Confirmar OK` vs `Confirmar Ok` differs only in case -> matches via
    invariant lowercase preprocess."""
    r = matches("Confirmar OK", "Confirmar Ok")
    assert r.matched is True
    assert r.score >= 0.95  # Should be near-1.0 (identical post-preprocess)


def test_threshold_below_default_no_match():
    """Wildly different strings drop below 0.7 threshold."""
    r = matches("Salvar", "Cancelar")
    assert r.matched is False


def test_custom_threshold_zero_always_matches():
    """fuzzy_level=0.0 means even score 0 matches."""
    r = matches("foo", "bar", fuzzy_level=0.0)
    assert r.matched is True


def test_custom_threshold_one_only_perfect():
    """fuzzy_level=1.0 only matches when score is exactly 1.0 (literal equality)."""
    assert matches("foo", "foo", fuzzy_level=1.0).matched is True
    # Imperfect match scaled by 0.999 falls just below
    assert matches("foo", "fo", fuzzy_level=1.0).matched is False


# ---------------------------------------------------------------------------
# Optional newline normalization
# ---------------------------------------------------------------------------

def test_normalize_newlines_off_by_default():
    """Without flag, \\r\\n stays as-is and counts as 2 chars different."""
    # Both have newlines so they should still preprocess down to same string
    r = matches("foo\nbar", "foo bar", normalize_newlines=False)
    # After preprocess both -> "foo bar" (whitespace collapse), so high score
    assert r.matched is True


def test_normalize_newlines_on():
    r = matches("foo\r\nbar", "foo bar", normalize_newlines=True)
    assert r.matched is True


# ---------------------------------------------------------------------------
# Case sensitive mode
# ---------------------------------------------------------------------------

def test_case_sensitive_mode_distinguishes_case():
    """case_sensitive=True skips lowercase in preprocess. `OK` vs `ok` then
    has higher edit distance (2 substitutions * cost 2 = 4) vs 4 char total."""
    r = matches("OK", "ok", case_sensitive=True)
    # Total chars = 4, distance = 4 (2 subs * cost 2) -> ratio = 0
    # Token-sort same problem. Score below 0.7.
    assert r.matched is False


# ---------------------------------------------------------------------------
# MatchResult dataclass contract
# ---------------------------------------------------------------------------

def test_match_result_is_frozen():
    r = matches("foo", "foo")
    assert isinstance(r, MatchResult)
    with pytest.raises(Exception):
        r.matched = False  # frozen
