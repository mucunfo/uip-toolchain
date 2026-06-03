from pathlib import Path

from uip_engine import agent_skills


def test_ensure_ccs_agent_skills_installs_for_codex_and_claude(tmp_path):
    records = agent_skills.ensure_ccs_agent_skills(home=tmp_path)

    assert len(records) == 6
    for agent in ("codex", "claude"):
        root = (
            tmp_path / ".agents" / "skills"
            if agent == "codex"
            else tmp_path / ".claude" / "skills"
        )
        for name in agent_skills.CCS_SKILL_NAMES:
            skill = root / name / "SKILL.md"
            assert skill.is_file()
            assert f"name: {name}" in skill.read_text(encoding="utf-8")
            assert (root / name / agent_skills.MANAGED_MARKER).is_file()


def test_ensure_ccs_agent_skills_is_idempotent(tmp_path):
    first = agent_skills.ensure_ccs_agent_skills(home=tmp_path)
    second = agent_skills.ensure_ccs_agent_skills(home=tmp_path)

    assert any(record.changed for record in first)
    assert not any(record.changed for record in second)


def test_ensure_ccs_agent_skills_can_be_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv(agent_skills.DISABLE_ENV_VAR, "1")

    assert agent_skills.ensure_ccs_agent_skills(home=tmp_path) == []
    assert not (tmp_path / ".agents").exists()
