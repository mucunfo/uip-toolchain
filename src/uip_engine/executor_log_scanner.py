"""Robot Execution log scanner — parse `%LOCALAPPDATA%\\UiPath\\Logs\\*_Execution.log`
pra `UIPATH:LOAD ERROR`, `XamlParseException`, VB compile errors pós-execução.

Use case (Tier 5 hardening): após `UiRobot execute --file <xaml>` em PHASE 6
opt-in (UIP_TOOLCHAIN_EXECUTOR_GATE=1), executor_drive.py captura exit code
mas NÃO consulta o log estruturado. Sem o log, RB-EXEC-FAIL traz só exit code
não-informativo. Este módulo enriquece findings com contexto real.

API:

  ``scan_recent_log(since: datetime) -> list[LogEntry]``
    Lê o latest `<date>_Execution.log` em %LOCALAPPDATA%\\UiPath\\Logs,
    parseia linhas com timestamp >= `since`, retorna entries com:
      - level (INFO/WARN/ERROR/FATAL)
      - message (raw text)
      - hit_pattern (None ou name do pattern conhecido casado)

Sem dependency em UiRobot binary — só lê filesystem. Funciona em qualquer
máquina onde Robot service tenha rodado pelo menos uma vez.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# Patterns de erros conhecidos. Match case-insensitive na message body do log.
_KNOWN_PATTERNS = [
    ("UIPATH:LOAD_ERROR", re.compile(r"UIPATH:LOAD\s+ERROR", re.IGNORECASE)),
    ("XAML_PARSE_EXCEPTION", re.compile(r"XamlParseException", re.IGNORECASE)),
    ("VB_NOT_DECLARED", re.compile(r"BC30451|is not declared", re.IGNORECASE)),
    ("ASSEMBLY_LOAD_FAIL", re.compile(r"Could not load (file|assembly)", re.IGNORECASE)),
    ("WORKFLOW_VALIDATION_ERROR", re.compile(r"Validation\s+Error", re.IGNORECASE)),
    ("XAML_OBJECT_WRITER_EX", re.compile(r"XamlObjectWriterException", re.IGNORECASE)),
]

# Linha de log típica:
#   2026-04-30 17:08:43.123 [Trace] [Foo] mensagem...
# `<ISO-ish datetime> [<level>] <body>`
_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
    r"\s+\[?(?P<level>INFO|WARN|ERROR|FATAL|Verbose|Trace|Information|Warning|Error|Fatal)\]?"
    r"\s+(?P<body>.*)$",
    re.IGNORECASE,
)


@dataclass
class LogEntry:
    timestamp: datetime
    level: str
    message: str
    hit_pattern: str | None


def _logs_dir() -> Path:
    """Resolve `%LOCALAPPDATA%\\UiPath\\Logs`."""
    base = os.environ.get("LOCALAPPDATA") or ""
    return Path(base) / "UiPath" / "Logs"


def _latest_execution_log(logs_dir: Path | None = None) -> Path | None:
    """Encontra `<date>_Execution.log` mais recente."""
    d = logs_dir or _logs_dir()
    if not d.is_dir():
        return None
    candidates = sorted(
        (p for p in d.glob("*_Execution.log") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def _match_pattern(message: str) -> str | None:
    for name, pat in _KNOWN_PATTERNS:
        if pat.search(message):
            return name
    return None


def scan_recent_log(
    since: datetime,
    logs_dir: Path | None = None,
) -> list[LogEntry]:
    """Lê latest Execution.log, retorna entries com timestamp >= `since` que
    contém algum `_KNOWN_PATTERNS` match. Empty list se sem log ou sem hits.
    """
    log_path = _latest_execution_log(logs_dir)
    if log_path is None:
        return []
    try:
        text = log_path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    out: list[LogEntry] = []
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        ts_raw = m.group("ts")
        try:
            # Try fractional seconds first; fallback no fractional
            ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        if ts < since:
            continue
        body = m.group("body")
        hit = _match_pattern(body)
        if hit is None:
            continue
        out.append(LogEntry(
            timestamp=ts,
            level=m.group("level"),
            message=body,
            hit_pattern=hit,
        ))
    return out
