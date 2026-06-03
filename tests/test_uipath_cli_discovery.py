from pathlib import Path

from uip_engine import analyzer


def test_discover_uipcli_ignores_official_uip_command(monkeypatch):
    """Official UiPath CLI owns `uip`; Studio gate discovery must not use it."""
    calls = []

    def fake_which(name):
        calls.append(name)
        if name == "uip":
            return r"C:\tools\uip.exe"
        return None

    monkeypatch.delenv("UIPATH_STUDIO_CLI", raising=False)
    monkeypatch.setattr(analyzer.shutil, "which", fake_which)
    monkeypatch.setattr(analyzer, "_UIPCLI_CANDIDATE_GLOBS", ())

    assert analyzer.discover_uipcli() is None
    assert calls == ["UiPath.Studio.CommandLine.exe"]


def test_discover_uipcli_accepts_explicit_studio_cli(monkeypatch, tmp_path):
    studio_cli = tmp_path / "UiPath.Studio.CommandLine.exe"
    studio_cli.write_text("", encoding="utf-8")

    monkeypatch.setenv("UIPATH_STUDIO_CLI", str(studio_cli))

    assert analyzer.discover_uipcli() == Path(studio_cli)
