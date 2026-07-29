import datetime

import pytest

from presidio_analyzer.predefined_recognizers import ZaIdNumberRecognizer
from presidio_analyzer.predefined_recognizers.country_specific.south_africa import (
    za_id_number_recognizer,
)
from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return ZaIdNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ZA_ID_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        ("8001015009087", 1, ((0, 13),),),
        ("8001015000086", 1, ((0, 13),),),
        ("My South African ID is 9202201234088.", 1, ((23, 36),),),
        ("RSA ID: 0002294321191", 1, ((8, 21),),),
        ("Permanent resident number 9912316789285 is on file.", 1, ((26, 39),),),
        ("Refugee ID number 0001015002288 is on file.", 1, ((18, 31),),),
        ("8001015009086", 0, (),),
        ("9913326789285", 0, (),),
        ("9902294321191", 0, (),),
        ("8001015000076", 0, (),),
        ("8001015009176", 0, (),),
        ("1234567890123", 0, (),),
        ("ID 80010150090", 0, (),),
        ("SA ID 80010150090870", 0, (),),
        ("AB8001015009087CD", 0, (),),
        # fmt: on
    ],
)
def test_analyze_valid_and_invalid_za_ids(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    """Tests the recognizer against valid and invalid South African ID numbers."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "id_number, expected",
    [
        ("8001015009087", True),
        ("8001015000086", True),
        ("9202201234088", True),
        ("0002294321191", True),
        ("9912316789285", True),
        ("0001015002288", True),
        ("8001015009086", False),
        ("9913326789285", False),
        ("9902294321191", False),
        ("8001015000076", False),
        ("8001015009176", False),
        ("80010150090", False),
        ("80010150090870", False),
        ("80010150090A7", False),
    ],
)
def test_validate_result(id_number, expected, recognizer):
    assert recognizer.validate_result(id_number) is expected


@pytest.mark.parametrize(
    "date_part, expected",
    [
        ("050101", True),
        ("000229", True),
        ("990229", False),
    ],
)
def test_has_valid_birth_date(date_part, expected):
    assert ZaIdNumberRecognizer._has_valid_birth_date(date_part) is expected


def test_has_valid_birth_date_rejects_future_date(monkeypatch):
    class FixedDate(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(2025, 6, 15)

    monkeypatch.setattr(za_id_number_recognizer, "date", FixedDate)

    assert ZaIdNumberRecognizer._has_valid_birth_date("251231") is False
    assert ZaIdNumberRecognizer._has_valid_birth_date("250615") is True
