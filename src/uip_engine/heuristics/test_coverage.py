"""Heuristics for test coverage rules (TC-COV-*).

Convenção Sicoob:
  - Performer tem pasta `Tests/` no root.
  - Test Case naming: `TC_<workflow>.xaml`.
  - Workflows produção = todos `.xaml` fora de `Framework/`, `Tests/`, `Data/`,
    pasta `.local/`, `.tmp/`.

Rules:
  TC-COV-1 — workflow produção sem TC_<name>.xaml correspondente. WARN per file.
  TC-COV-3 — Performer sem pasta `Tests/`. WARN project-level.
  TC-COV-4 — workflow com >3 in_args mas única variação em TC (proxy de
             data-variation insuficiente). INFO per file.

Detectors disparam só em projects.json com `projectType` ∈ {Process, Test}
e nome do projeto sufixado `_Performer` ou pastas com layout dispatcher/
performer Sicoob.
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree

from uip_engine._types import Finding
from uip_engine.context import FileContext, ProjectContext


_EXCLUDED_DIRS = frozenset({"Framework", "Tests", "Data", ".local", ".tmp", ".objects", ".screens"})


def _is_performer_project(pc: ProjectContext | None) -> bool:
    if pc is None:
        return False
    name = (pc.project_json.get("name") or "")
    if name.endswith("_Performer"):
        return True
    # Heuristic fallback: nome de pasta termina explicitamente em "-performer"
    # (kebab-case Sicoob). Substring match too loose, gera FP em paths
    # incidentais (ex: tmp dirs com 'performer' no nome).
    lower = pc.root.name.lower()
    return lower.endswith("-performer") or lower.endswith("_performer")


def _is_excluded(rel: Path) -> bool:
    parts = set(rel.parts)
    return bool(parts & _EXCLUDED_DIRS)


def _list_production_workflows(pc: ProjectContext) -> list[Path]:
    """Workflows produção: .xaml fora de pastas excluídas, sem prefixo TC_."""
    out = []
    for xaml in pc.root.rglob("*.xaml"):
        rel = xaml.relative_to(pc.root)
        if _is_excluded(rel):
            continue
        if xaml.name.startswith("TC_"):
            continue
        if xaml.name == "Main.xaml":
            # Main fica em scope mas é orchestration — opcional ter TC. Skip default.
            continue
        out.append(xaml)
    return out


def _list_test_cases(pc: ProjectContext) -> dict[str, Path]:
    """Mapa basename_stem → Path. Naming TC_<stem>.xaml."""
    tests_dir = pc.root / "Tests"
    if not tests_dir.exists():
        return {}
    out = {}
    for xaml in tests_dir.rglob("TC_*.xaml"):
        stem = xaml.stem[len("TC_"):]  # remove prefixo
        out[stem] = xaml
    return out


def _arg_count_xaml(xaml: Path) -> int:
    try:
        content = xaml.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return 0
    try:
        root = etree.fromstring(content.encode("utf-8"))
    except (etree.XMLSyntaxError, ValueError):
        return 0
    members = root.find("{http://schemas.microsoft.com/winfx/2006/xaml}Members")
    if members is None:
        return 0
    in_args = 0
    for child in members:
        tag = etree.QName(child.tag)
        if tag.localname != "Property":
            continue
        # in_args contam — prefix in_ no Name attr
        name = child.get("Name", "")
        if name.startswith("in_") or name.startswith("io_"):
            in_args += 1
    return in_args


# ---------- TC-COV-1 ----------

def detect_tc_cov_1_missing(rule, fc: FileContext, pc: ProjectContext | None) -> list[Finding]:
    """Per-file: emite se este XAML é produção e não tem TC_<stem>.xaml."""
    if not _is_performer_project(pc):
        return []
    rel = Path(fc.path).resolve().relative_to(pc.root.resolve()) if pc else None
    if rel is None or _is_excluded(rel):
        return []
    if Path(fc.path).name.startswith("TC_") or Path(fc.path).name == "Main.xaml":
        return []
    tcs = _list_test_cases(pc)
    stem = Path(fc.path).stem
    if stem in tcs:
        return []
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1,
        message=f"{rule.title}: TC_{stem}.xaml ausente em Tests/",
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )]


# ---------- TC-COV-3 ----------

def detect_tc_cov_3_no_tests_folder(rule, fc: FileContext, pc: ProjectContext | None) -> list[Finding]:
    """Project-level: emite uma vez por project.json se Performer sem Tests/."""
    if pc is None or not _is_performer_project(pc):
        return []
    if not str(fc.path).endswith("project.json"):
        return []
    tests_dir = pc.root / "Tests"
    if tests_dir.exists() and any(tests_dir.iterdir()):
        return []
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1,
        message=rule.title,
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )]


# ---------- TC-COV-4 ----------

def detect_tc_cov_4_low_arg_variation(rule, fc: FileContext, pc: ProjectContext | None) -> list[Finding]:
    """Per-file: workflow com >3 in_args + ≤1 TC. Proxy de data-variation."""
    params = rule.detect.get("params", {}) or {}
    arg_threshold = int(params.get("arg_threshold", 3))
    if not _is_performer_project(pc):
        return []
    rel = Path(fc.path).resolve().relative_to(pc.root.resolve()) if pc else None
    if rel is None or _is_excluded(rel):
        return []
    if Path(fc.path).name.startswith("TC_") or Path(fc.path).name == "Main.xaml":
        return []
    in_args = _arg_count_xaml(Path(fc.path))
    if in_args <= arg_threshold:
        return []
    stem = Path(fc.path).stem
    tcs_for_stem = list((pc.root / "Tests").rglob(f"TC_{stem}*.xaml")) if (pc.root / "Tests").exists() else []
    if len(tcs_for_stem) > 1:
        return []
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1,
        message=f"{rule.title}: {in_args} in_args, {len(tcs_for_stem)} TC",
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )]
