"""Tests for N-13 (verb infinitive), N-15 (log infinitive), U-5 (var aliases)."""
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.naming import detect_n13_verb_infinitive
from uip_engine.heuristics.logs import detect_n15_log_infinitive
from uip_engine.heuristics.unused import (
    detect_u5_variable_aliases,
    detect_u6_variable_hoist,
)


_VERB_PAIRS = [
    {"wrong": "Busca", "right": "Buscar"},
    {"wrong": "Atualiza", "right": "Atualizar"},
    {"wrong": "Recupera", "right": "Recuperar"},
    {"wrong": "Valida", "right": "Validar"},
]


def _project(tmp_path: Path) -> ProjectContext:
    pj = tmp_path / "project.json"
    pj.write_text('{"targetFramework":"Windows","expressionLanguage":"VisualBasic"}', encoding="utf-8")
    return ProjectContext(root=tmp_path, project_json={"targetFramework":"Windows"})


def _write_xaml(tmp_path: Path, body: str, name: str = "Foo.xaml") -> FileContext:
    f = tmp_path / name
    f.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity xmlns:ui="ui" xmlns:x="x">\n'
        f'{body}\n'
        '</Activity>',
        encoding="utf-8",
    )
    return FileContext(f)


# ============================================================================
# N-13 — Verb infinitive in identifiers
# ============================================================================

def _n13_rule(targets=None):
    return Rule(
        id="N-13", severity=Severity.WARN, category="architectural", target="all",
        title="Identificador com verbo deve usar infinitivo (-ar/-er/-ir)",
        description="",
        detect={"type": "python", "params": {
            "verbs": _VERB_PAIRS,
            "targets": targets or ["filename","xclass","property_name","variable_name"],
        }},
    )


def test_n13_filename_busca_flagged(tmp_path):
    fc = _write_xaml(tmp_path, '  ', name="BuscaDossie.xaml")
    findings = detect_n13_verb_infinitive(_n13_rule(), fc, _project(tmp_path))
    assert any("BuscaDossie" in f.message and "Buscar" in f.message for f in findings)


def test_n13_filename_buscar_ok(tmp_path):
    fc = _write_xaml(tmp_path, '  ', name="BuscarDossie.xaml")
    findings = detect_n13_verb_infinitive(_n13_rule(), fc, _project(tmp_path))
    assert not findings


def test_n13_xclass_atualiza_flagged(tmp_path):
    body = '<Activity x:Class="AtualizaConfig" xmlns:x="x" />'
    fc = _write_xaml(tmp_path, '', name="AtualizaConfig.xaml")
    fc.path.write_text(body, encoding="utf-8")
    fc = FileContext(fc.path)
    findings = detect_n13_verb_infinitive(_n13_rule(), fc, _project(tmp_path))
    msgs = " ".join(f.message for f in findings)
    assert "Atualiza" in msgs and "Atualizar" in msgs


def test_n13_variable_recupera_flagged(tmp_path):
    body = '<Variable x:TypeArguments="x:String" Name="vStRecuperaToken" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n13_verb_infinitive(_n13_rule(), fc, _project(tmp_path))
    assert any("vStRecuperaToken" in f.message for f in findings)


def test_n13_property_valida_flagged(tmp_path):
    body = '<x:Property Name="in_StValidaInput" Type="InArgument(x:String)" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n13_verb_infinitive(_n13_rule(), fc, _project(tmp_path))
    assert any("in_StValidaInput" in f.message and "Validar" in f.message for f in findings)


def test_n13_no_false_positive_substantive(tmp_path):
    body = '<Variable x:TypeArguments="x:String" Name="vStToken" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n13_verb_infinitive(_n13_rule(), fc, _project(tmp_path))
    assert not findings


# ============================================================================
# N-15 — Log message verb infinitive
# ============================================================================

def _n15_rule():
    return Rule(
        id="N-15", severity=Severity.INFO, category="architectural", target="all",
        title="LogMessage iniciada por verbo deve usar infinitivo",
        description="",
        detect={"type": "python", "params": {
            "exclude_paths": ["framework/", "tests/"],
            "forbidden_suffixes": {
                "gerundio": ["ando","endo","indo"],
                "passado": ["ou","eu","iu"],
                "presente": ["a","e","i"],
            },
            "valid_suffixes": ["ar","er","ir","or"],
            "skip_first_words": ["Início","Inicio","Fim","Erro","Status","Total"],
            "only_pure_literals": True,
        }},
    )


def test_n15_gerundio_flagged(tmp_path):
    body = '  <ui:LogMessage Message="[&quot;Conectando ao banco&quot;]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n15_log_infinitive(_n15_rule(), fc, _project(tmp_path))
    assert any("Conectando" in f.message and "gerundio" in f.message for f in findings)


def test_n15_passado_flagged(tmp_path):
    body = '  <ui:LogMessage Message="[&quot;Recriou o diretorio&quot;]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n15_log_infinitive(_n15_rule(), fc, _project(tmp_path))
    assert any("Recriou" in f.message for f in findings)


def test_n15_infinitive_ok(tmp_path):
    body = '  <ui:LogMessage Message="[&quot;Conectar ao banco&quot;]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n15_log_infinitive(_n15_rule(), fc, _project(tmp_path))
    assert not findings


def test_n15_dynamic_skipped(tmp_path):
    body = '  <ui:LogMessage Message="[in_StPrefixoLog + &quot;Atualizando TAG&quot;]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n15_log_infinitive(_n15_rule(), fc, _project(tmp_path))
    assert not findings  # has `+` → not pure literal


def test_n15_skip_word(tmp_path):
    body = '  <ui:LogMessage Message="[&quot;Início processamento&quot;]" />'
    fc = _write_xaml(tmp_path, body)
    findings = detect_n15_log_infinitive(_n15_rule(), fc, _project(tmp_path))
    assert not findings


def test_n15_framework_excluded(tmp_path):
    fr = tmp_path / "Framework"
    fr.mkdir()
    f = fr / "X.xaml"
    f.write_text('<Activity xmlns:ui="ui"><ui:LogMessage Message="[&quot;Conectando&quot;]" /></Activity>', encoding="utf-8")
    fc = FileContext(f)
    findings = detect_n15_log_infinitive(_n15_rule(), fc, _project(tmp_path))
    assert not findings


# ============================================================================
# U-5 — Variable aliases
# ============================================================================

def _u5_rule():
    return Rule(
        id="U-5", severity=Severity.WARN, category="architectural", target="all",
        title="Variáveis com mesma origem/Default — alias provável",
        description="",
        detect={"type": "python", "params": {
            "trivial_defaults": ["", "0", "False", "True", "Nothing"],
            "skip_types": ["scg:List", "scg:Dictionary"],
            "min_duplicate_assigns": 2,
            "normalize_whitespace": True,
        }},
    )


def test_u5_same_default_flagged(tmp_path):
    # Token-overlap heuristic (unused.py:594-604) requires shared semantic
    # tokens entre nomes pra evitar FP em vars com Defaults coincidentemente
    # iguais (ex: vDTabUsuariosA vs vDTabOperadores). Vars com semântica
    # compartilhada (Url/Base) overlapeiam → flagged.
    body = '''
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vStUrlBaseA" Default="https://api.example.com/v1" />
        <Variable x:TypeArguments="x:String" Name="vStUrlBaseB" Default="https://api.example.com/v1" />
      </Sequence.Variables>
    </Sequence>
    '''
    fc = _write_xaml(tmp_path, body)
    findings = detect_u5_variable_aliases(_u5_rule(), fc, _project(tmp_path))
    assert any("vStUrlBaseA" in f.message and "vStUrlBaseB" in f.message for f in findings)


def test_u5_trivial_default_skipped(tmp_path):
    body = '''
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vStA" Default="" />
        <Variable x:TypeArguments="x:String" Name="vStB" Default="" />
      </Sequence.Variables>
    </Sequence>
    '''
    fc = _write_xaml(tmp_path, body)
    findings = detect_u5_variable_aliases(_u5_rule(), fc, _project(tmp_path))
    # trivial "" → no finding
    assert not any("Default" in f.message for f in findings)


def test_u5_container_type_skipped(tmp_path):
    body = '''
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="scg:List(x:String)" Name="vLstA" Default="abc" />
        <Variable x:TypeArguments="scg:List(x:String)" Name="vLstB" Default="abc" />
      </Sequence.Variables>
    </Sequence>
    '''
    fc = _write_xaml(tmp_path, body)
    findings = detect_u5_variable_aliases(_u5_rule(), fc, _project(tmp_path))
    assert not findings


def test_u5_assigns_same_expression_flagged(tmp_path):
    body = '''
    <Sequence>
      <Assign>
        <Assign.To><OutArgument x:TypeArguments="x:String">[vStA]</OutArgument></Assign.To>
        <Assign.Value><InArgument x:TypeArguments="x:String">[in_Config(&quot;EndpointGED&quot;).ToString]</InArgument></Assign.Value>
      </Assign>
      <Assign>
        <Assign.To><OutArgument x:TypeArguments="x:String">[vStB]</OutArgument></Assign.To>
        <Assign.Value><InArgument x:TypeArguments="x:String">[in_Config(&quot;EndpointGED&quot;).ToString]</InArgument></Assign.Value>
      </Assign>
    </Sequence>
    '''
    fc = _write_xaml(tmp_path, body)
    findings = detect_u5_variable_aliases(_u5_rule(), fc, _project(tmp_path))
    assert any("vStA" in f.message and "vStB" in f.message for f in findings)


# ============================================================================
# U-6 — Variable hoisting candidate
# ============================================================================

def _u6_rule():
    return Rule(
        id="U-6", severity=Severity.WARN, category="architectural", target="all",
        title="Variable em scope estreito — preferir escopo maior (hoisting)",
        description="",
        detect={"type": "python", "params": {
            "loop_parents": ["ForEach", "ui:ForEach", "While", "DoWhile",
                             "ParallelForEach", "ui:ParallelForEach"],
            "exception_parents": ["Catch", "TryCatch.Catches"],
            "only_cross_scope_dup": True,
        }},
    )


def test_u6_cross_scope_dup_flagged(tmp_path):
    """Mesma var em 2 scopes Sequence → hoist candidate."""
    body = '''
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vStPrefixoLog" />
      </Sequence.Variables>
      <Sequence>
        <Sequence.Variables>
          <Variable x:TypeArguments="x:String" Name="vStPrefixoLog" />
        </Sequence.Variables>
      </Sequence>
    </Sequence>
    '''
    fc = _write_xaml(tmp_path, body)
    findings = detect_u6_variable_hoist(_u6_rule(), fc, _project(tmp_path))
    assert any("vStPrefixoLog" in f.message and "hoist" in f.message for f in findings)


def test_u6_single_scope_no_flag(tmp_path):
    body = '''
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vStOnlyHere" />
      </Sequence.Variables>
    </Sequence>
    '''
    fc = _write_xaml(tmp_path, body)
    findings = detect_u6_variable_hoist(_u6_rule(), fc, _project(tmp_path))
    assert not findings


def test_u6_loop_scope_skipped(tmp_path):
    """Var em ForEach scope → skip (loop-local intencional)."""
    body = '''
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vStItem" />
      </Sequence.Variables>
      <ui:ForEach>
        <ui:ForEach.Variables>
          <Variable x:TypeArguments="x:String" Name="vStItem" />
        </ui:ForEach.Variables>
      </ui:ForEach>
    </Sequence>
    '''
    fc = _write_xaml(tmp_path, body)
    findings = detect_u6_variable_hoist(_u6_rule(), fc, _project(tmp_path))
    assert not findings


def test_u6_different_types_no_flag(tmp_path):
    """Mesmo name + tipos diferentes → não agrupa, não flag."""
    body = '''
    <Sequence>
      <Sequence.Variables>
        <Variable x:TypeArguments="x:String" Name="vX" />
      </Sequence.Variables>
      <Sequence>
        <Sequence.Variables>
          <Variable x:TypeArguments="x:Int32" Name="vX" />
        </Sequence.Variables>
      </Sequence>
    </Sequence>
    '''
    fc = _write_xaml(tmp_path, body)
    findings = detect_u6_variable_hoist(_u6_rule(), fc, _project(tmp_path))
    assert not findings
