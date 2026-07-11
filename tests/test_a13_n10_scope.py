"""Scope corrections for A-13 (business-only exception messages) and N-10
(state-machine logging is not linear Activity->Log).

A-13 must fire only on hardcoded *business* exception messages
(`BusinessRuleException`), not on technical guards (`ArgumentException`,
`InvalidOperationException`, plain `Exception`, `SystemException`), which the
rule's own prose exempts as infra/technical inline. Its exclude globs must also
match infra folders nested under `Workflows/` (DB2/Orquestradora), not only at
the project root.

N-10 encodes the Sicoob linear `Activity -> Log` convention, which presupposes
sequential control flow. Inside a `StateMachine`, execution is event-driven
(states/transitions), so a LogMessage without an immediately-preceding sibling
activity documents a state/transition decision, not an anticipatory intent.
"""
from pathlib import Path

import pathspec
import yaml

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext
from uip_engine.detectors import detect_regex
from uip_engine.heuristics.logs import detect_n10_log_anticipatory

RULES_YAML = Path(__file__).resolve().parents[1] / "rules.yaml"


def _a13_rule() -> Rule:
    raw = yaml.safe_load(RULES_YAML.read_text(encoding="utf-8"))
    a13 = next(r for r in raw["rules"] if r["id"] == "A-13")
    return Rule(
        id="A-13", severity=Severity.WARN, category="architectural", target="all",
        title=a13["title"], description="", detect=a13["detect"],
        applies_to=a13.get("applies_to", {}), fix=a13.get("fix"),
    )


def _n10_rule() -> Rule:
    return Rule(
        id="N-10", severity=Severity.WARN, category="architectural", target="all",
        title="LogMessage antecipatório", description="",
        detect={"type": "python", "params": {
            "module": "uip_engine.heuristics.logs",
            "function": "detect_n10_log_anticipatory"}},
        fix={"apply_class": "structural", "prose": "reposition"},
    )


def _throw(cls: str, msg: str) -> str:
    return f'<Throw DisplayName="Throw" Exception="[New {cls}(&quot;{msg}&quot;)]" />'


# ---- A-13: business-only ----

def test_a13_fires_on_hardcoded_business_rule_exception(tmp_path):
    f = tmp_path / "W.xaml"
    f.write_text(
        "<Activity>"
        + _throw("UiPath.Core.BusinessRuleException", "Vendor nao identificado no device")
        + _throw("BusinessRuleException", "Item exige tratativa manual")
        + "</Activity>",
        encoding="utf-8",
    )
    findings = detect_regex(_a13_rule(), FileContext(f), None)
    assert len(findings) == 2


def test_a13_ignores_technical_exception_guards(tmp_path):
    f = tmp_path / "W.xaml"
    f.write_text(
        "<Activity>"
        + _throw("ArgumentException", "in_StOutputRoot e obrigatorio")
        + _throw("InvalidOperationException", "Inconsistencia de retry: artefato ausente")
        + _throw("Exception", "Falha tecnica de acesso ao device")
        + _throw("System.Exception", "Device SSH inacessivel")
        + "</Activity>",
        encoding="utf-8",
    )
    assert detect_regex(_a13_rule(), FileContext(f), None) == []


def test_a13_ignores_business_message_sourced_from_config(tmp_path):
    f = tmp_path / "W.xaml"
    f.write_text(
        '<Activity><Throw DisplayName="Throw" Exception="[New '
        'UiPath.Core.BusinessRuleException(in_Config(&quot;BusinessExceptionX&quot;).ToString)]" />'
        "</Activity>",
        encoding="utf-8",
    )
    assert detect_regex(_a13_rule(), FileContext(f), None) == []


def test_a13_exclude_globs_match_infra_folders_at_any_depth():
    spec = pathspec.PathSpec.from_lines(
        "gitwildmatch", _a13_rule().applies_to["exclude"])
    assert spec.match_file("Workflows/DB2/ImportaDadosControleProcessos.xaml")
    assert spec.match_file("Workflows/Orquestradora/CriarItensOrquestradora.xaml")
    assert spec.match_file("Framework/Process.xaml")
    # a genuine process workflow is NOT excluded
    assert not spec.match_file("Workflows/Rede/ValidarEntregaLinkWan.xaml")


# ---- N-10: state machines are not linear ----

def test_n10_ignores_log_inside_state_machine(tmp_path):
    f = tmp_path / "Main.xaml"
    f.write_text(
        "<Activity><StateMachine><State x:Name=\"Init\"><State.Entry><Sequence>"
        '<ui:LogMessage DisplayName="Log - stop reason" Level="Trace" '
        'Message="[&quot;Limite de erros consecutivos atingido&quot;]" />'
        '<ui:LogMessage DisplayName="Log - detail" Level="Error" '
        'Message="[&quot;Parando processo&quot;]" />'
        "</Sequence></State.Entry></State></StateMachine></Activity>",
        encoding="utf-8",
    )
    assert detect_n10_log_anticipatory(_n10_rule(), FileContext(f), None) == []


def test_n10_still_flags_anticipatory_log_in_plain_sequence(tmp_path):
    f = tmp_path / "W.xaml"
    f.write_text(
        "<Activity><Sequence>"
        '<ui:LogMessage DisplayName="Log - antecipatorio" Level="Trace" '
        'Message="[&quot;vou baixar o arquivo&quot;]" />'
        '<ui:ClickButton DisplayName="Click" />'
        "</Sequence></Activity>",
        encoding="utf-8",
    )
    findings = detect_n10_log_anticipatory(_n10_rule(), FileContext(f), None)
    assert len(findings) == 1
