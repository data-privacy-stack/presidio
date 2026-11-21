from abc import ABC, abstractmethod

from presidio_analyzer.text_normalizers.normalized_text import NormalizedText


class TextNormalizer(ABC):
    """
    Produce the text that the analyzer runs on, aligned with the original text.

    An :class:`~presidio_analyzer.AnalyzerEngine` given a text normalizer runs the
    NLP engine, the recognizers, context enhancement and the allow-list on the
    normalized text, and maps the results back to the original text, so the
    returned offsets are always offsets in the original text. When the
    normalization changed the text, pattern recognizers also run on the
    original text.

    An implementation only produces the normalized text and its alignment, as a
    :class:`NormalizedText`. For each normalized character, ``starts`` and
    ``ends`` give the range of original characters it comes from: both have the
    length of the normalized text, neither decreases, and each range is
    non-empty and within the original text. Removed characters appear in no
    range. The same text and language must always give the same result, since a
    text can be normalized more than once.
    """

    @abstractmethod
    def normalize(self, text: str, language: str) -> NormalizedText:
        """
        Normalize a text.

        :param text: The text to normalize.
        :param language: The language of the text, for normalizers that
        depend on it.
        :return: The normalized text and its alignment with ``text``.
        """
