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
import hashlib
import os
from pathlib import Path

from uip_engine._types import Finding
from uip_engine.context import FileContext, ProjectContext
from uip_engine.project_view import filter_walk_dirs, iter_project_xamls


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


# ---------- HY-7 unused Studio screenshots ----------

_SCREENSHOT_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"})


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _project_text_surface(pc: ProjectContext) -> str:
    chunks: list[str] = []
    for xaml in iter_project_xamls(pc.root):
        try:
            chunks.append(xaml.read_text(encoding="utf-8-sig", errors="replace"))
        except OSError:
            continue
    try:
        chunks.append((pc.root / "project.json").read_text(
            encoding="utf-8-sig", errors="replace"
        ))
    except OSError:
        pass
    return "\n".join(chunks).lower().replace("\\", "/")


def detect_hy7_unused_screenshots(rule, fc: FileContext, pc: ProjectContext | None) -> list[Finding]:
    if pc is None or Path(fc.path).name != "project.json":
        return []

    surface = _project_text_surface(pc)
    findings: list[Finding] = []
    for current_text, dirs, files in os.walk(pc.root):
        filter_walk_dirs(dirs)
        current = Path(current_text)
        rel_parts = {p.lower() for p in current.relative_to(pc.root).parts}
        if ".screenshots" not in rel_parts:
            continue
        for name in sorted(files):
            target = current / name
            if target.suffix.lower() not in _SCREENSHOT_SUFFIXES:
                continue
            rel = target.relative_to(pc.root).as_posix().lower()
            if name.lower() in surface or rel in surface:
                continue
            digest = _sha256(target)
            if digest is None:
                continue
            findings.append(Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(fc.path),
                line=1,
                message=f"{rule.title}: {rel}",
                fix_mechanical={
                    "type": "delete_project_file",
                    "kind": "screenshot",
                    "target": str(target),
                    "sha256": digest,
                },
                fix_prose=(rule.fix or {}).get("prose"),
            ))
    return findings


# ---------- HY-8 unreachable workflow files ----------

_RE_WORKFLOW_FILE_LITERAL = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*\bWorkflowFileName="([^"\[][^"]*)"',
)
_RE_WORKFLOW_FILE_DYNAMIC = re.compile(
    r'<ui:InvokeWorkflowFile\b[^>]*\bWorkflowFileName="\[',
)


def _norm_rel(path: Path) -> str:
    return path.as_posix().lower().lstrip("./")


def _is_protected_workflow_path(rel: Path) -> bool:
    parts = {p.lower() for p in rel.parts}
    if parts & {"framework", "0.framework", "mocks", "mock", "tests", "unit_tests"}:
        return True
    return any(part.endswith("framework") for part in parts)


def _manifest_workflow_roots(pc: ProjectContext) -> set[Path]:
    roots: set[Path] = set()
    pj = pc.project_json or {}
    for key in ("main", "mainFile", "mainFileName"):
        value = pj.get(key)
        if isinstance(value, str) and value.lower().endswith(".xaml"):
            roots.add((pc.root / value.replace("\\", "/")).resolve())
    roots.add((pc.root / "Main.xaml").resolve())

    def _walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, str) and (
                    k.lower() in {"filename", "file", "filepath", "workflowfilename"}
                    or v.lower().endswith(".xaml")
                ):
                    yield v
                else:
                    yield from _walk(v)
        elif isinstance(value, list):
            for item in value:
                yield from _walk(item)

    for rel in _walk(pj.get("entryPoints")):
        roots.add((pc.root / rel.replace("\\", "/")).resolve())
    return roots


def _resolve_workflow_target(pc: ProjectContext, caller: Path, raw: str) -> Path | None:
    normalized = raw.replace("\\", "/").lstrip("./")
    candidates = [
        pc.root / normalized,
        caller.parent / normalized,
    ]
    by_basename = [p for p in iter_project_xamls(pc.root) if p.name.lower() == Path(normalized).name.lower()]
    candidates.extend(by_basename)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved
    return None


def detect_hy8_unreachable_workflows(rule, fc: FileContext, pc: ProjectContext | None) -> list[Finding]:
    if pc is None or Path(fc.path).name != "project.json":
        return []

    xamls = {p.resolve() for p in iter_project_xamls(pc.root)}
    if not xamls:
        return []

    invokes: dict[Path, set[Path]] = {p: set() for p in xamls}
    has_literal_invoke = False
    for xaml in xamls:
        try:
            text = xaml.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        if _RE_WORKFLOW_FILE_DYNAMIC.search(text):
            return []
        for m in _RE_WORKFLOW_FILE_LITERAL.finditer(text):
            has_literal_invoke = True
            target = _resolve_workflow_target(pc, xaml, m.group(1))
            if target is not None and target in xamls:
                invokes.setdefault(xaml, set()).add(target)
    if not has_literal_invoke:
        return []

    roots = {p for p in _manifest_workflow_roots(pc) if p in xamls}
    roots.update(p for p in xamls if p.name.lower() in {"main.xaml", "process.xaml"})
    reachable = set(roots)
    queue = list(roots)
    while queue:
        current = queue.pop()
        for target in invokes.get(current, set()):
            if target in reachable:
                continue
            reachable.add(target)
            queue.append(target)

    findings: list[Finding] = []
    for xaml in sorted(xamls - reachable, key=lambda p: _norm_rel(p.relative_to(pc.root))):
        rel = xaml.relative_to(pc.root)
        rel_norm = _norm_rel(rel)
        if _is_protected_workflow_path(rel):
            continue
        digest = _sha256(xaml)
        if digest is None:
            continue
        findings.append(Finding(
            rule_id=rule.id,
            severity=rule.severity,
            category=rule.category,
            file=str(fc.path),
            line=1,
            message=f"{rule.title}: {rel.as_posix()}",
            fix_mechanical={
                "type": "delete_project_file",
                "kind": "workflow",
                "target": str(xaml),
                "sha256": digest,
            },
            fix_prose=(rule.fix or {}).get("prose"),
        ))
    return findings
