from pathlib import Path
import pytest
from scripts.rule_engine.runner import Runner
from scripts.rule_engine._types import ValidationResult


def test_runner_with_no_rules_returns_empty_result(tmp_path):
    project_dir = tmp_path / "Proj"
    project_dir.mkdir()
    (project_dir / "project.json").write_text('{"name":"t","targetFramework":"Windows"}')
    (project_dir / "Foo.xaml").write_text("<Activity/>")

    runner = Runner(rules=[], detectors={}, fixers={})
    result = runner.run(project_dir)

    assert isinstance(result, ValidationResult)
    assert result.findings == []


def test_runner_filters_by_target(tmp_path, sample_rule_factory):
    project_dir = tmp_path / "Proj"
    project_dir.mkdir()
    (project_dir / "project.json").write_text('{"targetFramework":"Legacy"}')
    (project_dir / "Foo.xaml").write_text("<Activity><BAD_PATTERN/></Activity>")

    rule = sample_rule_factory(target="windows")
    detectors = {"regex": _stub_regex_detector}
    runner = Runner(rules=[rule], detectors=detectors, fixers={})
    result = runner.run(project_dir)

    # Rule has target=windows, project is Legacy -> skipped
    assert result.findings == []


def test_runner_applies_to_include_filter(tmp_path, sample_rule_factory):
    project_dir = tmp_path / "Proj"
    project_dir.mkdir()
    (project_dir / "project.json").write_text('{"targetFramework":"Windows"}')
    (project_dir / "Framework").mkdir()
    (project_dir / "Framework" / "FW.xaml").write_text("<Activity><BAD_PATTERN/></Activity>")
    (project_dir / "Custom.xaml").write_text("<Activity><BAD_PATTERN/></Activity>")

    rule = sample_rule_factory(applies_to={"exclude": ["Framework/**"]})
    detectors = {"regex": _stub_regex_detector}
    runner = Runner(rules=[rule], detectors=detectors, fixers={})
    result = runner.run(project_dir)

    files_flagged = {Path(f.file).name for f in result.findings}
    assert "Custom.xaml" in files_flagged
    assert "FW.xaml" not in files_flagged


def _stub_regex_detector(rule, file_ctx, project_ctx):
    from scripts.rule_engine._types import Finding
    if "BAD_PATTERN" in file_ctx.content:
        return [Finding(
            rule_id=rule.id, severity=rule.severity, category=rule.category,
            file=str(file_ctx.path), line=1, message="hit",
        )]
    return []


@pytest.fixture
def sample_rule_factory():
    from scripts.rule_engine._types import Rule, Severity
    def make(applies_to=None, target="all"):
        return Rule(
            id="X-99", severity=Severity.ERROR, category="breaking",
            target=target, title="t", description="",
            detect={"type": "regex", "pattern": "BAD_PATTERN"},
            applies_to=applies_to or {},
        )
    return make
