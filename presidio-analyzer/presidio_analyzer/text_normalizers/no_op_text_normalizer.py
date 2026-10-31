from presidio_analyzer.text_normalizers.normalized_text import NormalizedText
from presidio_analyzer.text_normalizers.text_normalizer import TextNormalizer


class NoOpTextNormalizer(TextNormalizer):
    """A text normalizer that returns the text unchanged."""

    def normalize(self, text: str, language: str) -> NormalizedText:
        """Return ``text`` unchanged, aligned character by character."""
        return NormalizedText.identity(text)
