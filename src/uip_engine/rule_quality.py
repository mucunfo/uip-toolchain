"""Enterprise quality checks for loaded rules.

Schema validation answers "can the engine parse this rule?". These checks answer
"is this rule good enough to hand to a human or frontier-model patch loop?".
"""
from __future__ import annotations

from ._types import Rule
from .classify import get_apply_class


FORBIDDEN_AGENT_RUNTIME_TERMS = (
    "ollama",
    "local model",
    "modelo local",
    "llama.cpp",
    "claude -p",
    "claude code cli",
)


def validate_rule_quality(rules: list[Rule]) -> list[str]:
    """Return enterprise-quality violations for already parsed rules.

    Every effective rule must carry `fix.prose`: deterministic rules need an
    audit trail for what the fixer does, and contextual/structural rules need a
    clear instruction for frontier-model or human review.
    """
    errors: list[str] = []
    for rule in rules:
        fix = rule.fix or {}
        prose = str(fix.get("prose") or "").strip()
        apply_class = get_apply_class(rule)

        if not prose:
            errors.append(
                f"rule[{rule.id}]: missing fix.prose "
                f"(apply_class={apply_class}; enterprise rules require an "
                "explicit correction instruction for every effective rule)"
            )

        haystack = "\n".join(
            str(part or "")
            for part in (rule.title, rule.description, prose)
        ).lower()
        for term in FORBIDDEN_AGENT_RUNTIME_TERMS:
            if term in haystack:
                errors.append(
                    f"rule[{rule.id}]: references forbidden agent-runtime term "
                    f"'{term}'. Rules must stay model-provider agnostic and "
                    "frontier-model ready."
                )
                break

    return errors
