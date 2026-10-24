"""Bounded Unicode normalization views for pattern-based recognition.

Pattern recognizers run regular expressions on raw text, so entities written
with compatibility variants (e.g. full-width digits) or with invisible
format characters inserted (e.g. zero-width spaces) are missed: the raw
characters simply do not match ASCII patterns.

This module builds a *normalized view* of a text alongside an *offset map*
back to the original text, so matches found on the normalized view can be
reported with original-text offsets (which is what downstream redaction
needs).

The normalization is deliberately bounded:

* ``NFKC`` compatibility normalization, applied per character, which folds
  full-width and other compatibility variants to their canonical form
  (e.g. ``\\uff11`` -> ``1``).
* Removal of format characters (Unicode category ``Cf``), which covers
  zero-width spaces and similar invisible characters.

Normalization is applied per character rather than to the whole string.
Whole-string NFKC can compose across character boundaries, which would make
the offset map ambiguous; per-character normalization keeps every normalized
character attributable to exactly one original character, so the mapping is
simple and predictable. Cross-boundary composition cases are therefore not
handled, which is an accepted limitation of this bounded approach.

Whitespace is intentionally *not* removed: deleting whitespace could glue
unrelated characters together into spurious matches.
"""

import unicodedata
from typing import List, Tuple


def build_normalized_view(text: str) -> Tuple[str, List[int]]:
    """
    Build a normalized view of ``text`` and its offset map.

    :param text: The original text.
    :return: A tuple of the normalized text and an index map, where
        ``index_map[i]`` is the index in the original text of the character
        that produced the ``i``-th character of the normalized text.
        ``len(index_map) == len(normalized_text)`` always holds.
    """
    normalized_chars: List[str] = []
    index_map: List[int] = []
    for original_index, char in enumerate(text):
        for normalized_char in unicodedata.normalize("NFKC", char):
            if unicodedata.category(normalized_char) == "Cf":
                continue
            normalized_chars.append(normalized_char)
            index_map.append(original_index)
    return "".join(normalized_chars), index_map


def map_span_to_original(
    index_map: List[int], start: int, end: int
) -> Tuple[int, int]:
    """
    Map a span from normalized-view offsets to original-text offsets.

    The mapped span covers every original character that contributed to the
    normalized span. If a normalized character came from an original
    character that expanded to several normalized characters (e.g. a
    ligature), the whole original character is covered, since redaction
    must remove the original character as a unit.

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
