"""LLM-assisted LogMessage traceability validator.

Calls Claude Code CLI (`claude -p`) via subprocess to evaluate whether a
LogMessage message provides semantic traceability or is generic noise.

Caches verdicts per message-hash in `<engine>/.tmp/analyzer_cache/<sig>/llm_logmsg.json`
to avoid re-calling for identical messages across runs.

Batched: validates up to BATCH_SIZE messages per CLI call to amortize
system-prompt cache creation cost.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable


def _resolve_claude_cmd() -> str:
    """Find claude executable. Windows needs .cmd, Unix uses claude."""
    for cand in ("claude.cmd", "claude.exe", "claude"):
        p = shutil.which(cand)
        if p:
            return p
    # Windows fallback
    home = os.path.expanduser("~")
    for cand in (
        Path(home) / "AppData" / "Roaming" / "npm" / "claude.cmd",
        Path(home) / ".local" / "bin" / "claude",
    ):
        if cand.exists():
            return str(cand)
    raise FileNotFoundError("claude CLI not found in PATH or standard locations")

BATCH_SIZE = 50
MAX_PARALLEL = 4  # concurrent Claude CLI subprocess calls
MODEL = "claude-haiku-4-5-20251001"
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
    p = _cache_path(project_root)
    p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_message(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


_SYSTEM_PROMPT = (
    "You evaluate UiPath LogMessage strings for SEMANTIC TRACEABILITY. "
    "For each message, decide if it provides debugging value in production "
    "(specific action, contextual values, distinguishable from other logs).\n\n"
    "Rules:\n"
    "- Generic terms alone ('OK', 'Concluído', 'Done', 'Sucesso', 'Pronto', 'Fim') = fail\n"
    "- Short literals without runtime variable refs = fail\n"
    "- Message with variable concatenation ('& vX', '+ vY') = pass if names meaningful\n"
    "- Message referencing IDs, counts, decisions = pass\n\n"
    "OUTPUT FORMAT — STRICT JSON ARRAY, NO PROSE, NO MARKDOWN FENCES:\n"
    "[{\"idx\": <int>, \"verdict\": \"pass\"|\"fail\", \"reason\": \"<≤80 chars>\"}, ...]\n\n"
    "Use EXACTLY the field names: idx, verdict, reason.\n"
    "Use EXACTLY the verdict values: pass or fail (lowercase).\n"
)


def _call_claude(prompt: str) -> str:
    """Invoke claude CLI -p with prompt via stdin. Returns raw result string."""
    claude_bin = _resolve_claude_cmd()
    cmd = [
        claude_bin, "-p",
        "--output-format", "json",
        "--model", MODEL,
        "--exclude-dynamic-system-prompt-sections",
        "--append-system-prompt", _SYSTEM_PROMPT,
    ]
    proc = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {proc.stderr[:500]}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"claude CLI JSON parse: {e}; stdout[:500]={proc.stdout[:500]}")
    if payload.get("is_error"):
        raise RuntimeError(f"claude CLI is_error: {payload.get('result', '')[:300]}")
    return payload.get("result", "")


def _parse_verdicts(raw: str, n: int) -> list[dict]:
    """Extract JSON array from raw response. Tolerate ```json fences."""
    s = raw.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", s, re.DOTALL)
    if m:
        s = m.group(1).strip()
    try:
        arr = json.loads(s)
    except json.JSONDecodeError:
        return [{"idx": i, "verdict": "pass", "reason": "llm_parse_fail (fail-open)"} for i in range(n)]
    if not isinstance(arr, list):
        return [{"idx": i, "verdict": "pass", "reason": "llm_shape_fail (fail-open)"} for i in range(n)]
    return arr


def validate_messages(
    messages: list[str],
    project_root: Path,
) -> dict[str, dict]:
    """Validate a list of LogMessage Messages. Returns {message: {verdict, reason}}.

    Caches per-message. Only un-cached messages hit the LLM.
    Batches BATCH_SIZE per CLI call.
    """
    cache = _load_cache(project_root)
    result: dict[str, dict] = {}
    pending: list[str] = []

    unique_msgs = list(dict.fromkeys(messages))  # dedupe, preserve order
    for m in unique_msgs:
        h = _hash_message(m)
        if h in cache:
            result[m] = cache[h]
        else:
            pending.append(m)

    # Build batches.
    batches: list[list[str]] = []
    for i in range(0, len(pending), BATCH_SIZE):
        batches.append(pending[i:i + BATCH_SIZE])

    def _run_batch(batch: list[str]) -> tuple[list[str], list[dict]]:
        prompt = "Evaluate these LogMessages:\n\n" + "\n".join(
            f"[{idx}] {msg}" for idx, msg in enumerate(batch)
        ) + "\n\nReturn JSON array."
        try:
            raw = _call_claude(prompt)
            verdicts = _parse_verdicts(raw, len(batch))
        except Exception as e:
            verdicts = [
                {"idx": j, "verdict": "pass", "reason": f"llm_err: {type(e).__name__} (fail-open)"}
                for j in range(len(batch))
            ]
        return batch, verdicts

    # Run batches in parallel via ThreadPoolExecutor.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
        futures = [ex.submit(_run_batch, b) for b in batches]
        for fut in as_completed(futures):
            batch, verdicts = fut.result()
            for v in verdicts:
                idx = v.get("idx", v.get("index", v.get("i")))
                if not isinstance(idx, int) or idx >= len(batch):
                    continue
                raw_verdict = (
                    v.get("verdict")
                    or v.get("traceability")
                    or v.get("result")
                    or v.get("rating")
                    or "pass"
                )
                rv = str(raw_verdict).lower().strip()
                if rv in ("pass", "good", "ok", "ok.", "sufficient", "yes", "true"):
                    verdict = "pass"
                elif rv in ("fail", "poor", "bad", "insufficient", "no", "false"):
                    verdict = "fail"
                else:
                    verdict = "pass"
                reason = v.get("reason") or v.get("explanation") or v.get("rationale") or ""
                msg = batch[idx]
                entry = {"verdict": verdict, "reason": str(reason)[:120]}
                result[msg] = entry
                cache[_hash_message(msg)] = entry

    _save_cache(project_root, cache)
    return result


def is_traceable(message: str, project_root: Path) -> bool:
    """Single-message convenience. Fails-open on LLM error."""
    r = validate_messages([message], project_root)
    return r.get(message, {}).get("verdict", "pass") == "pass"
