"""E-1 / E-2 — error-handling anti-patterns tied to REAL Sicoob production failures.

Corpus-grounded (mined from 60 temp projects, 867 files): E-1 = throw_falha_tecnica_opaca
(Padrao #1), E-2 = nre_in_max_retry_check (Padrao #2). Both detection-only (fix_mechanical
None), WARN, scoped PHYSICALLY inside <Catch> via a stack scanner. TP samples must fire,
TN samples (validation throws in normal flow, two-arg throws, guarded logs, non-exception
vars) must NOT — these are the FP-mitigation contract.
"""
import tempfile
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext
from uip_engine.heuristics.exception_handling import (
    detect_e1_throw_swallows_inner,
    detect_e2_log_message_no_exc_guard,
    _count_top_level_commas,
)


def _rule(rid: str) -> Rule:
    return Rule(
        id=rid, severity=Severity.WARN, category="architectural", target="all",
        title=rid, description="",
        detect={"type": "python", "params": {
            "module": "uip_engine.heuristics.exception_handling",
            "function": "detect_e1_throw_swallows_inner"}},
        fix={"prose": "manual"},
    )


def _run(detect, body: str):
    d = Path(tempfile.mkdtemp())
    f = d / "Worker.xaml"
    f.write_text(
        '<Activity xmlns:ui="ui" xmlns:x="x" xmlns:s="s">' + body + "</Activity>",
        encoding="utf-8",
    )
    return detect(_rule("E"), FileContext(f), None)


# A real REFramework Catch handler (DelegateInArgument Name="exception").
_CATCH = (
    '<Catch x:TypeArguments="s:Exception"><ActivityAction x:TypeArguments="s:Exception">'
    '<ActivityAction.Argument><DelegateInArgument x:TypeArguments="s:Exception" '
    'Name="exception" /></ActivityAction.Argument><Sequence>{X}</Sequence>'
    '</ActivityAction></Catch>'
)


def _in_catch(x: str) -> str:
    return _CATCH.format(X=x)


# --- _count_top_level_commas (FP-critical helper) --------------------------

@pytest.mark.parametrize("args,exp", [
    ("msg", 0),
    ("msg, exception", 1),
    ('in_Config(&quot;a,b&quot;).ToString', 0),   # comma inside string+paren
    ("f(a,b)", 0),                                 # comma inside nested paren
    ('&quot;x, y&quot;', 0),                       # comma inside string
    ("a, b, c", 2),
    ('in_Config(&quot;X&quot;).ToString, exception', 1),  # real 2-arg
])
def test_count_top_level_commas(args, exp):
    assert _count_top_level_commas(args) == exp


# --- E-1 -------------------------------------------------------------------

def test_e1_tp_single_arg_inconfig_in_catch():
    f = _run(detect_e1_throw_swallows_inner, _in_catch(
        '<Throw Exception="[New Exception( in_Config(&quot;StatusDetalheFalhaSistema&quot;).ToString )]" /><Rethrow />'))
    assert len(f) == 1 and f[0].fix_mechanical is None


def test_e1_tp_single_arg_literal_with_commas_in_catch():
    # message literal CONTAINS commas — must still fire (comma counter ignores them)
    f = _run(detect_e1_throw_swallows_inner, _in_catch(
        '<Throw Exception="[New Exception(in_StPrefixoLog+&quot;a, b, c&quot;)]" />'))
    assert len(f) == 1


def test_e1_tp_systemexception_qualified_in_catch():
    f = _run(detect_e1_throw_swallows_inner, _in_catch(
        '<Throw Exception="[New System.Exception(&quot;erro&quot;)]" />'))
    assert len(f) == 1


def test_e1_tn_two_arg_preserves_inner():
    f = _run(detect_e1_throw_swallows_inner, _in_catch(
        '<Throw Exception="[New Exception(in_Config(&quot;X&quot;).ToString, exception)]" />'))
    assert f == []


def test_e1_tn_not_in_catch():
    f = _run(detect_e1_throw_swallows_inner,
             '<Throw Exception="[New BusinessRuleException(in_Config(&quot;X&quot;).ToString)]" />')
    assert f == []


def test_e1_tn_non_exception_type_in_catch():
    f = _run(detect_e1_throw_swallows_inner, _in_catch('<Throw Exception="[New Object()]" />'))
    assert f == []


def test_e1_tn_rethrow_after_trycatch_not_fired():
    # rethrow in IfElseIf AFTER the closed TryCatch — conservatively NOT in Catch
    body = ('<TryCatch>' + _CATCH.format(X="<Rethrow />") + '</TryCatch>'
            '<ui:IfElseIfBlock BlockType="If" Condition="[SystemException IsNot Nothing]">'
            '<Throw Exception="[New System.Exception(SystemException.Message)]" />'
            '</ui:IfElseIfBlock>')
    f = _run(detect_e1_throw_swallows_inner, body)
    assert f == []


# --- E-2 -------------------------------------------------------------------

# E-2 targets PASSED-IN nullable exception vars (in_*/io_*Exception), file-wide,
# and is CONTROL-FLOW-AWARE: an enclosing If/FlowDecision/ElseIf Condition with
# `<var> IsNot Nothing` suppresses it (the REFramework structural guard). The LOCAL
# Catch DelegateInArgument `exception` (non-null by contract) is NOT a target — it
# was the 49-hit noise that inverted value.

def test_e2_tp_system_exception_message_unguarded():
    # RetryCurrentTransaction "Max retries reached" shape — real nre_in_max_retry_check
    f = _run(detect_e2_log_message_no_exc_guard,
             '<Sequence><ui:LogMessage Level="Error" '
             'Message="[&quot;Max reached. &quot;+in_SystemException.Message]" /></Sequence>')
    assert len(f) == 1 and f[0].fix_mechanical is None


def test_e2_tp_business_exception_message_unguarded():
    f = _run(detect_e2_log_message_no_exc_guard,
             '<Sequence><ui:LogMessage Message="[in_StPrefixoLog + in_BusinessException.Message]" /></Sequence>')
    assert len(f) == 1


def test_e2_tn_local_catch_var_not_targeted():
    # local Catch DelegateInArgument 'exception' is non-null by contract -> NOT flagged
    f = _run(detect_e2_log_message_no_exc_guard, _in_catch(
        '<ui:LogMessage Level="Error" Message="[exception.Message]" />'))
    assert f == []


def test_e2_tn_structural_if_guard():
    # enclosing If Condition guards the passed-in var -> suppressed (REFramework)
    f = _run(detect_e2_log_message_no_exc_guard,
             '<If Condition="[in_BusinessException IsNot Nothing]"><If.Then>'
             '<ui:LogMessage Message="[in_BusinessException.Message]" /></If.Then></If>')
    assert f == []


def test_e2_tn_structural_flowdecision_guard_lowercase():
    # FlowDecision condition (lowercase isnot) guards the subtree -> suppressed
    f = _run(detect_e2_log_message_no_exc_guard,
             '<FlowDecision Condition="[in_SystemException isnot Nothing]"><FlowDecision.True>'
             '<ui:LogMessage Message="[in_SystemException.Message]" /></FlowDecision.True></FlowDecision>')
    assert f == []


def test_e2_tn_inline_guard():
    f = _run(detect_e2_log_message_no_exc_guard,
             '<Sequence><ui:LogMessage '
             'Message="[If(in_BusinessException IsNot Nothing, in_BusinessException.Message, &quot;&quot;)]" /></Sequence>')
    assert f == []


def test_e2_tn_non_exception_passed_var():
    f = _run(detect_e2_log_message_no_exc_guard,
             '<Sequence><ui:LogMessage Message="[&quot;R: &quot; + in_Response.Message]" /></Sequence>')
    assert f == []


# --- detection-only contract (audit anchor) --------------------------------

def test_e1_e2_are_detection_only():
    """Both rules must emit NO mechanical fix (rewriting Throw/Catch is unsafe)."""
    f1 = _run(detect_e1_throw_swallows_inner, _in_catch(
        '<Throw Exception="[New Exception(&quot;x&quot;)]" />'))
    f2 = _run(detect_e2_log_message_no_exc_guard,
              '<Sequence><ui:LogMessage Message="[in_SystemException.Message]" /></Sequence>')
    assert all(x.fix_mechanical is None for x in f1 + f2)
