"""Phase 10 tests — FixLoopGateCache contract.

Mínimos 3 testes:
  1. Baseline set/get + has_baseline flag.
  2. Refresh drops findings sobre modified files; keep findings sobre unchanged.
  3. Refresh sem baseline_set é no-op (não crasha).

NÃO invoca runtime_loadtest binary real (lento + side effects). Smoke do
binary fica em integration tests separados (out of scope Phase 10).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from uip_engine._gate_cache import FixLoopGateCache
from uip_engine._types import Category, Finding, Severity


def _finding(file: str, rule_id: str = "RT-LOAD-INVALID_WORKFLOW") -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=Severity.ERROR,
        category=Category.BREAKING,
        file=file,
        line=0,
        message=f"synthetic finding for {file}",
    )


def test_baseline_set_get(tmp_path: Path) -> None:
    cache = FixLoopGateCache(tmp_path)
    assert cache.has_baseline is False
    assert cache.merged_findings() == []

    findings = [_finding(str(tmp_path / "Main.xaml"))]
    cache.set_baseline(findings)

    assert cache.has_baseline is True
    out = cache.merged_findings()
    assert len(out) == 1
    assert out[0].rule_id == "RT-LOAD-INVALID_WORKFLOW"
    # Defensive copy: mutar `out` não deve afetar cache.
    out.clear()
    assert len(cache.merged_findings()) == 1


def test_refresh_drops_stale(tmp_path: Path) -> None:
    """Refresh deve dropar findings dos modified files + keep os outros.

    Mock _run_targeted pra evitar invocar binary real.
    """
    file1 = tmp_path / "Main.xaml"
    file2 = tmp_path / "Other.xaml"
    # Touch files pra Path.resolve() funcionar consistente em Windows.
    file1.write_text("<x/>", encoding="utf-8")
    file2.write_text("<x/>", encoding="utf-8")

    cache = FixLoopGateCache(tmp_path)
    cache.set_baseline([
        _finding(str(file1)),
        _finding(str(file2)),
    ])
    assert len(cache.merged_findings()) == 2

    # Mock targeted re-run pra retornar zero findings (file1 ficou clean).
    with patch.object(FixLoopGateCache, "_run_targeted", return_value=[]):
        cache.refresh_after_iter({file1.resolve()})

    remaining = cache.merged_findings()
    assert len(remaining) == 1, (
        f"Esperado 1 finding após refresh (file2 mantido), got {len(remaining)}: "
        f"{[f.file for f in remaining]}"
    )
    assert Path(remaining[0].file).resolve() == file2.resolve()


def test_refresh_no_baseline_noop(tmp_path: Path) -> None:
    """Sem baseline set, refresh deve ser no-op (silencioso, sem crash)."""
    cache = FixLoopGateCache(tmp_path)
    assert cache.has_baseline is False

    fake_path = tmp_path / "Some.xaml"
    # Não deve crashar nem ativar _run_targeted.
    with patch.object(FixLoopGateCache, "_run_targeted") as mock_targeted:
        cache.refresh_after_iter({fake_path})
        mock_targeted.assert_not_called()

    assert cache.has_baseline is False
    assert cache.merged_findings() == []


def test_refresh_empty_modified_noop(tmp_path: Path) -> None:
    """Modified files vazio → refresh é no-op mesmo com baseline set."""
    cache = FixLoopGateCache(tmp_path)
    findings = [_finding(str(tmp_path / "A.xaml"))]
    cache.set_baseline(findings)

    with patch.object(FixLoopGateCache, "_run_targeted") as mock_targeted:
        cache.refresh_after_iter(set())
        mock_targeted.assert_not_called()

    # Baseline preservado.
    assert len(cache.merged_findings()) == 1
