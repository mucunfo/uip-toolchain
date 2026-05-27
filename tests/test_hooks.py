"""Smoke test hooks — stub stdin JSON, valida stdout."""
from pathlib import Path
import json
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"

# Validation policy: tests NEVER run against `Projects/` UiPath projects.
# Only sanctioned target is the temp performer under Desktop\temp\.
REF_PATH = Path(
    "C:/Users/lisan/Desktop/temp/"
    "contestacao-de-compras-ajuste-na-reserva-de-fraude/"
    "contestacao-de-compras-ajuste-na-reserva-de-fraude-performer"
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
    # Main.xaml em REF (temp performer) emite findings tipo W-3 (default value
    # via element form), V-1 (value-type default Nothing), N-10 (LogMessage
    # antecipatório) e CX-* (cyclomatic complexity) com gates desabilitados.
    assert "[uipath-hook]" in proc.stdout
    assert "W-3" in proc.stdout or "V-1" in proc.stdout


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
    # REF project.json (temp performer) viola TCC-3 (Performer sem pasta Tests/)
    # com gates desabilitados pelos testes via conftest.
    assert "[uipath-hook]" in proc.stdout
    assert "TCC-3" in proc.stdout


def test_post_project_json_edit_silent_on_other_file():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "/tmp/foo.json"}}
    proc = _run_hook(HOOKS / "post_project_json_edit.py", payload)
    assert proc.returncode == 0
    assert proc.stdout == ""
