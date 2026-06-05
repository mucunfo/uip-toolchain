import json
from pathlib import Path

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


def _project(root: Path, folder: str, name: str):
    path = root / folder
    path.mkdir()
    (path / "project.json").write_text(
        json.dumps({"name": name, "projectVersion": "1.0.0"}),
        encoding="utf-8",
    )
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

    results = publish_done.execute(args, run_uip=fake_run, input_func=fake_input)

    assert len(results) == 1
    assert results[0].ok
    assert results[0].candidate.folder_name == "RepoA"
    assert calls[0] == ["login", "status", "--output", "json"]
    assert calls[1] == ["login", "tenant", "list", "--output", "json"]
    assert sum(1 for c in calls if c[:2] == ["login", "status"]) == 1
    assert calls[2] == [
        "rpa", "pack", str((tmp_path / "RepoA").resolve()), str(tmp_path / "out" / "RepoA" / "pack"),
        "--package-version", "1.0.1",
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


def test_root_option_remains_supported(tmp_path):
    _project(tmp_path, "RepoA", "ProjectA")

    args = publish_done.build_parser().parse_args([
        "patch",
        "--root",
        str(tmp_path),
        "--all",
        "--dry-run",
    ])

    results = publish_done.execute(args)

    assert len(results) == 1
    assert results[0].ok
