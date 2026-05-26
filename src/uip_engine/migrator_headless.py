"""migrator_headless wrapper — invoke .NET migrator_headless.exe subprocess.

Stream E §04: MigrationService.Migrate reflection-driven. Aims to cover the 130
migrators surfaced by ``UiPath.UIAutomationNext.Migration.dll`` without depending
on Studio's GA "Migrate to Windows" GUI binary.

Findings emitted como ``MG-<EVENT_REASON>`` severity ERROR/WARN dependendo de
``MigrationEventType``:

* ``Error``    → severity ERROR
* ``Warning``  → severity WARN
* ``Info``     → severity INFO (dropped from output by default)

Subprocess exit codes (returned verbatim by ``run_migrate``):

* ``0`` — todas migrations succeeded (or probe OK)
* ``1`` — at least one error during migration
* ``2`` — invalid args (engineering bug — should not happen)
* ``3`` — reflection probe failed (Migration DLL inacessível)
* ``-1`` — infra failure (binary missing, timeout, malformed JSON)

The wrapper degrades gracefully: when the .NET host is not built or not found,
``run_migrate`` returns ``(-1, [_infra_finding(...)])`` so callers can choose to
fall back to the legacy ``ActivityMigrator`` probe path or skip the gate
entirely.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._types import Category, Finding, Severity


_ENV_BIN = "UIPATH_MIGRATOR_HEADLESS_BIN"
_ENV_DLL = "UIPATH_MIGRATOR_DLL"
_ENGINE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_BIN = (
    _ENGINE_ROOT
    / "migrator_headless"
    / "bin"
    / "Release"
    / "net6.0-windows"
    / "migrator_headless.exe"
)
_DEBUG_BIN = (
    _ENGINE_ROOT
    / "migrator_headless"
    / "bin"
    / "Debug"
    / "net6.0-windows"
    / "migrator_headless.exe"
)


# Map MigrationEventReason → human-readable suffix used in MG-* rule_ids.
# Keep stable across versions; new reasons fall back to UNKNOWN.
_REASON_TO_RULE_SUFFIX = {
    "Success": "SUCCESS",
    "MigrationNotImplemented": "NOT_IMPLEMENTED",
    "UnexpectedException": "UNEXPECTED_EXCEPTION",
    "CreateDestination": "CREATE_DESTINATION",
    "UnexpectedPropertyException": "PROP_EXCEPTION",
    "ElementScopeNotSupported": "ELEMENT_SCOPE_UNSUPPORTED",
    "PropertyMigrationNotImplemented": "PROP_NOT_IMPLEMENTED",
    "PropertyWithExpressionNotImplemented": "PROP_EXPR_NOT_IMPLEMENTED",
    "AutomaticallyDownloadWebDriver": "WEBDRIVER_AUTODOWNLOAD",
    "UnsupportedPropertyType": "UNSUPPORTED_PROP_TYPE",
    "OCRNotFound": "OCR_NOT_FOUND",
    "OCRWithOutput": "OCR_WITH_OUTPUT",
    "RequiredTarget": "REQUIRED_TARGET",
    "PropertyNotFound": "PROP_NOT_FOUND",
    "ObsoleteProperty": "OBSOLETE_PROP",
    "AnchorProvider": "ANCHOR_PROVIDER",
    "BrowserNativeScraping": "BROWSER_NATIVE_SCRAPING",
    "StandaloneNotSupported": "STANDALONE_UNSUPPORTED",
    "AnchorAction": "ANCHOR_ACTION",
    "StandaloneOCREngineNotSupported": "STANDALONE_OCR_UNSUPPORTED",
    "ElementScope": "ELEMENT_SCOPE",
    "UpdatedModernRuntimeBrowser": "UPDATED_BROWSER",
    "AttachBrowserSelectorWithVar": "ATTACH_BROWSER_VAR_SELECTOR",
    "ActivityNotConfigured": "ACTIVITY_NOT_CONFIGURED",
    "ClassicExceptionsInTryCatch": "CLASSIC_EXCEPTIONS_TRYCATCH",
    "VariableSelector": "VARIABLE_SELECTOR",
    "ElementScopeInsideElementScope": "ELEMENT_SCOPE_NESTED",
}


@dataclass
class _MigratorBinary:
    path: Path
    exists: bool


def _binary_path() -> _MigratorBinary:
    """Resolve the migrator_headless.exe location.

    Priority:
      1. ``UIPATH_MIGRATOR_HEADLESS_BIN`` env override.
      2. ``<engine_root>/migrator_headless/bin/Release/net6.0-windows/migrator_headless.exe``
      3. ``<engine_root>/migrator_headless/bin/Debug/net6.0-windows/migrator_headless.exe``
    """
    override = os.environ.get(_ENV_BIN)
    if override:
        p = Path(override)
        return _MigratorBinary(p, p.exists())
    if _DEFAULT_BIN.exists():
        return _MigratorBinary(_DEFAULT_BIN, True)
    if _DEBUG_BIN.exists():
        return _MigratorBinary(_DEBUG_BIN, True)
    # Return the Release default as canonical location even if absent — caller
    # uses .exists to detect.
    return _MigratorBinary(_DEFAULT_BIN, False)


def _severity_from_host(host_severity: str) -> Severity | None:
    s = (host_severity or "").lower()
    if s == "error":
        return Severity.ERROR
    if s == "warning" or s == "warn":
        return Severity.WARN
    if s == "info" or s == "message":
        # INFO dropped by default — callers can subclass if they want them.
        return None
    if s == "start" or s == "end":
        return None
    return Severity.WARN  # be conservative for unknown severities


def _rule_id(reason: str | None) -> str:
    if not reason:
        return "MG-UNKNOWN"
    suffix = _REASON_TO_RULE_SUFFIX.get(reason)
    if suffix:
        return f"MG-{suffix}"
    # Pass through CamelCase-to-UPPER_SNAKE for unknown reasons (forward-compat
    # with future MigrationEventReason values).
    out = []
    for i, ch in enumerate(reason):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.upper())
    return "MG-" + "".join(out)


def _parse_output(stdout: str, project_root: Path) -> list[Finding]:
    """Parse the migrator_headless JSON envelope into Findings.

    Tolerant to:
    * malformed JSON (returns single INFRA finding)
    * unknown reasons (uses passthrough rule_id)
    * empty Results list (returns empty findings — that's a valid clean run)
    """
    try:
        payload = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError as exc:
        return [_infra_finding(
            "MG-INFRA-BAD-JSON",
            project_root,
            f"migrator_headless emitted non-JSON output: {exc}",
        )]

    findings: list[Finding] = []

    # Surface probe failures as their own infra finding.
    probe = payload.get("Probe") or {}
    if probe and probe.get("Error"):
        findings.append(_infra_finding(
            "MG-INFRA-PROBE-FAIL",
            project_root,
            f"Migration DLL probe failed: {probe.get('Error')}",
        ))

    for file_result in payload.get("Results") or []:
        rel_file = file_result.get("File") or str(project_root / "<unknown>")
        for ev in file_result.get("Events") or []:
            sev = _severity_from_host(ev.get("Severity", ""))
            if sev is None:
                continue
            reason = ev.get("Reason") or "Unknown"
            findings.append(Finding(
                rule_id=_rule_id(reason),
                severity=sev,
                category=Category.BREAKING,
                file=rel_file,
                line=0,
                message=_format_message(ev),
                fix_prose=_fix_prose_for_reason(reason),
            ))
    return findings


def _format_message(ev: dict[str, Any]) -> str:
    parts = []
    activity_type = ev.get("ActivityType")
    activity_name = ev.get("ActivityName")
    if activity_type:
        head = activity_type
        if activity_name and activity_name != activity_type:
            head += f" ('{activity_name}')"
        parts.append(head)
    prop = ev.get("PropertyName")
    if prop:
        parts.append(f"property={prop}")
    msg = ev.get("Message")
    if msg:
        parts.append(msg)
    return " | ".join(parts) if parts else "(no message)"


def _fix_prose_for_reason(reason: str) -> str:
    canned = {
        "MigrationNotImplemented":
            "Migrator entry not implemented for this activity. Replace manually with the "
            "Modern equivalent before Windows-target build.",
        "PropertyMigrationNotImplemented":
            "Property cannot be migrated automatically. Set the equivalent property "
            "manually on the modern activity.",
        "PropertyWithExpressionNotImplemented":
            "Expression-bearing property cannot be migrated. Rewrite the expression "
            "against the modern API.",
        "UnsupportedPropertyType":
            "Property type unsupported by the modern equivalent. Review the property "
            "binding and choose the closest modern alternative.",
        "ObsoleteProperty":
            "Property is obsolete in the modern API — remove or replace.",
        "ElementScopeNotSupported":
            "ElementScope is not supported under the modern UIAutomation surface. "
            "Wrap the inner activities in a NApplicationCard or NShowCardActivity.",
        "BrowserNativeScraping":
            "Native browser scraping changed semantics; verify selector behavior.",
        "OCRNotFound":
            "Could not migrate OCR engine reference — pick a Modern OCR engine.",
        "VariableSelector":
            "Selector built from a variable cannot be auto-migrated.",
    }
    return canned.get(reason, "Review Activity Migrator output and fix manually.")


def _infra_finding(rule_id: str, project_root: Path, message: str) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=Severity.WARN,
        category=Category.METADATA,
        file=str(project_root),
        line=0,
        message=message,
    )


def _timeout_finding(project_root: Path, timeout: int) -> Finding:
    return Finding(
        rule_id="MG-INFRA-TIMEOUT",
        severity=Severity.WARN,
        category=Category.METADATA,
        file=str(project_root),
        line=0,
        message=(
            f"migrator_headless subprocess exceeded timeout={timeout}s. "
            "Treating as inconclusive; rerun manually if needed."
        ),
    )


def run_migrate(
    project_root: Path,
    *,
    dry_run: bool = True,
    timeout: int = 300,
    dll_override: str | None = None,
) -> tuple[int, list[Finding]]:
    """Invoke migrator_headless.exe as subprocess.

    Returns ``(exit_code, findings)``.

    ``exit_code`` mirrors the .NET host's exit code, except that infra issues
    (missing binary, timeout, malformed JSON) return ``-1`` with an infra
    finding describing the failure mode. This lets the orchestrator decide
    whether to halt or treat the Activity Migrator probe as advisory.
    """
    project_root = Path(project_root)
    bin_info = _binary_path()
    if not bin_info.exists:
        return -1, [_infra_finding(
            "MG-INFRA-BIN-MISSING",
            project_root,
            f"migrator_headless.exe not found at {bin_info.path}. Build via "
            f"`dotnet build -c Release` in .uipath-rules/migrator_headless/.",
        )]

    args: list[str] = [str(bin_info.path), "--project", str(project_root)]
    if dry_run:
        args.append("--dry-run")
    if dll_override:
        args += ["--dll", dll_override]
    elif os.environ.get(_ENV_DLL):
        args += ["--dll", os.environ[_ENV_DLL]]

    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return -1, [_timeout_finding(project_root, timeout)]
    except OSError as exc:
        return -1, [_infra_finding(
            "MG-INFRA-OS-ERROR",
            project_root,
            f"OSError invoking migrator_headless: {exc}",
        )]

    findings = _parse_output(proc.stdout, project_root)
    if proc.returncode not in (0, 1) and not findings:
        # Surface a generic error if exit code is non-zero and JSON gave nothing.
        findings.append(_infra_finding(
            "MG-INFRA-EXIT-NONZERO",
            project_root,
            f"migrator_headless exited with code {proc.returncode}. "
            f"stderr: {proc.stderr.strip()[:500]}",
        ))
    return proc.returncode, findings


def run_probe(
    *,
    timeout: int = 30,
    dll_override: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Run the host in --probe mode, return ``(exit_code, parsed_payload)``.

    Used by tests and the integration patch to assert the host is wired
    correctly without invoking a real migration. ``parsed_payload`` is the
    raw JSON dict (no Finding normalization); inspectable for capability
    flags such as ``Probe.Resolvable``, ``Probe.MigrateMethodFound`` etc.
    """
    bin_info = _binary_path()
    if not bin_info.exists:
        return -1, {
            "error": "binary_missing",
            "expected_path": str(bin_info.path),
        }

    args = [str(bin_info.path), "--probe"]
    if dll_override:
        args += ["--dll", dll_override]
    elif os.environ.get(_ENV_DLL):
        args += ["--dll", os.environ[_ENV_DLL]]

    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return -1, {"error": str(exc)}

    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"error": "bad_json", "raw": proc.stdout[:500]}
    return proc.returncode, payload
