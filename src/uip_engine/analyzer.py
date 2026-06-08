"""Studio Analyzer integration — diff-based gate.

Engine layer #2 (ground truth): prefers official `uip rpa analyze` and falls
back to `UiPath.Studio.CommandLine.exe analyze` to validate fixes against the
Roslyn VB compiler and assembly metadata schema.

Diff-based: erros pré-existentes (analyzer baseline) são ignorados; só
reportamos erros INTRODUZIDOS pelos fixes.

Studio version vs target framework:
    uipcli respeita `project.json.targetFramework` ao analisar — se project é
    Windows 5.x mas Studio local é 26.x, Analyzer carrega rules compatíveis
    com targetFramework. Diff-based gate adicional protege contra rules-novas
    que Studio local tem mas Studio do CI alvo não — só conta erros novos
    relativos ao baseline.

Graceful degradation: se official `uip` e uipcli legado não forem encontrados,
`run_analyzer` retorna None e o gate é skipado.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


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
    (re.compile(r"\b[A-Z]:\\[^\"'<>|*?\r\n]*?\.xaml\.?", re.IGNORECASE), "<PATH>"),
    (re.compile(r"\b[A-Z]:\\[^\s\"'<>|*?\r\n]+"), "<PATH>"),
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


_XAML_HINT_RE = re.compile(
    r"(?P<path>"
    r"[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*[^\\/:*?\"<>|\r\n]+?\.xaml|"
    r"(?:[A-Za-z0-9_.\-À-ÿ() ]+[\\/])+[A-Za-z0-9_.\-À-ÿ() ]+\.xaml|"
    r"[A-Za-z0-9_.\-À-ÿ()]+\.xaml"
    r")(?=\.?(?:\s|$|[\"'<>]))",
    re.IGNORECASE,
)


def _infer_xaml_basename_from_description(desc: str) -> str:
    """Best-effort fallback for Studio load errors with empty FilePath.

    Some uipcli analyzer payloads report FilePath="" while the Description says
    e.g. "Nao foi possivel carregar o arquivo ...\\Cases\\TC_X.xaml". Without
    a file hint, the fix-loop can only FULL-SNAPSHOT rollback every changed XAML.
    Returning the basename lets the rollback stay granular.
    """
    if not desc:
        return ""
    matches = list(_XAML_HINT_RE.finditer(desc))
    if not matches:
        return ""
    # Prefer the last XAML mention; Studio messages often prefix with a project
    # path and the actual failing workflow appears closest to "Motivo:".
    hint = matches[-1].group("path").replace("/", "\\")
    return os.path.basename(hint)


_VALIDATION_ERROR_XAML_RE = re.compile(
    r"\[(?P<path>[^\]\r\n]+?\.xaml)\]\s+Validation error:\s*(?P<message>[^\r\n]+)",
    re.IGNORECASE,
)


def _read_optional_text(path: Path) -> str:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    return ""


def _infer_xaml_basename_from_validation_log(text: str, needle: str) -> str:
    """Infer XAML basename from official detailed-log validation lines.

    Official `uip rpa analyze` can collapse workflow validation failures into a
    project-level `Analyze failed: BCxxxxx...` envelope. The detailed log still
    carries lines such as:
      `[ValidateWorkflowStep] [Foo.xaml] Validation error: BC36915: ...`

    Returning the basename keeps analyzer-gate rollback granular instead of
    reverting every changed XAML.
    """
    if not text:
        return ""
    codes = {m.group(0).upper() for m in re.finditer(r"\bBC\d{5}\b", needle or "")}
    candidates: list[str] = []
    for match in _VALIDATION_ERROR_XAML_RE.finditer(text):
        message = match.group("message") or ""
        if codes and not any(code in message.upper() for code in codes):
            continue
        candidates.append(match.group("path").replace("/", "\\"))
    if not candidates:
        return ""
    return os.path.basename(candidates[-1])


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


def _official_uip_enabled() -> bool:
    return os.environ.get("UIP_TOOLCHAIN_USE_OFFICIAL_UIP", "1").strip().lower() not in (
        "0", "false", "no", "legacy",
    )


def _write_official_nuget_config(base_dir: Path) -> Path | None:
    ccs_nupkgs = os.environ.get("UIPATH_CCS_NUPKGS_DIR") or (
        r"C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs"
    )
    if not Path(ccs_nupkgs).is_dir():
        return None
    cfg = base_dir / "NuGet.config"
    cfg.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<configuration>\n'
        '  <packageSources>\n'
        '    <clear />\n'
        f'    <add key="Sicoob_Local" value="{ccs_nupkgs}" />\n'
        '    <add key="UiPath_Official" value="https://pkgs.dev.azure.com/uipath/Public.Feeds/_packaging/UiPath-Official/nuget/v3/index.json" />\n'
        '    <add key="UiPath_Marketplace" value="https://gallery.uipath.com/api/v3/index.json" />\n'
        '    <add key="NuGet_Org" value="https://api.nuget.org/v3/index.json" />\n'
        '  </packageSources>\n'
        '</configuration>\n',
        encoding="utf-8",
    )
    return cfg


def _run_official_analyzer(project_root: Path, timeout: int) -> set[AnalyzerIssue] | None:
    """Run official `uip rpa analyze`, returning normalized AnalyzerIssue rows."""
    if not _official_uip_enabled():
        return None
    from .official_uip import (
        compatibility_diagnostic,
        diagnose_official_uip_failure,
        discover_official_uip,
        get_official_uip_version,
        iter_analyzer_records,
        official_failure_text,
        run_official_uip,
    )
    import shutil as _shutil
    import tempfile

    official = discover_official_uip()
    if official is None:
        return None
    version_diag = compatibility_diagnostic(get_official_uip_version(str(official)))
    if version_diag is not None and version_diag.severity.lower() == "error":
        return {
            AnalyzerIssue(
                version_diag.file,
                version_diag.code,
                version_diag.severity,
                _normalize_description(version_diag.message),
            )
        }
    engine_root = Path(__file__).resolve().parents[2]
    base_tmp = engine_root / ".tmp" / "official_uip_analyzer"
    base_tmp.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(dir=str(base_tmp), prefix="analyzer_"))
    try:
        nuget_config = _write_official_nuget_config(tmpdir)
        detailed_log = tmpdir / "analyze.log"
        args = [
            "rpa", "analyze", str(project_root),
            "--output", "json",
            "--detailed-log-path", str(detailed_log),
        ]
        if nuget_config is not None:
            args.extend(["--nuget-sources-config-path", str(nuget_config)])
        governance = os.environ.get("UIPATH_GOVERNANCE_FILE_PATH")
        if governance:
            args.extend(["--governance-file-path", governance])
            gtype = os.environ.get("UIPATH_GOVERNANCE_FILE_TYPE")
            if gtype:
                args.extend(["--governance-file-type", gtype])
        res = run_official_uip(args, timeout=timeout, uip_path=official)
        failure_text = "\n".join(
            part for part in (
                official_failure_text(res),
                _read_optional_text(detailed_log),
            )
            if part
        )
        issues: set[AnalyzerIssue] = set()
        for raw in iter_analyzer_records(res.envelope):
            fp = raw.get("FilePath") or ""
            raw_desc = raw.get("Description") or ""
            basename = os.path.basename(fp) if fp else ""
            if (
                not basename.lower().endswith(".xaml")
                or basename == "System.Activities.Xaml"
            ):
                inferred = _infer_xaml_basename_from_description(raw_desc)
                if inferred:
                    basename = inferred
            if not basename:
                basename = _infer_xaml_basename_from_validation_log(
                    failure_text, raw_desc
                )
            issues.add(AnalyzerIssue(
                basename,
                raw.get("ErrorCode") or "",
                raw.get("ErrorSeverity") or "Error",
                _normalize_description(raw_desc),
            ))
        if res.returncode != 0 and not issues:
            for diagnostic in diagnose_official_uip_failure(
                failure_text,
                "rpa analyze",
            ):
                issues.add(AnalyzerIssue(
                    diagnostic.file,
                    diagnostic.code,
                    diagnostic.severity,
                    _normalize_description(diagnostic.message),
                ))
        if res.returncode != 0 and not issues:
            msg = ""
            if res.envelope is not None:
                msg = res.envelope.message or res.envelope.instructions or ""
            if not msg:
                msg = (res.stderr or res.stdout).strip()
            basename = (
                _infer_xaml_basename_from_description(msg)
                or _infer_xaml_basename_from_validation_log(failure_text, msg)
            )
            issues.add(AnalyzerIssue(
                basename,
                "ANALYZE_HALT",
                "Error",
                _normalize_description(f"official uip rpa analyze exit {res.returncode}: {msg}"),
            ))
        return issues
    except Exception as exc:
        print(f"[analyzer-gate] official uip rpa analyze failed: {exc}", file=sys.stderr)
        return None
    finally:
        _shutil.rmtree(tmpdir, ignore_errors=True)


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
        raw_desc = raw.get("Description") or ""
        basename = os.path.basename(fp) if fp else ""
        if (
            not basename.lower().endswith(".xaml")
            or basename == "System.Activities.Xaml"
        ):
            inferred = _infer_xaml_basename_from_description(raw_desc)
            if inferred:
                basename = inferred
        code = raw.get("ErrorCode") or ""
        sev = raw.get("ErrorSeverity") or ""
        desc = _normalize_description(raw_desc)
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
    halt_window_sec: int | None = None,
    skip_preflight: bool = False,
) -> set[AnalyzerIssue] | None:
    """Run Studio Analyzer on project. Returns set of issues or None if uipcli
    unavailable / invocation failed catastrophically.

    Empty set = clean project (no findings).
    None = gate skipped (graceful).

    Pre-flight + halt-detect (2026-05): antes de invocar `uipcli analyze`,
    verifica install responsivo + cloud reachable. Durante execução, watchdog
    CPU-delta mata uipcli se estagnar (60s sem progresso) — evita timeouts
    180s mudos com causa raiz "cloud heartbeat travado".

    Args:
        halt_window_sec: janela CPU-delta. None usa default módulo (60s).
        skip_preflight: True só pra testes (não invoca preflight). Production
            sempre False.
    """
    # uipcli exige path absoluto pra resolver project.json — relative path
    # retorna stdout vazio com return code 1 (silent fail).
    project_root = project_root.resolve()
    project_json = project_root / "project.json"
    if not project_json.is_file():
        return None

    official_issues = _run_official_analyzer(project_root, timeout)
    if official_issues is not None:
        return official_issues

    from .uipcli_runner import (
        preflight, run_uipcli_guarded, DEFAULT_HALT_WINDOW_SEC,
    )

    cli = uipcli_path or discover_uipcli()
    if cli is None or not cli.is_file():
        return None

    pre = None
    if not skip_preflight:
        pre = preflight(cli)
        if not pre.ok:
            print(f"[analyzer-gate] {pre.as_message()}", file=sys.stderr)
            return None

    res = run_uipcli_guarded(
        [str(cli), "analyze", "-p", str(project_json)],
        timeout_sec=timeout,
        halt_window_sec=halt_window_sec or DEFAULT_HALT_WINDOW_SEC,
        preflight_result=pre,
    )
    if not res.completed:
        print(f"[analyzer-gate] {res.as_diagnostic()}", file=sys.stderr)
        return None
    return parse_analyzer_output(res.stdout, res.stderr)


def _official_uip_cache_salt() -> str:
    """Best-effort official CLI identity for external-gate cache keys."""
    if not _official_uip_enabled():
        return "official-uip=disabled"
    try:
        from .official_uip import discover_official_uip, get_official_uip_version

        official = discover_official_uip()
        if official is None:
            return "official-uip=not-found"
        version = get_official_uip_version(str(official))
        raw_version = version.raw if version is not None else "unknown"
        return f"official-uip={official}|version={raw_version}"
    except Exception as exc:
        return f"official-uip=unreadable:{type(exc).__name__}"


def _project_signature(project_root: Path) -> str:
    """Content/contract hash used by analyzer and pack-gate caches."""
    from .project_view import (
        default_engine_contract_files,
        project_content_signature,
    )

    return project_content_signature(
        project_root,
        extra_files=default_engine_contract_files(),
        salt=f"external-gate-cache-v2\n{_official_uip_cache_salt()}",
    )


def _engine_cache_dir(project_root: Path) -> Path:
    """Cache dir per-project, alojado em `<engine_root>/.tmp/analyzer_cache/<sig>/`.

    Antes ficava em `<project_root>/.uip-toolchain-cache/` — poluía o working
    dir do projeto UiPath e podia vazar pra git (gitignore não cobre). Agora
    fica isolado em `.uip-toolchain/.tmp/` (gitignored, descartável entre
    sessões), alinhado com a política de intermediários da CLAUDE.md.

    `sig` = SHA1 (hex 16 chars) do absolute path do project_root → garante
    isolamento per-project sem colisão entre projetos com mesmo basename.
    """
    engine_root = Path(__file__).resolve().parents[2]
    sig = hashlib.sha1(str(project_root.resolve()).encode("utf-8")).hexdigest()[:16]
    return engine_root / ".tmp" / "analyzer_cache" / sig


def load_cached_baseline(
    project_root: Path,
    cache_dir: Path | None = None,
) -> set[AnalyzerIssue] | None:
    """Carrega baseline cacheado se signature ainda válida. None se miss
    ou cache invalido."""
    cache_dir = cache_dir or _engine_cache_dir(project_root)
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
    cache_dir = cache_dir or _engine_cache_dir(project_root)
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


# Pack-gate cache (Fix #5 2026-05) — analyzer baseline já existia (F27);
# este complementa cacheando findings injetados pelo gate `uipcli publish`.
# Key idêntica (_project_signature) → invalida por conteúdo do projeto,
# descriptor oficial, regras e contrato da engine.

def load_cached_pack_findings(
    project_root: Path,
    cache_dir: Path | None = None,
) -> list[dict] | None:
    """Carrega lista de findings serializados (dict form) do pack-gate.

    Returns:
        list[dict] com schema Finding-compatible se hit, None se miss/inválido.
        Caller é responsável por desserializar pra Finding via FINDING_KEYS.
    """
    cache_dir = cache_dir or _engine_cache_dir(project_root)
    if not cache_dir.is_dir():
        return None
    sig = _project_signature(project_root)
    cache_file = cache_dir / f"pack_findings_{sig}.json"
    if not cache_file.is_file():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, list):
        return None
    return data


def save_cached_pack_findings(
    project_root: Path,
    findings: list[dict],
    cache_dir: Path | None = None,
) -> None:
    """Persist findings (dict form) do pack-gate. No-op em error."""
    cache_dir = cache_dir or _engine_cache_dir(project_root)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    sig = _project_signature(project_root)
    cache_file = cache_dir / f"pack_findings_{sig}.json"
    try:
        cache_file.write_text(
            json.dumps(findings, ensure_ascii=False, indent=2),
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
    raw_new = post - baseline

    # Official `uip rpa analyze` sometimes collapses compiler failures to a
    # project-level ANALYZE_HALT without file/line. The description can change
    # between runs even when the project was already non-analyzable at baseline,
    # which made the fix-loop treat an unstable halt message as a new workflow
    # regression and trigger FULL-SNAPSHOT rollback. Keep final review strict,
    # but do not roll back mechanical fixes for same-kind project-level halts.
    baseline_project_halts = {
        (i.error_code, i.severity)
        for i in baseline
        if not i.file and i.error_code == "ANALYZE_HALT"
    }
    if baseline_project_halts:
        raw_new = {
            i for i in raw_new
            if not (
                not i.file
                and i.error_code == "ANALYZE_HALT"
                and (i.error_code, i.severity) in baseline_project_halts
            )
        }
    return raw_new


def format_issue(issue: AnalyzerIssue) -> str:
    parts = []
    if issue.file:
        parts.append(issue.file)
    if issue.error_code:
        parts.append(issue.error_code)
    parts.append(issue.severity)
    parts.append(issue.description[:200])
    return " | ".join(parts)
