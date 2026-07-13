"""Source-of-truth dos pins Sicoob.

Carrega `assets/canonical_pins.yaml` (single source-of-truth) e sintetiza
rule dicts compatíveis com schema do `loader.py`.

Loader chama `synthesize_canonical_rules()` em parse-time pra injetar
D-1a..D-1<N> + J-STUDIO-PIN sem duplicar 22 linhas de YAML por pacote.

Adicionar pin novo = editar `canonical_pins.yaml`. Loader pega automático.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml


_DEFAULT_RATIONALE = (
    "Drift em qualquer direção (maior OU menor) é violação policy — "
    "Activity Migrator pode injetar latest stable; engine realinha ao "
    "pin canonical."
)

# 2026-07-02: pins ficam advisory enquanto projetos reais validam dependências
# já declaradas. D-PINALERT continua cobrindo incompatibilidade XAML x versão.
_PIN_RULE_SEVERITY = "WARN"
_PIN_RULE_APPLY_CLASS = "contextual"


def _assets_dir() -> Path:
    """Repo-root/assets. `canonical.py` mora em `src/uip_engine/`."""
    return Path(__file__).resolve().parents[2] / "assets"


@functools.lru_cache(maxsize=1)
def load_canonical(path: Path | str | None = None) -> dict[str, Any]:
    """Parse canonical_pins.yaml. Cacheado por processo."""
    p = Path(path) if path else _assets_dir() / "canonical_pins.yaml"
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: top-level must be mapping")
    if raw.get("version") != 1:
        raise ValueError(f"{p}: only version 1 supported")
    studio = raw.get("studio") or {}
    if not isinstance(studio, dict) or "version" not in studio:
        raise ValueError(f"{p}: studio.version required")
    pins = raw.get("pins") or []
    if not isinstance(pins, list):
        raise ValueError(f"{p}: pins must be list")
    seen_ids: set[str] = set()
    seen_pkgs: set[str] = set()
    for entry in pins:
        if not isinstance(entry, dict):
            raise ValueError(f"{p}: pin entry must be mapping")
        for required in ("id", "package", "exact"):
            if required not in entry:
                raise ValueError(f"{p}: pin entry missing '{required}'")
        rid = entry["id"]
        pkg = entry["package"]
        if rid in seen_ids:
            raise ValueError(f"{p}: duplicate pin id '{rid}'")
        if pkg in seen_pkgs:
            raise ValueError(f"{p}: duplicate package '{pkg}'")
        seen_ids.add(rid)
        seen_pkgs.add(pkg)
    return raw


def _synthesize_d1_rule(entry: dict[str, Any]) -> dict[str, Any]:
    """Expand canonical pin entry → rule dict compatível com loader schema."""
    pkg = entry["package"]
    ver = entry["exact"]
    rationale = (entry.get("rationale") or "").strip() or _DEFAULT_RATIONALE
    detect_params: dict[str, Any] = {"package": pkg, "exact": ver}
    required_when_package = entry.get("required_when_package")
    if required_when_package:
        detect_params["required_when_package"] = required_when_package
    required_when_assemblies = entry.get("required_when_assemblies")
    if required_when_assemblies:
        detect_params["required_when_assemblies"] = required_when_assemblies
    required_when_xaml_patterns = entry.get("required_when_xaml_patterns")
    if required_when_xaml_patterns:
        detect_params["required_when_xaml_patterns"] = required_when_xaml_patterns
    return {
        "id": entry["id"],
        "severity": _PIN_RULE_SEVERITY,
        "category": "breaking",
        "target": "windows",
        "title": f"{pkg} == [{ver}]",
        "description": f"Pin EXATO Sicoob: `{pkg}` `[{ver}]`.\n{rationale}",
        "applies_to": {"include": ["project.json"]},
        "detect": {
            "type": "nuget_version_check",
            "params": detect_params,
        },
        "fix": {
            "apply_class": _PIN_RULE_APPLY_CLASS,
            "mechanical": {
                "type": "set_dependency_pin",
                "package": pkg,
                "version": f"[{ver}]",
            },
            "prose": f'Pinar `dependencies."{pkg}" = "[{ver}]"`.',
        },
    }


def _synthesize_studio_pin_rule(studio_version: str) -> dict[str, Any]:
    """J-1 — enforce project.json::studioVersion exato.

    Reusa detector `json_field_check` + fixer `set_json_field` (já no
    registry; zero tipo novo). ID `J-1` preserva ID histórico do bloco
    verbose anterior (substituído por canonical injection).
    """
    return {
        "id": "J-1",
        "severity": _PIN_RULE_SEVERITY,
        "category": "breaking",
        "target": "windows",
        "title": f"project.json::studioVersion == {studio_version}",
        "description": (
            f"Pin EXATO Sicoob Studio: `{studio_version}`.\n"
            "studioVersion estale (Studio mais antigo gravou o stamp) ou "
            "future (Studio mais novo bumpou) bate em incompat com pacotes "
            "canonical pinados em D-1*. Engine força realinhamento."
        ),
        "applies_to": {"include": ["project.json"]},
        "detect": {
            "type": "json_field_check",
            "params": {
                "path": "studioVersion",
                "expected": studio_version,
            },
        },
        "fix": {
            "apply_class": _PIN_RULE_APPLY_CLASS,
            "mechanical": {
                "type": "set_json_field",
                "path": "studioVersion",
                "value": studio_version,
            },
            "prose": f'Pinar `studioVersion = "{studio_version}"` em project.json.',
        },
    }


def synthesize_canonical_rules(
    canonical: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Yield list of synthesized rule dicts. Stable order: pins[], então studio."""
    data = canonical if canonical is not None else load_canonical()
    out: list[dict[str, Any]] = []
    for entry in data["pins"]:
        out.append(_synthesize_d1_rule(entry))
    out.append(_synthesize_studio_pin_rule(data["studio"]["version"]))
    return out


def canonical_pin_for(package: str) -> str | None:
    """Retorna pin exato (`X.Y.Z` sem brackets) pra `package` ou None."""
    data = load_canonical()
    for entry in data["pins"]:
        if entry["package"] == package:
            return entry["exact"]
    return None


def canonical_studio_version() -> str:
    """Atalho — `data["studio"]["version"]`."""
    return load_canonical()["studio"]["version"]
