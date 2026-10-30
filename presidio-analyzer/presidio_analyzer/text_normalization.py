r"""Bounded text normalization for the analyzer.

Entities are missed when they are written with full-width ("wide")
characters, as typed with many Chinese and Japanese input methods
(``１２３``, ``ＡＢＣ``), or with invisible characters inserted to split a
number (``123\u200b456``): ASCII patterns and models do not see them.

This module builds a *normalized view* of a text that undoes those two
things, alongside an *offset map* back to the original text, so entities
found on the normalized view can be reported with original-text offsets
(which is what downstream redaction needs). The analyzer engine uses it
when ``normalize_text`` is enabled.

The transform is deliberately narrow, so it is safe for text in any
language:

* Full-width letters and digits (U+FF10-U+FF19, U+FF21-U+FF3A and
  U+FF41-U+FF5A) are folded to ASCII.
* Other full-width ASCII variants (U+FF01-U+FF5E, e.g. ``＠``, ``．`` and
  ``－``) are folded only when they sit between letters or digits, as in an
  email address or an ID number. Full-width punctuation in running text,
  such as ``，`` or ``：`` after a Han character, is kept as written.
* Zero-width space and a few other invisible characters (see
  ``_INVISIBLE_CHARS``) are removed. Zero-width joiners and non-joiners are
  kept, since they are part of ordinary spelling in Persian, Urdu and Indic
  scripts.

Nothing else changes. In particular there is no Unicode compatibility (NFKC)
normalization, so every character of the normalized view comes from exactly
one original character.
"""

from bisect import bisect_left
from typing import List, Optional, Tuple

import regex

# Full-width forms U+FF01-U+FF5E are the ASCII characters U+0021-U+007E
# shifted by this offset.
_FULLWIDTH_OFFSET = 0xFEE0

_INVISIBLE_CHARS = frozenset(
    "\u00ad"  # soft hyphen
    "\u200b"  # zero-width space
    "\u2060"  # word joiner
    "\u2061\u2062\u2063\u2064"  # invisible math operators
    "\ufeff"  # zero-width no-break space (byte order mark)
)

_CHANGEABLE_CHAR_PATTERN = regex.compile(
    "[\uff01-\uff5e" + "".join(sorted(_INVISIBLE_CHARS)) + "]"
)


def _is_fullwidth(char: str) -> bool:
    return "\uff01" <= char <= "\uff5e"


def _fold(char: str) -> str:
    return chr(ord(char) - _FULLWIDTH_OFFSET)


def _is_letter_or_digit(char: str) -> bool:
    """Return True for ASCII letters and digits and their full-width forms."""
    if _is_fullwidth(char):
        char = _fold(char)
    return char.isascii() and char.isalnum()


def needs_normalized_view(text: str) -> bool:
    """
    Return True when a normalized view of ``text`` could differ from ``text``.

    This is a fast pre-check for callers that would otherwise build the view
    only to discover it equals the raw text.

    :param text: The original text.
    :return: True when ``text`` contains full-width or invisible characters.
    """
    return _CHANGEABLE_CHAR_PATTERN.search(text) is not None


def build_normalized_view(text: str) -> Tuple[str, List[int]]:
    """
    Build a normalized view of ``text`` and its offset map.

    :param text: The original text.
    :return: A tuple of the normalized text and an index map, where
        ``index_map[i]`` is the index in the original text of the character
        that produced the ``i``-th character of the normalized text.
        ``len(index_map) == len(normalized_text)`` always holds.
    """
    index_map = [i for i, char in enumerate(text) if char not in _INVISIBLE_CHARS]
    chars = [text[i] for i in index_map]
    normalized_chars = list(chars)

    position = 0
    while position < len(chars):
        if not _is_fullwidth(chars[position]):
            position += 1
        elif _is_letter_or_digit(chars[position]):
            normalized_chars[position] = _fold(chars[position])
            position += 1
        else:
            # A run of full-width symbols: fold it only when it sits between
            # letters or digits.
            run_end = position
            while (
                run_end < len(chars)
                and _is_fullwidth(chars[run_end])
                and not _is_letter_or_digit(chars[run_end])
            ):
                run_end += 1
            if (
                position > 0
                and run_end < len(chars)
                and _is_letter_or_digit(chars[position - 1])
                and _is_letter_or_digit(chars[run_end])
            ):
                for i in range(position, run_end):
                    normalized_chars[i] = _fold(chars[i])
            position = run_end

    return "".join(normalized_chars), index_map


def map_span_to_original(index_map: List[int], start: int, end: int) -> Tuple[int, int]:
    """
    Map a span from normalized-view offsets to original-text offsets.

    The mapped span covers every original character between the first and
    the last normalized character of the span, including invisible
    characters removed from inside it, since redaction must remove those
    too.

    :param index_map: The offset map returned by :func:`build_normalized_view`.
    :param start: Start offset in the normalized view (inclusive).
    :param end: End offset in the normalized view (exclusive).
    :return: The ``(start, end)`` span in the original text.
    """
    if not 0 <= start < end <= len(index_map):
        raise ValueError(
            f"Invalid normalized span ({start}, {end}) "
            f"for a normalized view of length {len(index_map)}."
        )
    original_start = index_map[start]
    original_end = index_map[end - 1] + 1
    return original_start, original_end


def map_span_to_normalized(
    index_map: List[int], start: int, end: int
) -> Optional[Tuple[int, int]]:
    """
    Map a span from original-text offsets to normalized-view offsets.

    Characters removed by the normalization are dropped from the span.

    :param index_map: The offset map returned by :func:`build_normalized_view`.
    :param start: Start offset in the original text (inclusive).
    :param end: End offset in the original text (exclusive).
    :return: The ``(start, end)`` span in the normalized view, or None when
        the span only covers removed characters.
    """
    normalized_start = bisect_left(index_map, start)
    normalized_end = bisect_left(index_map, end)
    if normalized_start >= normalized_end:
        return None
    return normalized_start, normalized_end
