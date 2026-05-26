"""Structured status emission — `.uip-toolchain/.tmp/engine_status.json`.

Permite monitor robusto sem `tail | grep` no stdout (que sofre com log dedup,
encoding e flush). Toda transição de fase atualiza o JSON via atomic write.

Schema (estável; mantenha backwards-compat ao alterar):

    {
      "schema_version": 1,
      "project": "C:/.../performer",
      "started_at": <epoch_sec>,
      "last_update": <epoch_sec>,
      "iter_no": <int>,        # 1-based loop counter
      "current_phase": <str|null>,
      "phases": [
        {
          "name": "phase1_deterministic",
          "iter_no": 1,
          "started_at": <epoch_sec>,
          "ended_at": <epoch_sec|null>,
          "status": "running|ok|fail|skipped",
          "details": { ... arbitrário ... }
        },
        ...
      ],
      "exit_status": "PASS|PENDING_REVIEW|FAIL|null"
    }

Atomic: escreve em `engine_status.json.tmp` + `os.replace()` → leitores nunca
veem arquivo parcial.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def _status_path() -> Path:
    engine_root = Path(__file__).resolve().parents[2]
    p = engine_root / ".tmp" / "engine_status.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


class EngineStatus:
    """Estado mutável do pipeline. Persiste atomicamente após cada update."""

    def __init__(self, project: Path) -> None:
        self.path = _status_path()
        self.state: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "project": str(project),
            "started_at": time.time(),
            "last_update": time.time(),
            "iter_no": 0,
            "current_phase": None,
            "phases": [],
            "exit_status": None,
        }
        self._flush()

    def begin_iter(self, iter_no: int) -> None:
        self.state["iter_no"] = iter_no
        self.state["last_update"] = time.time()
        self._flush()

    def begin_phase(self, name: str) -> None:
        """Marca início de uma fase. Append em `phases`. Set `current_phase`."""
        self.state["current_phase"] = name
        self.state["phases"].append({
            "name": name,
            "iter_no": self.state["iter_no"],
            "started_at": time.time(),
            "ended_at": None,
            "status": "running",
            "details": {},
        })
        self.state["last_update"] = time.time()
        self._flush()

    def end_phase(self, status: str, **details: Any) -> None:
        """Marca fim da fase corrente. `status` = ok|fail|skipped."""
        if not self.state["phases"]:
            return
        last = self.state["phases"][-1]
        last["ended_at"] = time.time()
        last["status"] = status
        if details:
            last["details"].update(_jsonable(details))
        self.state["current_phase"] = None
        self.state["last_update"] = time.time()
        self._flush()

    def finalize(self, exit_status: str) -> None:
        """Marca verdict final do pipeline."""
        self.state["exit_status"] = exit_status
        self.state["last_update"] = time.time()
        self._flush()

    def _flush(self) -> None:
        """Atomic write — tmp + replace garante leitor nunca vê parcial."""
        tmp = self.path.with_suffix(".json.tmp")
        try:
            tmp.write_text(
                json.dumps(self.state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, self.path)
        except OSError:
            # Non-fatal — status JSON é observabilidade, não load-bearing.
            pass


def _jsonable(obj: Any) -> Any:
    """Recursivamente converte obj pra primitives JSON-safe.

    Tipos especiais: Path → str, set → list, datetime → isoformat,
    objetos arbitrários → repr.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if isinstance(obj, set):
        return sorted(_jsonable(x) for x in obj)
    # Generic fallback — last resort
    return repr(obj)
