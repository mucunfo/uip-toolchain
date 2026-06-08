from __future__ import annotations

import os

from uip_engine.project_view import (
    iter_project_json_files,
    iter_project_xamls,
    project_content_signature,
)


def test_project_xaml_view_skips_technical_dirs(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "Main.xaml").write_text("<Activity />", encoding="utf-8")
    for folder in (".tmp", ".local", ".settings", "bin", "obj", "node_modules"):
        cached = project / folder
        cached.mkdir()
        (cached / "Cached.xaml").write_text("<Activity />", encoding="utf-8")

    assert [path.name for path in iter_project_xamls(project)] == ["Main.xaml"]


def test_project_json_view_skips_publish_handoff_dirs(tmp_path):
    root = tmp_path / "root"
    repo = root / "Repo"
    repo.mkdir(parents=True)
    (repo / "project.json").write_text("{}", encoding="utf-8")

    handoff = root / ".publish-dev-handoff" / "Bad"
    handoff.mkdir(parents=True)
    (handoff / "project.json").write_text("{}", encoding="utf-8")

    found = list(
        iter_project_json_files(root, extra_skip_dirs={".publish-dev-handoff"})
    )

    assert found == [repo / "project.json"]


def test_project_content_signature_uses_content_not_mtime(tmp_path):
    project = tmp_path / "Project"
    project.mkdir()
    (project / "project.json").write_text("{}", encoding="utf-8")
    xaml = project / "Main.xaml"
    xaml.write_text("<Activity DisplayName=\"Before\" />", encoding="utf-8")

    before_stat = xaml.stat()
    sig_before = project_content_signature(project)

    xaml.write_text("<Activity DisplayName=\"After\" />", encoding="utf-8")
    os.utime(xaml, ns=(before_stat.st_atime_ns, before_stat.st_mtime_ns))
    sig_after = project_content_signature(project)

    assert sig_after != sig_before
