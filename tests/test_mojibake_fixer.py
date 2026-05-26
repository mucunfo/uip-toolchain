import pytest
from pathlib import Path
from uip_engine.mojibake_fixer import (
    detect, fix, fix_file, validate_round_trip,
    MojibakeKind, DetectionResult,
)


def test_detect_clean_utf8():
    content = "Adicionado à transação".encode("utf-8")
    det = detect(content)
    assert det.kind == MojibakeKind.CLEAN


def test_detect_double_encoded():
    # "à transação" as UTF-8 bytes [C3 A0 20 74 72 ...] read as cp1252 = "Ã  transação"
    # Then re-encoded UTF-8: "Ã " becomes UTF-8 bytes [C3 83 C2 A0]
    original = "Adicionado à transação o resultado: ação".encode("utf-8")
    # Simulate the corruption
    corrupted = original.decode("cp1252").encode("utf-8")
    det = detect(corrupted)
    assert det.kind == MojibakeKind.DOUBLE_ENCODED_UTF8


def test_fix_double_encoded_round_trip():
    original = "Adicionado à transação".encode("utf-8")
    corrupted = original.decode("cp1252").encode("utf-8")
    fixed = fix(corrupted, MojibakeKind.DOUBLE_ENCODED_UTF8)
    assert fixed == original


def test_detect_non_utf8_bytes():
    # Raw cp1252 bytes that aren't valid UTF-8
    content = "à transação".encode("cp1252")
    det = detect(content)
    assert det.kind == MojibakeKind.NON_UTF8_BYTES


def test_fix_non_utf8_bytes():
    content_cp1252 = "à transação".encode("cp1252")
    fixed = fix(content_cp1252, MojibakeKind.NON_UTF8_BYTES)
    assert fixed.decode("utf-8") == "à transação"


def test_detect_replacement_chars():
    content = "Adicionado � transa��o".encode("utf-8")
    det = detect(content)
    assert det.kind == MojibakeKind.REPLACEMENT_CHARS


def test_fix_file_in_place(tmp_path):
    p = tmp_path / "test.xaml"
    original_text = "<Activity><x:String>à transação</x:String></Activity>"
    corrupted = original_text.encode("utf-8").decode("cp1252").encode("utf-8")
    p.write_bytes(corrupted)

    det, modified = fix_file(p)
    assert det.kind == MojibakeKind.DOUBLE_ENCODED_UTF8
    assert modified is True
    assert p.read_text(encoding="utf-8") == original_text


def test_fix_file_clean_no_op(tmp_path):
    p = tmp_path / "clean.xaml"
    p.write_text("<Activity><x:String>hello world</x:String></Activity>", encoding="utf-8")
    original = p.read_bytes()
    det, modified = fix_file(p)
    assert det.kind == MojibakeKind.CLEAN
    assert modified is False
    assert p.read_bytes() == original


def test_dry_run_no_write(tmp_path):
    p = tmp_path / "test.xaml"
    original_text = "à transação"
    corrupted = original_text.encode("utf-8").decode("cp1252").encode("utf-8")
    p.write_bytes(corrupted)

    det, modified = fix_file(p, dry_run=True)
    assert det.kind == MojibakeKind.DOUBLE_ENCODED_UTF8
    assert modified is True  # would have been modified
    # File content unchanged
    assert p.read_bytes() == corrupted
