from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple


@dataclass(frozen=True)
class NormalizedText:
    """
    A normalized text and its alignment with the original text.

    The ``i``-th character of ``text`` comes from the original characters
    ``original_text[starts[i]:ends[i]]``. A character removed by the
    normalization appears in no range. When one original character becomes
    several normalized characters, they share the same ``starts`` and ``ends``,
    and when several original characters become one normalized character, its
    range covers all of them.

    The constructor checks that ``starts`` and ``ends`` have the length of
    ``text``, that neither decreases, and that every range is non-empty and
    lies within ``original_text``.

    :param original_text: The text before normalization.
    :param text: The normalized text.
    :param starts: For each character of ``text``, the start index (inclusive)
    in ``original_text`` of the characters it comes from.
    :param ends: For each character of ``text``, the end index (exclusive)
    in ``original_text`` of the characters it comes from.
    """

    original_text: str
    text: str
    starts: Sequence[int]
    ends: Sequence[int]

    def __post_init__(self):
        """Check that ``starts`` and ``ends`` align ``text`` with the original."""
        if not len(self.starts) == len(self.ends) == len(self.text):
            raise ValueError(
                f"starts ({len(self.starts)}) and ends ({len(self.ends)}) must have "
                f"the length of the normalized text ({len(self.text)})."
            )
        if self._is_identity_alignment():
            return
        previous_start = previous_end = 0
        for i, (start, end) in enumerate(zip(self.starts, self.ends)):
            if not (
                previous_start <= start < end <= len(self.original_text)
                and previous_end <= end
            ):
                raise ValueError(
                    f"Invalid alignment at normalized index {i}: ({start}, {end}). "
                    "starts and ends must not decrease, and each range must be "
                    "non-empty and within the original text "
                    f"(length {len(self.original_text)})."
                )
            previous_start, previous_end = start, end

    def _is_identity_alignment(self) -> bool:
        # Checked in constant time for the ranges built by identity(), so a text
        # that is not normalized costs nothing to validate.
        length = len(self.original_text)
        return (
            isinstance(self.starts, range)
            and isinstance(self.ends, range)
            and len(self.text) == length
            and self.starts == range(length)
            and self.ends == range(1, length + 1)
        )

    @classmethod
    def identity(cls, text: str) -> "NormalizedText":
        """
        Return a normalized text equal to ``text``, aligned character by character.

        :param text: The original text.
        """
        return cls(
            original_text=text,
            text=text,
            starts=range(len(text)),
            ends=range(1, len(text) + 1),
        )

    @property
    def changed(self) -> bool:
        """Return True when the normalized text differs from the original text."""
        return self.text != self.original_text

    def to_original(self, start: int, end: int) -> Tuple[int, int]:
        """
        Map a span of the normalized text to the original text.

        The span covers every original character between the first and the
        last normalized character, including removed characters inside it,
        since redaction must remove those too.

        :param start: Start offset in the normalized text (inclusive).
        :param end: End offset in the normalized text (exclusive).
        :return: The ``(start, end)`` span in the original text.
        """
        if not 0 <= start < end <= len(self.text):
            raise ValueError(
                f"Invalid normalized span ({start}, {end}) "
                f"for a normalized text of length {len(self.text)}."
            )
        return self.starts[start], self.ends[end - 1]

    def to_normalized(self, start: int, end: int) -> Optional[Tuple[int, int]]:
        """
        Map a span of the original text to the normalized text.

        The span covers every normalized character that comes from an original
        character inside the span.

        :param start: Start offset in the original text (inclusive).
        :param end: End offset in the original text (exclusive).
        :return: The ``(start, end)`` span in the normalized text, or None when
        the span covers only removed characters.
        """
        normalized_start = bisect_right(self.ends, start)
        normalized_end = bisect_left(self.starts, end)
        if normalized_start >= normalized_end:
            return None
        return normalized_start, normalized_end
