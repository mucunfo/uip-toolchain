"""LogMessage traceability validator — 100% determinístico, OFFLINE.

Avalia se a Message de um LogMessage tem rastreabilidade semântica (ação
específica + contexto runtime) ou é ruído genérico.

HISTÓRICO (2026-05-30): versão anterior chamava `claude -p` (Claude Code CLI,
haiku) via subprocess por mensagem não-cacheada. Isso consumia o limite semanal
de tokens em TODA run de `uip` (N-16 dispara no review). REMOVIDO POR COMPLETO:
nenhum spawn de `claude`, nenhuma chamada de rede, nenhum subprocess. `uip` é
100% script offline. A heurística abaixo replica as regras do antigo
system-prompt de forma determinística.

Caches verdicts per message-hash em
`<engine>/.tmp/analyzer_cache/<sig>/llm_logmsg.json` (mantido p/ compat + skip de
recomputo barato).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


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


# ---------------------------------------------------------------------------
# Heurística determinística (substitui o antigo julgamento via LLM)
# ---------------------------------------------------------------------------

# Termos genéricos puros (sem contexto) → fail. Lower, sem pontuação final.
_GENERIC = {
    "", "ok", "okay", "done", "concluido", "concluído", "concluida", "concluída",
    "sucesso", "pronto", "fim", "finalizado", "finalizada", "iniciado", "iniciada",
    "inicio", "início", "started", "finished", "true", "false", "sim", "nao", "não",
    "erro", "error", "falha", "fail", "feito", "realizado", "realizada", "executado",
    "executada", "processando", "aguarde", "next", "continua", "continue",
    "fim do processo", "processo concluido", "processo concluído", "inicio do processo",
    "início do processo", "log", "teste", "test", "debug",
}

# Referência runtime: argumentos (in_/out_/io_), variáveis Hungarian (vXxx),
# membros (.ToString/.Reference/.Count/.Rows/.Length), Config(...)/Row(...),
# concatenação com identificador (+ x / & x). Presença => rastreável (pass).
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
    """Determinístico. Bias conservador (na dúvida, pass — fail-open histórico)."""
    raw = _decode(message or "").strip()
    body = raw
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()

    # Referência runtime / concatenação com identificador → rastreável.
    if _VARREF_RE.search(body):
        return {"verdict": "pass", "reason": "ref runtime/concat (heuristic)"}

    # Só literal: extrai texto entre aspas (ou o corpo inteiro).
    lits = re.findall(r'"([^"]*)"', body)
    lit = " ".join(lits).strip() if lits else body.strip().strip('"')
    norm = lit.lower().strip().rstrip(".!:;,…")

    if norm in _GENERIC:
        return {"verdict": "fail", "reason": "termo genérico sem contexto (heuristic)"}
    if len(norm) < 15:
        return {"verdict": "fail", "reason": "literal curto sem contexto (heuristic)"}
    # Literal descritivo longo (ação específica) → pass.
    return {"verdict": "pass", "reason": "literal descritivo (heuristic)"}


def validate_messages(
    messages: list[str],
    project_root: Path,
) -> dict[str, dict]:
    """Valida LogMessages. Retorna {message: {verdict, reason}}.

    100% determinístico/offline. Cacheado per-message (skip recomputo).
    """
    cache = _load_cache(project_root)
    result: dict[str, dict] = {}
    dirty = False
    for m in dict.fromkeys(messages):  # dedupe, preserva ordem
        h = _hash_message(m)
        hit = cache.get(h)
        if hit is not None:
            result[m] = hit
        else:
            v = _heuristic_verdict(m)
            result[m] = v
            cache[h] = v
            dirty = True
    if dirty:
        _save_cache(project_root, cache)
    return result


def is_traceable(message: str, project_root: Path) -> bool:
    """Single-message convenience."""
    r = validate_messages([message], project_root)
    return r.get(message, {}).get("verdict", "pass") == "pass"
