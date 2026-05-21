"""F38b — auto-clean `<project>_BeforeMigration_*` siblings após PASS.

PHASE 0 Activity Migrator cria backup pre-swap. Após engine PASS, backup é
dead weight (50-200MB). Auto-clean dispara só em PASS final.

Coverage:
  - Backup matching pattern → removido
  - Backup com timestamp inválido → preservado (não match)
  - Sibling não-relacionado → preservado
  - Opt-out via UIPATH_RULES_KEEP_BACKUP=1
  - Múltiplos backups (corrida anterior) → todos removidos
  - Readonly files (.git/refs) → handler chmod+retry
  - parent não existe → no-op
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from scripts.rule_engine.cli import _cleanup_pre_migration_backups


def _mkproject(parent: Path, name: str) -> Path:
    p = parent / name
    p.mkdir()
    (p / "project.json").write_text('{"name":"X"}', encoding="utf-8")
    return p


def _mkbackup(parent: Path, name: str, timestamp: str) -> Path:
    b = parent / f"{name}_BeforeMigration_{timestamp}"
    b.mkdir()
    (b / "Main.xaml").write_text("<Activity/>", encoding="utf-8")
    return b


def test_backup_matching_pattern_removed(tmp_path):
    project = _mkproject(tmp_path, "my-proj")
    backup = _mkbackup(tmp_path, "my-proj", "20260521-103248")
    assert backup.exists()
    removed = _cleanup_pre_migration_backups(project)
    assert len(removed) == 1
    assert removed[0] == backup
    assert not backup.exists()


def test_backup_invalid_timestamp_preserved(tmp_path):
    project = _mkproject(tmp_path, "my-proj")
    # Wrong format — not YYYYMMDD-HHMMSS
    weird = tmp_path / "my-proj_BeforeMigration_oldversion"
    weird.mkdir()
    removed = _cleanup_pre_migration_backups(project)
    assert removed == []
    assert weird.exists()


def test_unrelated_sibling_preserved(tmp_path):
    project = _mkproject(tmp_path, "my-proj")
    other = _mkproject(tmp_path, "other-proj")
    backup_other = _mkbackup(tmp_path, "other-proj", "20260521-103248")
    # Cleaning my-proj should NOT touch other-proj's backup
    removed = _cleanup_pre_migration_backups(project)
    assert removed == []
    assert other.exists()
    assert backup_other.exists()


def test_multiple_backups_all_removed(tmp_path):
    project = _mkproject(tmp_path, "my-proj")
    b1 = _mkbackup(tmp_path, "my-proj", "20260520-101010")
    b2 = _mkbackup(tmp_path, "my-proj", "20260521-103248")
    b3 = _mkbackup(tmp_path, "my-proj", "20260521-203030")
    removed = _cleanup_pre_migration_backups(project)
    assert set(removed) == {b1, b2, b3}
    for b in (b1, b2, b3):
        assert not b.exists()


def test_opt_out_via_env(tmp_path, monkeypatch):
    project = _mkproject(tmp_path, "my-proj")
    backup = _mkbackup(tmp_path, "my-proj", "20260521-103248")
    monkeypatch.setenv("UIPATH_RULES_KEEP_BACKUP", "1")
    removed = _cleanup_pre_migration_backups(project)
    assert removed == []
    assert backup.exists()


@pytest.mark.parametrize("value", ["1", "true", "yes"])
def test_opt_out_accepts_multiple_truthy(tmp_path, monkeypatch, value):
    project = _mkproject(tmp_path, "my-proj")
    backup = _mkbackup(tmp_path, "my-proj", "20260521-103248")
    monkeypatch.setenv("UIPATH_RULES_KEEP_BACKUP", value)
    removed = _cleanup_pre_migration_backups(project)
    assert removed == []
    assert backup.exists()


def test_no_backups_present_returns_empty(tmp_path):
    project = _mkproject(tmp_path, "my-proj")
    removed = _cleanup_pre_migration_backups(project)
    assert removed == []


def test_parent_not_exist_returns_empty(tmp_path):
    # Project path com parent que não existe (degenerado)
    fake = tmp_path / "nonexistent_parent" / "my-proj"
    removed = _cleanup_pre_migration_backups(fake)
    assert removed == []


def test_readonly_file_in_backup_handled(tmp_path):
    """.git/refs/ + packed-refs frequentemente são readonly no Windows.
    Handler chmod+retry deve resolver."""
    project = _mkproject(tmp_path, "my-proj")
    backup = _mkbackup(tmp_path, "my-proj", "20260521-103248")
    # Create readonly file inside backup
    git_dir = backup / ".git" / "refs"
    git_dir.mkdir(parents=True)
    readonly = git_dir / "HEAD"
    readonly.write_text("ref: refs/heads/main", encoding="utf-8")
    os.chmod(readonly, stat.S_IREAD)
    try:
        removed = _cleanup_pre_migration_backups(project)
        assert len(removed) == 1
        assert not backup.exists()
    finally:
        # Restore if cleanup somehow failed
        if readonly.exists():
            os.chmod(readonly, stat.S_IWRITE)


def test_pattern_excludes_partial_match(tmp_path):
    """Pattern requer EXATO `_BeforeMigration_<timestamp>` suffix; substring
    matches NÃO devem ser removidos."""
    project = _mkproject(tmp_path, "my-proj")
    # Não bate: missing _BeforeMigration_ prefix
    weird1 = tmp_path / "my-proj_Migration_20260521-103248"
    weird1.mkdir()
    # Não bate: timestamp tem extra suffix
    weird2 = tmp_path / "my-proj_BeforeMigration_20260521-103248_extra"
    weird2.mkdir()
    # Bate: exato
    real = _mkbackup(tmp_path, "my-proj", "20260521-103248")

    removed = _cleanup_pre_migration_backups(project)
    assert removed == [real]
    assert weird1.exists()
    assert weird2.exists()


def test_skips_non_directory_siblings(tmp_path):
    """Arquivos com nome matching não devem ser removidos (apenas dirs)."""
    project = _mkproject(tmp_path, "my-proj")
    # File com nome matching pattern (degenerado)
    bogus = tmp_path / "my-proj_BeforeMigration_20260521-103248"
    bogus.write_text("not a dir", encoding="utf-8")
    removed = _cleanup_pre_migration_backups(project)
    assert removed == []
    assert bogus.exists()
