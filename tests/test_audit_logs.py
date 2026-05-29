"""Regression tests for AUDIT_2026-05-28 lane=logs findings.

Covers:
  * N-15 — `presente` single-letter suffix bucket (a/e/i) over-matched PT-BR
    nouns. Now gated on a known-verb-stem check so noun-leading messages no
    longer false-positive while genuine present-indicative verbs still flag.
  * S-10 — restrictive-parent LogMessage detector only recorded the SELF-CLOSED
    form; the EXPANDED open+close form was silently missed. Now both forms are
    captured.

These tests target ONLY the audited behaviour; they do not touch any existing
shared test file.
"""
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.logs import (
    detect_n15_log_infinitive,
    detect_s10_logmessage_in_restrictive_parent,
)


# ---------------------------------------------------------------------------
# N-15 fixtures
# ---------------------------------------------------------------------------

_N15_PARAMS = {
    "exclude_paths": ["framework/", "tests/", "main.xaml", "process.xaml"],
    "forbidden_suffixes": {
        "gerundio": ["ando", "endo", "indo"],
        "passado": ["ou", "eu", "iu", "ei", "ava", "ia"],
        "presente": ["a", "e", "i"],
    },
    "valid_suffixes": ["ar", "er", "ir", "or"],
    "skip_first_words": [
        "Início", "Inicio", "Fim", "Erro", "Falha", "Sucesso", "Status",
        "Total", "Quantidade", "Valor", "Item", "Token", "ID", "Id", "TAG",
        "Log", "Dados", "Pasta", "Arquivo", "Email", "URL", "API", "DB",
        "XML", "JSON", "Title", "Message",
    ],
    "only_pure_literals": True,
}


def _make_n15_rule():
    return Rule(
        id="N-15",
        severity=Severity.INFO,
        category="architectural",
        target="all",
        title="LogMessage iniciada por verbo deve usar infinitivo",
        description="",
        detect={"type": "python", "params": dict(_N15_PARAMS)},
    )


def _n15_project(tmp_path: Path, message: str, name: str = "DoWork.xaml"):
    """Build a minimal project (so _is_in_chain is True) with one LogMessage."""
    proj = tmp_path / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "project.json").write_text(
        '{"name":"X","targetFramework":"Windows"}', encoding="utf-8"
    )
    f = proj / name
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        f'  <ui:LogMessage Level="Info" Message="{message}" />\n'
        '</Activity>',
        encoding="utf-8",
    )
    pc = ProjectContext(root=proj, project_json={"name": "X", "targetFramework": "Windows"})
    return _make_n15_rule(), FileContext(f), pc


# ---- N-15: presente bucket no longer flags nouns ----

def test_n15_presente_bucket_does_not_flag_noun_senha(tmp_path):
    """'Senha' ends in -a but is a NOUN, not a present-indicative verb."""
    rule, fc, pc = _n15_project(tmp_path, "Senha do cliente recuperada")
    findings = detect_n15_log_infinitive(rule, fc, pc)
    assert findings == [], f"unexpected FP on noun-leading message: {findings}"


def test_n15_presente_bucket_does_not_flag_other_nouns(tmp_path):
    """A sample of common PT-BR nouns ending in -a/-e/-i must NOT flag."""
    for noun_msg in (
        "Conta do cliente",
        "Linha processada",
        "Tabela carregada",
        "Base de dados",
        "Chave gerada",
        "Lote enviado",
        "Pagina aberta",
    ):
        rule, fc, pc = _n15_project(tmp_path, noun_msg)
        findings = detect_n15_log_infinitive(rule, fc, pc)
        assert findings == [], f"unexpected FP on '{noun_msg}': {findings}"


# ---- N-15: genuine present-indicative verbs still flag ----

def test_n15_presente_bucket_still_flags_known_verb_busca(tmp_path):
    """'Busca' is a known present-indicative verb form -> must flag (use 'Buscar')."""
    rule, fc, pc = _n15_project(tmp_path, "Busca dados do cliente")
    findings = detect_n15_log_infinitive(rule, fc, pc)
    assert len(findings) == 1
    assert "Busca" in findings[0].message


def test_n15_presente_bucket_flags_accented_verb_valida(tmp_path):
    """'Válida' (accented, ends 'a' = presente bucket) folds to 'valida'
    -> known verb stem -> flag (use 'Validar'). Exercises the accent-fold path.
    (NB: 3rd-person forms ending in 'm' like 'Obtém' are outside the a/e/i
    presente bucket by design, so they are intentionally not flagged here.)"""
    rule, fc, pc = _n15_project(tmp_path, "Válida o campo de entrada")
    findings = detect_n15_log_infinitive(rule, fc, pc)
    assert len(findings) == 1
    assert "Válida" in findings[0].message


def test_n15_presente_bucket_flags_atualiza(tmp_path):
    rule, fc, pc = _n15_project(tmp_path, "Atualiza TAG do XML")
    findings = detect_n15_log_infinitive(rule, fc, pc)
    assert len(findings) == 1


# ---- N-15: other (multi-char) buckets unaffected by the gate ----

def test_n15_gerundio_still_flags_unconditionally(tmp_path):
    """Gerundio bucket is unambiguous — flags regardless of verb-stem list."""
    rule, fc, pc = _n15_project(tmp_path, "Conectando ao banco")
    findings = detect_n15_log_infinitive(rule, fc, pc)
    assert len(findings) == 1
    assert "Conectando" in findings[0].message


def test_n15_passado_still_flags_unconditionally(tmp_path):
    """Passado bucket (-ou) is unambiguous — flags regardless of verb-stem list."""
    rule, fc, pc = _n15_project(tmp_path, "Recuperou dados de Controle")
    findings = detect_n15_log_infinitive(rule, fc, pc)
    assert len(findings) == 1
    assert "Recuperou" in findings[0].message


def test_n15_infinitive_never_flags(tmp_path):
    """Infinitive (-ar) is the desired form — never flags."""
    rule, fc, pc = _n15_project(tmp_path, "Buscar dados do cliente")
    findings = detect_n15_log_infinitive(rule, fc, pc)
    assert findings == []


# ---------------------------------------------------------------------------
# S-10 fixtures
# ---------------------------------------------------------------------------

def _make_s10_rule():
    return Rule(
        id="S-10",
        severity=Severity.ERROR,
        category="breaking",
        target="all",
        title="LogMessage em parent restritivo quebra compile",
        description="",
        detect={"type": "python", "params": {}},
    )


def _write_s10_xaml(tmp_path: Path, body: str) -> FileContext:
    f = tmp_path / "Foo.xaml"
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x" '
        'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib">\n'
        f'{body}\n'
        '</Activity>',
        encoding="utf-8",
    )
    return FileContext(f)


_EXPANDED_LOG = (
    '<ui:LogMessage DisplayName="Log" Level="Trace">'
    '<ui:LogMessage.Message>'
    '<InArgument x:TypeArguments="x:String">[in_StPrefixoLog + "ok"]</InArgument>'
    '</ui:LogMessage.Message>'
    '</ui:LogMessage>'
)


# ---- S-10: EXPANDED form is now captured ----

def test_s10_expanded_log_in_typed_collection_flagged(tmp_path):
    """scg:List<AssignOperation> is a typed collection — any LogMessage (even
    expanded open+close form) is a type error and must be flagged."""
    body = (
        '  <scg:List x:TypeArguments="AssignOperation" Capacity="1">\n'
        f'    {_EXPANDED_LOG}\n'
        '  </scg:List>'
    )
    fc = _write_s10_xaml(tmp_path, body)
    findings = detect_s10_logmessage_in_restrictive_parent(_make_s10_rule(), fc, None)
    assert len(findings) == 1, f"expanded log in typed collection not flagged: {findings}"
    assert "collection tipada" in findings[0].message


def test_s10_expanded_log_with_sibling_in_then_flagged(tmp_path):
    """If.Then accepts 1 child. Expanded LogMessage + another sibling => break."""
    body = (
        '  <If.Then>\n'
        f'    {_EXPANDED_LOG}\n'
        '    <ui:Assign DisplayName="A"/>\n'
        '  </If.Then>'
    )
    fc = _write_s10_xaml(tmp_path, body)
    findings = detect_s10_logmessage_in_restrictive_parent(_make_s10_rule(), fc, None)
    assert len(findings) == 1, f"expanded log w/ sibling in If.Then not flagged: {findings}"
    assert "aceita 1 child" in findings[0].message


def test_s10_self_close_log_still_flagged_in_typed_collection(tmp_path):
    """Regression guard: the ORIGINAL self-closed behaviour still works."""
    body = (
        '  <scg:List x:TypeArguments="AssignOperation" Capacity="1">\n'
        '    <ui:LogMessage Level="Trace" Message="x" />\n'
        '  </scg:List>'
    )
    fc = _write_s10_xaml(tmp_path, body)
    findings = detect_s10_logmessage_in_restrictive_parent(_make_s10_rule(), fc, None)
    assert len(findings) == 1
    assert "collection tipada" in findings[0].message


def test_s10_expanded_log_sole_child_of_then_not_flagged(tmp_path):
    """Single-child restrictive parent with the expanded LogMessage as its ONLY
    content child is valid (child_count == 1) — must NOT flag."""
    body = (
        '  <If.Then>\n'
        f'    {_EXPANDED_LOG}\n'
        '  </If.Then>'
    )
    fc = _write_s10_xaml(tmp_path, body)
    findings = detect_s10_logmessage_in_restrictive_parent(_make_s10_rule(), fc, None)
    assert findings == [], f"sole-child expanded log should be valid: {findings}"


def test_s10_finding_line_points_at_open_tag(tmp_path):
    """The reported line must be the OPEN tag of the expanded LogMessage."""
    body = (
        '  <scg:List x:TypeArguments="AssignOperation" Capacity="1">\n'
        f'    {_EXPANDED_LOG}\n'
        '  </scg:List>'
    )
    fc = _write_s10_xaml(tmp_path, body)
    findings = detect_s10_logmessage_in_restrictive_parent(_make_s10_rule(), fc, None)
    assert len(findings) == 1
    # _EXPANDED_LOG open tag sits on line 4 (decl=1, Activity=2, scg:List=3, log=4)
    assert findings[0].line == 4
