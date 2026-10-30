"""Tests for the bounded text normalization used by the analyzer engine."""

import pytest
from presidio_analyzer.text_normalization import (
    build_normalized_view,
    map_span_to_normalized,
    map_span_to_original,
    needs_normalized_view,
)


def to_fullwidth(text: str) -> str:
    """Map ASCII printable characters to their full-width forms."""
    return "".join(
        chr(ord(char) + 0xFEE0) if 0x21 <= ord(char) <= 0x7E else char for char in text
    )


def test_ascii_text_is_unchanged():
    text = "ID 110101199003077512, mail test@example.com"
    assert not needs_normalized_view(text)
    normalized, index_map = build_normalized_view(text)
    assert normalized == text
    assert index_map == list(range(len(text)))


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
    assert needs_normalized_view(text)
    normalized, index_map = build_normalized_view(text)
    assert normalized == text.replace(to_fullwidth(value), value)
    assert index_map == list(range(len(text)))


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
    normalized, _ = build_normalized_view(text)
    assert normalized == expected


@pytest.mark.parametrize(
    "text",
    [
        "می‌خواهم",  # Persian, zero-width non-joiner as part of the word
        "क्‍ष",  # Devanagari with a zero-width joiner
        "น้ำ",  # Thai, changed by NFKC
        "한국어",  # Korean
        "١٢٣ ۱۲۳",  # Arabic-Indic and Persian digits
        "①②③ x² ½ ﬁ",  # compatibility characters NFKC would rewrite
        "ｶﾀｶﾅ",  # half-width katakana
        "東京　大阪",  # ideographic space
        "é",  # combining accent
    ],
)
def test_other_text_is_unchanged(text):
    normalized, index_map = build_normalized_view(text)
    assert normalized == text
    assert index_map == list(range(len(text)))


def test_invisible_characters_are_removed():
    text = "ID 110​101­1990⁠0307﻿7512"
    assert needs_normalized_view(text)
    normalized, index_map = build_normalized_view(text)
    assert normalized == "ID 110101199003077512"
    # Original indices 6, 10, 15 and 20 are the removed characters.
    removed = {6, 10, 15, 20}
    assert index_map == [i for i in range(len(text)) if i not in removed]


def test_symbols_next_to_removed_characters_are_still_folded():
    normalized, _ = build_normalized_view("２３４​－５６－​７８９０")
    assert normalized == "234-56-7890"


def test_map_span_to_original_covers_removed_characters_inside_the_span():
    text = "ID 110​101 end"
    _, index_map = build_normalized_view(text)
    assert map_span_to_original(index_map, 3, 9) == (3, 10)


def test_map_span_to_original_rejects_invalid_spans():
    _, index_map = build_normalized_view("abc")
    with pytest.raises(ValueError):
        map_span_to_original(index_map, 2, 2)
    with pytest.raises(ValueError):
        map_span_to_original(index_map, 0, 4)


def test_map_span_to_normalized():
    text = "a​bc​ d"
    _, index_map = build_normalized_view(text)
    # "a​bc" -> "abc"
    assert map_span_to_normalized(index_map, 0, 4) == (0, 3)
    # Removed characters at the edges of the span are dropped.
    assert map_span_to_normalized(index_map, 1, 5) == (1, 3)
    # A span of removed characters only has no normalized counterpart.
    assert map_span_to_normalized(index_map, 1, 2) is None


def test_spans_round_trip():
    text = "pay " + to_fullwidth("DE89370400440532013000") + "​ now"
    _, index_map = build_normalized_view(text)
    span = map_span_to_normalized(index_map, 4, 26)
    assert span == (4, 26)
    assert map_span_to_original(index_map, *span) == (4, 26)
