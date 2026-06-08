from pathlib import Path

from uip_engine.classify import get_apply_class
from uip_engine.detectors import REGISTRY as DETECTOR_REGISTRY
from uip_engine.fixers import REGISTRY as FIXER_REGISTRY
from uip_engine.loader import load_rules
from uip_engine.rule_quality import validate_rule_quality


ROOT = Path(__file__).resolve().parents[1]


def test_effective_rules_all_have_fix_prose():
    rules = load_rules(
        ROOT / "rules.yaml",
        registered_detectors=set(DETECTOR_REGISTRY),
        registered_fixers=set(FIXER_REGISTRY),
    )

    errors = validate_rule_quality(rules)

    assert errors == []
    assert all(((r.fix or {}).get("prose") or "").strip() for r in rules)


def test_contextual_and_structural_rules_have_explicit_instructions():
    rules = load_rules(
        ROOT / "rules.yaml",
        registered_detectors=set(DETECTOR_REGISTRY),
        registered_fixers=set(FIXER_REGISTRY),
    )

    missing = [
        r.id
        for r in rules
        if get_apply_class(r) in {"contextual", "structural"}
        and not ((r.fix or {}).get("prose") or "").strip()
    ]

    assert missing == []


def test_rule_quality_rejects_missing_prose():
    rules = load_rules(
        ROOT / "tests" / "fixtures" / "rules_sample.yaml",
        inject_canonical=False,
    )

    errors = validate_rule_quality(rules)

    assert any("rule[X-1]: missing fix.prose" in err for err in errors)


def test_rule_quality_rejects_local_model_coupling():
    rules = load_rules(
        ROOT / "tests" / "fixtures" / "rules_sample.yaml",
        inject_canonical=False,
    )
    rules[0].fix = {"prose": "Corrigir com Ollama."}

    errors = validate_rule_quality(rules)

    assert any("forbidden agent-runtime term 'ollama'" in err for err in errors)


def test_rule_quality_rejects_hidden_agent_subprocess_coupling():
    rules = load_rules(
        ROOT / "tests" / "fixtures" / "rules_sample.yaml",
        inject_canonical=False,
    )
    rules[0].fix = {"prose": "Chamar claude -p para decidir a mensagem."}

    errors = validate_rule_quality(rules)

    assert any("forbidden agent-runtime term 'claude -p'" in err for err in errors)
