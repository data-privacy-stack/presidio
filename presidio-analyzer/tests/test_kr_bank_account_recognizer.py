import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers.country_specific.korea import (
    KrBankAccountRecognizer,
)


@pytest.fixture(scope="module")
def recognizer():
    return KrBankAccountRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["KR_BANK_ACCOUNT"]


# Patterns overlap by design (an NH account also matches the generic layouts),
# so positive cases assert on the best-scoring match instead of result counts.
@pytest.mark.parametrize(
    "text, start, end, score",
    [
        # NH (NongHyup) 302-prefixed 4-segment personal account
        ("302-1234-5678-91", 0, 16, 0.6),
        ("이체 계좌: 302-0123-4567-89", 7, 23, 0.6),
        # Common hyphenated 3-segment layouts
        ("110-234-567890", 0, 14, 0.3),
        ("457-910-012345", 0, 14, 0.3),
        # Mixed/plain digit runs (9-16 digits, excluding the 13-digit RRN shape)
        ("987654321012", 0, 12, 0.15),
        ("1002-123-456789", 0, 15, 0.15),
    ],
)
def test_when_account_like_then_best_match_found(
    text, start, end, score, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert results
    best = max(results, key=lambda r: r.score)
    assert_result_within_score_range(best, entities[0], start, end, score, score)


@pytest.mark.parametrize(
    "text",
    [
        # Korean mobile / VoIP phone numbers must not match
        "010-1234-5678",
        "070-1234-5678",
        "01012345678",
        "07012345678",
        # Resident registration number shapes must not match
        "960121-1234567",
        "9601211234567",
        # Any 13-digit pure run is left to KR_RRN's domain
        "9876543210123",
        # Dates must not match
        "2024-03-10",
        # Too short
        "45000",
        "12345678",
    ],
)
def test_when_look_alike_then_no_match(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []
