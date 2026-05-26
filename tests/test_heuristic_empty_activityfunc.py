"""Tests for heuristics/empty_activityfunc.py — S-18.

S-18 detect ActivityFunc body vazio em property .OCREngine/.CVEngine.
"""
from pathlib import Path

import pytest

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext
from uip_engine.heuristics.empty_activityfunc import (
    detect_empty_ocr_activityfunc,
)


def _rule() -> Rule:
    return Rule(
        id="S-18",
        severity=Severity.ERROR,
        category="breaking",
        target="windows",
        title="ActivityFunc body vazio em .OCREngine/.CVEngine",
        description="",
        detect={
            "type": "python",
            "params": {
                "module": "uip_engine.heuristics.empty_activityfunc",
                "function": "detect_empty_ocr_activityfunc",
            },
        },
        fix={"apply_class": "structural", "prose": "plug OCR activity"},
    )


def _fc(tmp_path: Path, body: str, name: str = "Sample.xaml") -> FileContext:
    f = tmp_path / name
    f.write_text(body, encoding="utf-8")
    return FileContext(f)


_HEADER = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
    '          xmlns:uix="http://schemas.uipath.com/workflow/activities/uiautomationnext"\n'
    '          xmlns:p1="http://schemas.uipath.com/workflow/activities/ocr"\n'
    '          xmlns:sd="clr-namespace:System.Drawing;assembly=System.Drawing.Primitives"\n'
    '          xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Collections"\n'
    '          xmlns:sd1="clr-namespace:System.Drawing;assembly=System.Drawing.Primitives"\n'
    '          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
)
_FOOTER = '</Activity>\n'


def _wrap(body: str) -> str:
    return _HEADER + body + _FOOTER


# ---------------------------------------------------------------------------
# Detector cases
# ---------------------------------------------------------------------------


def test_empty_ocrengine_activityfunc_flagged(tmp_path):
    """ActivityFunc body só com Argument → finding S-18."""
    body = """
    <uix:NApplicationCard>
      <uix:NApplicationCard.OCREngine>
        <ActivityFunc x:TypeArguments="sd:Image, scg:IEnumerable(scg:KeyValuePair(sd1:Rectangle, x:String))">
          <ActivityFunc.Argument>
            <DelegateInArgument x:TypeArguments="sd:Image" Name="Image" />
          </ActivityFunc.Argument>
        </ActivityFunc>
      </uix:NApplicationCard.OCREngine>
    </uix:NApplicationCard>
    """
    fc = _fc(tmp_path, _wrap(body))
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "S-18"
    assert "OCREngine" in f.message
    assert "OCR Engine must be set" in f.message
    assert f.line > 1


def test_ocrengine_with_uipathscreenocr_no_finding(tmp_path):
    """ActivityFunc com UiPathScreenOCR child → 0 findings (fixed)."""
    body = """
    <uix:NApplicationCard>
      <uix:NApplicationCard.OCREngine>
        <ActivityFunc x:TypeArguments="sd:Image, scg:IEnumerable(scg:KeyValuePair(sd1:Rectangle, x:String))">
          <ActivityFunc.Argument>
            <DelegateInArgument x:TypeArguments="sd:Image" Name="Image" />
          </ActivityFunc.Argument>
          <p1:UiPathScreenOCR Image="[Image]" Language="en" Profile="Screen" Scale="1" Timeout="100000" />
        </ActivityFunc>
      </uix:NApplicationCard.OCREngine>
    </uix:NApplicationCard>
    """
    fc = _fc(tmp_path, _wrap(body))
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert findings == []


def test_xaml_without_engine_props_no_finding(tmp_path):
    """XAML sem .OCREngine/.CVEngine → 0 findings."""
    body = """
    <Sequence>
      <ui:WriteLine Text="hello" />
    </Sequence>
    """
    fc = _fc(tmp_path, _wrap(body))
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert findings == []


def test_empty_cvengine_activityfunc_flagged(tmp_path):
    """CVEngine vazio também flagueia (mesmo mecanismo)."""
    body = """
    <uix:NApplicationCard>
      <uix:NApplicationCard.CVEngine>
        <ActivityFunc x:TypeArguments="sd:Image, x:Object">
          <ActivityFunc.Argument>
            <DelegateInArgument x:TypeArguments="sd:Image" Name="Image" />
          </ActivityFunc.Argument>
        </ActivityFunc>
      </uix:NApplicationCard.CVEngine>
    </uix:NApplicationCard>
    """
    fc = _fc(tmp_path, _wrap(body))
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert len(findings) == 1
    f = findings[0]
    assert "CVEngine" in f.message
    assert "CV Engine must be set" in f.message


def test_only_xml_comment_inside_activityfunc_is_still_empty(tmp_path):
    """ActivityFunc com só comentário XML não conta como activity → finding."""
    body = """
    <uix:NApplicationCard>
      <uix:NApplicationCard.OCREngine>
        <ActivityFunc x:TypeArguments="sd:Image, x:Object">
          <ActivityFunc.Argument>
            <DelegateInArgument x:TypeArguments="sd:Image" Name="Image" />
          </ActivityFunc.Argument>
          <!-- TODO: plug UiPathScreenOCR here -->
        </ActivityFunc>
      </uix:NApplicationCard.OCREngine>
    </uix:NApplicationCard>
    """
    fc = _fc(tmp_path, _wrap(body))
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert len(findings) == 1


def test_multiple_empty_ocrengines_same_file(tmp_path):
    """Múltiplos OCREngine vazios mesmo arquivo → N findings."""
    body = """
    <uix:NApplicationCard>
      <uix:NApplicationCard.OCREngine>
        <ActivityFunc x:TypeArguments="sd:Image, x:Object">
          <ActivityFunc.Argument>
            <DelegateInArgument x:TypeArguments="sd:Image" Name="Image" />
          </ActivityFunc.Argument>
        </ActivityFunc>
      </uix:NApplicationCard.OCREngine>
    </uix:NApplicationCard>
    <uix:NApplicationCard>
      <uix:NApplicationCard.OCREngine>
        <ActivityFunc x:TypeArguments="sd:Image, x:Object">
          <ActivityFunc.Argument>
            <DelegateInArgument x:TypeArguments="sd:Image" Name="Image" />
          </ActivityFunc.Argument>
        </ActivityFunc>
      </uix:NApplicationCard.OCREngine>
    </uix:NApplicationCard>
    """
    fc = _fc(tmp_path, _wrap(body))
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert len(findings) == 2
    # Linhas distintas
    assert findings[0].line != findings[1].line


def test_self_closed_activityfunc_inside_engine_prop_flagged(tmp_path):
    """ActivityFunc self-close trivialmente vazio → finding."""
    body = """
    <uix:NApplicationCard>
      <uix:NApplicationCard.OCREngine>
        <ActivityFunc x:TypeArguments="sd:Image, x:Object" />
      </uix:NApplicationCard.OCREngine>
    </uix:NApplicationCard>
    """
    fc = _fc(tmp_path, _wrap(body))
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert len(findings) == 1


def test_non_xaml_file_skipped(tmp_path):
    """Detector guard: só XAML."""
    f = tmp_path / "config.json"
    f.write_text("{}", encoding="utf-8")
    # FileContext aceita qualquer path; detector deve pular não-.xaml.
    fc = FileContext(f)
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert findings == []


def test_mixed_engine_props_separate_findings(tmp_path):
    """OCREngine empty + CVEngine empty no mesmo arquivo → 2 findings."""
    body = """
    <uix:NApplicationCard>
      <uix:NApplicationCard.OCREngine>
        <ActivityFunc x:TypeArguments="sd:Image, x:Object">
          <ActivityFunc.Argument>
            <DelegateInArgument x:TypeArguments="sd:Image" Name="Image" />
          </ActivityFunc.Argument>
        </ActivityFunc>
      </uix:NApplicationCard.OCREngine>
      <uix:NApplicationCard.CVEngine>
        <ActivityFunc x:TypeArguments="sd:Image, x:Object">
          <ActivityFunc.Argument>
            <DelegateInArgument x:TypeArguments="sd:Image" Name="Image" />
          </ActivityFunc.Argument>
        </ActivityFunc>
      </uix:NApplicationCard.CVEngine>
    </uix:NApplicationCard>
    """
    fc = _fc(tmp_path, _wrap(body))
    findings = detect_empty_ocr_activityfunc(_rule(), fc, None)
    assert len(findings) == 2
    msgs = sorted([f.message for f in findings])
    assert any("OCREngine" in m for m in msgs)
    assert any("CVEngine" in m for m in msgs)
