"""Thread-safety tests for `_load_ccs_contracts`.

Regression: assignment de `_CCS_CONTRACTS = {}` ANTES de population permitia
thread B ler dict vazio durante population em thread A. Resultado: detector
CCS-1 perdia findings em parallel mode (`RULE_ENGINE_NO_PARALLEL=0` default).
Sintoma observado em projeto real: 2 CCS-1 findings em serial, 0 em parallel
— silent FAIL no engine pipeline.

Fix: populate em variável local + atomic assignment ao global APÓS conclusão.
Plus threading.Lock pra evitar trabalho duplicado.
"""
from __future__ import annotations

import threading
import zipfile
from pathlib import Path

import pytest

from scripts.rule_engine.heuristics import ccs_contract as cc


def _build_fake_nupkg(out_dir: Path, name: str, workflows: dict[str, list[str]]) -> Path:
    """Cria nupkg sintética com workflows + args em content/*.xaml."""
    nupkg = out_dir / f"{name}.1.0.0.nupkg"
    with zipfile.ZipFile(nupkg, "w") as zf:
        for wf_name, args in workflows.items():
            props = "\n".join(
                f'    <x:Property Name="{a}" Type="InArgument(x:String)" />' for a in args
            )
            xaml = (
                '<?xml version="1.0" encoding="utf-8"?>\n'
                f'<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
                f'          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n'
                f'          x:Class="{wf_name}">\n'
                f'  <x:Members>\n{props}\n  </x:Members>\n'
                f'</Activity>\n'
            )
            zf.writestr(f"content/{wf_name}.xaml", xaml)
    return nupkg


@pytest.fixture
def fake_nupkgs(tmp_path, monkeypatch):
    """Aponta _NUPKGS_DIR pra dir tmp com nupkgs sintéticas + reseta cache."""
    nupkgs_dir = tmp_path / "nupkgs"
    nupkgs_dir.mkdir()
    _build_fake_nupkg(
        nupkgs_dir, "CCS_Foo",
        {"Login": ["in_URL", "in_User"], "Logout": ["in_Session"]},
    )
    _build_fake_nupkg(
        nupkgs_dir, "CCS_Bar",
        {"DoStuff": ["in_Arg1", "out_Result"]},
    )
    monkeypatch.setattr(cc, "_NUPKGS_DIR", nupkgs_dir)
    cc._reset_for_tests()
    yield nupkgs_dir
    cc._reset_for_tests()


def test_load_catalog_serial(fake_nupkgs):
    """Sanity check: catalog popula corretamente em single-thread."""
    catalog = cc._load_ccs_contracts()
    assert set(catalog.keys()) == {"CCS_Foo", "CCS_Bar"}
    assert catalog["CCS_Foo"]["Login"] == ["in_URL", "in_User"]
    assert catalog["CCS_Bar"]["DoStuff"] == ["in_Arg1", "out_Result"]


def test_load_catalog_parallel_no_empty_returns(fake_nupkgs):
    """Race regression: 50 threads chamam _load_ccs_contracts simultaneamente.

    Cada thread DEVE ver o catalog totalmente populado — nenhum vê dict vazio.
    Antes do fix: thread B podia pegar `_CCS_CONTRACTS = {}` assignado por
    thread A pré-population → catalog vazio → CCS-1 detector retorna [].
    """
    results: list[dict] = []
    errors: list[Exception] = []
    barrier = threading.Barrier(50)

    def worker():
        try:
            barrier.wait(timeout=5)  # contention sync
            catalog = cc._load_ccs_contracts()
            results.append(catalog)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"thread errors: {errors}"
    assert len(results) == 50

    # Cada thread DEVE ver catalog completo (2 packages, all workflows).
    for catalog in results:
        assert set(catalog.keys()) == {"CCS_Foo", "CCS_Bar"}, (
            f"thread got partial catalog: {set(catalog.keys())}"
        )
        assert "Login" in catalog["CCS_Foo"]
        assert "DoStuff" in catalog["CCS_Bar"]


def test_load_catalog_idempotent(fake_nupkgs):
    """Calls subsequentes retornam mesmo dict object (cached)."""
    c1 = cc._load_ccs_contracts()
    c2 = cc._load_ccs_contracts()
    assert c1 is c2


def test_reset_for_tests_clears_cache(fake_nupkgs):
    """`_reset_for_tests()` permite re-load (necessário pra testes que mutam fake_nupkgs)."""
    c1 = cc._load_ccs_contracts()
    cc._reset_for_tests()
    c2 = cc._load_ccs_contracts()
    # Mesmo conteúdo, mas pode ser objeto distinto (re-populado).
    assert c1 == c2


def test_missing_nupkgs_dir_returns_empty(tmp_path, monkeypatch):
    """`.nupkgs/` ausente → catalog vazio, não crash."""
    monkeypatch.setattr(cc, "_NUPKGS_DIR", tmp_path / "nonexistent")
    cc._reset_for_tests()
    try:
        catalog = cc._load_ccs_contracts()
        assert catalog == {}
    finally:
        cc._reset_for_tests()
