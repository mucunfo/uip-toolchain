"""Regression tests for the `yaml` lane of AUDIT_2026-05-28.md.

Scope: rules.yaml only. These tests load the relevant rules via yaml.safe_load
and assert the corrected regex / params / severity. They use ONLY the `re` and
`yaml` stdlib/3rd-party modules and intentionally do NOT import uip_engine
(parallel-lane isolation: importing the package would couple to other lanes'
in-flight edits).

Findings covered: S-3, A-13, A-18, V-3, API-1 (x2), SP-1, XML-1, W-33,
W-11c..h, J-2, T-4, D-PINALERT (prose), rule_count.
"""

import os
import re

import yaml

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RULES_PATH = os.path.join(_REPO_ROOT, "rules.yaml")


def _load_rules():
    with open(_RULES_PATH, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    return {r["id"]: r for r in doc["rules"]}, doc


def _raw_rules_text():
    with open(_RULES_PATH, encoding="utf-8") as fh:
        return fh.read()


RULES, DOC = _load_rules()


# --------------------------------------------------------------------------
# S-3 — detect drops dead lookahead; fix handles open AND close tags
# --------------------------------------------------------------------------

def test_s3_detect_matches_open_not_property_element_or_operation():
    pat = re.compile(RULES["S-3"]["detect"]["pattern"])
    # BAD: real <ui:Assign> open tags must match
    assert pat.search('<ui:Assign DisplayName="bad" />')
    assert pat.search("<ui:Assign>")
    # GOOD: never the property-element / sibling forms
    assert not pat.search("<ui:AssignOperation>")
    assert not pat.search("<ui:MultipleAssign>")
    assert not pat.search("<ui:Assign.To>")
    assert not pat.search("<ui:Assign.Value>")


def test_s3_fix_rewrites_open_and_close_tag():
    fix = RULES["S-3"]["fix"]["mechanical"]
    assert fix["type"] == "regex_replace"
    pat = re.compile(fix["pattern"])
    repl = fix["replacement"]
    src = (
        '<ui:Assign x="1"><ui:Assign.To>a</ui:Assign.To>'
        "<ui:Assign.Value>b</ui:Assign.Value></ui:Assign>"
    )
    out = pat.sub(repl, src)
    # BAD form (the open+close Assign corruption the audit flagged) now repaired:
    assert out == (
        '<Assign x="1"><ui:Assign.To>a</ui:Assign.To>'
        "<ui:Assign.Value>b</ui:Assign.Value></Assign>"
    )
    # property-element setters Assign.To / Assign.Value are preserved (not renamed)
    assert "<ui:Assign.To>" in out and "<ui:Assign.Value>" in out
    # AssignOperation untouched
    assert pat.sub(repl, "<ui:AssignOperation>") == "<ui:AssignOperation>"


def test_s3_dead_lookahead_removed():
    # The inert (?!Operation) negative-lookahead must be gone.
    assert "(?!Operation)" not in RULES["S-3"]["detect"]["pattern"]


# --------------------------------------------------------------------------
# A-13 — match XAML-escaped quote form; keep excluding in_Config(...)
# --------------------------------------------------------------------------

def test_a13_matches_escaped_quote_form():
    pat = re.compile(RULES["A-13"]["detect"]["pattern"])
    # BAD: the ONLY form that occurs on disk (&quot;-escaped) now matches
    bad_escaped = 'Exception="[New Exception(&quot;hardcoded message&quot;)]"'
    assert pat.search(bad_escaped)
    m = pat.search(bad_escaped)
    assert m.group(1) == "hardcoded message"
    # the raw-quote form still matches (belt-and-suspenders)
    bad_raw = 'Exception="[New Exception("hardcoded message")]"'
    assert pat.search(bad_raw)


def test_a13_does_not_flag_in_config_variable_arg():
    pat = re.compile(RULES["A-13"]["detect"]["pattern"])
    good = 'Exception="[New Exception(in_Config(&quot;Chave&quot;).ToString)]"'
    assert not pat.search(good)


# --------------------------------------------------------------------------
# A-18 — broaden prefix to both ui: and uix:
# --------------------------------------------------------------------------

def test_a18_matches_both_namespaces():
    pat = re.compile(RULES["A-18"]["detect"]["pattern"])
    # BAD: modern UIA serialized as uix: (the silent miss) must now match
    assert pat.search("<uix:NApplicationCard>")
    assert pat.search('<uix:NClick DisplayName="x" />')
    # legacy ui: still matches
    assert pat.search("<ui:NTypeInto ")
    # word boundary holds (no partial-name match)
    assert not pat.search("<ui:NApplicationCardFoo")


# --------------------------------------------------------------------------
# V-3 — double-escape detect/fix, scoped to Condition/Expression/ExpressionText.
# NOTE: widening to Message/OutputMessageFormat/Value was REVERTED — the blind
# regex_replace of `&amp;quot;` produces a bare `"` that breaks VB parse (orphan
# `quot`, rolled back by the safety gate -> the rule never applies and the project
# FAILs). Those attrs are a documented silent-miss GAP needing a context-aware
# detector (separate gt|lt auto-fix from quot manual). See rules.yaml V-3 comment.
# --------------------------------------------------------------------------

def test_v3_detect_matches_scoped_expression_attrs():
    pat = re.compile(RULES["V-3"]["detect"]["pattern"])
    # BAD: double-escape inside the safely-anchored expression attrs
    assert pat.search('<If Condition="[a &amp;lt; b]" />')
    assert pat.search('Expression="[a &amp;gt; b]"')
    assert pat.search('ExpressionText="[a &amp;gt; b]"')


def test_v3_detect_does_not_match_documented_gap_attrs():
    pat = re.compile(RULES["V-3"]["detect"]["pattern"])
    # Documented GAP (not a regression): Message/OutputMessageFormat are NOT
    # auto-detected, because the quot auto-fix is unsafe. Pinning the scope so a
    # future widening must consciously address the quot-context problem.
    assert not pat.search('<ui:LogMessage Message="[x &amp;gt; y]" />')
    assert not pat.search('OutputMessageFormat="[v &amp;quot;x&amp;quot;]"')


def test_v3_detect_does_not_match_single_encode():
    pat = re.compile(RULES["V-3"]["detect"]["pattern"])
    # GOOD: correct single-encode (&gt;) must NOT trigger
    assert not pat.search('<If Condition="[x &gt; y]" />')


def test_v3_fix_repairs_gt_lt_operators_in_scope():
    fix = RULES["V-3"]["fix"]["mechanical"]
    pat = re.compile(fix["pattern"])
    repl = fix["replacement"]
    # gt/lt -> operators (safe). quot is intentionally out of the widened scope.
    src = '<If Condition="[a &amp;gt; b]" />'
    assert pat.sub(repl, src) == '<If Condition="[a &gt; b]" />'


# --------------------------------------------------------------------------
# API-1 — order-independent detect + corrected description (default False)
# --------------------------------------------------------------------------

def test_api1_detect_order_independent():
    pat = re.compile(RULES["API-1"]["detect"]["pattern"])
    # BAD that WAS silently missed: ContinueOnError serialized BEFORE Method
    reversed_order = (
        '<ui:HttpClient ContinueOnError="True" DisplayName="POST x" '
        'Method="POST" Endpoint="u" />'
    )
    assert pat.search(reversed_order)
    # BAD normal order still matches
    assert pat.search('<ui:HttpClient Method="POST" ContinueOnError="True" />')
    # GOOD: idempotent verb is safe
    assert not pat.search('<ui:HttpClient Method="GET" ContinueOnError="True" />')
    # GOOD: no explicit ContinueOnError="True"
    assert not pat.search('<ui:HttpClient Method="POST" Endpoint="u" />')


def test_api1_description_default_is_false():
    desc = RULES["API-1"]["description"]
    # API-1 must NOT claim the default is True (SYS-5 is the source of truth: default False)
    assert "default=True" not in desc
    assert "False" in desc


def test_sys5_remains_source_of_truth():
    # Unchanged: SYS-5 keeps the canonical statement about the default.
    assert "ContinueOnError=False" in RULES["SYS-5"]["description"]


# --------------------------------------------------------------------------
# SP-1 / XML-1 — min -> exact so upward drift is flagged
# --------------------------------------------------------------------------

def test_sp1_uses_exact_pin():
    params = RULES["SP-1"]["detect"]["params"]
    assert params.get("exact") == "2.0.3"
    assert "min" not in params


def test_xml1_uses_exact_pin():
    params = RULES["XML-1"]["detect"]["params"]
    assert params.get("exact") == "1.1.0"
    assert "min" not in params


# --------------------------------------------------------------------------
# W-33 — severity ERROR -> WARN (matches contextual class + WARN-only prose)
# --------------------------------------------------------------------------

def test_w33_severity_is_warn():
    assert RULES["W-33"]["severity"] == "WARN"
    assert RULES["W-33"]["fix"]["apply_class"] == "contextual"


# --------------------------------------------------------------------------
# W-11c..h — standardize to ERROR (match W-11a/b hard compile-error siblings)
# --------------------------------------------------------------------------

def test_w11_catalog_family_is_error():
    for rid in ("W-11a", "W-11b", "W-11c", "W-11d", "W-11e", "W-11f", "W-11g", "W-11h"):
        assert RULES[rid]["severity"] == "ERROR", (rid, RULES[rid]["severity"])


def test_w11_baseline_rules_stay_warn():
    # W-11x / W-11y are best-effort baselines, intentionally NOT promoted.
    for rid in ("W-11x", "W-11y"):
        assert RULES[rid]["severity"] == "WARN", (rid, RULES[rid]["severity"])


def test_w11_criterion_header_comment_present():
    raw = _raw_rules_text()
    assert "W-11 AssemblyReference family — severity criterion" in raw


# --------------------------------------------------------------------------
# J-2 — reworded to single-field studioVersion check
# --------------------------------------------------------------------------

def test_j2_title_and_description_dropped_packages_claim():
    j2 = RULES["J-2"]
    assert "abaixo do m" in j2["title"]  # "abaixo do mínimo"
    assert "packages" not in j2["title"]
    # the bogus "e packages 25.x" / "vs packages" claim is gone
    assert "25.x" not in j2["description"]
    assert "vs packages" not in j2["description"]
    # detector unchanged: still single-field min check
    assert j2["detect"]["params"]["path"] == "studioVersion"
    assert j2["detect"]["params"]["min"] == "23.10.0"


# --------------------------------------------------------------------------
# T-4 — description trimmed to "extra" only (drop "ou faltando")
# --------------------------------------------------------------------------

def test_t4_description_only_extra():
    desc = RULES["T-4"]["description"]
    assert "extra" in desc
    assert "ou faltando" not in desc
    # detector scope unchanged
    assert RULES["T-4"]["detect"]["params"]["direction"] == "caller_extra"


# --------------------------------------------------------------------------
# D-PINALERT — prose/comment corrected
# --------------------------------------------------------------------------

def test_dpinalert_prose_truthful_about_nwindow_operation():
    prose = RULES["D-PINALERT"]["fix"]["prose"]
    # NWindowOperation IS auto-applied via strip_nwindow_operation (deterministic)
    assert "strip_nwindow_operation" in prose


def test_dpinalert_no_dangling_check_perfect_reference():
    raw = _raw_rules_text()
    # the non-existent module reference must be gone, replaced by the real location
    assert "check_perfect" not in raw
    assert "_effective_apply_class" in raw


# --------------------------------------------------------------------------
# rule_count — dead "auto-update" comment corrected/removed
# --------------------------------------------------------------------------

def test_rule_count_comment_not_misleading():
    raw = _raw_rules_text()
    assert "auto-update at validation" not in raw
    # field may stay but the comment must no longer claim auto-update behavior
    assert DOC["metadata"]["rule_count"] == 0


# --------------------------------------------------------------------------
# whole-file sanity: rules.yaml still parses and every covered rule exists
# --------------------------------------------------------------------------

def test_all_covered_rules_present_and_yaml_valid():
    for rid in (
        "S-3", "A-13", "A-18", "V-3", "API-1", "SYS-5", "SP-1", "XML-1",
        "W-33", "W-11c", "W-11d", "W-11e", "W-11f", "W-11g", "W-11h",
        "J-2", "T-4", "D-PINALERT",
    ):
        assert rid in RULES, rid
