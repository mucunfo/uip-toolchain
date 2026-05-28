"""D-TRANSITIVE-CONFLICT — duplicate identity divergente / downgrade skew.

Lê `.local/AllDependencies.json` (Studio's NuGet project.assets cache):

  targets:
    net6.0-windows7.0:
      <package>/<version>:
        dependencies: { <dep>: <min_ver> }
        ...

Checks aplicados:
  1. **Duplicate identity**: mesmo package name aparecendo com 2+ versions
     diferentes nas keys `<package>/<version>` (raro em single-target restore;
     anomalia digna de finding).
  2. **Downgrade skew**: package A declara `dependencies.B = "Y.Y.Y"` mas
     versão B resolvida no graph é `< Y.Y.Y`. NuGet escolhe lowest-applicable
     transitive — pode quebrar runtime se downgrade dropar API.

Findings emitidos como `D-TRANSITIVE-CONFLICT` severity ERROR (rule deterministic).

Fix mecânico não trivial (exige upgrade transitive na project.json ou pin
explícito). Emit prose-only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from uip_engine._types import Finding


_PKG_KEY_RE = re.compile(r"^(?P<name>[A-Za-z0-9_.\-]+)/(?P<ver>[0-9].*)$")


def _parse_semver(s: str) -> tuple:
    """X.Y.Z[-pre[+build]] → tupla ordenável. Pre-release ordena abaixo de release."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[-.](.+))?", s)
    if not m:
        return (0, 0, 0, "")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    suffix = m.group(4) or ""
    return (major, minor, patch, suffix if suffix else "\x7f")


def _strip_constraint(raw: str) -> str:
    """`[1.0.0]` → `1.0.0`. `[1.0.0,)` → `1.0.0`. Lower bound do range."""
    m = re.match(r"^\[?\s*(\d+\.\d+\.\d+(?:[-.][A-Za-z0-9.+_-]+)?)", raw or "")
    return m.group(1) if m else raw


def _load_assets(project_root: Path) -> dict | None:
    """Lê .local/AllDependencies.json. None se ausente / inválido."""
    pj = project_root / ".local" / "AllDependencies.json"
    if not pj.is_file():
        return None
    try:
        return json.loads(pj.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def detect_transitive_conflict(rule, fc, pc) -> list[Finding]:
    """Walk `.local/AllDependencies.json` targets, detect dup identity + downgrade."""
    if pc is None:
        return []
    assets = _load_assets(pc.root)
    if assets is None:
        return []
    targets = assets.get("targets") or {}
    findings: list[Finding] = []
    for tfm, packages in targets.items():
        if not isinstance(packages, dict):
            continue
        # 1. Duplicate identity scan
        by_name: dict[str, list[str]] = {}
        for key in packages:
            m = _PKG_KEY_RE.match(key)
            if not m:
                continue
            by_name.setdefault(m.group("name"), []).append(m.group("ver"))
        for name, versions in by_name.items():
            uniq = sorted(set(versions), key=_parse_semver)
            if len(uniq) > 1:
                findings.append(Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    category=rule.category,
                    file=str(pc.root / ".local" / "AllDependencies.json"),
                    line=1,
                    message=(
                        f"{rule.title}: {name} resolvido em múltiplas versões "
                        f"({uniq}) sob TFM {tfm}"
                    ),
                    fix_mechanical=None,
                    fix_prose=(rule.fix or {}).get("prose"),
                ))
        # 2. Downgrade skew scan
        resolved: dict[str, str] = {}
        for key in packages:
            m = _PKG_KEY_RE.match(key)
            if m:
                # Em duplicate identity já flagged; aqui pega max pra check
                cur = resolved.get(m.group("name"))
                new_v = m.group("ver")
                if cur is None or _parse_semver(new_v) > _parse_semver(cur):
                    resolved[m.group("name")] = new_v
        for key, meta in packages.items():
            m = _PKG_KEY_RE.match(key)
            if not m or not isinstance(meta, dict):
                continue
            parent_name = m.group("name")
            for dep_name, dep_range in (meta.get("dependencies") or {}).items():
                wanted = _strip_constraint(str(dep_range))
                got = resolved.get(dep_name)
                if got is None:
                    continue
                if _parse_semver(got) < _parse_semver(wanted):
                    findings.append(Finding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        file=str(pc.root / ".local" / "AllDependencies.json"),
                        line=1,
                        message=(
                            f"{rule.title}: {parent_name} declara "
                            f"{dep_name}>={wanted} mas graph resolveu {got}"
                        ),
                        fix_mechanical=None,
                        fix_prose=(rule.fix or {}).get("prose"),
                    ))
    return findings
