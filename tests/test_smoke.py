"""Smoke tests — engine em projetos reais. Não deve crashar."""
from pathlib import Path
import subprocess
import sys
import json as jsonlib
import pytest

ROOT = Path(__file__).resolve().parent.parent
EMPTY_RULES = ROOT / "tests" / "fixtures" / "empty_rules.yaml"

REF_PATH = Path(
    "C:/Users/lisan/OneDrive - Sicoob/Projects/"
    "importar-cadastro-avais-fiancas-honrados/"
    "importar-cadastro-avais-fiancas-honrados-performer"
)
DISPATCHER_PATH = Path(
    "C:/Users/lisan/OneDrive - Sicoob/Projects/"
    "baixar-documentos-cobranca-ajuizada/"
    "baixar-documentos-cobranca-ajuizada-dispatcher"
)
PERFORMER_PATH = Path(
    "C:/Users/lisan/OneDrive - Sicoob/Projects/"
    "baixar-documentos-cobranca-ajuizada/"
    "baixar-documentos-cobranca-ajuizada-performer"
)


def _run_review(project_path: Path, rules_file: Path | None = None):
    cmd = [sys.executable, "-m", "uip_engine.cli", "review",
           str(project_path), "--format", "json"]
    if rules_file is not None:
        cmd += ["--rules-file", str(rules_file)]
    return subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=180,
    )


@pytest.mark.skipif(not REF_PATH.exists(), reason="REF não disponível")
def test_smoke_ref_with_empty_rules_zero_findings():
    """Engine com rules vazio em REF — zero findings, exit 0."""
    proc = _run_review(REF_PATH, EMPTY_RULES)
    assert proc.returncode == 0, f"crashed: {proc.stderr}"
    out = jsonlib.loads(proc.stdout)
    assert out["summary"]["errors"] == 0
    assert out["summary"]["warnings"] == 0


@pytest.mark.skipif(not DISPATCHER_PATH.exists(), reason="dispatcher não disponível")
def test_smoke_dispatcher_with_empty_rules_no_crash():
    proc = _run_review(DISPATCHER_PATH, EMPTY_RULES)
    assert proc.returncode == 0, f"crashed: {proc.stderr}"


@pytest.mark.skipif(not PERFORMER_PATH.exists(), reason="performer não disponível")
def test_smoke_performer_with_empty_rules_no_crash():
    proc = _run_review(PERFORMER_PATH, EMPTY_RULES)
    assert proc.returncode == 0, f"crashed: {proc.stderr}"


@pytest.mark.skipif(not REF_PATH.exists(), reason="REF não disponível")
def test_smoke_ref_current_rules_no_internal_error():
    """REF rodado contra rules.yaml atual — pode ter findings, mas sem erro interno."""
    proc = _run_review(REF_PATH)
    assert proc.returncode < 10, f"internal error (exit {proc.returncode}): {proc.stderr}"


@pytest.mark.skipif(not DISPATCHER_PATH.exists(), reason="dispatcher não disponível")
def test_smoke_dispatcher_current_rules_no_internal_error():
    proc = _run_review(DISPATCHER_PATH)
    assert proc.returncode < 10, f"internal error (exit {proc.returncode}): {proc.stderr}"


@pytest.mark.skipif(not PERFORMER_PATH.exists(), reason="performer não disponível")
def test_smoke_performer_current_rules_no_internal_error():
    proc = _run_review(PERFORMER_PATH)
    assert proc.returncode < 10, f"internal error (exit {proc.returncode}): {proc.stderr}"
