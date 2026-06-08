import json
import subprocess
from pathlib import Path

import pytest

from uip_engine import publish_done
from uip_engine.official_uip import OfficialUipEnvelope, OfficialUipResult


def _result(data, *, code="Ok", returncode=0, result="Success"):
    payload = {
        "Result": result,
        "Code": code,
        "Data": data,
    }
    envelope = OfficialUipEnvelope(
        result=result,
        code=code,
        data=data,
        message=None,
        instructions=None,
        context=None,
        log=None,
        raw=payload,
    )
    return OfficialUipResult(
        argv=["uip"],
        returncode=returncode,
        stdout=json.dumps(payload),
        stderr="",
        envelope=envelope,
    )


def _project(root: Path, folder: str, name: str, *, packable: bool = True):
    path = root / folder
    path.mkdir()
    (path / "project.json").write_text(
        json.dumps({"name": name, "projectVersion": "1.0.0"}),
        encoding="utf-8",
    )
    if packable:
        (path / "project.uiproj").write_text("{}", encoding="utf-8")
    return path


def test_parse_selection_accepts_ranges_and_all():
    assert publish_done.parse_selection("1,3,5-7", max_index=8) == [1, 3, 5, 6, 7]
    assert publish_done.parse_selection("all", max_index=3) == [1, 2, 3]
    assert publish_done.parse_selection("todos", max_index=2) == [1, 2]


def test_discover_projects_lists_direct_project_dirs(tmp_path):
    _project(tmp_path, "RepoB", "ProjectB")
    _project(tmp_path, "RepoA", "ProjectA")
    (tmp_path / "not-a-project").mkdir()

    candidates = publish_done.discover_projects(tmp_path)

    assert [(c.folder_name, c.project_name) for c in candidates] == [
        ("RepoA", "ProjectA"),
        ("RepoB", "ProjectB"),
    ]


def test_discover_projects_accepts_direct_project_folder(tmp_path):
    project = _project(tmp_path, "RepoA", "ProjectA")

    candidates = publish_done.discover_projects(project)

    assert [(c.folder_name, c.project_name) for c in candidates] == [
        ("RepoA", "ProjectA"),
    ]


def test_discover_projects_skips_engine_and_handoff_dirs(tmp_path):
    _project(tmp_path, "RepoA", "ProjectA")
    (tmp_path / ".tmp").mkdir()
    _project(tmp_path / ".tmp", "CachedRepo", "CachedProject")
    (tmp_path / ".publish-dev-handoff").mkdir()
    _project(tmp_path / ".publish-dev-handoff", "Downloaded", "DownloadedProject")

    candidates = publish_done.discover_projects(tmp_path)

    assert [(c.folder_name, c.project_name) for c in candidates] == [
        ("RepoA", "ProjectA"),
    ]


def test_batch_interactive_selection_logs_in_once_and_runs_selected(tmp_path):
    _project(tmp_path, "RepoA", "ProjectA")
    _project(tmp_path, "RepoB", "ProjectB")
    calls = []
    answers = iter(["1", "y"])

    def fake_input(prompt):
        return next(answers)

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:2] == ["rpa", "pack"]:
            pack_dir = Path(command[3])
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "ProjectA.1.0.1.nupkg").write_bytes(b"packed")
            return _result({"Status": "Packed"})
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    args = publish_done.build_parser().parse_args([
        "patch",
        str(tmp_path),
        "--out-dir",
        str(tmp_path / "out"),
    ])

    results = publish_done.execute(
        args,
        run_uip=fake_run,
        input_func=fake_input,
        check_environment=False,
    )

    assert len(results) == 1
    assert results[0].ok
    assert results[0].candidate.folder_name == "RepoA"
    assert not (tmp_path / "out" / ".work").exists()
    assert calls[0] == ["login", "status", "--output", "json"]
    assert calls[1] == ["login", "tenant", "list", "--output", "json"]
    assert sum(1 for c in calls if c[:2] == ["login", "status"]) == 1
    assert calls[2][:3] == [
        "rpa", "pack", str((tmp_path / "RepoA").resolve()),
    ]
    assert calls[2][3].endswith(str(Path("RepoA") / "pack"))
    assert str(tmp_path / "out" / ".work") not in calls[2][3]
    assert calls[2][4:] == [
        "--package-version", "1.0.1",
        "--skip-analyze",
        "--output", "json",
    ]


def test_batch_dry_run_does_not_call_uip(tmp_path):
    _project(tmp_path, "RepoA", "ProjectA")
    called = False

    def fake_run(command):
        nonlocal called
        called = True
        raise AssertionError(command)

    args = publish_done.build_parser().parse_args([
        "minor",
        str(tmp_path),
        "--all",
        "--dry-run",
    ])

    results = publish_done.execute(args, run_uip=fake_run)

    assert not called
    assert len(results) == 1
    assert results[0].ok


def test_batch_syncs_project_uiproj_for_project_json_only_project(tmp_path):
    _project(tmp_path, "RepoA", "ProjectA", packable=False)
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([
                {"TenantName": "RPA_Desenvolvimento"},
            ])
        if command[:2] == ["rpa", "pack"]:
            assert (tmp_path / "RepoA" / "project.uiproj").is_file()
            pack_dir = Path(command[3])
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "ProjectA.1.0.1.nupkg").write_bytes(b"packed")
            return _result({"Status": "Packed"})
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    args = publish_done.build_parser().parse_args([
        "patch",
        str(tmp_path),
        "--all",
        "--yes",
        "--out-dir",
        str(tmp_path / "out"),
    ])

    results = publish_done.execute(args, run_uip=fake_run, check_environment=False)

    assert len(results) == 1
    assert results[0].ok
    assert any(command[:2] == ["rpa", "pack"] for command in calls)
    assert not any(command[:2] == ["rpa-legacy", "pack"] for command in calls)
    assert (tmp_path / "RepoA" / "project.uiproj").is_file()
    assert (tmp_path / "out" / "ProjectA.1.0.1.nupkg").is_file()


def test_batch_commit_requires_branch_when_message_is_set(tmp_path):
    _project(tmp_path, "RepoA", "ProjectA")

    args = publish_done.build_parser().parse_args([
        "patch",
        str(tmp_path),
        "--all",
        "--dry-run",
        "--commit-message",
        "chore: publish version",
    ])

    with pytest.raises(ValueError, match="--commit-message requires --commit-branch"):
        publish_done.execute(args, check_environment=False)


def test_batch_commits_publish_changes_on_expected_branch(tmp_path):
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    repo.mkdir()
    project = _project(repo, "RepoA", "ProjectA")
    manual_note = repo / "manual-note.txt"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "initial"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "branch", "-M", "release/nc-179"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "release/nc-179"], check=True, capture_output=True)
    manual_note.write_text("manual change before publish\n", encoding="utf-8")
    calls = []

    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:2] == ["rpa", "pack"]:
            pack_dir = Path(command[3])
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "ProjectA.1.0.1.nupkg").write_bytes(b"packed")
            return _result({"Status": "Packed"})
        if command[:3] == ["or", "packages", "upload"]:
            return _result({"Status": "Uploaded"})
        if command[:3] == ["or", "packages", "download"]:
            destination = Path(command[command.index("--destination") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"downloaded")
            return _result({"SavedTo": str(destination)})
        raise AssertionError(f"unexpected command: {command}")

    args = publish_done.build_parser().parse_args([
        "patch",
        str(repo),
        "--all",
        "--yes",
        "--out-dir",
        str(tmp_path / "out"),
        "--commit-message",
        "chore: publish DEV packages",
        "--commit-branch",
        "release/nc-179",
    ])

    results = publish_done.execute(args, run_uip=fake_run, check_environment=False)

    assert len(results) == 1
    assert results[0].ok
    assert results[0].commit_status is not None
    assert "COMMIT" in results[0].commit_status
    assert "PUSH origin/release/nc-179" in results[0].commit_status
    assert json.loads((project / "project.json").read_text())["projectVersion"] == "1.0.1"
    subject = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--pretty=%s"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert subject == "chore: publish DEV packages"
    changed = subprocess.run(
        ["git", "-C", str(repo), "show", "--name-only", "--pretty=", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    changed_names = {line.replace("\\", "/") for line in changed}
    assert "RepoA/project.json" in changed_names
    assert "manual-note.txt" in changed_names
    remote_subject = subprocess.run(
        ["git", "--git-dir", str(remote), "log", "-1", "--pretty=%s", "release/nc-179"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert remote_subject == "chore: publish DEV packages"


def test_batch_commit_branch_preflight_runs_before_uip_calls(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _project(repo, "RepoA", "ProjectA")
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "initial"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "branch", "-M", "main"], check=True)
    called = False

    def fake_run(command):
        nonlocal called
        called = True
        raise AssertionError(command)

    args = publish_done.build_parser().parse_args([
        "patch",
        str(repo),
        "--all",
        "--yes",
        "--commit-message",
        "chore: publish DEV packages",
        "--commit-branch",
        "release/nc-179",
    ])

    with pytest.raises(RuntimeError, match="current branch is 'main'"):
        publish_done.execute(args, run_uip=fake_run, check_environment=False)

    assert not called


def test_ensure_dotnet_sdk_for_official_pack_accepts_existing_sdk_8(monkeypatch, tmp_path):
    dotnet = tmp_path / "dotnet.cmd"
    dotnet.write_text("", encoding="utf-8")

    monkeypatch.setattr(publish_done.shutil, "which", lambda *a, **k: str(dotnet))

    class Proc:
        returncode = 0
        stdout = "8.0.421 [C:\\Users\\lisan\\.dotnet\\sdk]\n"
        stderr = ""

    monkeypatch.setattr(publish_done.subprocess, "run", lambda *a, **k: Proc())

    publish_done.ensure_dotnet_sdk_for_official_pack()


def test_ensure_dotnet_sdk_for_official_pack_rejects_sdk_6(monkeypatch, tmp_path):
    dotnet = tmp_path / "dotnet.cmd"
    dotnet.write_text("", encoding="utf-8")

    monkeypatch.setattr(publish_done.shutil, "which", lambda *a, **k: str(dotnet))

    class Proc:
        returncode = 0
        stdout = "6.0.428 [C:\\Users\\lisandro.souza\\.dotnet\\sdk]\n"
        stderr = ""

    monkeypatch.setattr(publish_done.subprocess, "run", lambda *a, **k: Proc())

    with pytest.raises(RuntimeError, match="requires .NET SDK 8\\+"):
        publish_done.ensure_dotnet_sdk_for_official_pack()


def test_ensure_dotnet_sdk_for_official_pack_errors_when_sdk_is_missing(monkeypatch):
    monkeypatch.setattr(publish_done.shutil, "which", lambda *a, **k: None)

    with pytest.raises(RuntimeError, match=".NET SDK 8\\+ not found"):
        publish_done.ensure_dotnet_sdk_for_official_pack()


def test_root_option_remains_supported(tmp_path):
    _project(tmp_path, "RepoA", "ProjectA")

    args = publish_done.build_parser().parse_args([
        "patch",
        "--root",
        str(tmp_path),
        "--all",
        "--dry-run",
    ])

    results = publish_done.execute(args, check_environment=False)

    assert len(results) == 1
    assert results[0].ok
