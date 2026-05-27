"""mtime-based file watcher para `cli all` loop em FAIL state.

Poll a cada `interval_s` (default 2s) — coleta snapshot {path: mtime} de:
  - **/*.xaml
  - project.json
  - assets/Config_*.xlsx
  - .gitignore

Bloqueia até qualquer arquivo trocar mtime. Retorna conjunto de paths
modificados. Ctrl-C (KeyboardInterrupt) propagated para abortar loop.

Excluídos: pastas .tmp/, .local/, bin/, obj/, .objects/, .screens/, .git/.
"""
from __future__ import annotations

import time
from pathlib import Path


_WATCH_PATTERNS = ("*.xaml", "project.json", "Config*.xlsx", ".gitignore")
_EXCLUDED_DIRS = frozenset({
    ".tmp", ".local", "bin", "obj", ".objects", ".screens",
    ".git", "__pycache__", "node_modules",
})


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(part in _EXCLUDED_DIRS for part in rel.parts)


def snapshot(root: Path) -> dict[Path, float]:
    """Coleta {path: mtime} para arquivos relevantes em `root`."""
    state: dict[Path, float] = {}
    for pattern in _WATCH_PATTERNS:
        for f in root.rglob(pattern):
            if not f.is_file() or _is_excluded(f, root):
                continue
            try:
                state[f] = f.stat().st_mtime
            except OSError:
                continue
    return state


def diff(before: dict[Path, float], after: dict[Path, float]) -> set[Path]:
    """Conjunto de paths com mtime diferente, novos ou removidos."""
    changed: set[Path] = set()
    for p, mt in after.items():
        if before.get(p) != mt:
            changed.add(p)
    for p in before:
        if p not in after:
            changed.add(p)
    return changed


def wait_for_change(
    root: Path,
    interval_s: float = 2.0,
    initial_state: dict[Path, float] | None = None,
) -> set[Path]:
    """Bloqueia até mtime change em `root`. Retorna paths modificados.

    `interval_s` poll cadence. `initial_state` opcional (default = snapshot
    fresh). KeyboardInterrupt propaga.
    """
    state = initial_state if initial_state is not None else snapshot(root)
    while True:
        time.sleep(interval_s)
        new_state = snapshot(root)
        changed = diff(state, new_state)
        if changed:
            return changed
        state = new_state
