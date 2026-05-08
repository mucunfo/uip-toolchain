"""Core data types for the rule engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    INFO = 1
    WARN = 2
    ERROR = 3
    HALT = 4


class Category:
    BREAKING = "breaking"
    ARCHITECTURAL = "architectural"
    TESTING = "testing"
    AGENT_BEHAVIOR = "agent_behavior"
    METADATA = "metadata"

    ALL = frozenset({BREAKING, ARCHITECTURAL, TESTING, AGENT_BEHAVIOR, METADATA})


class Target:
    ALL = "all"
    WINDOWS = "windows"
    LEGACY = "legacy"

    VALID = frozenset({ALL, WINDOWS, LEGACY})


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    category: str
    file: str
    line: int
    message: str
    fix_mechanical: dict[str, Any] | None = None
    fix_prose: str | None = None
    suppressed: bool = False


@dataclass
class Rule:
    id: str
    severity: Severity
    category: str
    target: str
    title: str
    description: str
    detect: dict[str, Any]
    applies_to: dict[str, Any] = field(default_factory=dict)
    fix: dict[str, Any] | None = None
    references: list[str] = field(default_factory=list)
    examples: dict[str, str] = field(default_factory=dict)
    deprecated_at: str | None = None
    replaced_by: str | None = None


@dataclass
class ValidationResult:
    findings: list[Finding] = field(default_factory=list)
    internal_errors: list[str] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def add_internal_error(self, msg: str) -> None:
        self.internal_errors.append(msg)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings
                   if f.severity == Severity.ERROR and not f.suppressed)

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings
                   if f.severity == Severity.WARN and not f.suppressed)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings
                   if f.severity == Severity.INFO and not f.suppressed)

    @property
    def halt_count(self) -> int:
        return sum(1 for f in self.findings
                   if f.severity == Severity.HALT and not f.suppressed)

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0 or self.halt_count > 0

    def max_severity(self) -> Severity | None:
        active = [f.severity for f in self.findings if not f.suppressed]
        return max(active) if active else None
