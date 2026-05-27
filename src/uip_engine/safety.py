"""Post-fix safety gate.

Após cada fixer escrever um arquivo, validamos estruturalmente. Camadas:
  1. XML/JSON well-formedness (stdlib parser).
  2. VB ref ↔ declaration consistency (vb_validator) — captura BC30451-class
     errors (var não declarada). Detecta refs órfãs introduzidas pelo fix.

Regressão é DEFINIDA como: estado válido pré-fix + estado inválido pós-fix.
File já malformado pré-fix → fix não criou o defeito → no rollback.

Cobertura:
  - Primary: o arquivo passado pro fixer (`f.file`).
  - Cascade (multi-file fixers tipo rename_argument): bytes pré-fix de TODOS
    XAMLs em project_root snapshotados upfront. Pós-fix, files com mtime
    delta passam por XML well-form gate + VB orphan diff gate; rollback
    automático individual em caso de regressão.
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
    status: str            # 'ok' | 'noop' | 'error' | 'regression' | 'regression-cascade' | 'regression-cascade-vb'
    error: str | None      # human-readable error / regression reason


def _decode_for_vb(raw: bytes) -> str | None:
    """Strict utf-8 decode (BOM-tolerant). None se decode falhar — sinaliza
    gate p/ rollback (encoding corruption = regressão real, não silenciar)."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


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
      2. Captura mtime + bytes de TODOS os XAML em project_root.
      3. Chama fixer.
      4. Valida `file_path`. Se falha → rollback bytes pré-fix; status=regression.
      5. VB orphan gate em primary (decode strict; encoding corruption = rollback).
      6. Cascade: cada file com mtime delta passa por XML well-form + VB orphan;
         rollback individual em regressão; status=regression-cascade(-vb).
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

    pre_mtimes: dict[Path, int] = {}
    pre_bytes_cascade: dict[Path, bytes] = {}
    if project_root is not None:
        try:
            for x in project_root.rglob("*.xaml"):
                try:
                    xr = x.resolve()
                    pre_mtimes[xr] = x.stat().st_mtime_ns
                    pre_bytes_cascade[xr] = x.read_bytes()
                except OSError:
                    continue
        except Exception:
            pre_mtimes = {}
            pre_bytes_cascade = {}

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
    # Decode strict (errors="replace" antes mascarava bytes corrompidos pelo
    # fix → orphans somiam silentemente). Se decode falhar = regressão.
    if file_path.suffix.lower() == ".xaml" and ok:
        pre_text = _decode_for_vb(primary_bytes)
        try:
            post_bytes = file_path.read_bytes()
        except OSError:
            post_bytes = b""
        post_text = _decode_for_vb(post_bytes)
        if pre_text is None or post_text is None:
            try:
                file_path.write_bytes(primary_bytes)
            except OSError as werr:
                return ApplyResult(False, "regression-vb",
                                   f"{file_path.name}: encoding corruption | rollback FAILED: {werr}")
            return ApplyResult(False, "regression-vb",
                               f"{file_path.name}: encoding corruption (rolled back)")
        try:
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
    # Snapshotamos bytes pre-fix de todos XAMLs do projeto (pre_bytes_cascade);
    # rollback automático em caso de regressão XML ou VB-orphan no caller.
    cascade_errors: list[str] = []
    cascade_vb_errors: list[str] = []
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

        # XML well-form gate em cascade.
        ok2, err2 = validate_file(x_resolved)
        if not ok2:
            pre_b = pre_bytes_cascade.get(x_resolved)
            if pre_b is not None:
                try:
                    x_resolved.write_bytes(pre_b)
                    cascade_errors.append(
                        f"{x_resolved.name}: {err2} (rolled back)")
                except OSError as werr:
                    cascade_errors.append(
                        f"{x_resolved.name}: {err2} | rollback FAILED: {werr}")
            else:
                cascade_errors.append(f"{x_resolved.name}: {err2} (no snapshot)")
            continue

        # VB orphan gate em cascade. Decode strict pré e pós.
        pre_b = pre_bytes_cascade.get(x_resolved)
        if pre_b is None:
            continue
        pre_t = _decode_for_vb(pre_b)
        try:
            post_b = x_resolved.read_bytes()
        except OSError:
            continue
        post_t = _decode_for_vb(post_b)
        if pre_t is None or post_t is None:
            # Encoding corruption no cascade → rollback.
            try:
                x_resolved.write_bytes(pre_b)
                cascade_vb_errors.append(
                    f"{x_resolved.name}: encoding corruption (rolled back)")
            except OSError as werr:
                cascade_vb_errors.append(
                    f"{x_resolved.name}: encoding corruption | rollback FAILED: {werr}")
            continue
        try:
            cascade_orphans = vb_validator.diff_orphans(pre_t, post_t)
        except Exception:
            cascade_orphans = set()
        if cascade_orphans:
            try:
                x_resolved.write_bytes(pre_b)
                cascade_vb_errors.append(
                    f"{x_resolved.name}: new orphan refs "
                    f"{sorted(cascade_orphans)} (rolled back)")
            except OSError as werr:
                cascade_vb_errors.append(
                    f"{x_resolved.name}: new orphan refs "
                    f"{sorted(cascade_orphans)} | rollback FAILED: {werr}")

    if cascade_vb_errors:
        return ApplyResult(False, "regression-cascade-vb",
                           "; ".join(cascade_vb_errors))
    if cascade_errors:
        return ApplyResult(False, "regression-cascade",
                           "; ".join(cascade_errors))

    return ApplyResult(True, "ok", None)
