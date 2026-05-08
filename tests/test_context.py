from pathlib import Path
import pytest
from scripts.rule_engine.context import FileContext, ProjectContext

FIX = Path(__file__).parent / "fixtures"


def test_filecontext_loads_xaml():
    ctx = FileContext(FIX / "minimal.xaml")
    assert "<Activity" in ctx.content
    assert ctx.path.name == "minimal.xaml"


def test_filecontext_active_strips_commented_out():
    ctx = FileContext(FIX / "minimal.xaml")
    # active_content = same as content for now (no CommentOut blocks here)
    assert ctx.active_content == ctx.content


def test_filecontext_lines_property():
    ctx = FileContext(FIX / "minimal.xaml")
    assert len(ctx.lines) > 5
    assert ctx.lines[0].startswith("<!--")


def test_projectcontext_finds_root_with_project_json(tmp_path):
    proj = tmp_path / "MyProject"
    proj.mkdir()
    (proj / "project.json").write_text('{"name": "test", "targetFramework": "Windows"}')
    sub = proj / "Workflows"
    sub.mkdir()
    (sub / "Foo.xaml").write_text("<Activity/>")

    pc = ProjectContext.find_root(sub / "Foo.xaml")
    assert pc.root == proj
    assert pc.target_framework == "Windows"


def test_projectcontext_returns_none_when_no_project_json(tmp_path):
    f = tmp_path / "loose.xaml"
    f.write_text("<Activity/>")
    pc = ProjectContext.find_root(f)
    assert pc is None


def test_filecontext_active_content_strips_commentout():
    ctx = FileContext(FIX / "with_commentout.xaml")
    assert "dead" in ctx.content
    assert "dead" not in ctx.active_content
    assert "alive" in ctx.active_content
