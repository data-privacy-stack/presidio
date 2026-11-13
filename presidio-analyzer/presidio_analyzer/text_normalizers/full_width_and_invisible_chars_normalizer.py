import regex

from presidio_analyzer.text_normalizers.normalized_text import NormalizedText
from presidio_analyzer.text_normalizers.text_normalizer import TextNormalizer

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


class FullWidthAndInvisibleCharsNormalizer(TextNormalizer):
    r"""
    Fold full-width characters to ASCII and remove invisible characters.

    Entities are missed when they are written with full-width ("wide")
    characters, as typed with many Chinese and Japanese input methods
    (``１２３``, ``ＡＢＣ``), or with invisible characters
    inserted to split a number (``123\u200b456``): ASCII patterns and
    models do not see them.

    The transform is deliberately narrow, so it is safe for text in any
    language:

    * Full-width letters and digits (U+FF10-U+FF19, U+FF21-U+FF3A and
      U+FF41-U+FF5A) are folded to ASCII.
    * Other full-width ASCII variants (U+FF01-U+FF5E, for example the full-width
      at sign, full stop and hyphen-minus) are folded only when they sit between
      letters or digits, as in an email address or an ID number. Full-width
      punctuation in running text, such as a full-width comma or colon after a
      Han character, is kept as written.
    * Zero-width space, soft hyphen, word joiner, the invisible math operators
      and the byte order mark are removed. Zero-width joiners and non-joiners
      are kept, since they are part of ordinary spelling in Persian, Urdu and
      Indic scripts.

    Nothing else changes; there is no Unicode compatibility (NFKC)
    normalization. The language is not used.
    """

    def normalize(self, text: str, language: str) -> NormalizedText:
        """Fold full-width characters and remove invisible characters in ``text``."""
        if _CHANGEABLE_CHAR_PATTERN.search(text) is None:
            return NormalizedText.identity(text)

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

        return NormalizedText(
            original_text=text,
            text="".join(normalized_chars),
            starts=index_map,
            ends=[i + 1 for i in index_map],
        )
