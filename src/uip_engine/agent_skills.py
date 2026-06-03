"""Install CCS-managed agent skills for local agent clients."""
from __future__ import annotations

import filecmp
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


CCS_SKILL_NAMES = ("ccs-creator", "ccs-auditor", "ccs-quality")
CCS_SKILL_SOURCE_DIR = Path(__file__).with_name("ccs_agent_skills")
MANAGED_MARKER = ".ccs-uip-managed"
DISABLE_ENV_VAR = "UIP_TOOLCHAIN_DISABLE_AGENT_SKILL_SYNC"


@dataclass(frozen=True)
class SkillInstallRecord:
    agent: str
    name: str
    destination: Path
    changed: bool


def _repo_skill_root() -> Path | None:
    root = Path(__file__).resolve().parents[2] / ".agents" / "skills"
    if all((root / name / "SKILL.md").is_file() for name in CCS_SKILL_NAMES):
        return root
    return None


def _packaged_skill_root() -> Path | None:
    root = CCS_SKILL_SOURCE_DIR
    if all((root / name / "SKILL.md").is_file() for name in CCS_SKILL_NAMES):
        return root
    return None


def skill_source_root() -> Path:
    """Return the canonical skill source root for this execution."""
    for candidate in (_repo_skill_root(), _packaged_skill_root()):
        if candidate is not None:
            return candidate
    raise FileNotFoundError(
        "CCS agent skill templates not found. Expected .agents/skills or "
        "packaged uip_engine/ccs_agent_skills."
    )


def default_agent_skill_roots(home: Path | None = None) -> dict[str, Path]:
    """Global skill destinations for supported local agent clients."""
    base = home or Path.home()
    return {
        "codex": base / ".agents" / "skills",
        "claude": base / ".claude" / "skills",
    }


def _copy_file_if_changed(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file() and filecmp.cmp(src, dst, shallow=False):
        return False
    shutil.copy2(src, dst)
    return True


def _copy_tree_if_changed(src: Path, dst: Path) -> bool:
    changed = False
    for entry in src.rglob("*"):
        rel = entry.relative_to(src)
        target = dst / rel
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        changed = _copy_file_if_changed(entry, target) or changed
    marker = dst / MANAGED_MARKER
    marker_text = "managed-by=ccs-uip\n"
    if not marker.is_file() or marker.read_text(encoding="utf-8") != marker_text:
        marker.write_text(marker_text, encoding="utf-8")
        changed = True
    return changed


def ensure_ccs_agent_skills(
    *,
    agents: tuple[str, ...] = ("codex", "claude"),
    home: Path | None = None,
    verbose: bool = False,
) -> list[SkillInstallRecord]:
    """Ensure CCS skills are installed globally for Codex and Claude.

    The operation is idempotent and only overwrites files under the CCS-managed
    skill names. Official UiPath `uipath-*` skills are intentionally untouched.
    """
    if os.environ.get(DISABLE_ENV_VAR, "").strip().lower() in {
        "1", "true", "yes",
    }:
        return []

    source_root = skill_source_root()
    roots = default_agent_skill_roots(home)
    records: list[SkillInstallRecord] = []
    for agent in agents:
        root = roots.get(agent)
        if root is None:
            raise ValueError(f"unsupported agent for CCS skills: {agent}")
        root.mkdir(parents=True, exist_ok=True)
        for name in CCS_SKILL_NAMES:
            src = source_root / name
            dst = root / name
            changed = _copy_tree_if_changed(src, dst)
            records.append(SkillInstallRecord(agent, name, dst, changed))

    if verbose:
        changed = [r for r in records if r.changed]
        if changed:
            summary = ", ".join(f"{r.agent}:{r.name}" for r in changed)
            print(f"[ccs-skills] installed/updated {summary}", file=sys.stderr)
    return records


def main(argv: list[str] | None = None) -> int:
    argv = argv or []
    verbose = "--quiet" not in argv
    records = ensure_ccs_agent_skills(verbose=verbose)
    changed = sum(1 for record in records if record.changed)
    print(f"CCS skills OK: {len(records)} checked, {changed} changed")
    return 0
