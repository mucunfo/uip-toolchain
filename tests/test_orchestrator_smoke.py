import json
from pathlib import Path

from uip_engine import cli
from uip_engine.official_uip import OfficialUipEnvelope, OfficialUipResult
from uip_engine.orchestrator_smoke import (
    format_smoke_result,
    run_orchestrator_smoke,
)


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


def _write_manifest(path: Path, **extra) -> Path:
    item = {
        "packageId": "InvoiceProcessing",
        "packageVersion": "1.2.4",
        "processKey": "11111111-1111-1111-1111-111111111111",
        "folderPath": "Shared",
        "runtimeType": "Unattended",
        "processName": "Invoice Processing",
    }
    item.update(extra)
    path.write_text(
        json.dumps({"tenant": "RPA_Desenvolvimento", "items": [item]}),
        encoding="utf-8",
    )
    return path


def _fake_run_success(calls):
    def fake_run(command):
        calls.append(command)
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "packages", "versions"]:
            return _result([{"Version": "1.2.4"}])
        if command[:3] == ["or", "packages", "entry-points"]:
            return _result([{
                "Path": "Main.xaml",
                "DisplayName": "Main",
                "InputArguments": {
                    "invoice": "String",
                    "in_RequiredTicket": "String",
                },
            }])
        if command[:3] == ["or", "processes", "get"]:
            return _result({
                "Key": command[3],
                "Name": "Invoice Processing",
                "ProcessKey": "InvoiceProcessing",
                "ProcessVersion": "1.2.4",
                "FolderPath": "Shared",
            })
        if command[:3] == ["or", "processes", "resources"]:
            return _result([{"ResourceType": "Queue", "ResourceName": "Invoices", "ValidationStatus": "Success"}])
        if command[:3] == ["or", "folders", "runtimes"]:
            return _result([{"Type": "Unattended", "Total": 2, "Connected": 1, "Available": 1}])
        if command[:3] == ["or", "machines", "list"]:
            return _result([
                {"Name": "dev-bot-01", "Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "UnattendedSlots": 1}
            ])
        if command[:4] == ["or", "sessions", "unattended", "list"]:
            return _result([
                {"SessionId": 701, "RuntimeType": "Unattended", "State": "Available"}
            ])
        if command[:3] == ["or", "jobs", "start"]:
            return _result([{
                "Key": "22222222-2222-2222-2222-222222222222",
                "State": "Successful",
                "HostMachineName": "dev-bot-01",
                "ReleaseName": "Invoice Processing",
            }])
        if command[:3] == ["or", "jobs", "logs"]:
            return _result([])
        raise AssertionError(command)

    return fake_run


def test_smoke_dry_run_does_not_call_uip(tmp_path):
    manifest = _write_manifest(tmp_path / "manifest.json")
    calls = []

    result = run_orchestrator_smoke(manifest, run_uip=lambda command: calls.append(command), execute=False)

    assert not result.executed
    assert result.warn_count == 1
    assert calls == []
    assert "DRY-RUN" in format_smoke_result(result)


def test_smoke_execute_runs_readiness_job_and_error_log_check(tmp_path):
    manifest = _write_manifest(tmp_path / "manifest.json", inputArguments={"invoice": "123"})
    calls = []

    result = run_orchestrator_smoke(
        manifest,
        run_uip=_fake_run_success(calls),
        execute=True,
        timeout_seconds=60,
    )

    assert result.ok
    assert len(result.jobs) == 1
    assert result.jobs[0].job_key == "22222222-2222-2222-2222-222222222222"
    start_call = next(call for call in calls if call[:3] == ["or", "jobs", "start"])
    assert "--wait-for-completion" in start_call
    assert "--no-download" in start_call
    assert "--input-arguments" in start_call
    assert '{"invoice":"123"}' in start_call
    assert ["or", "jobs", "logs", "22222222-2222-2222-2222-222222222222", "--level", "Error", "--limit", "1", "--output", "json"] in calls


def test_smoke_flags_faulted_job_and_collects_context(tmp_path):
    manifest = _write_manifest(tmp_path / "manifest.json")

    def fake_run(command):
        if command[:2] == ["login", "status"]:
            return _result({"Status": "Logged in"})
        if command[:3] == ["login", "tenant", "list"]:
            return _result([{"TenantName": "RPA_Desenvolvimento"}])
        if command[:3] == ["login", "tenant", "set"]:
            return _result({"TenantName": command[3]})
        if command[:3] == ["or", "jobs", "start"]:
            return _result([{
                "Key": "22222222-2222-2222-2222-222222222222",
                "State": "Faulted",
            }])
        if command[:3] == ["or", "jobs", "logs"]:
            return _result([{"Level": "Error", "Message": "Selector not found"}])
        if command[:3] == ["or", "jobs", "get"]:
            return _result({"Key": command[3], "State": "Faulted", "Message": "Selector not found"})
        if command[:3] == ["or", "jobs", "history"]:
            return _result([{"State": "Pending"}, {"State": "Running"}, {"State": "Faulted"}])
        raise AssertionError(command)

    result = run_orchestrator_smoke(
        manifest,
        run_uip=fake_run,
        execute=True,
        run_readiness=False,
    )

    assert not result.ok
    codes = {issue.code for issue in result.issues}
    assert "SMOKE-JOB-STATE" in codes
    assert "SMOKE-ERROR-LOG" in codes
    assert "SMOKE-JOB-DIAGNOSTIC" in codes
    assert "SMOKE-JOB-HISTORY" in codes


def test_cli_orchestrator_smoke_requires_execute_for_success(monkeypatch, tmp_path, capsys):
    manifest = _write_manifest(tmp_path / "manifest.json")
    monkeypatch.setattr("uip_engine.official_uip.run_official_uip", _fake_run_success([]))
    args = cli.build_parser().parse_args([
        "orchestrator-smoke",
        str(manifest),
    ])

    rc = cli._cmd_orchestrator_smoke(args)

    out = capsys.readouterr().out
    assert rc == cli.EXIT_WARN
    assert "DRY-RUN" in out


def test_cli_orchestrator_smoke_execute(monkeypatch, tmp_path, capsys):
    manifest = _write_manifest(tmp_path / "manifest.json")
    monkeypatch.setattr("uip_engine.official_uip.run_official_uip", _fake_run_success([]))
    args = cli.build_parser().parse_args([
        "orchestrator-smoke",
        str(manifest),
        "--execute",
        "--timeout",
        "60",
    ])

    rc = cli._cmd_orchestrator_smoke(args)

    out = capsys.readouterr().out
    assert rc == cli.EXIT_OK
    assert "ORCHESTRATOR smoke: OK" in out
