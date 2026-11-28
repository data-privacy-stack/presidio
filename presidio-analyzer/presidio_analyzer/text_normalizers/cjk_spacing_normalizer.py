import regex

from presidio_analyzer.text_normalizers.normalized_text import NormalizedText

from .full_width_and_invisible_chars_normalizer import (
    FullWidthAndInvisibleCharsNormalizer,
)

_CJK_CHARS = r"\p{Han}\p{Hiragana}\p{Katakana}\p{Hangul}"
_CJK_CHAR_PATTERN = regex.compile(f"[{_CJK_CHARS}]")
# A position between a CJK character and an ASCII letter or digit, either way round.
_GAP_PATTERN = regex.compile(
    f"(?<=[{_CJK_CHARS}])(?=[A-Za-z0-9])|(?<=[A-Za-z0-9])(?=[{_CJK_CHARS}])"
)


class CjkSpacingNormalizer(FullWidthAndInvisibleCharsNormalizer):
    r"""
    Put a space between CJK text and the ASCII letters and digits next to it.

    Chinese, Japanese and Korean text often has no spaces around numbers,
    emails and other values (``号码4111111111111111结束``). Patterns that use
    ``\b`` treat CJK characters as word characters, so they find no word
    boundary there and miss the value.

    This normalizer first does what
    :class:`FullWidthAndInvisibleCharsNormalizer` does, then puts a space
    between a Han, Hiragana, Katakana or Hangul character and an ASCII letter
    or digit next to it. Each space is mapped to the CJK character next to it,
    so the offsets of a detected value do not change. The language is not used.
    """

    def normalize(self, text: str, language: str) -> NormalizedText:
        """Fold ``text`` like the parent class, then space out CJK text."""
        folded = super().normalize(text, language)
        gaps = {match.start() for match in _GAP_PATTERN.finditer(folded.text)}
        if not gaps:
            return folded

        chars, starts, ends = [], [], []
        for i, char in enumerate(folded.text):
            if i in gaps:
                cjk = i - 1 if _CJK_CHAR_PATTERN.match(folded.text[i - 1]) else i
                chars.append(" ")
                starts.append(folded.starts[cjk])
                ends.append(folded.ends[cjk])
            chars.append(char)
            starts.append(folded.starts[i])
            ends.append(folded.ends[i])

        return NormalizedText(
            original_text=text, text="".join(chars), starts=starts, ends=ends
        )
