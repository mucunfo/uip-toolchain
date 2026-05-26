"""executor_drive — UiPath Robot Executor headless validation gate.

Stream E §01: ``UiPath.Executor.NetCore.exe`` é o Robot real (Windows target),
mas é **service-bound** — recusa invocação direta com
``System.InvalidOperationException: Execution must happen through the service``.

Probe Phase 6 (ver ``.tmp/phase_6_executor_probe.md``):

* `UiPath.Executor.NetCore.exe` — não invocável headless
* `UiPath.Studio.CommandLine.exe` — só `analyze`/`publish` (já integrado)
* `UiRobot.exe execute --file <xaml>` — **runtime real**, não validate-only

Como não existe gate "validate-only" no executor layer, este módulo expõe um
**opt-in** restritivo que invoca `UiRobot execute --file` em XAMLs isolados
(`Tests/`, `Test_*.xaml`, `*_smoke.xaml`) e captura o exit code + saída.

Fallback ladder (resolução do binário em ordem):

1. env ``UIPATH_EXECUTOR_BIN`` — override explícito (qualquer .exe)
2. ``UiRobot.exe`` do Studio 26 install
3. ``UiRobot.exe`` do Studio 23x install
4. None → finding ``RB-EXEC-INFRA`` (info), engine continua sem gate

Findings emitidos:

* ``RB-EXEC-OK`` — INFO, XAML executou com exit 0
* ``RB-EXEC-FAIL`` — ERROR/BREAKING, XAML retornou exit ≠ 0
* ``RB-EXEC-TIMEOUT`` — WARN, hard-kill após ``timeout``
* ``RB-EXEC-INFRA`` — INFO, binário não localizado ou pré-flight falhou
* ``RB-EXEC-SKIP`` — INFO, nenhum XAML safe-to-run encontrado no projeto

Limitations explicit:

* Gate é **caro** (15–60s por XAML em projetos médios). Opt-in via
  ``UIPATH_RULES_EXECUTOR_GATE=1`` no `cli.py` (não integrar default).
* `UiRobot execute --file` requer Robot service `UiPath.Service.UserHost` ativo.
  Sem service, exit ≠ 0; finding emitido como INFRA.
* **NÃO** invoque em XAMLs com UI activities (Chrome/SAP), Config_*.xlsx com
  credentials reais, ou acesso REST/MQ produtivo. A heurística
  ``_is_safe_to_run`` filtra por convenção de nome — qualquer XAML fora dos
  prefixos seguros (`Tests/`, `Test_`, `_smoke`) é skipado.
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

from ._types import Category, Finding, Severity

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENV_BIN_OVERRIDE = "UIPATH_EXECUTOR_BIN"
_ENV_TIMEOUT = "UIPATH_RULES_EXECUTOR_TIMEOUT"

_DEFAULT_TIMEOUT_SEC = 300

# Studio install candidates (mesmo padrão de analyzer._UIPCLI_CANDIDATE_GLOBS)
_UIROBOT_CANDIDATES = [
    r"%LOCALAPPDATA%\Programs\UiPathPlatform\Studio\*\UiRobot.exe",
    r"%USERPROFILE%\Documents\UiPathStudio23x\UiPath\Studio\UiRobot.exe",
    r"%PROGRAMFILES%\UiPath\Studio\UiRobot.exe",
    r"%PROGRAMFILES(X86)%\UiPath\Studio\UiRobot.exe",
]

# Padrões de XAML safe-to-run (não-produtivos)
_SAFE_PATTERNS = (
    re.compile(r"(?:^|[\\/])Tests?[\\/]", re.IGNORECASE),
    re.compile(r"(?:^|[\\/])Test_[^\\/]+\.xaml$", re.IGNORECASE),
    re.compile(r"_smoke\.xaml$", re.IGNORECASE),
    re.compile(r"_test\.xaml$", re.IGNORECASE),
)


# ---------------------------------------------------------------------------
# Binary resolution
# ---------------------------------------------------------------------------

def _binary_path() -> tuple[Path | None, str]:
    """Resolve binary path. Returns (path, kind) where kind is one of:
    ``"override"``, ``"uirobot"``, ``"unknown"`` (path is None when nothing found).
    """
    explicit = os.environ.get(_ENV_BIN_OVERRIDE)
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return (p, "override")

    import glob
    candidates: list[Path] = []
    for pat in _UIROBOT_CANDIDATES:
        expanded = os.path.expandvars(pat)
        for match in glob.glob(expanded):
            candidates.append(Path(match))

    if not candidates:
        return (None, "unknown")

    # Prefer Studio install with numeric version in parent dir (Studio 26+
    # ships under `Studio\<semver>\` while Studio 23x ships flat at
    # `Studio\`). Numeric-versioned dirs win over flat layouts.
    def _rank(p: Path) -> tuple[int, str]:
        parent = p.parent.name
        has_version = bool(re.match(r"^\d+\.\d+", parent))
        return (1 if has_version else 0, parent)

    candidates.sort(key=_rank, reverse=True)
    return (candidates[0], "uirobot")


# ---------------------------------------------------------------------------
# Safety filter
# ---------------------------------------------------------------------------

def _is_safe_to_run(xaml_path: Path, project_root: Path) -> bool:
    """True iff XAML matches a known-safe pattern (Tests/, Test_*, *_smoke,
    *_test). Anything else is treated as potentially-productive and skipped.
    """
    try:
        rel = xaml_path.relative_to(project_root).as_posix()
    except ValueError:
        rel = xaml_path.as_posix()
    return any(pat.search(rel) for pat in _SAFE_PATTERNS)


def _discover_safe_xamls(project_root: Path) -> list[Path]:
    """Locate XAMLs in project that match safe-to-run convention."""
    safe: list[Path] = []
    for xaml in project_root.rglob("*.xaml"):
        # Skip Activity Migrator backups
        if "_BeforeMigration_" in xaml.as_posix():
            continue
        if _is_safe_to_run(xaml, project_root):
            safe.append(xaml)
    return safe


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

_FAIL_HINTS = (
    re.compile(r"UnhandledException", re.IGNORECASE),
    re.compile(r"System\.InvalidOperationException", re.IGNORECASE),
    re.compile(r"License\s+not\s+available", re.IGNORECASE),
    re.compile(r"Robot\s+service\s+is\s+not\s+running", re.IGNORECASE),
    re.compile(r"could\s+not\s+connect\s+to\s+the\s+robot\s+service", re.IGNORECASE),
    re.compile(r"Activity\s+could\s+not\s+be\s+loaded", re.IGNORECASE),
    # Robot CLI -f rejects raw XAML for windows/cross-platform projects.
    # Surfaces immediately with exit 127. This is an infrastructure
    # limitation, not a workflow defect — caller treats as INFRA.
    re.compile(
        r"not\s+possible\s+to\s+run\s+UiPath\s+Studio\s+windows.*Robot\s+CLI",
        re.IGNORECASE | re.DOTALL,
    ),
)

# When UiRobot rejects raw XAML for Windows projects, downgrade the finding
# from RB-EXEC-FAIL to RB-EXEC-INFRA (infra limitation, not workflow bug).
_INFRA_REJECTION = re.compile(
    r"not\s+possible\s+to\s+run\s+UiPath\s+Studio\s+windows.*Robot\s+CLI",
    re.IGNORECASE | re.DOTALL,
)


def _parse_output(stdout: str, stderr: str) -> str | None:
    """Extract a short summary line from executor output. Returns None when
    no useful hint matched (caller falls back to generic message).
    """
    combined = (stdout or "") + "\n" + (stderr or "")
    for pat in _FAIL_HINTS:
        m = pat.search(combined)
        if m:
            # Walk back to start of the line containing match for context.
            start = combined.rfind("\n", 0, m.start()) + 1
            end = combined.find("\n", m.end())
            if end == -1:
                end = len(combined)
            return combined[start:end].strip()[:240]
    return None


# ---------------------------------------------------------------------------
# Subprocess invoke
# ---------------------------------------------------------------------------

def _invoke_executor(
    binary: Path,
    xaml_path: Path,
    timeout: int,
    kind: str,
) -> tuple[int, str, str, float, bool]:
    """Run binary against xaml_path. Returns (returncode, stdout, stderr,
    duration_sec, timed_out)."""
    if kind == "uirobot":
        args = [str(binary), "execute", "--file", str(xaml_path)]
    elif kind == "override":
        # Override: usuário sabe o que está fazendo. Passa --file convention,
        # se binário não aceitar, returncode reflete.
        args = [str(binary), "execute", "--file", str(xaml_path)]
    else:
        return (-1, "", f"unsupported binary kind: {kind}", 0.0, False)

    start = time.monotonic()
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            ),
        )
    except (FileNotFoundError, PermissionError, OSError) as exc:
        return (-1, "", f"spawn failed: {exc}", 0.0, False)

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        duration = time.monotonic() - start
        return (proc.returncode, stdout, stderr, duration, False)
    except subprocess.TimeoutExpired:
        # Hard-kill: terminate process group (UiRobot can spawn Executor children).
        try:
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
                time.sleep(1.0)
            proc.kill()
        except OSError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        duration = time.monotonic() - start
        return (proc.returncode if proc.returncode is not None else -1,
                stdout, stderr, duration, True)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_validate(
    project_root: Path,
    *,
    timeout: int | None = None,
) -> tuple[int, list[Finding]]:
    """Invoke Executor (via UiRobot wrapper) on safe-to-run XAMLs.

    Args:
        project_root: project folder containing ``project.json``.
        timeout: per-XAML hard timeout (seconds). Default 300, env override
            ``UIPATH_RULES_EXECUTOR_TIMEOUT``.

    Returns:
        ``(exit_code, findings)`` — exit_code is 0 when ALL safe XAMLs passed
        or when no safe XAML was found / no binary available, 2 otherwise.
    """
    findings: list[Finding] = []

    if timeout is None:
        env_to = os.environ.get(_ENV_TIMEOUT)
        try:
            timeout = int(env_to) if env_to else _DEFAULT_TIMEOUT_SEC
        except ValueError:
            timeout = _DEFAULT_TIMEOUT_SEC

    binary, kind = _binary_path()
    if binary is None:
        findings.append(Finding(
            rule_id="RB-EXEC-INFRA",
            severity=Severity.INFO,
            category=Category.BREAKING,
            file=str(project_root),
            line=0,
            message=(
                "executor_drive: nenhum UiRobot.exe/Executor encontrado nos "
                "candidatos padrão. Set UIPATH_EXECUTOR_BIN para override ou "
                "instale UiPath Studio. Gate skipado."
            ),
        ))
        return (0, findings)

    safe_xamls = _discover_safe_xamls(project_root)
    if not safe_xamls:
        findings.append(Finding(
            rule_id="RB-EXEC-SKIP",
            severity=Severity.INFO,
            category=Category.BREAKING,
            file=str(project_root),
            line=0,
            message=(
                "executor_drive: nenhum XAML safe-to-run encontrado "
                "(convenção: Tests/, Test_*.xaml, *_smoke.xaml, *_test.xaml). "
                "Gate skipado — XAMLs produtivos não são executados sem "
                "opt-in explícito por arquivo."
            ),
        ))
        return (0, findings)

    any_fail = False
    for xaml in safe_xamls:
        rc, stdout, stderr, duration, timed_out = _invoke_executor(
            binary, xaml, timeout, kind,
        )
        rel_path = str(xaml)
        if timed_out:
            findings.append(Finding(
                rule_id="RB-EXEC-TIMEOUT",
                severity=Severity.WARN,
                category=Category.BREAKING,
                file=rel_path,
                line=0,
                message=(
                    f"executor_drive: timeout após {duration:.0f}s "
                    f"(limite {timeout}s) executando XAML safe-to-run. "
                    f"binary={binary.name}"
                ),
            ))
            continue

        if rc == 0:
            findings.append(Finding(
                rule_id="RB-EXEC-OK",
                severity=Severity.INFO,
                category=Category.BREAKING,
                file=rel_path,
                line=0,
                message=(
                    f"executor_drive: XAML executou OK em {duration:.1f}s "
                    f"(binary={binary.name})."
                ),
            ))
            continue

        combined = (stdout or "") + "\n" + (stderr or "")
        if _INFRA_REJECTION.search(combined):
            # UiRobot CLI does not accept raw XAML for Windows/cross-platform
            # projects (only legacy or published nupkg). Treat as INFRA — gate
            # cannot validate this project layout without a publish step.
            findings.append(Finding(
                rule_id="RB-EXEC-INFRA",
                severity=Severity.INFO,
                category=Category.BREAKING,
                file=rel_path,
                line=0,
                message=(
                    "executor_drive: UiRobot CLI rejeita XAML direto em "
                    "projetos Windows/cross-platform — só aceita .nupkg "
                    "publicado. Gate skipado para este XAML."
                ),
            ))
            continue

        any_fail = True
        summary = _parse_output(stdout, stderr) or (
            f"exit={rc} (sem hint estruturado em stdout/stderr)"
        )
        findings.append(Finding(
            rule_id="RB-EXEC-FAIL",
            severity=Severity.ERROR,
            category=Category.BREAKING,
            file=rel_path,
            line=0,
            message=(
                f"executor_drive: XAML falhou em {duration:.1f}s — {summary}"
            ),
            fix_prose=(
                "Investigar stack trace completo executando manualmente: "
                f'"{binary}" execute --file "{xaml}". '
                "Se falha é 'Execution must happen through the service', "
                "garanta que UiPath.Service.UserHost está rodando. "
                "Se 'Activity could not be loaded', dependency drift do "
                "Activity Migrator — rodar 'uip <project>' completo."
            ),
        ))

    return (2 if any_fail else 0, findings)


__all__ = ["run_validate"]
