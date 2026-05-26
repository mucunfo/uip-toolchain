"""FixLoopGateCache — caches subprocess gate findings across fix loop iters.

Phase 10 (2026-05-26).

Problem: fix loop iterates fixpoint (até 20 iters em `cli._cmd_fix`). Gates
runtime-loadtest / activity-compile / pack-gate / nuget-gate / analyze custam
30-60s cada. Re-run per-iter inviabiliza fix loop (20 * 60s = 20min só em
gates).

Solution: cache baseline em iter-0, depois per-iter:
  - Drop findings sobre files modificados pelo iter atual.
  - Re-run runtime_loadtest TARGETED só nos files modificados (binary aceita
    `--stdin` batch com lista de paths).
  - Merge: baseline (files não-modificados) + targeted (modificados).

Atualmente cobre APENAS runtime-loadtest. Outros gates (activity-compile,
pack-gate, nuget-gate) ficam em `cli.py::_run_*_gate` helpers — Phase 10.1
backlog.

Contract:
  cache = FixLoopGateCache(project_root)
  # iter 0:
  cache.set_baseline(findings_from_full_run)
  # iter N:
  modified = {Path(...), ...}
  cache.refresh_after_iter(modified)   # drop stale + re-run targeted
  current = cache.merged_findings()    # full snapshot pós-refresh
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ._types import Finding


class FixLoopGateCache:
    """Cache de subprocess gate findings p/ fix loop fixpoint."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self._baseline: list[Finding] | None = None

    @property
    def has_baseline(self) -> bool:
        """True após primeiro set_baseline()."""
        return self._baseline is not None

    def set_baseline(self, findings: list[Finding]) -> None:
        """Registra baseline findings (chamado em iter 0 do fix loop)."""
        self._baseline = list(findings)

    def merged_findings(self) -> list[Finding]:
        """Snapshot atual do cache. Empty list se sem baseline."""
        return list(self._baseline or [])

    def refresh_after_iter(self, modified_files: set[Path]) -> None:
        """Atualiza cache: drop findings sobre modified files + re-run targeted.

        Args:
            modified_files: set de paths absolutos modificados pelo iter atual.

        No-op se:
          - baseline ainda não foi set (cache não populado);
          - modified_files vazio (nada a invalidar).
        """
        if self._baseline is None:
            return
        if not modified_files:
            return

        # Normalize p/ comparação consistente.
        modified_resolved = {Path(p).resolve() for p in modified_files}

        # Drop stale findings sobre modified files. Wrap em try/except pra
        # tolerar findings com `file` inválido (e.g., project.json virtual).
        kept: list[Finding] = []
        for f in self._baseline:
            try:
                f_path = Path(f.file).resolve()
            except (OSError, ValueError):
                # Path inválido — mantém finding (não temos como comparar).
                kept.append(f)
                continue
            if f_path in modified_resolved:
                continue  # drop stale
            kept.append(f)

        # Targeted re-run só dos modified files.
        targeted = self._run_targeted(modified_resolved)
        self._baseline = kept + targeted

    def _run_targeted(self, modified_files: set[Path]) -> list[Finding]:
        """Invoca runtime_loadtest --stdin batch com modified files apenas.

        Returns:
            Lista de Finding produzidos pelo runtime_loadtest binary. Empty
            se binary indisponível, timeout ou erro infra.
        """
        # Lazy import pra evitar ciclo com runtime_loadtest.
        from .runtime_loadtest import _binary_path, _parse_output

        binary = _binary_path()
        if binary is None:
            return []

        # Skipa arquivos que runtime_loadtest também skipa (consistência com
        # invocação full em `run_loadtest`).
        filtered: list[str] = []
        for p in modified_files:
            s = str(p)
            if "_BeforeMigration_" in s:
                continue
            if ".tmp" in p.parts:
                continue
            if p.suffix.lower() != ".xaml":
                continue
            filtered.append(s)

        if not filtered:
            return []

        stdin_data = "\n".join(sorted(filtered))
        try:
            proc = subprocess.run(
                [str(binary), "--stdin"],
                input=stdin_data,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,  # targeted = poucos files, 60s é generoso
                check=False,
                cwd=str(self.project_root),
            )
        except (subprocess.TimeoutExpired, OSError):
            return []

        return _parse_output(proc.stdout, self.project_root, proc.stderr or "")
