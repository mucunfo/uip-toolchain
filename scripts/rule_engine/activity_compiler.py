"""activity_compiler wrapper — invoca UiPath.ActivityCompiler.CommandLine.exe subprocess.

Compila VB/C# expressions em cada XAML do projeto, producing per-XAML
Expressions DLLs (mesmo binário oficial usado por Studio durante Publish).
Catches:
  - VB compile errors em Variable.Default / InArgument / OutArgument expressions
  - Type unresolved em expression scope
  - Missing assembly refs visíveis em expression context

Stream E §01: binário oficial Studio install. Disponível em duas versões:
  - Studio 23x: C:\\Users\\lisan\\Documents\\UiPathStudio23x\\UiPath\\Studio\\
  - Studio 26:  $(LOCALAPPDATA)\\Programs\\UiPathPlatform\\Studio\\26.0.193-cloud.23060\\

Findings emitidos como `AC-COMPILE-<STATUS>` severity ERROR category BREAKING.

Graceful degradation:
  - Binary not found → AC-COMPILE-INFRA warning, gate skipa.
  - Subprocess timeout → AC-COMPILE-TIMEOUT.
  - Output unparseable → AC-COMPILE-INFRA com snippet.

Sintaxe CLI confirmada via probe (.tmp/phase_1b_cli_probe.md):

  UiPath.ActivityCompiler.CommandLine.exe run \\
      -l <libraryName>        # project.json::name
      -p <projectDirectory>   # project root
      -o <outputFolder>       # tmp dir (must exist)
      -w <outputVersion>      # project.json::projectVersion
      -L VB                   # expression language
      -C true                 # compile expressions AOT
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ._types import Finding, Severity, Category


# Binary name canonical pra ambas versões Studio.
_BINARY_NAME = "UiPath.ActivityCompiler.CommandLine.exe"

# Studio install hints — usadas se env var não setado e registry miss.
# Order: 23x first (older but well-known LTS local install), Studio 26 next.
_STUDIO_HINT_PATHS = (
    r"C:\Users\lisan\Documents\UiPathStudio23x\UiPath\Studio\UiPath.ActivityCompiler.CommandLine.exe",
    r"%LocalAppData%\Programs\UiPathPlatform\Studio\*\UiPath.ActivityCompiler.CommandLine.exe",
    r"%LocalAppData%\Programs\UiPath\Studio\*\UiPath.ActivityCompiler.CommandLine.exe",
    r"%ProgramFiles%\UiPath\Studio\*\UiPath.ActivityCompiler.CommandLine.exe",
    r"%ProgramFiles(x86)%\UiPath\Studio\*\UiPath.ActivityCompiler.CommandLine.exe",
)


def _binary_path() -> Path | None:
    """Resolve UiPath.ActivityCompiler.CommandLine.exe path.

    Lookup order:
      1. env UIPATH_ACTIVITY_COMPILER_BIN (explicit override)
      2. Studio 23x hard-coded user path (confirmed install)
      3. Studio 26 via %LocalAppData%\\Programs\\UiPathPlatform glob (latest)
      4. Other well-known install paths (Programs\\UiPath, ProgramFiles, ...)
      5. None (caller emite AC-COMPILE-INFRA)
    """
    explicit = os.environ.get("UIPATH_ACTIVITY_COMPILER_BIN", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p

    candidates: list[Path] = []
    for hint in _STUDIO_HINT_PATHS:
        expanded = os.path.expandvars(hint)
        if "*" in expanded:
            for match in glob.glob(expanded):
                m = Path(match)
                if m.is_file():
                    candidates.append(m)
        else:
            p = Path(expanded)
            if p.is_file():
                candidates.append(p)

    if not candidates:
        return None

    # Prefer the hard-coded 23x path first (deterministic), then latest version
    # by parent dir name lexicographic sort for glob matches.
    fixed = [c for c in candidates if "UiPathStudio23x" in str(c)]
    if fixed:
        return fixed[0]
    # Studio 26+ candidates — most recent version wins.
    candidates.sort(key=lambda p: p.parent.name)
    return candidates[-1]


def _read_project_meta(project_root: Path) -> tuple[str, str]:
    """Read project.json → (libraryName, outputVersion).

    Defaults if file missing / fields absent:
      libraryName = project_root.name (sanitized to safe identifier)
      outputVersion = "1.0.0"
    """
    project_json = project_root / "project.json"
    default_name = re.sub(r"[^A-Za-z0-9_.-]", "_", project_root.name) or "UnknownProject"
    default_version = "1.0.0"

    if not project_json.is_file():
        return default_name, default_version

    try:
        data = json.loads(project_json.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default_name, default_version

    name = (data.get("name") or "").strip() or default_name
    version = (data.get("projectVersion") or "").strip() or default_version
    return name, version


def run_compile(project_root: Path, timeout: int = 180) -> tuple[int, list[Finding]]:
    """Run UiPath.ActivityCompiler.CommandLine em projeto inteiro.

    Args:
        project_root: Path para raiz do projeto UiPath (contém project.json).
        timeout: Timeout total subprocess em segundos (default 180s = 3min).

    Returns:
        (exit_code, findings_list). exit_code segue subprocess returncode:
        0 = compile OK, !=0 = compile error or infra issue.
    """
    project_root = Path(project_root).resolve()
    binary = _binary_path()
    if binary is None:
        return 2, [_infra_finding(
            project_root,
            "UiPath.ActivityCompiler.CommandLine.exe não encontrado em paths "
            "padrão Studio (23x / UiPathPlatform 26 / Programs UiPath / "
            "ProgramFiles). Override via env UIPATH_ACTIVITY_COMPILER_BIN."
        )]

    # Sanity: project.json deve existir, senão gate não tem o que fazer.
    if not (project_root / "project.json").is_file():
        return 2, [_infra_finding(
            project_root,
            f"project.json não encontrado em {project_root}. "
            "Gate activity_compiler precisa de projeto UiPath válido."
        )]

    library_name, output_version = _read_project_meta(project_root)

    # Tmp output dir — engine root /.tmp/activity_compiler/<project_hash>/.
    # Hash do path absoluto pra evitar collision entre runs paralelos em
    # projetos diferentes mas com mesmo nome.
    engine_root = Path(__file__).resolve().parents[2]
    proj_hash = hashlib.sha1(str(project_root).encode("utf-8")).hexdigest()[:10]
    out_dir = engine_root / ".tmp" / "activity_compiler" / proj_hash
    try:
        # Wipe stale output (caso run anterior tenha deixado fragments).
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return 2, [_infra_finding(
            project_root,
            f"Falha ao criar tmp output dir {out_dir}: {type(e).__name__}: {e}."
        )]

    cmd = [
        str(binary), "run",
        "-l", library_name,
        "-p", str(project_root),
        "-o", str(out_dir),
        "-w", output_version,
        "-L", "VB",
        "-C", "true",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        return 2, [Finding(
            rule_id="AC-COMPILE-TIMEOUT",
            severity=Severity.ERROR,
            category=Category.BREAKING,
            file=str(project_root / "project.json"),
            line=0,
            message=f"UiPath.ActivityCompiler.CommandLine timeout >{timeout}s. "
                    "Aumentar --activity-compile-timeout ou investigar "
                    "projeto gigante / loop em compile.",
        )]
    except OSError as e:
        return 2, [_infra_finding(
            project_root,
            f"activity_compiler subprocess OSError: {type(e).__name__}: {e}. "
            "Binary corrupto ou permissão negada?"
        )]
    finally:
        # Sempre cleanup output dir — só interessam diagnostics, não DLL output.
        try:
            shutil.rmtree(out_dir, ignore_errors=True)
        except OSError:
            pass

    findings = _parse_output(proc.stdout or "", proc.stderr or "", project_root)
    # Se exit !=0 mas zero findings parseable, emit INFRA com snippet pra
    # facilitar debug.
    if proc.returncode != 0 and not findings:
        combined = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
        snippet = combined[:600] if combined else "(empty output)"
        findings.append(_infra_finding(
            project_root,
            f"activity_compiler exit={proc.returncode} sem findings parseable. "
            f"Output snippet: {snippet!r}"
        ))
    return proc.returncode, findings


def _infra_finding(project_root: Path, message: str) -> Finding:
    """Helper pra finding diagnóstico de infra (binary missing/timeout/parse)."""
    return Finding(
        rule_id="AC-COMPILE-INFRA",
        severity=Severity.WARN,
        category=Category.METADATA,
        file=str(project_root / "project.json"),
        line=0,
        message=message,
        fix_prose=(
            "Gate activity_compiler skipa silenciosamente se binary não "
            "encontrado. Instalar Studio (qualquer versão >=23.10) ou setar "
            "env UIPATH_ACTIVITY_COMPILER_BIN apontando pra binary custom."
        ),
    )


# Pattern 1: `<path>.xaml(line,col): BC<NNNN>: <msg>`
#         or `<path>.xaml(line,col): error BC<NNNN>: <msg>`
_FILE_POS_DIAG_RE = re.compile(
    r"^(?P<file>[^\s:][^:]*\.xaml)"
    r"\((?P<line>\d+),(?P<col>\d+)\)"
    r":\s*(?:error\s+|warning\s+)?(?P<code>BC\d{4,5}|CS\d{4,5}|[A-Z]{2,5}\d{2,5})"
    r":\s*(?P<msg>.+?)\s*$",
    re.MULTILINE,
)

# Pattern 2: `<path>.xaml: BC<NNNN>: <msg>` (no position)
_FILE_DIAG_RE = re.compile(
    r"^(?P<file>[^\s:][^:]*\.xaml)"
    r":\s*(?:error\s+|warning\s+)?(?P<code>BC\d{4,5}|CS\d{4,5}|[A-Z]{2,5}\d{2,5})"
    r":\s*(?P<msg>.+?)\s*$",
    re.MULTILINE,
)

# Pattern 3: generic `error <code>: <msg>` sem file context
_GENERIC_ERR_RE = re.compile(
    r"^\s*(?:error|Error)\s+(?P<code>[A-Z]{2,5}\d{2,5}|BC\d{4,5}|CS\d{4,5})"
    r":\s*(?P<msg>.+?)\s*$",
    re.MULTILINE,
)


def _parse_output(stdout: str, stderr: str, project_root: Path) -> list[Finding]:
    """Parse stdout+stderr em lista de Finding.

    Dedup por (file, code, msg[:120]) pra evitar duplicates quando mesmo
    erro aparece em stdout E stderr.
    """
    findings: list[Finding] = []
    seen: set[tuple[str, str, str]] = set()
    combined = (stdout or "") + "\n" + (stderr or "")

    def _emit(file_path: str, line_no: int, code: str, msg: str) -> None:
        msg_short = (msg or "").strip()
        if len(msg_short) > 400:
            msg_short = msg_short[:397] + "..."
        dedup_key = (file_path, code, msg_short[:120])
        if dedup_key in seen:
            return
        seen.add(dedup_key)
        findings.append(Finding(
            rule_id=f"AC-COMPILE-{code}",
            severity=Severity.ERROR,
            category=Category.BREAKING,
            file=file_path,
            line=line_no,
            message=f"Expression compile fail [{code}]: {msg_short}",
            fix_prose=(
                "UiPath.ActivityCompiler.CommandLine rejeitou o XAML durante "
                "compile AOT de expressions VB/C#. Causas típicas: smart-quote "
                "em Variable.Default ('“' em vez de '\"'), parens unbalanced, "
                "identifier não declarado em scope, type unresolved (assembly "
                "ref missing), syntax error em condição IfElse/While/Assign. "
                "Abra XAML em Studio e procure underline vermelho na linha."
            ),
        ))

    # Pattern 1 — com posição
    for m in _FILE_POS_DIAG_RE.finditer(combined):
        file_raw = m.group("file").strip()
        # Resolve absolute path se relativo ao project root.
        file_path = _resolve_file(file_raw, project_root)
        try:
            line_no = int(m.group("line"))
        except (TypeError, ValueError):
            line_no = 0
        _emit(file_path, line_no, m.group("code"), m.group("msg"))

    # Pattern 2 — sem posição. Pula matches já cobertos por pattern 1
    # (mesmo file + code).
    for m in _FILE_DIAG_RE.finditer(combined):
        file_raw = m.group("file").strip()
        # Skip if combined re-match would clash: dedup_key cuida disso.
        file_path = _resolve_file(file_raw, project_root)
        _emit(file_path, 0, m.group("code"), m.group("msg"))

    # Pattern 3 — generic, sem file (atribui a project.json)
    if not findings:
        for m in _GENERIC_ERR_RE.finditer(combined):
            _emit(
                str(project_root / "project.json"),
                0,
                m.group("code"),
                m.group("msg"),
            )

    return findings


def _resolve_file(file_raw: str, project_root: Path) -> str:
    """Resolve raw file string (relative or absolute) to absolute path str."""
    p = Path(file_raw)
    if p.is_absolute():
        return str(p)
    candidate = (project_root / file_raw).resolve()
    return str(candidate)
