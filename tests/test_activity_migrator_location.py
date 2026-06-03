from __future__ import annotations

import shutil
from pathlib import Path

from uip_engine import migrate


def test_bundled_activity_migrator_is_default(monkeypatch) -> None:
    monkeypatch.delenv("UIPATH_ACTIVITY_MIGRATOR", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    migrator = migrate.find_migrator(None)

    assert migrator is not None
    assert migrator.name == "UiPath.Upgrade.exe"
    repo_root = Path(__file__).resolve().parents[1]
    assert migrator == repo_root / "tools" / "UiPathActivityMigrator" / "UiPath.Upgrade.exe"


def test_machine_global_migrator_paths_are_not_implicit(monkeypatch, tmp_path) -> None:
    fake_repo_file = tmp_path / "repo" / "src" / "uip_engine" / "migrate.py"
    fake_repo_file.parent.mkdir(parents=True)
    fake_repo_file.write_text("", encoding="utf-8")
    fake_path_binary = tmp_path / "path" / "UiPath.Upgrade.exe"
    fake_path_binary.parent.mkdir()
    fake_path_binary.write_bytes(b"fake")
    fake_studio_binary = tmp_path / "studio" / "UiPath.Upgrade.exe"
    fake_studio_binary.parent.mkdir()
    fake_studio_binary.write_bytes(b"fake")

    monkeypatch.delenv("UIPATH_ACTIVITY_MIGRATOR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(fake_studio_binary.parent))
    monkeypatch.setenv("PROGRAMFILES", str(fake_studio_binary.parent))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(fake_studio_binary.parent))
    monkeypatch.setattr(shutil, "which", lambda _name: str(fake_path_binary))
    monkeypatch.setattr(migrate, "__file__", str(fake_repo_file))

    assert migrate.find_migrator(None) is None
