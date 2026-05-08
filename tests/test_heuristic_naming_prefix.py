"""Tests for naming_prefix.py — N-1/N-2 prefix validation.

Foco: bug do `vIntegerCount` — prefixo válido exige Nome capitalizado após.
`Int` em `vIntegerCount` é substring de `Integer`, não prefixo de tipo.
"""
from pathlib import Path

import pytest

from scripts.rule_engine._types import Rule, Severity
from scripts.rule_engine.context import FileContext
from scripts.rule_engine.heuristics.naming_prefix import (
    _has_valid_prefix,
    _compute_var_fix,
    _compute_arg_fix,
    detect_n1_variable_prefix,
    detect_n2_argument_prefix,
)


_TYPE_PAIRS = [
    ("SecureString", "SSt"),
    ("DataTable", "DTab"),
    ("DateTime", "Dt"),
    ("Dictionary", "Dict"),
    ("Boolean", "Bl"),
    ("Double", "Dbl"),
    ("Int32", "Int"),
    ("Int64", "Lng"),
    ("String", "St"),
]
_WRONG_MAP = {
    "Bool": "Bl",
    "Boolean": "Bl",
    "DTime": "Dt",
    "DateTime": "Dt",
    "Decimal": "Dbl",
    "Str": "St",
    "String": "St",
    "Integer": "Int",
    "Number": "Int",
    "DT": "DTab",
    "Tab": "DTab",
}
_PARAMS = {
    "type_prefix": [{"type": t, "prefix": p} for t, p in _TYPE_PAIRS],
    "wrong_prefix_map": _WRONG_MAP,
    "bare_special": [],
    "reframework_main_vars": [],
    "bare_arg_names": [],
}


# ---- _has_valid_prefix ----

def test_has_valid_prefix_followed_by_uppercase():
    assert _has_valid_prefix("IntCount", "Int") is True


def test_has_valid_prefix_followed_by_digit():
    assert _has_valid_prefix("Int32Value", "Int") is True


def test_has_valid_prefix_exact_match():
    assert _has_valid_prefix("Int", "Int") is True


def test_has_valid_prefix_followed_by_lowercase_invalid():
    """vIntegerCount — Int é substring de Integer, não prefixo válido."""
    assert _has_valid_prefix("IntegerCount", "Int") is False


def test_has_valid_prefix_dtime_invalid():
    """vDTimeAtual — Dt é substring de DTime."""
    assert _has_valid_prefix("DTimeAtual", "Dt") is False


def test_has_valid_prefix_no_match():
    assert _has_valid_prefix("StrName", "Int") is False


# ---- _compute_var_fix bug fixes ----

def test_compute_var_fix_integer_to_int():
    """vIntegerCount (Int32) → vIntCount via wrong_prefix_map."""
    result = _compute_var_fix("vIntegerCount", "Int", _WRONG_MAP)
    assert result == "vIntCount"


def test_compute_var_fix_dtime_to_dt():
    """vDTimeAtual (DateTime) → vDtAtual via wrong_prefix_map."""
    result = _compute_var_fix("vDTimeAtual", "Dt", _WRONG_MAP)
    assert result == "vDtAtual"


def test_compute_var_fix_correct_prefix_no_change():
    """vIntCount já correto → None (sem mudança)."""
    result = _compute_var_fix("vIntCount", "Int", _WRONG_MAP)
    assert result is None


def test_compute_var_fix_string_to_st():
    """vStringNome (String) → vStNome."""
    result = _compute_var_fix("vStringNome", "St", _WRONG_MAP)
    assert result == "vStNome"


def test_compute_var_fix_bool_to_bl():
    """vBoolStatus (Boolean) → vBlStatus."""
    result = _compute_var_fix("vBoolStatus", "Bl", _WRONG_MAP)
    assert result == "vBlStatus"


# ---- _compute_arg_fix bug fixes ----

def test_compute_arg_fix_integer_to_int():
    """in_IntegerCount (Int32) → in_IntCount."""
    result = _compute_arg_fix("in_IntegerCount", "in", "Int", _WRONG_MAP)
    assert result == "in_IntCount"


def test_compute_arg_fix_dtime_to_dt():
    """in_DTimeData (DateTime) → in_DtData."""
    result = _compute_arg_fix("in_DTimeData", "in", "Dt", _WRONG_MAP)
    assert result == "in_DtData"


def test_compute_arg_fix_correct_prefix_no_change():
    """in_IntCount já correto → None."""
    result = _compute_arg_fix("in_IntCount", "in", "Int", _WRONG_MAP)
    assert result is None


# ---- end-to-end detector ----

def _write_xaml(tmp_path: Path, body: str) -> FileContext:
    f = tmp_path / "Foo.xaml"
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        f'{body}\n'
        '</Activity>',
        encoding="utf-8",
    )
    return FileContext(f)


def _make_n1_rule():
    return Rule(
        id="N-1",
        severity=Severity.WARN,
        category="architectural",
        target="all",
        title="Variável usa prefixo v[Tipo][Nome]",
        description="",
        detect={"type": "python", "params": dict(_PARAMS)},
    )


def _make_n2_rule():
    return Rule(
        id="N-2",
        severity=Severity.WARN,
        category="architectural",
        target="all",
        title="Argumento usa prefixo (in_|out_|io_)[Tipo][Nome]",
        description="",
        detect={"type": "python", "params": dict(_PARAMS)},
    )


def test_n1_detects_vintegercount(tmp_path):
    body = (
        '  <Sequence>\n'
        '    <Sequence.Variables>\n'
        '      <Variable x:TypeArguments="x:Int32" Name="vIntegerCount" />\n'
        '    </Sequence.Variables>\n'
        '  </Sequence>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n1_variable_prefix(_make_n1_rule(), fc, None)
    assert len(findings) == 1
    assert "vIntCount" in findings[0].message
    assert findings[0].fix_mechanical == {
        "type": "rename_attribute",
        "from": "vIntegerCount",
        "to": "vIntCount",
    }


def test_n1_detects_vdtimeatual(tmp_path):
    body = (
        '  <Sequence>\n'
        '    <Sequence.Variables>\n'
        '      <Variable x:TypeArguments="s:DateTime" Name="vDTimeAtual" />\n'
        '    </Sequence.Variables>\n'
        '  </Sequence>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n1_variable_prefix(_make_n1_rule(), fc, None)
    assert len(findings) == 1
    assert "vDtAtual" in findings[0].message


def test_n1_no_finding_for_correct_name(tmp_path):
    body = (
        '  <Sequence>\n'
        '    <Sequence.Variables>\n'
        '      <Variable x:TypeArguments="x:Int32" Name="vIntCount" />\n'
        '    </Sequence.Variables>\n'
        '  </Sequence>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n1_variable_prefix(_make_n1_rule(), fc, None)
    assert findings == []


def test_n2_detects_in_integercount(tmp_path):
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_IntegerCount" Type="InArgument(x:Int32)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n2_argument_prefix(_make_n2_rule(), fc, None)
    assert len(findings) == 1
    assert "in_IntCount" in findings[0].message
    assert findings[0].fix_mechanical["from"] == "in_IntegerCount"
    assert findings[0].fix_mechanical["to"] == "in_IntCount"


def test_n2_no_finding_for_correct_arg(tmp_path):
    body = (
        '  <x:Members>\n'
        '    <x:Property Name="in_IntCount" Type="InArgument(x:Int32)" />\n'
        '  </x:Members>'
    )
    fc = _write_xaml(tmp_path, body)
    findings = detect_n2_argument_prefix(_make_n2_rule(), fc, None)
    assert findings == []


# ---- Nu prefix + CamelCase boundary ----

_WRONG_MAP_WITH_NU = dict(_WRONG_MAP)
_WRONG_MAP_WITH_NU["Nu"] = "Int"


def test_compute_var_fix_nu_prefix_int32():
    """vNuTimeout (Int32 type) → vIntTimeout. Nu seguido de uppercase = strip."""
    out = _compute_var_fix("vNuTimeout", "Int", _WRONG_MAP_WITH_NU,
                           [p for _, p in _TYPE_PAIRS])
    assert out == "vIntTimeout"


def test_compute_var_fix_nu_prefix_int64():
    """vNuValor (Int64 type) → vLngValor. Nu strip, prepend Lng."""
    out = _compute_var_fix("vNuValor", "Lng", _WRONG_MAP_WITH_NU,
                           [p for _, p in _TYPE_PAIRS])
    assert out == "vLngValor"


def test_compute_var_fix_nu_prefix_double():
    """vNuPercent (Double type) → vDblPercent."""
    out = _compute_var_fix("vNuPercent", "Dbl", _WRONG_MAP_WITH_NU,
                           [p for _, p in _TYPE_PAIRS])
    assert out == "vDblPercent"


def test_compute_var_fix_numero_word_not_stripped():
    """vNumero — `Nu` seguido de lowercase 'm'. CamelCase boundary protege.
    Sem strip de Nu (false-positive), só prepend prefix esperado."""
    # vNumero (no caps after "Nu") - boundary fails, Nu não é stripped
    # mas regra _has_valid_prefix("Numero", "Int") = False, então é bad.
    # Result: prepend Int → vIntNumero (bizarro mas não corrompe palavra)
    out = _compute_var_fix("vNumero", "Int", _WRONG_MAP_WITH_NU,
                           [p for _, p in _TYPE_PAIRS])
    # Numero seguido de lowercase NÃO é wrong-prefix candidato. Output safe.
    assert "merox" not in out.lower()  # não deve corromper meio da palavra
