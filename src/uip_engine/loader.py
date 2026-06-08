"""Parse rules.yaml + schema validation."""
from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path
from typing import Any

import yaml

from ._types import Rule, Severity, Category, Target


class SchemaError(Exception):
    pass


# Detecta atribuição `fix_mechanical=...` com valor que NÃO seja literal None.
# Casa: `fix_mechanical=mech`, `fix_mechanical={"type": ...}`, `fix_mechanical=fix_mech_spec`.
# Não casa: `fix_mechanical=None`, `fix_mechanical=(rule.fix or {}).get("mechanical")`
# (esta última deriva apenas do YAML — não emit dinâmico).
_RE_DYN_FIX_MECH = re.compile(
    r"fix_mechanical\s*=\s*(?!None\b)"
    r"(?!\(rule\.fix\s*or\s*\{\}\)\.get\(['\"]mechanical['\"]\))"
    r"[A-Za-z_{]"
)


def _python_detector_emits_dynamic_mech(detect: dict) -> bool:
    """True se função Python referenciada por detector emite fix_mechanical
    dinâmico (não derivado de `rule.fix.mechanical` do YAML)."""
    params = detect.get("params") or {}
    mod_name = params.get("module")
    fn_name = params.get("function")
    if not mod_name or not fn_name:
        return False
    try:
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, fn_name)
        src = inspect.getsource(fn)
    except Exception:
        return False
    return bool(_RE_DYN_FIX_MECH.search(src))


_SEVERITY_MAP = {
    "INFO": Severity.INFO,
    "WARN": Severity.WARN,
    "ERROR": Severity.ERROR,
    "HALT": Severity.HALT,
}


def load_rules(
    path: Path | str,
    registered_detectors: set[str] | None = None,
    registered_fixers: set[str] | None = None,
    inject_canonical: bool = True,
) -> list[Rule]:
    """Parse YAML and validate schema. Raises SchemaError on any violation.

    `inject_canonical=True` (default) sintetiza D-1* + J-1 a partir de
    `assets/canonical_pins.yaml` e prepende em `rules_raw` (idempotente:
    skip ID já presente). Production code usa default.

    Testes que carregam fixtures isoladas (rules_sample.yaml, empty.yaml)
    passam `inject_canonical=False` pra evitar contaminação.
    """
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise SchemaError(f"{p}: top-level must be mapping")
    if raw.get("version") != 1:
        raise SchemaError(f"{p}: only version 1 supported")

    rules_raw = raw.get("rules", [])
    if not isinstance(rules_raw, list):
        raise SchemaError(f"{p}: rules must be a list")

    # Injeta regras D-1* + J-1 sintetizadas do canonical_pins.yaml.
    # Idempotente: skip ID já presente em rules.yaml (coexistência durante
    # transição). Quando rules.yaml não contém mais blocos D-1* verbose,
    # injection vira a única fonte.
    if inject_canonical:
        from .canonical import synthesize_canonical_rules
        explicit_ids: set[str] = {
            r["id"] for r in rules_raw
            if isinstance(r, dict) and isinstance(r.get("id"), str)
        }
        try:
            injected = [
                r for r in synthesize_canonical_rules()
                if r["id"] not in explicit_ids
            ]
        except Exception as e:
            raise SchemaError(f"canonical_pins.yaml: {e}") from e
        rules_raw = injected + rules_raw

    rules: list[Rule] = []
    seen_ids: set[str] = set()

    for i, rule_raw in enumerate(rules_raw):
        rule = _parse_rule(rule_raw, i, registered_detectors, registered_fixers)
        if rule.id in seen_ids:
            raise SchemaError(f"duplicate rule id: {rule.id}")
        seen_ids.add(rule.id)
        rules.append(rule)

    return rules


def _parse_rule(
    raw: dict[str, Any],
    idx: int,
    registered_detectors: set[str] | None,
    registered_fixers: set[str] | None,
) -> Rule:
    if not isinstance(raw, dict):
        raise SchemaError(f"rule[{idx}]: must be mapping")

    required = ["id", "severity", "category", "target", "title", "description", "detect"]
    for field_name in required:
        if field_name not in raw:
            raise SchemaError(f"rule[{idx}]: missing required field '{field_name}'")

    rid = raw["id"]
    # Rule IDs: começam com prefixo upper alphanum (S, W, M, F37, etc.),
    # seguido por `-`, depois um ou mais segmentos alphanum/underscore
    # separados por `-`. Permite multi-hyphen pra IDs de gates oficiais.
    if not re.match(r"^[A-Z][A-Z0-9]*(?:-[A-Za-z0-9_]+)+$", str(rid)):
        raise SchemaError(f"rule[{idx}]: invalid id format '{rid}'")

    sev_raw = str(raw["severity"]).upper()
    if sev_raw not in _SEVERITY_MAP:
        raise SchemaError(f"rule[{rid}]: invalid severity '{sev_raw}'")
    severity = _SEVERITY_MAP[sev_raw]

    category = str(raw["category"])
    if category not in Category.ALL:
        raise SchemaError(f"rule[{rid}]: invalid category '{category}'")

    target = str(raw["target"])
    if target not in Target.VALID:
        raise SchemaError(f"rule[{rid}]: invalid target '{target}'")

    detect = raw["detect"]
    if not isinstance(detect, dict) or "type" not in detect:
        raise SchemaError(f"rule[{rid}]: detect must have 'type'")

    detect_type = str(detect["type"])
    if registered_detectors is not None and detect_type not in registered_detectors:
        raise SchemaError(f"rule[{rid}]: unknown detect.type '{detect_type}'")

    if detect_type == "regex" and "pattern" in detect:
        _validate_regex(rid, detect["pattern"])
    elif detect_type == "regex_with_context" and "pattern" in detect.get("params", {}):
        _validate_regex(rid, detect["params"]["pattern"])

    fix_raw = raw.get("fix")
    if fix_raw is not None and not isinstance(fix_raw, dict):
        raise SchemaError(f"rule[{rid}]: fix must be mapping or null")

    if fix_raw and "mechanical" in fix_raw and fix_raw["mechanical"]:
        mech = fix_raw["mechanical"]
        if "type" not in mech:
            raise SchemaError(f"rule[{rid}]: fix.mechanical missing 'type'")
        if registered_fixers is not None and mech["type"] not in registered_fixers:
            raise SchemaError(
                f"rule[{rid}]: unknown fix.mechanical.type '{mech['type']}'"
            )

    # Python detector + heuristic-emitted fix_mechanical sem `mechanical:` no
    # YAML DEVE declarar `apply_class` (ARCHITECTURE p.121). Default contextual
    # bloqueia silente. Validar para falhar fast em CI.
    if detect_type == "python":
        has_yaml_mech = bool(fix_raw and (fix_raw.get("mechanical") or {}))
        has_apply_class = bool(fix_raw and fix_raw.get("apply_class"))
        if (not has_yaml_mech) and (not has_apply_class):
            if _python_detector_emits_dynamic_mech(detect):
                raise SchemaError(
                    f"rule[{rid}]: python detector emite fix_mechanical "
                    f"dinâmico mas YAML não tem `mechanical:` nem "
                    f"`apply_class`. Default contextual bloqueia auto-apply "
                    f"silente. Declarar `fix.apply_class: deterministic` "
                    f"(ou contextual/structural) explicitamente."
                )

    return Rule(
        id=rid,
        severity=severity,
        category=category,
        target=target,
        title=str(raw["title"]),
        description=str(raw["description"]),
        detect=detect,
        applies_to=raw.get("applies_to", {}) or {},
        fix=fix_raw,
        references=raw.get("references", []) or [],
        examples=raw.get("examples", {}) or {},
        deprecated_at=raw.get("deprecated_at"),
        replaced_by=raw.get("replaced_by"),
    )


def _validate_regex(rule_id: str, pattern: str) -> None:
    try:
        re.compile(pattern)
    except re.error as e:
        raise SchemaError(f"rule[{rule_id}]: invalid regex: {e}")
