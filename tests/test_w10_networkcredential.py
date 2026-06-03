from pathlib import Path

from uip_engine.context import FileContext
from uip_engine.detectors import detect_regex_with_context
from uip_engine.fixers import apply_regex_replace
from uip_engine.loader import load_rules


RULES_PATH = Path(__file__).resolve().parents[1] / "rules.yaml"


def _w10_rule():
    return next(rule for rule in load_rules(RULES_PATH) if rule.id == "W-10")


def test_w10_detects_and_fixes_lowercase_new_net_networkcredential(tmp_path):
    xaml = tmp_path / "Db2.xaml"
    xaml.write_text(
        '<Activity ConnectionString="[new Net.NetworkCredential( '
        '&quot;&quot;, in_SStDB2Credential ).Password]" />',
        encoding="utf-8",
    )
    rule = _w10_rule()

    findings = detect_regex_with_context(rule, FileContext(xaml), None)

    assert len(findings) == 1
    assert apply_regex_replace(xaml, findings[0].fix_mechanical, dry_run=False)
    content = xaml.read_text(encoding="utf-8")
    assert "New System.Net.NetworkCredential(" in content
    assert "new Net.NetworkCredential(" not in content
