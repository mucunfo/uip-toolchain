"""Adapter for the official UiPath CLI (`uip`).

The CCS public command is `ccs-uip`; `uip` is reserved for UiPath's official
CLI. This module discovers and invokes official `uip` for migrated gates such
as `uip rpa analyze` and `uip rpa pack`, with JSON-envelope parsing and
explicit logging. Legacy Studio CLI remains a fallback where still supported.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


OFFICIAL_UIP_ENV_VAR = "UIPATH_UIP_CLI"
SUPPORTED_UIP_MAJOR = 1


@dataclass(frozen=True)
class OfficialUipEnvelope:
    result: str
    code: str | None
    data: Any
    message: str | None
    instructions: str | None
    context: Any
    log: str | None
    raw: dict[str, Any]

    @property
    def ok(self) -> bool:
        return self.result.lower() == "success"


@dataclass(frozen=True)
class OfficialUipResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    envelope: OfficialUipEnvelope | None


@dataclass(frozen=True)
class OfficialUipDiagnostic:
    code: str
    message: str
    severity: str = "Error"
    file: str = "project.json"


@dataclass(frozen=True)
class OfficialUipVersion:
    raw: str
    major: int
    minor: int
    patch: int

    @property
    def line(self) -> str:
        return f"{self.major}.{self.minor}.x"


def _prefer_cmd_wrapper(path: Path) -> Path:
    """Use npm's .cmd wrapper on Windows when discovery returns a PowerShell shim."""
    if path.suffix.lower() == ".ps1":
        cmd = path.with_suffix(".cmd")
        if cmd.is_file():
            return cmd
    return path


def discover_official_uip() -> Path | None:
    """Find the official UiPath CLI host.

    `uip` is owned by UiPath's npm-distributed CLI. The CCS full gate is
    `ccs-uip`; do not use this function to discover the legacy Studio CLI.
    """
    explicit = os.environ.get(OFFICIAL_UIP_ENV_VAR)
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p

    via_path = shutil.which("uip")
    if via_path:
        return _prefer_cmd_wrapper(Path(via_path))
    return None


def parse_semver(text: str) -> OfficialUipVersion | None:
    """Parse the host semver printed by `uip --version`."""
    match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", text.strip())
    if not match:
        return None
    return OfficialUipVersion(
        raw=match.group(0),
        major=int(match.group(1)),
        minor=int(match.group(2)),
        patch=int(match.group(3)),
    )


@lru_cache(maxsize=16)
def get_official_uip_version(uip_path: str) -> OfficialUipVersion | None:
    """Return official CLI host version, or None when it cannot be read."""
    proc = subprocess.run(
        [uip_path, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_official_uip_subprocess_env(),
    )
    if proc.returncode != 0:
        return None
    return parse_semver(proc.stdout or proc.stderr)


def compatibility_diagnostic(
    version: OfficialUipVersion | None,
) -> OfficialUipDiagnostic | None:
    """Validate the CLI line supported by this toolchain.

    UiPath CLI follows semver from 1.0.0 onward. This toolchain supports the
    stable 1.x contract and intentionally blocks pre-1 preview or future major
    versions until their command/output contracts are validated.
    """
    if version is None:
        return OfficialUipDiagnostic(
            code="CLI_VERSION_UNKNOWN",
            severity="Warning",
            message=(
                "Could not read official UiPath CLI version with `uip --version`; "
                "continuing, but compatibility is not proven."
            ),
        )
    if version.major < SUPPORTED_UIP_MAJOR:
        return OfficialUipDiagnostic(
            code="CLI_VERSION_UNSUPPORTED",
            message=(
                f"Official UiPath CLI {version.raw} is a pre-1.x preview line. "
                "Install @uipath/cli@1.1.0 or another validated 1.x version."
            ),
        )
    if version.major > SUPPORTED_UIP_MAJOR:
        return OfficialUipDiagnostic(
            code="CLI_VERSION_UNSUPPORTED",
            message=(
                f"Official UiPath CLI {version.raw} is outside the validated 1.x "
                "contract. Validate command flags/output before using this "
                "toolchain gate."
            ),
        )
    return None


def parse_uip_envelope(stdout: str) -> OfficialUipEnvelope | None:
    """Parse the official CLI JSON envelope from stdout."""
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or "Result" not in payload:
        return None
    return OfficialUipEnvelope(
        result=str(payload.get("Result") or ""),
        code=payload.get("Code"),
        data=payload.get("Data"),
        message=payload.get("Message"),
        instructions=payload.get("Instructions"),
        context=payload.get("Context"),
        log=payload.get("Log"),
        raw=payload,
    )


def _official_uip_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    dotnet_root = env.get("UIP_TOOLCHAIN_DOTNET_ROOT")
    if not dotnet_root:
        candidate = Path.home() / ".dotnet"
        if (candidate / "dotnet.exe").is_file():
            dotnet_root = str(candidate)
    if dotnet_root:
        env["DOTNET_ROOT"] = dotnet_root
        env["PATH"] = dotnet_root + os.pathsep + env.get("PATH", "")
    return env


def _iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _first_present(data: dict[str, Any], *names: str) -> Any:
    lower = {str(k).lower(): v for k, v in data.items()}
    for name in names:
        if name in data:
            return data[name]
        value = lower.get(name.lower())
        if value is not None:
            return value
    return None


def iter_analyzer_records(envelope: OfficialUipEnvelope | None):
    """Yield analyzer-like finding records from the official JSON envelope.

    The official envelope is stable, but individual command `Data` shapes can
    evolve. This extractor intentionally accepts common field spellings and
    nested structures instead of assuming one rigid schema.
    """
    if envelope is None:
        return
    for item in _iter_dicts(envelope.data):
        code = _first_present(item, "ErrorCode", "RuleId", "RuleName", "Code")
        desc = _first_present(item, "Description", "Message", "ErrorMessage")
        severity = _first_present(item, "ErrorSeverity", "Severity", "Level")
        if code is None and desc is None:
            continue
        yield {
            "ErrorCode": str(code or "LOAD"),
            "Description": str(desc or ""),
            "ErrorSeverity": str(severity or "Error"),
            "FilePath": str(_first_present(item, "FilePath", "Path", "File") or ""),
            "Item": str(_first_present(item, "Item", "Activity") or ""),
            "ActivityDisplayName": str(
                _first_present(item, "ActivityDisplayName", "DisplayName") or ""
            ),
        }


def official_failure_text(result: OfficialUipResult) -> str:
    """Combine official CLI failure surfaces into one diagnostic string."""
    parts = [result.stdout, result.stderr]
    if result.envelope is not None:
        parts.extend([
            result.envelope.message or "",
            result.envelope.instructions or "",
            result.envelope.log or "",
        ])
    return "\n".join(part for part in parts if part)


def diagnose_official_uip_failure(text: str, command: str) -> list[OfficialUipDiagnostic]:
    """Convert common official `uip` infrastructure failures into CCS diagnostics."""
    diagnostics: list[OfficialUipDiagnostic] = []
    seen: set[tuple[str, str]] = set()

    def add(code: str, message: str, *, severity: str = "Error") -> None:
        key = (code, message)
        if key in seen:
            return
        seen.add(key)
        diagnostics.append(OfficialUipDiagnostic(code=code, message=message, severity=severity))

    def _canonical_package_name(package: str) -> str:
        if package.lower() == "uipath.coreipc":
            return "UiPath.CoreIpc"
        return package

    for match in re.finditer(r"Could not load file or assembly '([^',]+)", text):
        assembly = match.group(1).strip()
        add(
            "CLI_ASSEMBLY_MISSING",
            (
                f"official uip {command} cannot load assembly '{assembly}'. "
                "This is usually a restore/feed/package graph issue, not a "
                "generic analyzer halt. Run `uip rpa restore` with the same "
                "NuGet.config, verify local CCS package feeds, and align the "
                "package pins that provide this assembly."
            ),
        )

    required_pkg_re = re.compile(
        r"install\s+the\s+([A-Za-z0-9_.-]+)\s+package,\s+version\s+"
        r"([0-9][A-Za-z0-9_.+-]*)\s+or\s+higher",
        re.IGNORECASE,
    )
    for match in required_pkg_re.finditer(text):
        package = _canonical_package_name(match.group(1).strip())
        version = match.group(2).strip()
        add(
            "CLI_REQUIRED_PACKAGE_MISSING",
            (
                f"official uip {command} requires package '{package}' "
                f"version {version} or higher. Add a direct project.json "
                f"dependency pin, for example dependencies.\"{package}\" = "
                f"\"[{version}]\", or add/align the corresponding canonical "
                "toolchain pin."
            ),
        )

    local_server_pkg_re = re.compile(
        r"make\s+sure\s+you\s+have\s+the\s+([A-Za-z0-9_.-]+)\s+package\s+"
        r"version\s+([0-9][A-Za-z0-9_.+-]*)\s+or\s+higher\s+installed",
        re.IGNORECASE,
    )
    for match in local_server_pkg_re.finditer(text):
        package = _canonical_package_name(match.group(1).strip())
        version = match.group(2).strip()
        add(
            "CLI_REQUIRED_PACKAGE_MISSING",
            (
                f"official uip {command} requires package '{package}' "
                f"version {version} or higher. Add or align the direct "
                "project.json dependency pin before running analyzer/pack."
            ),
        )

    for match in re.finditer(r"Detected package downgrade:\s*([^\r\n]+)", text):
        package = match.group(1).strip()
        code = "RESTORE_DOWNGRADE" if command == "rpa restore" else "CLI_PACKAGE_DOWNGRADE"
        add(
            code,
            (
                f"official uip {command} detected package downgrade: {package}. "
                "Pin the direct dependency in project.json to the version required "
                "by the transitive package graph, or update the CCS package that "
                "declares the higher minimum."
            ),
        )

    nu_matches = re.finditer(r"\b(NU\d{4,5})\s*:\s*([^\r\n]+)", text)
    for match in nu_matches:
        nu_code = match.group(1)
        msg = match.group(2).strip()
        if nu_code in {"NU1101", "NU1102"}:
            add(
                "RESTORE_PACKAGE_MISSING",
                (
                    f"official uip {command} failed package resolution ({nu_code}): "
                    f"{msg}. Verify package id/version pins and NuGet sources, "
                    "including the local CCS feed."
                ),
            )
        elif nu_code == "NU1605":
            add(
                "RESTORE_DOWNGRADE",
                (
                    f"official uip {command} detected package downgrade ({nu_code}): "
                    f"{msg}. Pin the direct dependency in project.json to the "
                    "version required by the transitive package graph."
                ),
            )
        elif nu_code in {"NU1301", "NU1801", "NU1900"}:
            add(
                "RESTORE_FEED_UNAVAILABLE",
                (
                    f"official uip {command} could not access a NuGet source "
                    f"({nu_code}): {msg}. Check VPN/proxy/feed credentials and "
                    "the generated NuGet.config."
                ),
            )
        else:
            add(
                "RESTORE_NUGET_ERROR",
                (
                    f"official uip {command} reported NuGet error {nu_code}: "
                    f"{msg}."
                ),
            )

    feed_markers = (
        "unable to load the service index for source",
        "no packages exist with this id in source",
        "the remote name could not be resolved",
        "a connection attempt failed",
    )
    lower_text = text.lower()
    if any(marker in lower_text for marker in feed_markers):
        add(
            "RESTORE_FEED_UNAVAILABLE",
            (
                f"official uip {command} could not fully use one or more NuGet "
                "sources. Check VPN/proxy/feed credentials and the generated "
                "NuGet.config."
            ),
        )

    if "No project.uiproj or webAppManifest.json found" in text:
        add(
            "CLI_PROJECT_FORMAT",
            (
                f"official uip {command} requires a migrated Windows project with "
                "project.uiproj/webAppManifest.json. Run migration before the "
                "official pack/analyze gate, or keep this as a legacy pre-scan only."
            ),
        )

    if "NETSDK1045" in text or "does not support targeting .NET 8.0" in text:
        add(
            "CLI_DOTNET_SDK",
            (
                f"official uip {command} requires a compatible .NET SDK/runtime for "
                "the RPA tool. Install .NET 8 SDK or set UIP_TOOLCHAIN_DOTNET_ROOT "
                "to a validated SDK path."
            ),
        )

    return diagnostics


def run_official_uip(
    args: list[str],
    *,
    timeout: int = 180,
    uip_path: Path | None = None,
) -> OfficialUipResult:
    """Run official `uip` and parse its JSON envelope when present."""
    cli = uip_path or discover_official_uip()
    if cli is None:
        raise FileNotFoundError(
            "official UiPath CLI `uip` not found. Install @uipath/cli or set "
            f"{OFFICIAL_UIP_ENV_VAR}."
        )

    argv = [str(cli), *args]
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=_official_uip_subprocess_env(),
    )
    return OfficialUipResult(
        argv=argv,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        envelope=parse_uip_envelope(proc.stdout),
    )
