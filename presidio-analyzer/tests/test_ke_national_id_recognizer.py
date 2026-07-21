import pytest

from presidio_analyzer.predefined_recognizers import KeNationalIdRecognizer
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from tests.assertions import assert_result_within_score_range

# Synthetic Kenyan national ID numbers used throughout the tests.
VALID_ID_8 = "12345678"   # 8-digit (current format)
VALID_ID_7 = "1234567"    # 7-digit (older cards)


@pytest.fixture(scope="module")
def recognizer():
    return KeNationalIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["KE_NATIONAL_ID"]


@pytest.fixture(scope="module")
def enhancer():
    return LemmaContextAwareEnhancer()


# ── Tests that call analyze() directly (no context enhancement) ───────────────
# PatternRecognizer does not apply LemmaContextAwareEnhancer internally, so
# scores remain at the base pattern score (0.01) regardless of surrounding text.

@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off

        # Bare 8-digit ID, no context
        (
            VALID_ID_8,
            1,
            ((0, 8),),
            ((0.0, 0.29),),
        ),
        # Bare 7-digit ID, no context
        (
            VALID_ID_7,
            1,
            ((0, 7),),
            ((0.0, 0.29),),
        ),

        # --- Invalid inputs ---

        # 6 digits: below minimum length
        (
            "123456",
            0,
            (),
            (),
        ),
        # 9 digits: above maximum length
        (
            "123456789",
            0,
            (),
            (),
        ),
        # Non-numeric
        (
            "1234567a",
            0,
            (),
            (),
        ),
        # Embedded in a longer number (word boundary)
        (
            f"99{VALID_ID_8}88",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_ke_national_id_without_context_then_expected_results(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


# ── Tests that verify context-driven score boosts ────────────────────────────
# LemmaContextAwareEnhancer compares individual spaCy token lemmas against the
# recognizer's CONTEXT list (substring mode).  Every case below includes a
# single-token context word that is present in KeNationalIdRecognizer.CONTEXT
# ("national", "kenya", "kenyan", "nid", "registration") so the boost is
# deterministic.

@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off

        # "national" token — single-token context entry
        (
            f"national id: {VALID_ID_8}",
            1,
            ((13, 21),),
            ((0.3, 1.0),),
        ),
        # "kenya" token — single-token context entry
        (
            f"Kenya national id number: {VALID_ID_7}",
            1,
            ((26, 33),),
            ((0.3, 1.0),),
        ),
        # "nid" token — single-token context entry
        (
            f"nid: {VALID_ID_8}",
            1,
            ((5, 13),),
            ((0.3, 1.0),),
        ),
        # "national" token in multi-word phrase
        (
            f"national identity card: {VALID_ID_8}",
            1,
            ((24, 32),),
            ((0.3, 1.0),),
        ),
        # "kenyan" token — single-token context entry
        (
            f"Kenyan id {VALID_ID_7} was reported",
            1,
            ((10, 17),),
            ((0.3, 1.0),),
        ),
        # fmt: on
    ],
)
def test_when_ke_national_id_with_context_then_score_boosted(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    enhancer,
    spacy_nlp_engine,
):
    if spacy_nlp_engine is None:
        pytest.skip("spaCy NLP engine not available in this test run")

    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    raw_results = recognizer.analyze(text, entities)
    results = enhancer.enhance_using_context(
        text, raw_results, nlp_artifacts, [recognizer]
    )

    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


class TestKeNationalIdValidation:
    """Unit tests for KeNationalIdRecognizer.validate_result."""

    def test_8_digit_id_returns_none(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result(VALID_ID_8) is None

    def test_7_digit_id_returns_none(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result(VALID_ID_7) is None

    def test_6_digit_returns_false(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result("123456") is False

    def test_9_digit_returns_false(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result("123456789") is False

    def test_non_numeric_returns_false(self):
        recognizer = KeNationalIdRecognizer()
        assert recognizer.validate_result("1234567a") is False
