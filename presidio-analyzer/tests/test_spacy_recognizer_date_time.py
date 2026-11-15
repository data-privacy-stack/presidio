"""Tests for the DATE/TIME guard in SpacyRecognizer (issue #2415)."""

from presidio_analyzer.predefined_recognizers import SpacyRecognizer


class _FakeSpan:
    """Minimal stand-in for a spaCy span inside NlpArtifacts."""

    def __init__(self, label: str, start: int, end: int):
        self.label_ = label
        self.start_char = start
        self.end_char = end


class _FakeNlpArtifacts:
    """Minimal stand-in for NlpArtifacts holding a single NER entity."""

    def __init__(self, span: _FakeSpan, score: float):
        self.entities = [span]
        self.scores = [score]


def _analyze_span(text: str, span_text: str):
    start = text.index(span_text)
    artifacts = _FakeNlpArtifacts(
        _FakeSpan("DATE_TIME", start, start + len(span_text)), 0.85
    )
    return SpacyRecognizer().analyze(
        text=text, entities=["DATE_TIME"], nlp_artifacts=artifacts
    )


def test_phone_number_span_is_not_returned_as_date_time():
    """A DATE span that a supported region validates is a phone, not a date."""
    text = "Call me on 9848012345 about the water problem."

    assert _analyze_span(text, "9848012345") == []


def test_uk_phone_number_span_is_not_returned_as_date_time():
    """The guard also applies to a number valid in another supported region."""
    text = "Call me on 07700 900123 about the water problem."

    assert _analyze_span(text, "07700 900123") == []


def test_date_span_that_is_not_a_phone_number_is_returned():
    """A span no supported region validates keeps its DATE_TIME result."""
    text = "I bought my car in 1972."

    results = _analyze_span(text, "1972")

    assert len(results) == 1
    assert results[0].entity_type == "DATE_TIME"
    assert results[0].score == 0.85
