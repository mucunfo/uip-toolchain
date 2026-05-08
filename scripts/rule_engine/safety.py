"""Post-fix safety gate.

Após cada fixer escrever um arquivo, validamos estruturalmente. Camadas:
  1. XML/JSON well-formedness (stdlib parser).
  2. VB ref ↔ declaration consistency (vb_validator) — captura BC30451-class
     errors (var não declarada). Detecta refs órfãs introduzidas pelo fix.

Regressão é DEFINIDA como: estado válido pré-fix + estado inválido pós-fix.
File já malformado pré-fix → fix não criou o defeito → no rollback.

V1 limitations:
  - Cobertura primária: o arquivo passado pro fixer (`f.file`).
  - Multi-file fixers (rename_argument que escreve callers) detectam cascade
    via mtime delta dentro de project_root. Cascade NÃO é roll-backable
    automaticamente nesta versão (sem snapshot pré-fix dos callers); apenas
    surfaceado como [REGRESSION cascade] pra revisão humana.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import vb_validator


@dataclass
class ApplyResult:
    changed: bool
    status: str            # 'ok' | 'noop' | 'error' | 'regression' | 'regression-cascade'
    error: str | None      # human-readable error / regression reason


def validate_file(path: Path) -> tuple[bool, str | None]:
    """Cheap structural validation. XAML→ET.parse; JSON→json.loads.

    Não valida schema UiPath nem VB. Captura corrupção grossa: tags abertas,
    XML mal-formado, JSON quebrado.
    """
    suffix = path.suffix.lower()
    if suffix == ".xaml":
        try:
            ET.parse(str(path))
            return True, None
        except ET.ParseError as e:
            return False, f"XML ParseError: {e}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
    if suffix == ".json":
        try:
            import json as _json
            text = path.read_text(encoding="utf-8-sig")
            _json.loads(text)
            return True, None
        except Exception as e:
            return False, f"JSON: {type(e).__name__}: {e}"
    return True, None


def apply_with_gate(
    fixer: Callable,
    file_path: Path,
    spec: dict[str, Any],
    *,
    dry_run: bool,
    project_root: Path | None = None,
    fixer_kwargs: dict[str, Any] | None = None,
) -> ApplyResult:
    """Wrap fixer call: snapshot primary file → apply → validate → rollback on fail.

    Em modo dry_run: pula snapshot/rollback (fixer não escreve).

    Em modo apply:
      1. Lê bytes pré-fix de `file_path` (snapshot p/ rollback).
      2. Captura mtime de TODOS os XAML em project_root (detectar cascade).
      3. Chama fixer.
      4. Valida `file_path`. Se falha → rollback bytes pré-fix; status=regression.
      5. Detecta arquivos cascade (mtime mudou); valida cada. Se algum falha →
         status=regression-cascade (sem rollback automático nesta versão).
    """
    fixer_kwargs = fixer_kwargs or {}

    # dry_run: no writes, no snapshot
    if dry_run:
        try:
            changed = fixer(file_path, spec, dry_run=True, **fixer_kwargs)
        except Exception as e:
            return ApplyResult(False, "error", f"{type(e).__name__}: {e}")
        return ApplyResult(bool(changed), "ok" if changed else "noop", None)

    # Apply mode: snapshot primary, baseline-validity, cascade tracking.
    # Regression é DEFINIDO como: file era válido pré-fix e ficou inválido pós-fix.
    # Files já malformados pré-fix (XAML com namespace não-bound, JSON quebrado,
    # etc.) NÃO disparam rollback — fixer não introduziu o defeito.
    try:
        primary_bytes = file_path.read_bytes()
    except OSError as e:
        return ApplyResult(False, "error", f"snapshot read: {e}")

    pre_primary_ok, _ = validate_file(file_path)

    pre_validity: dict[Path, bool] = {}
    pre_mtimes: dict[Path, int] = {}
    if project_root is not None:
        try:
            for x in project_root.rglob("*.xaml"):
                try:
                    pre_mtimes[x.resolve()] = x.stat().st_mtime_ns
                except OSError:
                    continue
        except Exception:
            pre_mtimes = {}

    try:
        changed = fixer(file_path, spec, dry_run=False, **fixer_kwargs)
    except Exception as e:
        return ApplyResult(False, "error", f"{type(e).__name__}: {e}")

    if not changed:
        return ApplyResult(False, "noop", None)

    # Primary file — regression só se pre era válido E post não.
    ok, err = validate_file(file_path)
    if pre_primary_ok and not ok:
        try:
            file_path.write_bytes(primary_bytes)
        except OSError as werr:
            return ApplyResult(False, "regression",
                               f"{file_path.name}: {err} | rollback FAILED: {werr}")
        return ApplyResult(False, "regression", f"{file_path.name}: {err} (rolled back)")

    # VB ref orphan check (only XAML, only if XML is well-formed).
    if file_path.suffix.lower() == ".xaml" and ok:
        try:
            pre_text = primary_bytes.decode("utf-8-sig", errors="replace")
            post_text = file_path.read_text(encoding="utf-8-sig", errors="replace")
            new_orphans = vb_validator.diff_orphans(pre_text, post_text)
        except Exception:
            new_orphans = set()
        if new_orphans:
            try:
                file_path.write_bytes(primary_bytes)
            except OSError as werr:
                return ApplyResult(False, "regression-vb",
                                   f"{file_path.name}: new orphan refs {sorted(new_orphans)} | rollback FAILED: {werr}")
            return ApplyResult(False, "regression-vb",
                               f"{file_path.name}: new orphan refs {sorted(new_orphans)} (rolled back)")

    # Cascade detection: files fora do primary que fixer escreveu.
    # Cascade regression: arquivo era válido pré-fix (mtime delta + capturar
    # validity pré). Como não snapshotamos pré-validade de TODOS arquivos
    # (custo alto), aproximação: validate cascade. Caller corrupto = log,
    # mas só conta como regression se mtime mudou + não era válido.
    cascade_errors: list[str] = []
    primary_resolved = file_path.resolve()
    for x_resolved, pre_mt in pre_mtimes.items():
        if x_resolved == primary_resolved:
            continue
        try:
            post_mt = x_resolved.stat().st_mtime_ns
        except OSError:
            continue
        if post_mt == pre_mt:
            continue
        # Arquivo foi escrito. Validar pós; só reportar se inválido AGORA.
        # (Pre-validity desconhecida; conservadoramente reporta como cascade
        # pra revisão humana — não rollback automático nesta versão.)
        ok2, err2 = validate_file(x_resolved)
        if not ok2:
            cascade_errors.append(f"{x_resolved.name}: {err2}")

    if cascade_errors:
        return ApplyResult(True, "regression-cascade",
                           "; ".join(cascade_errors))

    return ApplyResult(True, "ok", None)
