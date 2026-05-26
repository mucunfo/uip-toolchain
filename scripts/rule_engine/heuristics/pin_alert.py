"""D-PIN-ALERT heuristic — XAML APIs exclusivas de versão > pin.

Cruza `project.json::dependencies` (pin atual por pacote) com a lista
`assets/version_exclusive_apis.yaml` (APIs introduzidas em versão X).
Para cada package onde `pinned < introduced_in`, varre XAML pelo
`pattern` e emite finding por match.

Motivação: Activity Migrator GA do Studio pega latest stable e injeta
APIs/atributos novos nos XAMLs. Quando engine realinha o package ao pin
Sicoob (regra D-1*), as APIs órfãs sobrevivem no XAML e geram
`UIPATH:LOAD ERROR` no analyzer do Studio. D-PIN-ALERT detecta ANTES
do realinhamento.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from scripts.rule_engine._types import Finding


_CACHE: dict[str, Any] | None = None


def _load_apis_yaml(engine_root: Path) -> dict:
    """Cached load de assets/version_exclusive_apis.yaml."""
    global _CACHE
    if _CACHE is None:
        path = engine_root / "assets" / "version_exclusive_apis.yaml"
        if not path.exists():
            _CACHE = {}
        else:
            try:
                _CACHE = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:
                _CACHE = {}
    return _CACHE


def _reset_cache_for_tests() -> None:
    """Reset cache (chamado por testes que mutam o YAML em runtime)."""
    global _CACHE
    _CACHE = None


def _parse_v(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def detect_pin_alert(rule, fc, pc):
    if pc is None:
        return []
    if fc.path.suffix.lower() != ".xaml":
        return []

    # Engine root = parents[3] de .../scripts/rule_engine/heuristics/pin_alert.py
    engine_root = Path(__file__).resolve().parents[3]
    apis = _load_apis_yaml(engine_root)
    if not apis:
        return []

    deps = pc.project_json.get("dependencies", {}) or {}
    findings: list[Finding] = []
    content = fc.active_content

    for package, pkg_data in apis.items():
        if package not in deps:
            continue
        raw = deps[package]
        m = re.match(r"\[?([\d.]+)", str(raw))
        if not m:
            continue
        pinned_v = _parse_v(m.group(1))

        for api in (pkg_data or {}).get("apis", []) or []:
            intro_raw = api.get("introduced_in")
            pat = api.get("pattern")
            if not intro_raw or not pat:
                continue
            intro_v = _parse_v(intro_raw)
            if pinned_v >= intro_v:
                continue  # pin já cobre — sem alerta
            mech_spec = api.get("mechanical")
            for match in re.finditer(pat, content):
                line = content[: match.start()].count("\n") + 1
                fix_text = api.get("fix", "")
                findings.append(
                    Finding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        file=str(fc.path),
                        line=line,
                        message=(
                            f"{rule.title}: API '{pat}' exige {package} "
                            f">= {intro_raw} mas pin atual é {raw}. "
                            f"Migrator pode ter injetado pós-bump. {fix_text}"
                        ),
                        fix_mechanical=mech_spec,
                        fix_prose=fix_text or None,
                    )
                )

        # `removed_apis`: APIs/atribs removidos em versão >= removed_in.
        # Caso típico: Activity Migrator faz upgrade (ex: Office365 1.x→3.x)
        # mas deixa atributos obsoletos no XAML legacy → Studio load-fail
        # `Não é possível definir o associado desconhecido 'Activity.Attr'`.
        for api in (pkg_data or {}).get("removed_apis", []) or []:
            rem_raw = api.get("removed_in")
            pat = api.get("pattern")
            if not rem_raw or not pat:
                continue
            rem_v = _parse_v(rem_raw)
            if pinned_v < rem_v:
                continue  # pin ainda inclui API — sem alerta
            mech_spec = api.get("mechanical")
            for match in re.finditer(pat, content):
                line = content[: match.start()].count("\n") + 1
                fix_text = api.get("fix", "")
                findings.append(
                    Finding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        file=str(fc.path),
                        line=line,
                        message=(
                            f"{rule.title}: API '{pat}' removida em {package} "
                            f">= {rem_raw} mas XAML legacy ainda usa. "
                            f"Migrator upgrade deixou attr obsoleto. {fix_text}"
                        ),
                        fix_mechanical=mech_spec,
                        fix_prose=fix_text or None,
                    )
                )

    return findings
