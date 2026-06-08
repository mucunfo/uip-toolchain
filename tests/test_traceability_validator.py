from pathlib import Path

from uip_engine.traceability_validator import is_traceable, validate_messages


def test_validate_messages_flags_generic_literals(tmp_path: Path):
    verdicts = validate_messages(["OK", '[in_StPrefixoLog + "Fim"]'], tmp_path)

    assert verdicts["OK"]["verdict"] == "fail"
    assert verdicts['[in_StPrefixoLog + "Fim"]']["verdict"] == "pass"


def test_is_traceable_accepts_runtime_context(tmp_path: Path):
    assert is_traceable(
        '[in_StPrefixoLog + ("Processou linhas: " + vDTabItens.Rows.Count.ToString)]',
        tmp_path,
    )


def test_validate_messages_works_with_empty_path_and_cache(tmp_path: Path):
    msg = "Validou retorno da consulta cadastral"

    first = validate_messages([msg], tmp_path)
    second = validate_messages([msg], tmp_path)

    assert first == second
    assert first[msg]["verdict"] == "pass"
