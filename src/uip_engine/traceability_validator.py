"""Deterministic LogMessage traceability validator.

Evaluates whether a LogMessage message carries semantic traceability: a
specific action plus useful runtime context. This module is deliberately
offline: no model call, no network, no subprocess.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


# Kept for cache compatibility with the pre-rename module. The content is now
# deterministic heuristic verdicts, not LLM responses.
CACHE_FILE_NAME = "llm_logmsg.json"


def _cache_path(project_root: Path) -> Path:
    engine_root = Path(__file__).resolve().parents[2]
    sig = hashlib.sha1(str(project_root.resolve()).encode("utf-8")).hexdigest()[:16]
    cache_dir = engine_root / ".tmp" / "analyzer_cache" / sig
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / CACHE_FILE_NAME


def _load_cache(project_root: Path) -> dict[str, dict]:
    p = _cache_path(project_root)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(project_root: Path, cache: dict[str, dict]) -> None:
    try:
        p = _cache_path(project_root)
        p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _hash_message(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


_GENERIC = {
    "", "ok", "okay", "done", "concluido", "concluida",
    "sucesso", "pronto", "fim", "finalizado", "finalizada", "iniciado",
    "iniciada", "inicio", "started", "finished", "true", "false", "sim",
    "nao", "erro", "error", "falha", "fail", "feito", "realizado",
    "realizada", "executado", "executada", "processando", "aguarde", "next",
    "continua", "continue", "fim do processo", "processo concluido",
    "inicio do processo", "log", "teste", "test", "debug",
}

_VARREF_RE = re.compile(
    r"\b(in|out|io)_[A-Za-z0-9_]+"
    r"|\bv[A-Z][A-Za-z0-9_]*"
    r"|\.ToString\b|\.Reference\b|\.Count\b|\.Length\b|\.Rows\b|\.Item\b"
    r"|\bConfig\s*\(|\bRow\s*\(|\bGenericValue\b|\bException\b|\bTransactionItem\b"
    r"|&\s*[A-Za-z_]|\+\s*[A-Za-z_]",
)


def _decode(s: str) -> str:
    return (s.replace("&quot;", '"').replace("&amp;", "&")
             .replace("&lt;", "<").replace("&gt;", ">").replace("&apos;", "'")
             .replace("&#39;", "'"))


def _heuristic_verdict(message: str) -> dict:
    """Return a conservative pass/fail verdict for one LogMessage message."""
    raw = _decode(message or "").strip()
    body = raw
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()

    if _VARREF_RE.search(body):
        return {"verdict": "pass", "reason": "ref runtime/concat (heuristic)"}

    literals = re.findall(r'"([^"]*)"', body)
    literal = " ".join(literals).strip() if literals else body.strip().strip('"')
    normalized = literal.lower().strip().rstrip(".!:;,")

    if normalized in _GENERIC:
        return {"verdict": "fail", "reason": "termo generico sem contexto"}
    if len(normalized) < 15:
        return {"verdict": "fail", "reason": "literal curto sem contexto"}
    return {"verdict": "pass", "reason": "literal descritivo"}


def validate_messages(
    messages: list[str],
    project_root: Path,
) -> dict[str, dict]:
    """Validate LogMessage messages. Returns `{message: {verdict, reason}}`."""
    cache = _load_cache(project_root)
    result: dict[str, dict] = {}
    dirty = False
    for message in dict.fromkeys(messages):
        key = _hash_message(message)
        hit = cache.get(key)
        if hit is not None:
            result[message] = hit
            continue
        verdict = _heuristic_verdict(message)
        result[message] = verdict
        cache[key] = verdict
        dirty = True
    if dirty:
        _save_cache(project_root, cache)
    return result


def is_traceable(message: str, project_root: Path) -> bool:
    """Single-message convenience wrapper."""
    verdicts = validate_messages([message], project_root)
    return verdicts.get(message, {}).get("verdict", "pass") == "pass"
