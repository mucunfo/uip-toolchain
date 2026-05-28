"""Tests Tier 5 — Robot Execution log scanner."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from uip_engine.executor_log_scanner import (
    _latest_execution_log,
    _match_pattern,
    scan_recent_log,
)


def test_pattern_match_known():
    assert _match_pattern("UIPATH:LOAD ERROR: foo") == "UIPATH:LOAD_ERROR"
    assert _match_pattern("System.XamlParseException at line 42") == "XAML_PARSE_EXCEPTION"
    assert _match_pattern("BC30451: 'in_Foo' is not declared") == "VB_NOT_DECLARED"
    assert _match_pattern("Could not load file or assembly 'Foo.dll'") == "ASSEMBLY_LOAD_FAIL"


def test_pattern_no_match_returns_none():
    assert _match_pattern("Just a normal info log line") is None


def test_latest_log_missing_dir(tmp_path):
    assert _latest_execution_log(tmp_path / "nonexistent") is None


def test_latest_log_picks_most_recent(tmp_path):
    (tmp_path / "2026-01-01_Execution.log").write_text("old")
    (tmp_path / "2026-04-30_Execution.log").write_text("newer")
    latest = _latest_execution_log(tmp_path)
    assert latest is not None
    assert latest.name == "2026-04-30_Execution.log"


def test_scan_recent_log_filters_by_timestamp(tmp_path):
    log = tmp_path / "2026-05-27_Execution.log"
    log.write_text(
        "2026-05-27 09:00:00 [INFO] just info\n"
        "2026-05-27 10:00:00 [ERROR] UIPATH:LOAD ERROR foo\n"
        "2026-05-27 11:00:00 [ERROR] XamlParseException baz\n"
        "2026-05-27 08:00:00 [ERROR] UIPATH:LOAD ERROR old\n"
    )
    # since=10:00 — só 10h e 11h hits qualificam
    since = datetime(2026, 5, 27, 10, 0, 0)
    entries = scan_recent_log(since, logs_dir=tmp_path)
    assert len(entries) == 2
    assert entries[0].hit_pattern == "UIPATH:LOAD_ERROR"
    assert entries[1].hit_pattern == "XAML_PARSE_EXCEPTION"


def test_scan_recent_log_empty_when_no_log(tmp_path):
    assert scan_recent_log(datetime(2026, 1, 1), logs_dir=tmp_path) == []


def test_scan_recent_log_skips_lines_without_hits(tmp_path):
    log = tmp_path / "2026-05-27_Execution.log"
    log.write_text(
        "2026-05-27 10:00:00 [INFO] benign\n"
        "2026-05-27 10:01:00 [WARN] also benign\n"
    )
    entries = scan_recent_log(datetime(2026, 1, 1), logs_dir=tmp_path)
    assert entries == []
