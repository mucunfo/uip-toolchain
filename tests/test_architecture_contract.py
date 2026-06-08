from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_architecture_tracks_public_publish_contract():
    text = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "ccs-uip-publish-dev" not in text
    assert "ccs-uip-publish-done" not in text
    assert "`ccs-uip-publish`" in text
    assert "publish_readiness.py" in text
    assert "uip rpa pack --skip-analyze" in text
    assert "ProjectView" in text
