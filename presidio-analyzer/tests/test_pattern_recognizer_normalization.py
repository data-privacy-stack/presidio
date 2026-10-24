"""Tests for opt-in normalization-aware pattern recognition.

Covers Presidio issue #2396: entities written with full-width digits or
with zero-width characters inserted are missed when patterns run on raw
text, but detected when patterns run on a bounded normalized view
(NFKC + format-character removal) with spans mapped back to the
original text.
"""

import pytest
from presidio_analyzer import Pattern, PatternRecognizer
from presidio_analyzer.text_normalization import (
    build_normalized_view,
    map_span_to_original,
)

from tests import assert_result

DIGITS = "110101199003077512"
ID_PATTERN = r"(?<![0-9])[0-9]{17}[0-9X](?![0-9])"


def make_id_recognizer(normalize_text: bool) -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="ID_NUM",
        patterns=[Pattern("id18", ID_PATTERN, 0.9)],
        normalize_text=normalize_text,
    )


def fullwidth(text: str) -> str:
    return "".join(chr(0xFF10 + int(c)) if c.isdigit() else c for c in text)


def mask(text: str, results) -> str:
    """Replace result spans in the original text, as an anonymizer would."""
    masked = text
    for result in sorted(results, key=lambda r: r.start, reverse=True):
        masked = masked[: result.start] + "[REDACTED]" + masked[result.end :]
    return masked


# --- build_normalized_view / map_span_to_original ---


def test_normalized_view_identity_for_ascii():
    text = "ID 110101199003077512"
    normalized, index_map = build_normalized_view(text)
    assert normalized == text
    assert index_map == list(range(len(text)))


def test_normalized_view_folds_fullwidth_digits():
    normalized, index_map = build_normalized_view("ID " + fullwidth(DIGITS))
    assert normalized == "ID " + DIGITS
    assert index_map == list(range(3)) + list(range(3, 21))


def test_normalized_view_drops_zero_width_characters():
    text = "ID 110\u200b101\u200b1990\u200b0307\u200b7512"
    normalized, index_map = build_normalized_view(text)
    assert normalized == "ID " + DIGITS
    # The 4 zero-width characters (original indices 6, 10, 15, 20) are
    # dropped, so the map skips them; every normalized char still maps
    # to exactly one original char.
    assert index_map == [
        0,
        1,
        2,
        3,
        4,
        5,
        7,
        8,
        9,
        11,
        12,
        13,
        14,
        16,
        17,
        18,
        19,
        21,
        22,
        23,
        24,
    ]


def test_normalized_view_expansion_maps_to_single_original_char():
    # U+FB01 (Latin small ligature fi) expands to two characters.
    normalized, index_map = build_normalized_view("a\ufb01b")
    assert normalized == "afib"
    assert index_map == [0, 1, 1, 2]


def test_map_span_to_original_covers_whole_expanded_char():
    _, index_map = build_normalized_view("a\ufb01b")
    # Normalized span (1, 2) covers only "f" of the expansion, but the
    # mapped span must cover the whole original ligature character.
    assert map_span_to_original(index_map, 1, 2) == (1, 2)
    assert map_span_to_original(index_map, 1, 3) == (1, 2)


def test_map_span_to_original_rejects_invalid_spans():
    _, index_map = build_normalized_view("abc")
    with pytest.raises(ValueError):
        map_span_to_original(index_map, 2, 2)
    with pytest.raises(ValueError):
        map_span_to_original(index_map, 0, 4)


# --- PatternRecognizer with normalize_text ---


def test_without_normalization_obfuscated_forms_missed():
    recognizer = make_id_recognizer(normalize_text=False)
    assert recognizer.analyze("ID " + DIGITS, ["ID_NUM"])
    assert recognizer.analyze("ID " + fullwidth(DIGITS), ["ID_NUM"]) == []
    assert (
        recognizer.analyze("ID 110\u200b101\u200b1990\u200b0307\u200b7512", ["ID_NUM"])
        == []
    )


def test_with_normalization_all_forms_detected_with_original_spans():
    recognizer = make_id_recognizer(normalize_text=True)

    results = recognizer.analyze("ID " + DIGITS, ["ID_NUM"])
    assert len(results) == 1
    assert_result(results[0], "ID_NUM", 3, 21, 0.9)

    results = recognizer.analyze("ID " + fullwidth(DIGITS), ["ID_NUM"])
    assert len(results) == 1
    assert_result(results[0], "ID_NUM", 3, 21, 0.9)

    text = "ID 110\u200b101\u200b1990\u200b0307\u200b7512"
    results = recognizer.analyze(text, ["ID_NUM"])
    assert len(results) == 1
    # Span covers the digits plus the 4 inserted zero-width characters.
    assert_result(results[0], "ID_NUM", 3, 25, 0.9)


def test_with_normalization_masking_invariant_on_original_text():
    recognizer = make_id_recognizer(normalize_text=True)
    cases = [
        ("ID " + DIGITS, "ID [REDACTED]"),
        ("ID " + fullwidth(DIGITS), "ID [REDACTED]"),
        (
            "ID 110\u200b101\u200b1990\u200b0307\u200b7512",
            "ID [REDACTED]",
        ),
        (
            "Contact ID " + fullwidth(DIGITS) + " end",
            "Contact ID [REDACTED] end",
        ),
    ]
    for text, expected in cases:
        results = recognizer.analyze(text, ["ID_NUM"])
        assert len(results) == 1
        assert mask(text, results) == expected


def test_with_normalization_mixed_ascii_and_fullwidth_digits():
    recognizer = make_id_recognizer(normalize_text=True)
    mixed = DIGITS[:9] + fullwidth(DIGITS[9:])
    results = recognizer.analyze("ID " + mixed, ["ID_NUM"])
    assert len(results) == 1
    assert_result(results[0], "ID_NUM", 3, 21, 0.9)


def test_with_normalization_no_duplicate_when_both_views_match():
    # Native digits match on both the raw and the normalized pass;
    # they must be reported exactly once.
    recognizer = make_id_recognizer(normalize_text=True)
    results = recognizer.analyze("ID " + DIGITS, ["ID_NUM"])
    assert len(results) == 1


def test_with_normalization_ligature_match_covers_original_char():
    recognizer = PatternRecognizer(
        supported_entity="WORD",
        patterns=[Pattern("fi", r"fi", 0.9)],
        normalize_text=True,
    )
    results = recognizer.analyze("a\ufb01b", ["WORD"])
    assert len(results) == 1
    assert_result(results[0], "WORD", 1, 2, 0.9)


def test_with_normalization_validation_runs_on_normalized_text():
    class AsciiOnlyRecognizer(PatternRecognizer):
        def validate_result(self, pattern_text):
            # Full-width digits are not ASCII; only the normalized
            # match passes this validation.
            return pattern_text.isascii()

    recognizer = AsciiOnlyRecognizer(
        supported_entity="ID_NUM",
        patterns=[Pattern("id18", ID_PATTERN, 0.9)],
        normalize_text=True,
    )
    results = recognizer.analyze("ID " + fullwidth(DIGITS), ["ID_NUM"])
    assert len(results) == 1
    assert results[0].score == 1.0


def test_normalize_text_round_trips_through_dict():
    recognizer = make_id_recognizer(normalize_text=True)
    serialized = recognizer.to_dict()
    assert serialized["normalize_text"] is True
    restored = PatternRecognizer.from_dict(serialized)
    assert restored.normalize_text is True
    assert restored.analyze("ID " + fullwidth(DIGITS), ["ID_NUM"])
