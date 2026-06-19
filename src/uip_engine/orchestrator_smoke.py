"""Controlled Orchestrator smoke execution for published UiPath processes."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .official_uip import OfficialUipResult, official_failure_text
from .orchestrator_readiness import (
    ReadinessEntry,
    audit_orchestrator_readiness,
    load_readiness_manifest,
)
from .publish_dev import DEV_TENANT, RunUip, _envelope_data, _first_str, _records, ensure_login


SUCCESSFUL_JOB_STATES = frozenset({"successful"})


@dataclass(frozen=True)
class SmokeEntry:
    readiness: ReadinessEntry
    input_arguments: Any = None
    input_file: str | None = None
    attachments: tuple[str, ...] = ()
    attachment_ids: tuple[str, ...] = ()
    environment_variables: Any = None
    user_keys: str | None = None
    machine_keys: str | None = None
    run_as_me: bool = False
    healing_agent: bool = False
    job_priority: str | None = None
    reference: str | None = None
    timeout_seconds: int | None = None
    poll_interval_seconds: int | None = None


@dataclass(frozen=True)
class SmokeIssue:
    code: str
    severity: str
    subject: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.severity.upper() == "ERROR"

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "subject": self.subject,
            "message": self.message,
        }


@dataclass(frozen=True)
class SmokeJob:
    subject: str
    process_key: str
    job_key: str | None
    state: str | None
    host_machine: str | None = None
    release_name: str | None = None
    raw: dict[str, Any] | None = None

    @property
    def successful(self) -> bool:
        return (self.state or "").strip().lower() in SUCCESSFUL_JOB_STATES

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "processKey": self.process_key,
            "jobKey": self.job_key,
            "state": self.state,
            "hostMachine": self.host_machine,
            "releaseName": self.release_name,
        }


@dataclass(frozen=True)
class SmokeResult:
    tenant: str
    manifest_path: Path
    executed: bool
    jobs: tuple[SmokeJob, ...] = field(default_factory=tuple)
    issues: tuple[SmokeIssue, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.executed and not any(issue.is_error for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.is_error)

    @property
    def warn_count(self) -> int:
        return sum(1 for issue in self.issues if not issue.is_error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant": self.tenant,
            "manifestPath": str(self.manifest_path),
            "executed": self.executed,
            "summary": {
                "jobs": len(self.jobs),
                "successful": sum(1 for job in self.jobs if job.successful),
                "errors": self.error_count,
                "warnings": self.warn_count,
                "ok": self.ok,
            },
            "jobs": [job.to_dict() for job in self.jobs],
            "issues": [issue.to_dict() for issue in self.issues],
        }


def load_smoke_manifest(path: Path) -> tuple[str | None, tuple[SmokeEntry, ...]]:
    tenant, readiness_entries = load_readiness_manifest(path)
    raw_items = _manifest_items(path)
    if len(raw_items) != len(readiness_entries):
        raise ValueError("manifest parse mismatch between readiness and smoke entries")
    entries = tuple(
        _smoke_entry(readiness_entry, raw)
        for readiness_entry, raw in zip(readiness_entries, raw_items)
    )
    return tenant, entries


def run_orchestrator_smoke(
    manifest_path: Path,
    *,
    run_uip: RunUip,
    tenant: str | None = None,
    execute: bool = False,
    timeout_seconds: int = 300,
    poll_interval_seconds: int = 5,
    run_readiness: bool = True,
    check_error_logs: bool = True,
) -> SmokeResult:
    manifest_tenant, entries = load_smoke_manifest(manifest_path)
    effective_tenant = tenant or manifest_tenant or DEV_TENANT

    if not execute:
        return SmokeResult(
            tenant=effective_tenant,
            manifest_path=manifest_path,
            executed=False,
            issues=(_warn(
                "SMOKE-DRY-RUN",
                str(manifest_path),
                "smoke jobs were not started; pass --execute to run them",
            ),),
        )

    if run_readiness:
        readiness = audit_orchestrator_readiness(
            manifest_path,
            run_uip=run_uip,
            tenant=effective_tenant,
        )
        if not readiness.ok:
            return SmokeResult(
                tenant=effective_tenant,
                manifest_path=manifest_path,
                executed=True,
                issues=tuple(
                    SmokeIssue(
                        code=f"READINESS-{issue.code}",
                        severity=issue.severity,
                        subject=issue.subject,
                        message=issue.message,
                    )
                    for issue in readiness.issues
                ),
            )
    else:
        ensure_login(run_uip, dev_tenant=effective_tenant)

    jobs: list[SmokeJob] = []
    issues: list[SmokeIssue] = []
    for entry in entries:
        start_result = _start_job(
            entry,
            run_uip,
            timeout_seconds=entry.timeout_seconds or timeout_seconds,
            poll_interval_seconds=entry.poll_interval_seconds or poll_interval_seconds,
        )
        jobs.extend(start_result.jobs)
        issues.extend(start_result.issues)
        if check_error_logs:
            for job in start_result.jobs:
                if not job.job_key:
                    continue
                issues.extend(_check_error_logs(entry, job, run_uip))
                if not job.successful:
                    issues.extend(_collect_failure_context(entry, job, run_uip))

    return SmokeResult(
        tenant=effective_tenant,
        manifest_path=manifest_path,
        executed=True,
        jobs=tuple(jobs),
        issues=tuple(issues),
    )


def format_smoke_result(result: SmokeResult) -> str:
    if not result.executed:
        lines = [
            (
                f"ORCHESTRATOR smoke: DRY-RUN; tenant={result.tenant}; "
                "no jobs were started"
            )
        ]
    else:
        status = "OK" if result.ok else "FAIL"
        lines = [
            (
                f"ORCHESTRATOR smoke: {status}; tenant={result.tenant}; "
                f"jobs={len(result.jobs)}; "
                f"successful={sum(1 for job in result.jobs if job.successful)}; "
                f"errors={result.error_count}; warnings={result.warn_count}"
            )
        ]
    for job in result.jobs:
        lines.append(
            "  - "
            f"{'OK' if job.successful else 'FAIL'} {job.subject}: "
            f"job={job.job_key or '(missing)'} state={job.state or '(missing)'}"
            + (f" host={job.host_machine}" if job.host_machine else "")
        )
    for issue in result.issues:
        lines.append(
            f"  - {issue.severity} {issue.code} {issue.subject}: {issue.message}"
        )
    if result.executed and result.ok:
        lines.append(
            "  Smoke proof includes job completion state plus zero Error-level "
            "job logs when log checking is enabled."
        )
    return "\n".join(lines)


def smoke_result_to_json(result: SmokeResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


@dataclass(frozen=True)
class _StartResult:
    jobs: tuple[SmokeJob, ...]
    issues: tuple[SmokeIssue, ...]


def _start_job(
    entry: SmokeEntry,
    run_uip: RunUip,
    *,
    timeout_seconds: int,
    poll_interval_seconds: int,
) -> _StartResult:
    command = [
        "or", "jobs", "start", entry.readiness.process_key,
        "--jobs-count", "1",
        "--runtime-type", entry.readiness.runtime_type,
        "--wait-for-completion",
        "--timeout", str(timeout_seconds),
        "--poll-interval", str(poll_interval_seconds),
        "--no-download",
        "--output", "json",
    ]
    if entry.readiness.folder_key:
        command.extend(["--folder-key", entry.readiness.folder_key])
    elif entry.readiness.folder_path:
        command.extend(["--folder-path", entry.readiness.folder_path])
    _extend_optional_job_args(command, entry)

    result: OfficialUipResult = run_uip(command)
    if result.returncode != 0 or result.envelope is None or not result.envelope.ok:
        return _StartResult(
            jobs=(),
            issues=(_error(
                "SMOKE-JOB-START",
                entry.readiness.subject,
                official_failure_text(result) or "uip or jobs start failed",
            ),),
        )

    try:
        data = _envelope_data(result)
    except Exception as exc:
        return _StartResult(
            jobs=(),
            issues=(_error("SMOKE-JOB-START", entry.readiness.subject, str(exc)),),
        )

    jobs = tuple(_job_from_record(entry, record) for record in _records(data))
    if not jobs:
        return _StartResult(
            jobs=(),
            issues=(_error(
                "SMOKE-JOB-MISSING",
                entry.readiness.subject,
                "uip or jobs start returned no job records",
            ),),
        )

    issues: list[SmokeIssue] = []
    for job in jobs:
        if not job.successful:
            issues.append(_error(
                "SMOKE-JOB-STATE",
                entry.readiness.subject,
                f"job {job.job_key or '(missing)'} finished as {job.state or '(missing)'}",
            ))
    return _StartResult(jobs=jobs, issues=tuple(issues))


def _extend_optional_job_args(command: list[str], entry: SmokeEntry) -> None:
    if entry.input_arguments is not None:
        command.extend(["--input-arguments", _json_arg(entry.input_arguments)])
    if entry.input_file:
        command.extend(["--input-file", entry.input_file])
    for attachment in entry.attachments:
        command.extend(["--attachment", attachment])
    for attachment_id in entry.attachment_ids:
        command.extend(["--attachment-id", attachment_id])
    if entry.environment_variables is not None:
        command.extend(["--environment-variables", _json_arg(entry.environment_variables)])
    if entry.user_keys:
        command.extend(["--user-keys", entry.user_keys])
    if entry.machine_keys:
        command.extend(["--machine-keys", entry.machine_keys])
    if entry.run_as_me:
        command.append("--run-as-me")
    if entry.healing_agent:
        command.append("--healing-agent")
    if entry.job_priority:
        command.extend(["--job-priority", entry.job_priority])
    if entry.reference:
        command.extend(["--reference", entry.reference])


def _check_error_logs(
    entry: SmokeEntry,
    job: SmokeJob,
    run_uip: RunUip,
) -> list[SmokeIssue]:
    result: OfficialUipResult = run_uip([
        "or", "jobs", "logs", job.job_key or "",
        "--level", "Error",
        "--limit", "1",
        "--output", "json",
    ])
    if result.returncode != 0 or result.envelope is None or not result.envelope.ok:
        return [_warn(
            "SMOKE-ERROR-LOG-CHECK",
            entry.readiness.subject,
            (
                f"could not inspect Error-level logs for job {job.job_key}: "
                f"{official_failure_text(result) or 'no diagnostic output'}"
            ),
        )]
    records = _records(result.envelope.data)
    if records:
        return [_error(
            "SMOKE-ERROR-LOG",
            entry.readiness.subject,
            f"job {job.job_key} has Error-level robot logs",
        )]
    return []


def _collect_failure_context(
    entry: SmokeEntry,
    job: SmokeJob,
    run_uip: RunUip,
) -> list[SmokeIssue]:
    issues: list[SmokeIssue] = []
    get_result: OfficialUipResult = run_uip([
        "or", "jobs", "get", job.job_key or "",
        "--all-fields",
        "--no-download",
        "--output", "json",
    ])
    if get_result.returncode == 0 and get_result.envelope is not None and get_result.envelope.ok:
        for record in _records(get_result.envelope.data)[:1]:
            detail = _first_str(
                record,
                "Info",
                "ErrorInfo",
                "Exception",
                "Message",
                "FaultedReason",
                "PendingReasons",
            )
            if detail:
                issues.append(_error(
                    "SMOKE-JOB-DIAGNOSTIC",
                    entry.readiness.subject,
                    _trim(detail),
                ))
    history_result: OfficialUipResult = run_uip([
        "or", "jobs", "history", job.job_key or "",
        "--output", "json",
    ])
    if history_result.returncode == 0 and history_result.envelope is not None and history_result.envelope.ok:
        states = [
            _first_str(record, "State", "JobState", "Status")
            for record in _records(history_result.envelope.data)
        ]
        states = [state for state in states if state]
        if states:
            issues.append(_warn(
                "SMOKE-JOB-HISTORY",
                entry.readiness.subject,
                "state history: " + " -> ".join(states[:12]),
            ))
    return issues


def _manifest_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = payload.get("items") or payload.get("processes") or payload.get("entries")
    else:
        raise ValueError("manifest must be a JSON object or array")
    if not isinstance(raw_items, list):
        raise ValueError("manifest must contain items/processes array")
    return [item for item in raw_items if isinstance(item, dict)]


def _smoke_entry(readiness_entry: ReadinessEntry, raw: dict[str, Any]) -> SmokeEntry:
    timeout = _int_or_none(_optional(raw, "timeoutSeconds", "timeout_seconds", "timeout"))
    poll_interval = _int_or_none(_optional(
        raw,
        "pollIntervalSeconds",
        "poll_interval_seconds",
        "pollInterval",
    ))
    return SmokeEntry(
        readiness=readiness_entry,
        input_arguments=_optional_raw(raw, "inputArguments", "input_arguments"),
        input_file=_optional(raw, "inputFile", "input_file"),
        attachments=_tuple_strings(_optional_raw(raw, "attachments", "attachment")),
        attachment_ids=_tuple_strings(_optional_raw(raw, "attachmentIds", "attachment_ids")),
        environment_variables=_optional_raw(raw, "environmentVariables", "environment_variables"),
        user_keys=_optional(raw, "userKeys", "user_keys"),
        machine_keys=_optional(raw, "machineKeys", "machine_keys"),
        run_as_me=_bool(raw, "runAsMe", "run_as_me"),
        healing_agent=_bool(raw, "healingAgent", "healing_agent"),
        job_priority=_optional(raw, "jobPriority", "job_priority"),
        reference=_optional(raw, "reference"),
        timeout_seconds=timeout,
        poll_interval_seconds=poll_interval,
    )


def _job_from_record(entry: SmokeEntry, record: dict[str, Any]) -> SmokeJob:
    return SmokeJob(
        subject=entry.readiness.subject,
        process_key=entry.readiness.process_key,
        job_key=_first_str(record, "Key", "JobKey", "Id"),
        state=_first_str(record, "State", "Status", "JobState"),
        host_machine=_first_str(record, "HostMachineName", "MachineName", "RobotMachineName"),
        release_name=_first_str(record, "ReleaseName", "ProcessName", "Name"),
        raw=record,
    )


def _optional(raw: dict[str, Any], *names: str) -> str | None:
    value = _optional_raw(raw, *names)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_raw(raw: dict[str, Any], *names: str) -> Any:
    lowered = {str(key).lower(): value for key, value in raw.items()}
    for name in names:
        if name in raw:
            return raw[name]
        value = lowered.get(name.lower())
        if value is not None:
            return value
    return None


def _bool(raw: dict[str, Any], *names: str) -> bool:
    value = _optional_raw(raw, *names)
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "sim"}


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value)


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return (str(value),)


def _json_arg(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") or text.startswith("["):
            return text
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _trim(value: str, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _error(code: str, subject: str, message: str) -> SmokeIssue:
    return SmokeIssue(code=code, severity="ERROR", subject=subject, message=message)


def _warn(code: str, subject: str, message: str) -> SmokeIssue:
    return SmokeIssue(code=code, severity="WARN", subject=subject, message=message)
