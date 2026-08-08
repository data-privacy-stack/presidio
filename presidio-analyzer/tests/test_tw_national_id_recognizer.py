"""Tests for Taiwan National ID recognizer."""

import pytest
from presidio_analyzer.predefined_recognizers import TwNationalIdRecognizer

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Create a Taiwan National ID recognizer instance for testing."""
    return TwNationalIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Taiwan National ID entity type for testing."""
    return ["TW_NATIONAL_ID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        ("A100000001", 1, ((0, 10),), ((0.5, 1.0),),),
        ("B120863514", 1, ((0, 10),), ((0.5, 1.0),),),
        ("(A100000001)", 1, ((1, 11),), ((0.5, 1.0),),),
        (
            "身分證字號：A100000001",
            1,
            ((6, 16),),
            ((0.5, 1.0),),
        ),
        (
            "身分證字號A100000001",
            1,
            ((5, 15),),
            ((0.5, 1.0),),
        ),
        (
            "A100000001已驗證",
            1,
            ((0, 10),),
            ((0.5, 1.0),),
        ),
        (
            "National ID A100000001 belongs to the applicant.",
            1,
            ((12, 22),),
            ((0.5, 1.0),),
        ),
        (
            "Primary ID A100000001, secondary ID B120863514",
            2,
            ((11, 21), (36, 46),),
            ((0.5, 1.0), (0.5, 1.0),),
        ),
        ("A100000002", 0, (), (),),
        ("Z100000000", 0, (), (),),
        ("A300000001", 0, (), (),),
        ("AA00000001", 0, (), (),),
        ("A10000001", 0, (), (),),
        ("A1000000011", 0, (), (),),
        ("身分證 A100000002", 0, (), (),),
        ("a100000001", 1, ((0, 10),), ((0.5, 1.0),),),
    ],
)
def test_when_tw_national_id_in_text_then_all_matches_are_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    """Test that Taiwan National ID recognizer correctly identifies IDs."""
    results = sorted(
        recognizer.analyze(text, entities),
        key=lambda result: result.start,
    )
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if st_score == "max":
            st_score = max_score
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


@pytest.mark.parametrize(
    "value, expected",
    [
        ("A100000001", True),
        ("B120863514", True),
        ("A100000002", False),
        ("Z100000000", False),
        ("A300000001", False),
        ("AA00000001", False),
        ("A10000001", False),
        ("A1000000011", False),
        ("a100000001", True),
    ],
)
def test_validate_result(value, expected, recognizer):
    """Test validate_result with valid and invalid Taiwan IDs."""
    assert recognizer.validate_result(value) is expected


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["TW_NATIONAL_ID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "zh"


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "身分證",
        "身分證字號",
        "身份證",
        "身份證字號",
        "國民身分證",
        "national id",
        "id number",
    ]
    assert recognizer.context == expected_context
