from scripts.rule_engine.suppressions import (
    parse_suppressions, is_suppressed_at, FILE_SCOPE
)


def test_parse_inline_single_rule():
    content = '''<Sequence>
  <!-- rule-disable: A-7 -->
  <ui:LogMessage />
</Sequence>'''
    supps = parse_suppressions(content)
    assert len(supps) == 1
    assert supps[0].rule_id == "A-7"
    assert supps[0].line > 0
    assert supps[0].scope != FILE_SCOPE


def test_parse_inline_multiple_rules():
    content = '<!-- rule-disable: A-7, S-8 -->'
    supps = parse_suppressions(content)
    assert len(supps) == 2
    assert {s.rule_id for s in supps} == {"A-7", "S-8"}


def test_parse_legacy_rtk_disable():
    content = '<!-- rtk-disable: A-7 -->'
    supps = parse_suppressions(content)
    assert len(supps) == 1
    assert supps[0].rule_id == "A-7"


def test_parse_file_scope():
    content = '<!-- rule-disable-file: A-3 -->\n<Activity>...</Activity>'
    supps = parse_suppressions(content)
    assert len(supps) == 1
    assert supps[0].rule_id == "A-3"
    assert supps[0].scope == FILE_SCOPE


def test_is_suppressed_inline_proximity():
    content = '''line1
<!-- rule-disable: A-7 -->
line3
line4
'''
    supps = parse_suppressions(content)
    assert is_suppressed_at(supps, "A-7", line=3) is True
    assert is_suppressed_at(supps, "A-7", line=4) is True
    assert is_suppressed_at(supps, "A-7", line=20) is False
    assert is_suppressed_at(supps, "S-8", line=3) is False


def test_is_suppressed_file_scope_applies_anywhere():
    content = '<!-- rule-disable-file: A-3 -->\n...'
    supps = parse_suppressions(content)
    assert is_suppressed_at(supps, "A-3", line=1) is True
    assert is_suppressed_at(supps, "A-3", line=999) is True
