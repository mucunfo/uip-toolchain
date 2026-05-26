"""Smoke test hooks — stub stdin JSON, valida stdout."""
from pathlib import Path
import json
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"

REF_PATH = Path(
    "C:/Users/lisan/OneDrive - Sicoob/Projects/"
    "importar-cadastro-avais-fiancas-honrados/"
    "importar-cadastro-avais-fiancas-honrados-performer"
)


def _run_hook(script: Path, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120,
    )


@pytest.mark.skipif(not REF_PATH.exists(), reason="REF não disponível")
def test_post_xaml_edit_emits_findings_on_known_violator():
    main_xaml = REF_PATH / "Main.xaml"
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(main_xaml)}}
    proc = _run_hook(HOOKS / "post_xaml_edit.py", payload)
    assert proc.returncode == 0, f"hook crashed: {proc.stderr}"
    # Main.xaml em REF tem W-11a + X-1 — esperar findings
    assert "[uipath-hook]" in proc.stdout
    assert "X-1" in proc.stdout or "W-11a" in proc.stdout


def test_post_xaml_edit_silent_on_non_xaml():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "/tmp/foo.txt"}}
    proc = _run_hook(HOOKS / "post_xaml_edit.py", payload)
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_post_xaml_edit_silent_on_other_tool():
    payload = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/foo.xaml"}}
    proc = _run_hook(HOOKS / "post_xaml_edit.py", payload)
    assert proc.returncode == 0
    assert proc.stdout == ""


@pytest.mark.skipif(not REF_PATH.exists(), reason="REF não disponível")
def test_post_project_json_edit_emits_findings():
    pj = REF_PATH / "project.json"
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(pj)}}
    proc = _run_hook(HOOKS / "post_project_json_edit.py", payload)
    assert proc.returncode == 0, f"hook crashed: {proc.stderr}"
    # REF project.json viola J-1 (studioVersion 21.x) + J-2 + J-6
    assert "[uipath-hook]" in proc.stdout
    assert "J-" in proc.stdout


def test_post_project_json_edit_silent_on_other_file():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "/tmp/foo.json"}}
    proc = _run_hook(HOOKS / "post_project_json_edit.py", payload)
    assert proc.returncode == 0
    assert proc.stdout == ""
