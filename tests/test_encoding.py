from pathlib import Path
import pytest
from uip_engine.encoding import detect_and_decode

FIX = Path(__file__).parent / "fixtures"


def test_utf8_bom_decoded():
    text = detect_and_decode(FIX / "utf8_bom.xaml")
    assert text.startswith("<Activity>")
    # BOM stripped — first char must not be U+FEFF
    assert not text.startswith("﻿")


def test_utf8_no_bom_decoded():
    text = detect_and_decode(FIX / "utf8_no_bom.xaml")
    assert text.startswith("<Activity>")


def test_utf16_bom_decoded():
    text = detect_and_decode(FIX / "utf16_bom.xaml")
    assert text.startswith("<Activity>")


def test_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        detect_and_decode(FIX / "missing.xaml")
