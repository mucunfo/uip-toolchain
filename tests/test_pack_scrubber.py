"""Tests for uip_engine.pack_scrubber.

Real-world fixture: a Sicoob CCS library nupkg em
`C:\\Users\\lisan\\OneDrive - Sicoob\\Projects\\.nupkgs\\`. Copy pra tmp_path
antes de qualquer modificação — NUNCA mutar originals.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from uip_engine.pack_scrubber import (
    NupkgInfo,
    inspect,
    scrub_repository,
    _strip_repository_from_nuspec,
    _parse_nuspec_repository,
)


NUPKGS_DIR = Path(r"C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs")
SAMPLE_NUPKG = NUPKGS_DIR / "CCS_SipagDirect.3.0.3.nupkg"


_pytestmark_real_lib = pytest.mark.skipif(
    not SAMPLE_NUPKG.exists(),
    reason="Sample CCS nupkg missing (offline / .nupkgs not synced)",
)


@pytest.fixture
def sample_copy(tmp_path: Path) -> Path:
    """Copia o CCS nupkg pra tmp dir; original NUNCA modificado."""
    if not SAMPLE_NUPKG.exists():
        pytest.skip("Sample nupkg not available")
    target = tmp_path / SAMPLE_NUPKG.name
    shutil.copy(SAMPLE_NUPKG, target)
    return target


# ---------------------------------------------------------------------------
# Unit tests (sintéticos, sem fixture real)
# ---------------------------------------------------------------------------


def _make_nuspec_xml(with_repo: bool = True) -> bytes:
    """Build a minimal nuspec mirroring Studio output."""
    repo_tag = (
        '<repository type="GIT" url="ssh://git@example.com/repo.git" '
        'branch="main" commit="abc123def" />'
        if with_repo
        else ""
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">\n'
        "  <metadata minClientVersion=\"3.3\">\n"
        "    <id>FakeLib</id>\n"
        "    <version>1.2.3</version>\n"
        f"    {repo_tag}\n"
        "  </metadata>\n"
        "</package>\n"
    ).encode("utf-8")


def test_parse_extracts_id_version_repository():
    data = _make_nuspec_xml(with_repo=True)
    meta = _parse_nuspec_repository(data)
    assert meta["id"] == "FakeLib"
    assert meta["version"] == "1.2.3"
    assert meta["repo_url"] == "ssh://git@example.com/repo.git"
    assert meta["repo_commit"] == "abc123def"
    assert meta["repo_branch"] == "main"


def test_parse_no_repository_returns_none():
    data = _make_nuspec_xml(with_repo=False)
    meta = _parse_nuspec_repository(data)
    assert meta["id"] == "FakeLib"
    assert meta.get("repo_url") is None


def test_strip_repository_removes_tag():
    data = _make_nuspec_xml(with_repo=True)
    new_data, removed = _strip_repository_from_nuspec(data)
    assert removed is True
    assert b"<repository" not in new_data
    # id/version preservados
    meta = _parse_nuspec_repository(new_data)
    assert meta["id"] == "FakeLib"
    assert meta["version"] == "1.2.3"
    assert meta.get("repo_url") is None


def test_strip_repository_idempotent_when_absent():
    data = _make_nuspec_xml(with_repo=False)
    new_data, removed = _strip_repository_from_nuspec(data)
    assert removed is False
    # Bytes podem ser re-serialized — não strict equality, mas content equiv.
    meta = _parse_nuspec_repository(new_data)
    assert meta["id"] == "FakeLib"


def test_strip_malformed_xml_safe():
    bad = b"<not xml at all"
    new_data, removed = _strip_repository_from_nuspec(bad)
    assert removed is False
    assert new_data == bad


# ---------------------------------------------------------------------------
# Synthetic .nupkg roundtrip (sem fixture real necessário)
# ---------------------------------------------------------------------------


def _build_synthetic_nupkg(target: Path, *, with_repo: bool = True) -> None:
    """Cria um .nupkg minimal mas estruturalmente válido."""
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("_rels/.rels", "<Relationships/>")
        zf.writestr("FakeLib.nuspec", _make_nuspec_xml(with_repo=with_repo))
        zf.writestr("content/Hello.xaml", "<Activity/>")
        zf.writestr("lib/net6.0/FakeLib.dll", b"\x4d\x5a")  # MZ header dummy


def test_inspect_synthetic_pkg(tmp_path: Path):
    pkg = tmp_path / "FakeLib.1.0.0.nupkg"
    _build_synthetic_nupkg(pkg, with_repo=True)
    info = inspect(pkg)
    assert info.package_id == "FakeLib"
    assert info.version == "1.2.3"
    assert info.repository_url == "ssh://git@example.com/repo.git"
    assert info.has_signature is False
    assert info.content_files_count == 1
    assert info.lib_files_count == 1


def test_scrub_synthetic_inplace(tmp_path: Path):
    pkg = tmp_path / "FakeLib.1.0.0.nupkg"
    _build_synthetic_nupkg(pkg, with_repo=True)
    info_before = inspect(pkg)
    assert info_before.repository_url is not None

    info_after = scrub_repository(pkg)
    assert info_after.repository_url is None
    # Estrutura preservada
    assert info_after.content_files_count == info_before.content_files_count
    assert info_after.lib_files_count == info_before.lib_files_count
    # Re-inspect file (atomic replace happened in place)
    info_check = inspect(pkg)
    assert info_check.repository_url is None


def test_scrub_synthetic_output_path(tmp_path: Path):
    pkg = tmp_path / "FakeLib.1.0.0.nupkg"
    out = tmp_path / "FakeLib.1.0.0.scrubbed.nupkg"
    _build_synthetic_nupkg(pkg, with_repo=True)
    info_after = scrub_repository(pkg, output_path=out)
    assert out.exists()
    assert info_after.repository_url is None
    # Source não modificado
    info_src = inspect(pkg)
    assert info_src.repository_url is not None


def test_scrub_dry_run_no_change(tmp_path: Path):
    pkg = tmp_path / "FakeLib.1.0.0.nupkg"
    _build_synthetic_nupkg(pkg, with_repo=True)
    before_bytes = pkg.read_bytes()
    info_after = scrub_repository(pkg, dry_run=True)
    after_bytes = pkg.read_bytes()
    assert before_bytes == after_bytes
    assert info_after.repository_url is not None  # ainda lá


def test_sha512_sidecar_recomputed(tmp_path: Path):
    import base64
    import hashlib

    pkg = tmp_path / "FakeLib.1.0.0.nupkg"
    _build_synthetic_nupkg(pkg, with_repo=True)
    sidecar = pkg.with_suffix(pkg.suffix + ".sha512")
    sidecar.write_text("STALE-DIGEST", encoding="ascii")

    scrub_repository(pkg)

    expected = base64.b64encode(hashlib.sha512(pkg.read_bytes()).digest()).decode(
        "ascii"
    )
    assert sidecar.read_text(encoding="ascii") == expected


def test_scrub_preserves_entry_order(tmp_path: Path):
    pkg = tmp_path / "FakeLib.1.0.0.nupkg"
    _build_synthetic_nupkg(pkg, with_repo=True)
    with zipfile.ZipFile(pkg, "r") as zf:
        order_before = zf.namelist()
    scrub_repository(pkg)
    with zipfile.ZipFile(pkg, "r") as zf:
        order_after = zf.namelist()
    assert order_after == order_before


# ---------------------------------------------------------------------------
# Real CCS lib fixture (skip se .nupkgs offline)
# ---------------------------------------------------------------------------


@_pytestmark_real_lib
def test_inspect_real_sicoob_lib(sample_copy: Path):
    info = inspect(sample_copy)
    assert info.package_id == "CCS_SipagDirect"
    assert info.version == "3.0.3"
    assert info.repository_url is not None
    assert "bit.sicoob.com.br" in info.repository_url
    assert info.has_signature is False
    assert info.lib_files_count > 0
    assert info.content_files_count > 0


@_pytestmark_real_lib
def test_scrub_removes_repository_real(sample_copy: Path, tmp_path: Path):
    out = tmp_path / "scrubbed.nupkg"
    info_after = scrub_repository(sample_copy, output_path=out)
    assert info_after.repository_url is None
    info_check = inspect(out)
    assert info_check.repository_url is None
    # Source não modificado
    info_src = inspect(sample_copy)
    assert info_src.repository_url is not None


@_pytestmark_real_lib
def test_scrub_preserves_other_content_real(sample_copy: Path, tmp_path: Path):
    out = tmp_path / "scrubbed.nupkg"
    info_before = inspect(sample_copy)
    info_after = scrub_repository(sample_copy, output_path=out)
    assert info_after.content_files_count == info_before.content_files_count
    assert info_after.lib_files_count == info_before.lib_files_count
    assert info_after.total_entries == info_before.total_entries
    # [Content_Types].xml byte-identical (Override entry refers to .nuspec path,
    # which didn't change name).
    assert info_after.content_types_size == info_before.content_types_size


@_pytestmark_real_lib
def test_inplace_atomic_real(sample_copy: Path):
    info_after = scrub_repository(sample_copy)
    assert info_after.repository_url is None
    # Still a valid zip + .nuspec present
    with zipfile.ZipFile(sample_copy, "r") as zf:
        names = zf.namelist()
        assert any(n.endswith(".nuspec") and "/" not in n for n in names)
