"""Regression: REF breaking errors must all be in projects.yaml known_exceptions."""
from pathlib import Path
import json
import subprocess
import sys
import yaml
import pytest

ROOT = Path(__file__).resolve().parent.parent
PROJECTS_YAML = ROOT / "projects.yaml"

REF_PATH = Path(
    "C:/Users/lisan/OneDrive - Sicoob/Projects/"
    "importar-cadastro-avais-fiancas-honrados/"
    "importar-cadastro-avais-fiancas-honrados-performer"
)


@pytest.mark.skipif(not REF_PATH.exists(), reason="REF não disponível")
def test_ref_breaking_findings_all_known():
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.rule_engine.cli", "review",
         str(REF_PATH), "--format", "json"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=180,
        encoding="utf-8", errors="replace",
    )
    assert proc.returncode < 10, f"internal error: {proc.stderr}"

    data = json.loads(proc.stdout)
    breaking_errors = {
        f["rule_id"] for f in data["findings"]
        if f["category"] == "breaking" and f["severity"] in ("ERROR", "HALT")
    }

    projects = yaml.safe_load(PROJECTS_YAML.read_text(encoding="utf-8"))
    ref = next(p for p in projects["golden_projects"]
               if p["name"] == REF_PATH.name)
    known = {e["rule_id"] for e in ref.get("known_exceptions", []) or []}

    unexpected = breaking_errors - known
    assert not unexpected, (
        f"REF breaking errors NOT in known_exceptions: {sorted(unexpected)}. "
        f"Either fix REF, add detector exception, or document in projects.yaml."
    )
