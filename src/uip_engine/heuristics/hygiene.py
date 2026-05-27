"""Heuristics for CI/CD hygiene rules (HY-*).

HY-1 merge conflict markers leftover (`<<<<<<<` / `=======` / `>>>>>>>`)
     em XAML/JSON/Config.xlsx. Publish quebra silencioso. ERROR breaking.
HY-2 project.json.description = placeholder Studio default
     (Blank Process/Blank Library/Process Description/""). WARN.
HY-3 Main.xaml vazio — root Activity → Sequence sem children executáveis.
     WARN, indica projeto inicial não desenvolvido.
HY-4 .gitignore ausente ou faltando entries obrigatórios Sicoob:
     `.local/`, `bin/`, `obj/`, `*.user`, `.uipath/`. WARN, project-level.
HY-5 EOL mix CRLF+LF mesmo arquivo. XAML normalize CRLF (Windows std). INFO.
HY-6 BOM em project.json. JSON convention UTF-8 sem BOM. INFO.
"""
from __future__ import annotations

import re
from pathlib import Path

from uip_engine._types import Finding
from uip_engine.context import FileContext, ProjectContext


_RE_MERGE_MARKER = re.compile(r'^(<{7}|={7}|>{7})(?:\s|$)', re.MULTILINE)

_PLACEHOLDER_DESCRIPTIONS = frozenset({
    "",
    "Blank Process",
    "Blank Library",
    "Process Description",
    "Library Description",
})

_GITIGNORE_REQUIRED = (
    ".local/",
    "bin/",
    "obj/",
    "*.user",
    ".uipath/",
)


def _line_for(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


# ---------- HY-1 merge markers ----------

def detect_hy1_merge_markers(rule, fc: FileContext, pc) -> list[Finding]:
    findings: list[Finding] = []
    for m in _RE_MERGE_MARKER.finditer(fc.content):
        findings.append(Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=_line_for(fc.content, m.start()),
            message=f"{rule.title}: marker `{m.group(1)}` leftover",
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings


# ---------- HY-2 placeholder description (project.json) ----------

def detect_hy2_placeholder_description(rule, fc: FileContext, pc: ProjectContext | None) -> list[Finding]:
    if pc is None or not str(fc.path).endswith("project.json"):
        return []
    desc = (pc.project_json.get("description") or "").strip()
    if desc not in _PLACEHOLDER_DESCRIPTIONS:
        return []
    project_name = pc.project_json.get("name", "ProjetoSemNome")
    fix_mech = (rule.fix or {}).get("mechanical")
    if isinstance(fix_mech, dict):
        fix_mech = dict(fix_mech)
        # Inject project name como value default. set_json_field params.
        fix_mech.setdefault("path", "description")
        fix_mech["value"] = f"Projeto Sicoob — {project_name}"
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1,
        message=f"{rule.title}: description='{desc}'",
        fix_mechanical=fix_mech,
        fix_prose=(rule.fix or {}).get("prose"),
    )]


# ---------- HY-3 Main.xaml empty ----------

_RE_ROOT_SEQUENCE_EMPTY = re.compile(
    r'<Activity\b[^>]*>\s*'
    r'(?:<TextExpression\..*?</TextExpression\.[^>]+>\s*)*'  # imports block
    r'(?:<x:Members\s*[/>].*?</x:Members>\s*)?'             # members block
    r'<Sequence\b[^>]*?(?:/>|>\s*'
    r'(?:<Sequence\.Variables\s*[/>].*?</Sequence\.Variables>\s*)?'
    r'</Sequence>)',
    re.DOTALL,
)


def detect_hy3_main_empty(rule, fc: FileContext, pc: ProjectContext | None) -> list[Finding]:
    name = Path(fc.path).name
    if name != "Main.xaml":
        return []
    if _RE_ROOT_SEQUENCE_EMPTY.search(fc.content):
        return [Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=1,
            message=rule.title,
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        )]
    return []


# ---------- HY-4 .gitignore missing entries (project-level) ----------

def detect_hy4_gitignore(rule, fc: FileContext, pc: ProjectContext | None) -> list[Finding]:
    if pc is None or not str(fc.path).endswith("project.json"):
        return []
    gitignore = pc.root / ".gitignore"
    if not gitignore.exists():
        missing = list(_GITIGNORE_REQUIRED)
        fix_mech = (rule.fix or {}).get("mechanical")
        if isinstance(fix_mech, dict):
            fix_mech = dict(fix_mech)
            fix_mech["missing"] = missing
            fix_mech["target"] = str(gitignore)  # destino real do fixer
        # Finding anchor = project.json (sempre existe) p/ safety snapshot.
        # Fixer escreve no `target` injetado em spec.
        return [Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=1,
            message=f"{rule.title}: .gitignore ausente",
            fix_mechanical=fix_mech,
            fix_prose=(rule.fix or {}).get("prose"),
        )]
    try:
        content = gitignore.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    existing = {line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")}
    missing = [e for e in _GITIGNORE_REQUIRED if e not in existing]
    if not missing:
        return []
    fix_mech = (rule.fix or {}).get("mechanical")
    if isinstance(fix_mech, dict):
        fix_mech = dict(fix_mech)
        fix_mech["missing"] = missing
        fix_mech["target"] = str(gitignore)
    # Mesma estratégia: anchor = project.json p/ safety pipeline.
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1,
        message=f"{rule.title}: faltam {missing}",
        fix_mechanical=fix_mech,
        fix_prose=(rule.fix or {}).get("prose"),
    )]


# ---------- HY-5 EOL mix (xaml + json) ----------

def detect_hy5_eol_mix(rule, fc: FileContext, pc) -> list[Finding]:
    try:
        raw = Path(fc.path).read_bytes()
    except OSError:
        return []
    has_crlf = b"\r\n" in raw
    # Stripa CRLF antes pra contar LF puro
    raw_no_crlf = raw.replace(b"\r\n", b"")
    has_lone_lf = b"\n" in raw_no_crlf
    if has_crlf and has_lone_lf:
        return [Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(fc.path), line=1,
            message=rule.title,
            fix_mechanical=(rule.fix or {}).get("mechanical"),
            fix_prose=(rule.fix or {}).get("prose"),
        )]
    return []


# ---------- HY-6 BOM em project.json ----------

def detect_hy6_bom_json(rule, fc: FileContext, pc) -> list[Finding]:
    if not str(fc.path).endswith(".json"):
        return []
    try:
        with open(fc.path, "rb") as fh:
            head = fh.read(3)
    except OSError:
        return []
    if head != b"\xef\xbb\xbf":
        return []
    return [Finding(
        rule_id=rule.id, severity=rule.severity, category=rule.category,
        file=str(fc.path), line=1,
        message=rule.title,
        fix_mechanical=(rule.fix or {}).get("mechanical"),
        fix_prose=(rule.fix or {}).get("prose"),
    )]
