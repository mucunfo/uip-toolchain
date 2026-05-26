"""Tests for uip_engine.hungarian_inference."""
from __future__ import annotations

import pytest

from uip_engine.hungarian_inference import (
    DIRECTION_WRAPPER,
    HUNGARIAN_PREFIXES,
    HungarianMatch,
    infer,
    parse,
    parse_all_known_prefixes,
)


@pytest.mark.parametrize("name,expected", [
    ("in_StPrefixoLog",     "InArgument(x:String)"),
    ("io_StFoo",            "InOutArgument(x:String)"),
    ("out_StFoo",           "OutArgument(x:String)"),
    ("in_IntCount",         "InArgument(x:Int32)"),
    ("in_LngBig",           "InArgument(x:Int64)"),
    ("in_BolSuccess",       "InArgument(x:Boolean)"),
    ("in_BlLegacy",         "InArgument(x:Boolean)"),  # alias
    ("in_DtBirth",          "InArgument(s:DateTime)"),
    ("in_DblValue",         "InArgument(x:Double)"),
    ("in_DecPrice",         "InArgument(x:Decimal)"),
    ("in_DtbResults",       "InArgument(sd:DataTable)"),
    ("in_DtrRow",           "InArgument(sd:DataRow)"),
    ("in_DictMap",          "InArgument(scg:Dictionary(x:String, x:Object))"),
    ("in_LstItems",         "InArgument(scg:List(x:Object))"),
    ("in_SStWords",         "InArgument(scg:List(x:String))"),
    ("in_SsLegacy",         "InArgument(scg:List(x:String))"),  # alias
    ("in_ArrNames",         "InArgument(x:String[])"),
    ("in_EmlMessage",       "InArgument(smm:MailMessage)"),
    ("in_BrException",      "InArgument(uipath:BusinessRuleException)"),
    ("in_ExSystemError",    "InArgument(s:Exception)"),
    ("in_QItem",            "InArgument(uipath:QueueItem)"),
])
def test_infer_known_prefixes(name, expected):
    assert infer(name) == expected


@pytest.mark.parametrize("name", [
    "in_Config",            # no Hungarian prefix
    "in_unknown",           # lowercase, no convention
    "vBolFlag",             # variable name, not arg
    "Foo",                  # no direction prefix
    "in_",                  # incomplete
    "",                     # empty
])
def test_infer_unknown_returns_none(name):
    assert infer(name) is None


def test_parse_longest_prefix_wins():
    # SSt > St ambiguity
    m = parse("in_SStWords")
    assert m is not None
    assert m.type_prefix == "SSt"
    assert m.inferred_clr_type == "scg:List(x:String)"


def test_parse_returns_dataclass():
    m = parse("io_IntCount")
    assert m is not None
    assert isinstance(m, HungarianMatch)
    assert m.direction == "io"
    assert m.type_prefix == "Int"
    assert m.inferred_clr_type == "x:Int32"
    assert m.wrapped_type == "InOutArgument(x:Int32)"
    assert m.rest == "Count"


def test_parse_all_known_prefixes_returns_dict():
    d = parse_all_known_prefixes()
    assert isinstance(d, dict)
    # Spot-check critical entries.
    assert d["St"] == "x:String"
    assert d["Int"] == "x:Int32"
    assert d["Bol"] == "x:Boolean"
    assert d["SSt"] == "scg:List(x:String)"
    assert d["Dtb"] == "sd:DataTable"
    # Aliases must be present too.
    assert d["Bl"] == "x:Boolean"
    assert d["Ss"] == "scg:List(x:String)"
    # Length sanity: at least the documented prefixes are exposed.
    assert len(d) == len(HUNGARIAN_PREFIXES)


def test_direction_wrappers_cover_all_directions():
    assert DIRECTION_WRAPPER == {
        "in":  "InArgument",
        "io":  "InOutArgument",
        "out": "OutArgument",
    }


def test_parse_handles_non_string_input():
    assert parse(None) is None  # type: ignore[arg-type]
    assert parse(123) is None   # type: ignore[arg-type]


def test_parse_rejects_lowercase_after_direction():
    # `in_stuff` violates CamelCase rule (must start with uppercase).
    assert parse("in_stuff") is None
