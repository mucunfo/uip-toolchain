"""Regression tests for AUDIT_2026-05-28 findings S-9 and N-13 (naming lane).

Both findings are PT-BR/EN homograph false positives. The over-flagged words
live PURELY in rules.yaml params (S-9 `forbidden`, N-13 `verbs`) — NOT hardcoded
in heuristics/naming.py — so the actual data fix is a rules.yaml change owned by
the yaml lane. The naming.py detectors are correct: they flag exactly what the
params declare.

These tests pin the DETECTOR CONTRACT so the yaml-lane data fix has a concrete
regression anchor:

  S-9  — "Data" is the PT-BR word for "date" (in_DataNascimento, vDataVencimento).
         With "Data" in `forbidden`, the detector flags it (the FP). Once the yaml
         lane drops "Data" from `forbidden`, the FP disappears while every other
         forbidden EN word still fires.

  N-13 — "Lista" is the PT-BR noun "a list" (vListaClientes, vListaNegra). It is
         also the present-3sg of "listar". With "Lista" in `verbs`, the detector
         flags the noun usages (the FP). The CITED trigger `vLstListaClientes` is a
         non-issue (the `Lst` type-prefix is not stripped, stem stays `LstLista...`,
         no verb match). Once the yaml lane drops the noun-homographs from `verbs`,
         the noun FPs disappear while genuine verbs (Busca/Atualiza/Valida) still
         fire.

This file does NOT modify naming.py (no code-level fix is appropriate: a hardcoded
noun/date allowlist would violate the module's "no hardcoded lists" contract and
the project's "rules are CORRECTED not suppressed" policy — the correction is data,
applied in the yaml lane).
"""
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext
from uip_engine.heuristics.naming import (
    detect_s9_pt_br,
    detect_n13_verb_infinitive,
    detect_s6_xclass_filename,
)


def _make_s6_rule() -> Rule:
    return Rule(
        id="S-6", severity=Severity.WARN, category="architectural", target="all",
        title="x:Class igual filename sem extensao", description="",
        detect={"type": "python", "params": {
            "module": "uip_engine.heuristics.naming",
            "function": "detect_s6_xclass_filename"}},
        fix={"mechanical": {"type": "rename_xclass"}, "prose": "rename x:Class"},
    )


def _write_named(tmp_path: Path, filename: str, xclass: str, body: str = "") -> FileContext:
    f = tmp_path / filename
    f.write_text(
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<Activity x:Class="{xclass}" xmlns:this="clr" xmlns:x="x">{body}</Activity>',
        encoding="utf-8",
    )
    return FileContext(f)


def test_s6_numbered_filename_emits_no_mech(tmp_path):
    """Filename numerado/com espaco (NAO e' x:Class valido) -> S-6 nao pode
    carregar rename_xclass mech (geraria `<this:1.1 ...>` = XML invalido ->
    rollback infinito no batch). Surfacea como contextual (renomear o ARQUIVO)."""
    fc = _write_named(
        tmp_path, "1.1 ObtemEstruturaEmailTabRegras.xaml", "OldClass",
        "<this:OldClass.in_Arg><x:String>v</x:String></this:OldClass.in_Arg>",
    )
    findings = detect_s6_xclass_filename(_make_s6_rule(), fc, None)
    assert len(findings) == 1
    assert findings[0].fix_mechanical is None, (
        "numbered filename must NOT carry rename_xclass mech (would produce "
        "malformed <this:1.1 ...> tag)"
    )


def test_s6_valid_filename_keeps_mech(tmp_path):
    """Filename que e' identificador valido -> S-6 mantem o rename_xclass mech."""
    fc = _write_named(tmp_path, "ObtemEstrutura.xaml", "OldClass")
    findings = detect_s6_xclass_filename(_make_s6_rule(), fc, None)
    assert len(findings) == 1
    assert findings[0].fix_mechanical is not None
    assert findings[0].fix_mechanical.get("type") == "rename_xclass"


def _write_xaml(tmp_path: Path, members: str) -> FileContext:
    f = tmp_path / "Worker.xaml"
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        '  <x:Members>\n'
        f'{members}\n'
        '  </x:Members>\n'
        '</Activity>',
        encoding="utf-8",
    )
    return FileContext(f)


def _prop(name: str) -> str:
    return f'    <x:Property Name="{name}" Type="InArgument(x:String)" />'


def _var(name: str) -> str:
    return f'    <Variable x:TypeArguments="x:String" Name="{name}" />'


# --- S-9 detector contract --------------------------------------------------

# The exact forbidden list shipped in rules.yaml (excerpt that matters here).
_S9_FORBIDDEN_WITH_DATA = ["File", "Path", "Data", "Source", "Value"]
_S9_FORBIDDEN_WITHOUT_DATA = ["File", "Path", "Source", "Value"]  # yaml-lane fix
_S9_EXCEPTIONS = ["Config", "Item", "Row", "Element"]


def _make_s9_rule(forbidden):
    return Rule(
        id="S-9",
        severity=Severity.WARN,
        category="architectural",
        target="all",
        title="Identificadores em PT-BR",
        description="",
        detect={
            "type": "python",
            "params": {"forbidden": list(forbidden), "exceptions": list(_S9_EXCEPTIONS)},
        },
    )


def _ids(findings):
    # extract the offending identifier from each finding message
    return [f.message for f in findings]


def test_s9_flags_data_when_present_in_forbidden(tmp_path):
    """Documents the FP: with 'Data' in forbidden, in_DataNascimento is flagged."""
    fc = _write_xaml(tmp_path, _prop("in_DataNascimento"))
    findings = detect_s9_pt_br(_make_s9_rule(_S9_FORBIDDEN_WITH_DATA), fc, None)
    assert len(findings) == 1
    assert "Data" in findings[0].message
    assert "in_DataNascimento" in findings[0].message


def test_s9_no_flag_when_data_removed_from_forbidden(tmp_path):
    """yaml-lane fix: dropping 'Data' from forbidden clears the PT-BR FP."""
    members = "\n".join([
        _prop("in_DataNascimento"),
        _var("vDataVencimento"),
        _prop("out_DataFinal"),
    ])
    fc = _write_xaml(tmp_path, members)
    findings = detect_s9_pt_br(_make_s9_rule(_S9_FORBIDDEN_WITHOUT_DATA), fc, None)
    assert findings == [], _ids(findings)


def test_s9_still_flags_other_en_words_after_data_removed(tmp_path):
    """Removing 'Data' must NOT weaken detection of genuine EN words."""
    members = "\n".join([
        _prop("in_FilePath"),         # File at '_' boundary — genuine EN flag
        _prop("in_SourceValue"),      # Source / Value — genuine EN
        _var("vDataVencimento"),      # Data — must NOT flag now
    ])
    fc = _write_xaml(tmp_path, members)
    findings = detect_s9_pt_br(_make_s9_rule(_S9_FORBIDDEN_WITHOUT_DATA), fc, None)
    flagged = _ids(findings)
    # vDataVencimento must not appear among flagged identifiers
    assert not any("vDataVencimento" in m for m in flagged), flagged
    # at least the genuine EN identifiers are still caught
    assert any("in_FilePath" in m for m in flagged), flagged
    assert any("in_SourceValue" in m for m in flagged), flagged


# --- N-13 detector contract -------------------------------------------------

_N13_TARGETS = ["filename", "xclass", "property_name", "variable_name"]

# Verb list including the noun-homographs (as shipped) ...
_N13_VERBS_WITH_NOUNS = [
    {"wrong": "Busca", "right": "Buscar"},
    {"wrong": "Atualiza", "right": "Atualizar"},
    {"wrong": "Valida", "right": "Validar"},
    {"wrong": "Lista", "right": "Listar"},   # homograph: noun "a list"
    {"wrong": "Trata", "right": "Tratar"},   # homograph: noun "treatment/deal"
]
# ... and the yaml-lane fix that drops the ambiguous noun-homographs.
_N13_VERBS_NO_NOUNS = [
    {"wrong": "Busca", "right": "Buscar"},
    {"wrong": "Atualiza", "right": "Atualizar"},
    {"wrong": "Valida", "right": "Validar"},
]


def _make_n13_rule(verbs):
    return Rule(
        id="N-13",
        severity=Severity.WARN,
        category="architectural",
        target="all",
        title="Identificador com verbo deve usar infinitivo",
        description="",
        detect={
            "type": "python",
            "params": {"targets": list(_N13_TARGETS), "verbs": list(verbs)},
        },
    )


def test_n13_cited_trigger_is_a_non_issue(tmp_path):
    """The audit's CITED trigger `vLstListaClientes` does NOT misbehave: the `Lst`
    type-prefix is not stripped (s[2]='t' is lowercase), the stem stays
    `LstListaClientes`, which startswith no verb. Confirms the cited evidence
    was wrong — this is the conservative guard for N-13."""
    fc = _write_xaml(tmp_path, _var("vLstListaClientes"))
    findings = detect_n13_verb_infinitive(_make_n13_rule(_N13_VERBS_WITH_NOUNS), fc, None)
    assert findings == [], _ids(findings)


def test_n13_noun_homograph_lista_is_flagged_when_present(tmp_path):
    """Documents the confirmed FP: noun 'Lista' (a list) flagged as verb when the
    homograph is in the verb list."""
    members = "\n".join([
        _var("vListaClientes"),   # noun: list of clients
        _var("vListaNegra"),      # noun: blacklist
        _prop("in_ListaContas"),  # noun: list of accounts
    ])
    fc = _write_xaml(tmp_path, members)
    findings = detect_n13_verb_infinitive(_make_n13_rule(_N13_VERBS_WITH_NOUNS), fc, None)
    flagged = _ids(findings)
    assert any("vListaClientes" in m for m in flagged), flagged
    assert any("vListaNegra" in m for m in flagged), flagged
    assert any("in_ListaContas" in m for m in flagged), flagged


def test_n13_noun_homograph_cleared_when_lista_removed(tmp_path):
    """yaml-lane fix: dropping the noun-homograph 'Lista'/'Trata' clears the noun
    FPs while genuine present-3sg verbs still fire."""
    members = "\n".join([
        _var("vListaClientes"),       # noun — must NOT flag now
        _var("vListaNegra"),          # noun — must NOT flag now
        _prop("in_ListaContas"),      # noun — must NOT flag now
        _var("vBuscaToken"),          # genuine verb — must STILL flag
        _prop("in_StAtualizaConfig"), # genuine verb — must STILL flag
        _var("vValidaRegras"),        # genuine verb — must STILL flag
    ])
    fc = _write_xaml(tmp_path, members)
    findings = detect_n13_verb_infinitive(_make_n13_rule(_N13_VERBS_NO_NOUNS), fc, None)
    flagged = _ids(findings)
    # noun homographs gone
    assert not any("Lista" in m for m in flagged), flagged
    # genuine verbs preserved
    assert any("vBuscaToken" in m for m in flagged), flagged
    assert any("in_StAtualizaConfig" in m for m in flagged), flagged
    assert any("vValidaRegras" in m for m in flagged), flagged


def test_n13_genuine_verbs_unaffected_by_noun_removal(tmp_path):
    """Removing noun-homographs must not change behavior for clearly-verb names."""
    fc = _write_xaml(tmp_path, _var("vBuscaDossie"))
    with_nouns = detect_n13_verb_infinitive(_make_n13_rule(_N13_VERBS_WITH_NOUNS), fc, None)
    without_nouns = detect_n13_verb_infinitive(_make_n13_rule(_N13_VERBS_NO_NOUNS), fc, None)
    assert len(with_nouns) == 1
    assert len(without_nouns) == 1
    assert with_nouns[0].message == without_nouns[0].message
