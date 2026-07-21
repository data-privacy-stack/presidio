import pytest

from presidio_analyzer.predefined_recognizers import NgBvnRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from tests.assertions import assert_result_within_score_range

# Representative 11-digit BVN values used throughout the tests.
# These are synthetic — they follow the 11-digit format but are not real BVNs.
VALID_BVN_1 = "22345678901"
VALID_BVN_2 = "98765432101"
VALID_BVN_3 = "55512345678"


@pytest.fixture(scope="module")
def recognizer():
    return NgBvnRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["NG_BVN"]


@pytest.fixture(scope="module")
def enhancer():
    return LemmaContextAwareEnhancer()


# ── Tests that call analyze() directly (no context enhancement) ───────────────
# PatternRecognizer does not apply LemmaContextAwareEnhancer internally, so
# scores remain at the base pattern score (0.01) regardless of surrounding text.
# These cases cover bare matches and invalid inputs.

@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off

        # Bare BVN, no context — very weak signal
        (
            VALID_BVN_1,
            1,
            ((0, 11),),
            ((0.0, 0.29),),
        ),
        # Two bare BVNs, no context
        (
            f"{VALID_BVN_1} and {VALID_BVN_2}",
            2,
            ((0, 11), (16, 27)),
            ((0.0, 0.29), (0.0, 0.29)),
        ),

        # --- Invalid inputs: must not be detected ---

        # Wrong length: 10 digits
        (
            "2234567890",
            0,
            (),
            (),
        ),
        # Wrong length: 12 digits
        (
            "223456789012",
            0,
            (),
            (),
        ),
        # Non-numeric characters
        (
            "2234567890a",
            0,
            (),
            (),
        ),
        # Embedded in a longer number: word boundary must not match
        (
            f"99{VALID_BVN_1}88",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_bvn_without_context_then_expected_results(
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
# recognizer's CONTEXT list.  Only single-token context entries (e.g. "bvn",
# "nibss") trigger a boost; multi-word phrases are never matched against a
# single lemma.  Every test case below includes at least one such single-token
# context word so the boost is deterministic.

@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off

        # Exact context word "bvn"
        (
            f"bvn: {VALID_BVN_1}",
            1,
            ((5, 16),),
            ((0.3, 1.0),),
        ),
        # "BVN" token alongside the full phrase — "bvn" lemma triggers the boost
        (
            f"BVN bank verification number: {VALID_BVN_2}",
            1,
            ((30, 41),),
            ((0.3, 1.0),),
        ),
        # Context word "BVN" appears earlier in sentence
        (
            f"Please provide your BVN for KYC. Your BVN is {VALID_BVN_3}.",
            1,
            ((46, 57),),
            ((0.3, 1.0),),
        ),
        # "nibss" single-token context word
        (
            f"NIBSS BVN record: {VALID_BVN_1}",
            1,
            ((18, 29),),
            ((0.3, 1.0),),
        ),
        # fmt: on
    ],
)
def test_when_bvn_with_context_then_score_boosted(
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


class TestBvnValidation:
    """Unit tests for NgBvnRecognizer.validate_result."""

    def test_valid_11_digit_bvn_returns_none(self):
        recognizer = NgBvnRecognizer()
        # Returns None (not True) to preserve context-driven score.
        assert recognizer.validate_result(VALID_BVN_1) is None

    def test_10_digit_string_returns_false(self):
        recognizer = NgBvnRecognizer()
        assert recognizer.validate_result("2234567890") is False

    def test_12_digit_string_returns_false(self):
        recognizer = NgBvnRecognizer()
        assert recognizer.validate_result("223456789012") is False

    def test_non_numeric_returns_false(self):
        recognizer = NgBvnRecognizer()
        assert recognizer.validate_result("2234567890a") is False

    def test_all_zeros_11_digits_returns_none(self):
        # All-zeros is numerically valid format (11 digits, all numeric).
        recognizer = NgBvnRecognizer()
        assert recognizer.validate_result("00000000000") is None
