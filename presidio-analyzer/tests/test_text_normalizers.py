"""Tests for the text normalizers and NormalizedText."""

import pytest
from presidio_analyzer.text_normalizers import (
    FullWidthAndInvisibleCharsNormalizer,
    NoOpTextNormalizer,
    NormalizedText,
)


def to_fullwidth(text: str) -> str:
    """Map ASCII printable characters to their full-width forms."""
    return "".join(
        chr(ord(char) + 0xFEE0) if 0x21 <= ord(char) <= 0x7E else char for char in text
    )


def normalize(text: str) -> NormalizedText:
    return FullWidthAndInvisibleCharsNormalizer().normalize(text, "en")


def test_ascii_text_is_unchanged():
    text = "ID 110101199003077512, mail test@example.com"
    normalized = normalize(text)
    assert normalized.text == text
    assert not normalized.changed
    assert list(normalized.starts) == list(range(len(text)))


@pytest.mark.parametrize(
    "value",
    [
        "110101199003077512",
        "ABCxyz",
        "test@example.com",
        "https://example.com/a?b=c",
        "234-56-7890",
        "192.168.0.1",
        "AA:BB:CC:DD:EE:FF",
        "01/02/2024",
    ],
)
def test_fullwidth_values_are_folded(value):
    text = "x " + to_fullwidth(value) + " y"
    normalized = normalize(text)
    assert normalized.changed
    assert normalized.text == text.replace(to_fullwidth(value), value)
    assert list(normalized.starts) == list(range(len(text)))
    assert list(normalized.ends) == list(range(1, len(text) + 1))


@pytest.mark.parametrize(
    "text,expected",
    [
        # Full-width punctuation in running CJK text is kept; only the
        # full-width digits and the symbols between letters or digits change.
        ("你好，世界：１２３", "你好，世界：123"),
        ("邮箱：ｊｏｈｎ＠ｅｘａｍｐｌｅ．ｃｏｍ。", "邮箱：john@example.com。"),
        ("（５５５）１２３－４５６７", "（555)123-4567"),
        ("「ＯＫ」！", "「OK」！"),
        ("１，０００円", "1,000円"),
    ],
)
def test_fullwidth_symbols_are_folded_only_between_letters_or_digits(text, expected):
    assert normalize(text).text == expected


@pytest.mark.parametrize(
    "text",
    [
        "می\u200cخواهم",  # Persian, zero-width non-joiner as part of the word
        "क्\u200dष",  # Devanagari with a zero-width joiner
        "น้ำ",  # Thai, changed by NFKC
        "한국어",  # Korean
        "١٢٣ ۱۲۳",  # Arabic-Indic and Persian digits
        "①②③ x² ½ ﬁ",  # compatibility characters NFKC would rewrite
        "ｶﾀｶﾅ",  # half-width katakana
        "東京　大阪",  # ideographic space
        "e\u0301",  # combining accent
    ],
)
def test_other_text_is_unchanged(text):
    normalized = normalize(text)
    assert normalized.text == text
    assert not normalized.changed
    assert list(normalized.starts) == list(range(len(text)))


def test_invisible_characters_are_removed():
    text = "ID 110\u200b101\u00ad1990\u20600307\ufeff7512"
    normalized = normalize(text)
    assert normalized.text == "ID 110101199003077512"
    # Original indices 6, 10, 15 and 20 are the removed characters.
    removed = {6, 10, 15, 20}
    kept = [i for i in range(len(text)) if i not in removed]
    assert list(normalized.starts) == kept
    assert list(normalized.ends) == [i + 1 for i in kept]


def test_symbols_next_to_removed_characters_are_still_folded():
    normalized = normalize("２３４\u200b－５６－\u200b７８９０")
    assert normalized.text == "234-56-7890"


def test_to_original_covers_removed_characters_inside_the_span():
    text = "ID 110\u200b101 end"
    assert normalize(text).to_original(3, 9) == (3, 10)


def test_to_original_rejects_invalid_spans():
    normalized = normalize("abc")
    with pytest.raises(ValueError):
        normalized.to_original(2, 2)
    with pytest.raises(ValueError):
        normalized.to_original(0, 4)


def test_to_normalized():
    text = "a\u200bbc\u200b d"
    normalized = normalize(text)
    # "a\u200bbc" -> "abc"
    assert normalized.to_normalized(0, 4) == (0, 3)
    # Removed characters at the edges of the span are dropped.
    assert normalized.to_normalized(1, 5) == (1, 3)
    # A span of removed characters only has no normalized counterpart.
    assert normalized.to_normalized(1, 2) is None


def test_spans_round_trip():
    text = "pay " + to_fullwidth("DE89370400440532013000") + "\u200b now"
    normalized = normalize(text)
    span = normalized.to_normalized(4, 26)
    assert span == (4, 26)
    assert normalized.to_original(*span) == (4, 26)


def test_no_op_normalizer_returns_the_text_unchanged():
    normalized = NoOpTextNormalizer().normalize("ID １２３", "en")
    assert normalized.text == "ID １２３"
    assert not normalized.changed
    assert normalized.to_original(3, 6) == (3, 6)
    assert normalized.to_normalized(0, 2) == (0, 2)


def test_identity():
    normalized = NormalizedText.identity("abc")
    assert normalized.text == normalized.original_text == "abc"
    assert list(normalized.starts) == [0, 1, 2]
    assert list(normalized.ends) == [1, 2, 3]


def test_expansion_maps_to_the_whole_original_character():
    # "ß" -> "ss": both normalized characters come from original index 0.
    normalized = NormalizedText(
        original_text="ß x", text="ss x", starts=[0, 0, 1, 2], ends=[1, 1, 2, 3]
    )
    assert normalized.changed
    assert normalized.to_original(1, 2) == (0, 1)
    assert normalized.to_original(0, 4) == (0, 3)
    assert normalized.to_normalized(0, 1) == (0, 2)
    assert normalized.to_normalized(2, 3) == (3, 4)


def test_composition_maps_to_both_original_characters():
    # "e" + combining acute accent -> precomposed "e with acute".
    normalized = NormalizedText(
        original_text="e\u0301x", text="\u00e9x", starts=[0, 2], ends=[2, 3]
    )
    assert normalized.to_original(0, 1) == (0, 2)
    assert normalized.to_original(1, 2) == (2, 3)
    # A match on either original character covers the composed character.
    assert normalized.to_normalized(0, 1) == (0, 1)
    assert normalized.to_normalized(1, 2) == (0, 1)
    assert normalized.to_normalized(2, 3) == (1, 2)


@pytest.mark.parametrize(
    "text,starts,ends,message",
    [
        ("ab", [0], [1], "must have the length of the normalized text"),
        ("ab", [1, 0], [2, 1], "Invalid alignment at normalized index 1"),
        ("ab", [0, 1], [1, 4], "Invalid alignment at normalized index 1"),
        ("ab", [0, 1], [1, 1], "Invalid alignment at normalized index 1"),
        ("ab", [-1, 1], [1, 2], "Invalid alignment at normalized index 0"),
        # Ranges that are not the identity alignment are checked like lists.
        ("ab", range(2), range(2), "Invalid alignment at normalized index 0"),
    ],
)
def test_normalized_text_checks_its_alignment(text, starts, ends, message):
    with pytest.raises(ValueError, match=message):
        NormalizedText(original_text="abc", text=text, starts=starts, ends=ends)
