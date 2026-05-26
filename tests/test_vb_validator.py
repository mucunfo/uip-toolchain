"""Tests for vb_validator — orphan ref detection."""
from uip_engine.vb_validator import (
    extract_declarations, extract_references, find_orphans, diff_orphans,
)


def test_extract_declarations_variable():
    content = '<Variable x:TypeArguments="x:String" Name="vStFoo" />'
    assert extract_declarations(content) == {"vstfoo"}


def test_extract_declarations_property():
    content = '<x:Property Name="in_StBar" Type="InArgument(x:String)"/>'
    assert extract_declarations(content) == {"in_stbar"}


def test_extract_declarations_delegate_arg():
    content = '<DelegateInArgument x:TypeArguments="x:String" Name="item" />'
    assert extract_declarations(content) == {"item"}


def test_extract_references_bracket():
    content = '<Assign Result="[vStFoo]" />'
    refs = extract_references(content)
    assert "vstfoo" in refs


def test_extract_references_member_access_skipped():
    content = '<Assign Value="[vDt.AddDays(1)]" />'
    refs = extract_references(content)
    assert "vdt" in refs
    # AddDays é method, não top-level identifier
    assert "adddays" not in refs


def test_extract_references_in_argument_body():
    content = '<InArgument x:TypeArguments="x:String">[vStName]</InArgument>'
    refs = extract_references(content)
    assert "vstname" in refs


def test_extract_references_skip_string_literal():
    """`&quot;hello&quot;` é literal VB, não identifier."""
    content = '<Assign Value="[&quot;hello&quot; + vStName]" />'
    refs = extract_references(content)
    assert "vstname" in refs
    assert "hello" not in refs


def test_find_orphans_clean():
    content = (
        '<root xmlns:x="urn:x">'
        '<Variable x:TypeArguments="x:String" Name="vStFoo" />'
        '<Assign Value="[vStFoo + &quot;suffix&quot;]" />'
        '</root>'
    )
    assert find_orphans(content) == set()


def test_find_orphans_detects_undeclared():
    content = (
        '<root xmlns:x="urn:x">'
        '<Variable x:TypeArguments="x:String" Name="vStFoo" />'
        '<Assign Value="[vStBar]" />'  # vStBar não declarado
        '</root>'
    )
    orphans = find_orphans(content)
    assert "vstbar" in orphans
    assert "vstfoo" not in orphans


def test_find_orphans_whitelist_keywords():
    """`New`, `Nothing`, types — não são orphans."""
    content = '<Assign Value="[New Dictionary(Of String, Object)]" />'
    assert find_orphans(content) == set()


def test_find_orphans_whitelist_reframework():
    """`TransactionItem`, `Config` — REFramework convention, whitelist."""
    content = '<Assign Value="[TransactionItem.SpecificContent(&quot;X&quot;)]" />'
    assert find_orphans(content) == set()


def test_diff_orphans_detects_new():
    """Use case real: rename incompleto cria orphan. Pre tem decl + ref;
    post tem decl renomeada mas ref antigo sobra → new orphan."""
    pre = (
        '<root xmlns:x="urn:x">'
        '<Variable x:TypeArguments="x:String" Name="dt_X" />'
        '<ReadRange DataTable="[dt_X]" />'
        '</root>'
    )
    post = (
        '<root xmlns:x="urn:x">'
        '<Variable x:TypeArguments="x:String" Name="vDTabX" />'
        '<ReadRange DataTable="[Dt_X]" />'  # rename incompleto: ref antigo sobrou
        '</root>'
    )
    new = diff_orphans(pre, post)
    assert "dt_x" in new


def test_diff_orphans_clean_rename():
    """Rename correto: pre + post ambos sem orphans → no diff."""
    pre = (
        '<root xmlns:x="urn:x">'
        '<Variable x:TypeArguments="x:String" Name="dt_X" />'
        '<ReadRange DataTable="[dt_X]" />'
        '</root>'
    )
    post = (
        '<root xmlns:x="urn:x">'
        '<Variable x:TypeArguments="x:String" Name="vDTabX" />'
        '<ReadRange DataTable="[vDTabX]" />'
        '</root>'
    )
    assert diff_orphans(pre, post) == set()


def test_diff_orphans_extra_whitelist():
    """Custom framework vars passados como whitelist."""
    pre = '<root><Assign Value="[customFwk]" /></root>'
    post = '<root><Assign Value="[customFwk]" /></root>'
    assert diff_orphans(pre, post, extra_whitelist={"customfwk"}) == set()
