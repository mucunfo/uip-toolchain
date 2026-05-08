"""Studio Analyzer integration — diff-based gate.

Engine layer #2 (ground truth): wraps `UiPath.Studio.CommandLine.exe analyze`
para validar fixes contra Roslyn VB compiler + assembly metadata schema.

Diff-based: erros pré-existentes (analyzer baseline) são ignorados; só
reportamos erros INTRODUZIDOS pelos fixes.

Studio version vs target framework:
    uipcli respeita `project.json.targetFramework` ao analisar — se project é
    Windows 5.x mas Studio local é 26.x, Analyzer carrega rules compatíveis
    com targetFramework. Diff-based gate adicional protege contra rules-novas
    que Studio local tem mas Studio do CI alvo não — só conta erros novos
    relativos ao baseline.

Graceful degradation: se uipcli não encontrado, `run_analyzer` retorna None
e gate é skipado (warning only).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AnalyzerIssue:
    """Normalized issue from Studio Analyzer.

    Diff key: (file_basename, error_code, severity, normalized_description).
    File basename used (não path) p/ resiliência a renomes parciais.
    Description normalizada (line numbers/IDs strippados) p/ stable diff.
    """
    file: str          # basename only
    error_code: str    # e.g. "ST-MRD-002", "BC30109", "" if none
    severity: str      # "Error" | "Warning" | "Info"
    description: str   # normalized message


_UIPCLI_CANDIDATE_GLOBS = (
    r"%LocalAppData%\Programs\UiPathPlatform\Studio\*\UiPath.Studio.CommandLine.exe",
    r"%LocalAppData%\Programs\UiPath\Studio\*\UiPath.Studio.CommandLine.exe",
    r"%ProgramFiles%\UiPath\Studio\*\UiPath.Studio.CommandLine.exe",
    r"%ProgramFiles(x86)%\UiPath\Studio\*\UiPath.Studio.CommandLine.exe",
)

_ENV_VAR = "UIPATH_STUDIO_CLI"

# uipcli emite o JSON delimitado por `#json{` ... `}#json` (ambos lados marcam).
# Algumas versões antigas só prefixam — handle both.
_JSON_BLOCK_RE = re.compile(r"#json\s*(\{.*?\})\s*(?:#json\b|$)",
                              re.DOTALL | re.MULTILINE)
_GUID_KEY_RE = re.compile(
    r"^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})-"
    r"(FilePath|ErrorCode|Item|ErrorSeverity|Description|Recommendation)$"
)

# Normalize patterns: strip absolute paths + line numbers + GUIDs em msgs
# para diff stable entre runs.
_NORMALIZE_PATTERNS = (
    (re.compile(r"\b[A-Z]:\\[^\s\"'<>|*?]+"), "<PATH>"),
    (re.compile(r"\b/[a-zA-Z][^\s\"'<>|*?]+"), "<PATH>"),
    (re.compile(r"\b\d{4,}\b"), "<NUM>"),
    (re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
     "<GUID>"),
    # IdRef tokens like LogMessage_Auto_42 → LogMessage_Auto_<N>
    (re.compile(r"_(\d+)\b"), "_<N>"),
)


def _normalize_description(desc: str) -> str:
    """Strip volatile substrings (paths, GUIDs, numeric IDs, line numbers)
    pra que mesmo issue em 2 runs case na diff key."""
    out = desc
    for pat, repl in _NORMALIZE_PATTERNS:
        out = pat.sub(repl, out)
    # Collapse whitespace
    out = re.sub(r"\s+", " ", out).strip()
    return out


def discover_uipcli() -> Path | None:
    """Localize UiPath.Studio.CommandLine.exe. Order: env var, PATH,
    well-known install paths. Most-recent version wins (lexicographic on
    parent dir name → version string)."""
    explicit = os.environ.get(_ENV_VAR)
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    via_path = shutil.which("UiPath.Studio.CommandLine.exe")
    if via_path:
        return Path(via_path)
    candidates: list[Path] = []
    import glob
    for pat in _UIPCLI_CANDIDATE_GLOBS:
        expanded = os.path.expandvars(pat)
        for hit in glob.glob(expanded):
            candidates.append(Path(hit))
    if not candidates:
        return None
    # Sort by parent dir name (version string) — most recent last.
    candidates.sort(key=lambda p: p.parent.name)
    return candidates[-1]


def _parse_json_block(stdout: str) -> list[dict]:
    """Extract the `#json{...}` block, group GUID-prefixed keys into dicts.
    Returns list of normalized issue dicts. Empty list if no #json block."""
    m = _JSON_BLOCK_RE.search(stdout)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    grouped: dict[str, dict] = {}
    for key, val in data.items():
        km = _GUID_KEY_RE.match(key)
        if not km:
            continue
        guid, field_name = km.group(1), km.group(2)
        grouped.setdefault(guid, {})[field_name] = val
    return list(grouped.values())


def parse_analyzer_output(stdout: str, stderr: str = "") -> set[AnalyzerIssue]:
    """Parse uipcli stdout (+ optional stderr) → set of AnalyzerIssue.

    Captures:
      - Issues do bloco #json{...} (analyzer findings).
      - Erros prefixados `NU\\d+:` (pacote NuGet — pré-existente típico).
      - Erros de carregamento "Não foi possível carregar o arquivo X. Motivo:".
    """
    issues: set[AnalyzerIssue] = set()
    for raw in _parse_json_block(stdout):
        fp = raw.get("FilePath") or ""
        basename = os.path.basename(fp) if fp else ""
        code = raw.get("ErrorCode") or ""
        sev = raw.get("ErrorSeverity") or ""
        desc = _normalize_description(raw.get("Description") or "")
        issues.add(AnalyzerIssue(basename, code, sev, desc))

    # NU\d+ package errors (1 per line)
    for line in stdout.splitlines():
        nu = re.match(r"^(NU\d+):\s*(.*)$", line.strip())
        if nu:
            issues.add(AnalyzerIssue(
                "", nu.group(1), "Error",
                _normalize_description(nu.group(2)),
            ))

    return issues


def run_analyzer(
    project_root: Path,
    uipcli_path: Path | None = None,
    timeout: int = 180,
) -> set[AnalyzerIssue] | None:
    """Run Studio Analyzer on project. Returns set of issues or None if uipcli
    unavailable / invocation failed catastrophically.

    Empty set = clean project (no findings).
    None = gate skipped (graceful).
    """
    cli = uipcli_path or discover_uipcli()
    if cli is None or not cli.is_file():
        return None
    # uipcli exige path absoluto pra resolver project.json — relative path
    # retorna stdout vazio com return code 1 (silent fail).
    project_root = project_root.resolve()
    project_json = project_root / "project.json"
    if not project_json.is_file():
        return None
    try:
        proc = subprocess.run(
            [str(cli), "analyze", "-p", str(project_json)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return parse_analyzer_output(proc.stdout or "", proc.stderr or "")


def _project_signature(project_root: Path) -> str:
    """Hash de SHA1(project.json mtime + xaml count + max xaml mtime).
    Usado como cache key — invalida quando projeto muda materialmente."""
    import hashlib
    h = hashlib.sha1()
    pj = project_root / "project.json"
    if pj.is_file():
        h.update(str(int(pj.stat().st_mtime_ns)).encode())
    xamls = list(project_root.rglob("*.xaml"))
    h.update(str(len(xamls)).encode())
    if xamls:
        max_mtime = max(int(x.stat().st_mtime_ns) for x in xamls)
        h.update(str(max_mtime).encode())
    return h.hexdigest()[:16]


def load_cached_baseline(
    project_root: Path,
    cache_dir: Path | None = None,
) -> set[AnalyzerIssue] | None:
    """Carrega baseline cacheado se signature ainda válida. None se miss
    ou cache invalido."""
    cache_dir = cache_dir or (project_root / ".uipath-rules-cache")
    if not cache_dir.is_dir():
        return None
    sig = _project_signature(project_root)
    cache_file = cache_dir / f"analyzer_baseline_{sig}.json"
    if not cache_file.is_file():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return {
        AnalyzerIssue(
            file=item["file"],
            error_code=item["error_code"],
            severity=item["severity"],
            description=item["description"],
        )
        for item in data
    }


def save_cached_baseline(
    project_root: Path,
    baseline: set[AnalyzerIssue],
    cache_dir: Path | None = None,
) -> None:
    """Persist baseline em cache. No-op em error."""
    cache_dir = cache_dir or (project_root / ".uipath-rules-cache")
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    sig = _project_signature(project_root)
    cache_file = cache_dir / f"analyzer_baseline_{sig}.json"
    data = [
        {
            "file": i.file,
            "error_code": i.error_code,
            "severity": i.severity,
            "description": i.description,
        }
        for i in baseline
    ]
    try:
        cache_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def diff_new_issues(
    baseline: set[AnalyzerIssue] | None,
    post: set[AnalyzerIssue] | None,
) -> set[AnalyzerIssue]:
    """Return issues NEW in `post` vs `baseline`. None handling:
      - baseline=None (gate not run pre): returns empty (cannot diff safely).
      - post=None (gate not run post): returns empty.
    """
    if baseline is None or post is None:
        return set()
    return post - baseline


def format_issue(issue: AnalyzerIssue) -> str:
    parts = []
    if issue.file:
        parts.append(issue.file)
    if issue.error_code:
        parts.append(issue.error_code)
    parts.append(issue.severity)
    parts.append(issue.description[:200])
    return " | ".join(parts)
