"""Tests for uip_engine.watch — mtime-based file watcher."""
import time
from pathlib import Path

import pytest

from uip_engine.watch import snapshot, diff, wait_for_change


def _touch(p: Path, content: str = "x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_snapshot_collects_relevant_files(tmp_path):
    _touch(tmp_path / "project.json", '{"name":"X"}')
    _touch(tmp_path / "Main.xaml", "<Activity />")
    _touch(tmp_path / "assets" / "Config_Dispatcher.xlsx", "x")
    _touch(tmp_path / "ignored.txt", "x")
    state = snapshot(tmp_path)
    paths = {p.name for p in state}
    assert "project.json" in paths
    assert "Main.xaml" in paths
    assert "Config_Dispatcher.xlsx" in paths
    assert "ignored.txt" not in paths


def test_snapshot_excludes_dirs(tmp_path):
    _touch(tmp_path / "Main.xaml", "x")
    _touch(tmp_path / ".tmp" / "Cached.xaml", "x")
    _touch(tmp_path / "bin" / "build.xaml", "x")
    _touch(tmp_path / ".git" / "HEAD", "x")
    state = snapshot(tmp_path)
    names = {str(p) for p in state}
    assert any("Main.xaml" in n for n in names)
    assert not any(".tmp" in n for n in names)
    assert not any("/bin/" in n.replace("\\", "/") for n in names)
    assert not any(".git" in n for n in names)


def test_diff_empty_when_no_change(tmp_path):
    _touch(tmp_path / "Main.xaml", "x")
    s1 = snapshot(tmp_path)
    s2 = snapshot(tmp_path)
    assert diff(s1, s2) == set()


def test_diff_detects_mtime_change(tmp_path):
    p = tmp_path / "Main.xaml"
    _touch(p, "v1")
    s1 = snapshot(tmp_path)
    time.sleep(0.05)
    _touch(p, "v2")
    s2 = snapshot(tmp_path)
    changed = diff(s1, s2)
    assert p in changed


def test_diff_detects_new_file(tmp_path):
    _touch(tmp_path / "Main.xaml", "x")
    s1 = snapshot(tmp_path)
    new_file = tmp_path / "Other.xaml"
    _touch(new_file, "y")
    s2 = snapshot(tmp_path)
    changed = diff(s1, s2)
    assert new_file in changed


def test_diff_detects_removed_file(tmp_path):
    p = tmp_path / "Main.xaml"
    _touch(p, "x")
    s1 = snapshot(tmp_path)
    p.unlink()
    s2 = snapshot(tmp_path)
    changed = diff(s1, s2)
    assert p in changed


def test_wait_for_change_returns_on_modification(tmp_path, monkeypatch):
    """wait_for_change com poll rápido + modificação injetada via fixture."""
    p = tmp_path / "Main.xaml"
    _touch(p, "v1")
    state = snapshot(tmp_path)

    # Patch time.sleep para no-op; injeta mudança no primeiro tick.
    import uip_engine.watch as w
    real_sleep = time.sleep
    tick = {"n": 0}

    def fake_sleep(s):
        tick["n"] += 1
        if tick["n"] == 1:
            # Após primeiro sleep, modifica arquivo p/ trigger
            real_sleep(0.05)
            p.write_text("v2", encoding="utf-8")
        return None

    monkeypatch.setattr(w.time, "sleep", fake_sleep)
    changed = wait_for_change(tmp_path, interval_s=0.0, initial_state=state)
    assert p in changed
