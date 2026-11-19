"""AnalyzerEngine with a text normalizer.

Covers issue #2396: entities written with full-width characters or with
zero-width characters inserted are missed on the raw text. With a text
normalizer, the engine analyzes the normalized text and maps the results back
to original-text offsets.
"""

from typing import List

import pytest
from presidio_analyzer import (
    AnalysisExplanation,
    AnalyzerEngine,
    BatchAnalyzerEngine,
    FullWidthAndInvisibleCharsNormalizer,
    LocalRecognizer,
    NoOpTextNormalizer,
    NormalizedText,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    RecognizerResult,
    TextNormalizer,
)
from presidio_analyzer.nlp_engine import NlpArtifacts, NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    CryptoRecognizer,
    DateRecognizer,
    EmailRecognizer,
    IbanRecognizer,
    IpRecognizer,
    MacAddressRecognizer,
    UrlRecognizer,
    UsSsnRecognizer,
    UuidRecognizer,
)

DIGITS = "110101199003077512"
ID_PATTERN = r"(?<![0-9])[0-9]{17}[0-9X](?![0-9])"
ZERO_WIDTH_ID = "110\u200b101\u200b1990\u200b0307\u200b7512"
NORMALIZED_NOTE = "Detected on the normalized text"
ZERO_WIDTH_SPACE = chr(0x200B)


def to_fullwidth(text: str) -> str:
    """Map ASCII printable characters to their full-width forms."""
    return "".join(
        chr(ord(char) + 0xFEE0) if 0x21 <= ord(char) <= 0x7E else char for char in text
    )


def mask(text: str, results: List[RecognizerResult]) -> str:
    """Replace result spans in the original text, as an anonymizer would."""
    masked = text
    for result in sorted(results, key=lambda r: r.start, reverse=True):
        masked = masked[: result.start] + "[REDACTED]" + masked[result.end :]
    return masked


def no_op_nlp_engine() -> NoOpNlpEngine:
    return NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}])


def make_engine(recognizers, normalize: bool = True, nlp_engine=None) -> AnalyzerEngine:
    return AnalyzerEngine(
        registry=RecognizerRegistry(recognizers=recognizers),
        nlp_engine=nlp_engine or no_op_nlp_engine(),
        text_normalizer=FullWidthAndInvisibleCharsNormalizer() if normalize else None,
    )


def id_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="ID_NUM", patterns=[Pattern("id18", ID_PATTERN, 0.9)]
    )


class RecordingRecognizer(LocalRecognizer):
    """Finds a keyword and records the text and tokens it was given."""

    def __init__(self, keyword: str):
        self.keyword = keyword
        self.calls = []
        super().__init__(supported_entities=["KEYWORD"], name="RecordingRecognizer")

    def load(self) -> None:
        pass

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        tokens = nlp_artifacts.tokens if nlp_artifacts else None
        self.calls.append((text, getattr(tokens, "text", None)))
        start = text.find(self.keyword)
        if start < 0:
            return []
        return [RecognizerResult("KEYWORD", start, start + len(self.keyword), 0.8)]


class FixedSpansRecognizer(LocalRecognizer):
    """Returns the same (entity, start, end) results for any text."""

    def __init__(self, spans):
        self.spans = spans
        super().__init__(
            supported_entities=[entity for entity, _, _ in spans],
            name="FixedSpansRecognizer",
        )

    def load(self) -> None:
        pass

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        return [
            RecognizerResult(
                entity,
                start,
                end,
                0.8,
                analysis_explanation=AnalysisExplanation(
                    recognizer=self.name, original_score=0.8
                ),
            )
            for entity, start, end in self.spans
        ]


class DropHashNormalizer(TextNormalizer):
    """A custom normalizer that removes '#' characters."""

    def normalize(self, text: str, language: str) -> NormalizedText:
        kept = [i for i, char in enumerate(text) if char != "#"]
        return NormalizedText(
            original_text=text,
            text="".join(text[i] for i in kept),
            starts=kept,
            ends=[i + 1 for i in kept],
        )


def test_text_is_not_normalized_by_default():
    engine = make_engine([id_recognizer()], normalize=False)

    assert isinstance(engine.text_normalizer, NoOpTextNormalizer)
    assert engine.analyze("ID " + to_fullwidth(DIGITS), language="en") == []
    assert engine.analyze("ID " + ZERO_WIDTH_ID, language="en") == []


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ID " + DIGITS, "ID [REDACTED]"),
        ("ID " + to_fullwidth(DIGITS), "ID [REDACTED]"),
        ("ID " + ZERO_WIDTH_ID, "ID [REDACTED]"),
        ("ID " + DIGITS[:9] + to_fullwidth(DIGITS[9:]), "ID [REDACTED]"),
        (
            "Contact ID " + to_fullwidth(DIGITS) + " end",
            "Contact ID [REDACTED] end",
        ),
    ],
)
def test_obfuscated_ids_are_detected_with_original_spans(text, expected):
    results = make_engine([id_recognizer()]).analyze(text, language="en")

    assert len(results) == 1
    assert results[0].score == 0.9
    assert mask(text, results) == expected


def test_match_found_on_raw_and_normalized_text_is_reported_once():
    # The full-width word makes the engine normalize; the ID itself is ASCII,
    # so both passes of the pattern recognizer find it.
    text = "ID " + DIGITS + " ＯＫ"

    results = make_engine([id_recognizer()]).analyze(text, language="en")

    assert [(r.start, r.end) for r in results] == [(3, 21)]


def test_patterns_written_for_raw_text_still_match():
    recognizer = PatternRecognizer(
        supported_entity="FULLWIDTH_CODE",
        patterns=[Pattern("code", "[０-９]{6}", 0.7)],
    )
    text = "code １２３４５６ end"

    results = make_engine([recognizer]).analyze(text, language="en")

    assert [(r.entity_type, r.start, r.end) for r in results] == [
        ("FULLWIDTH_CODE", 5, 11)
    ]


# (recognizer class, valid ASCII value, entity)
PREDEFINED_CASES = [
    (CreditCardRecognizer, "4111111111111111", "CREDIT_CARD"),
    (CryptoRecognizer, "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "CRYPTO"),
    (DateRecognizer, "01/02/2024", "DATE_TIME"),
    (EmailRecognizer, "test@example.com", "EMAIL_ADDRESS"),
    (IbanRecognizer, "DE89370400440532013000", "IBAN_CODE"),
    (IpRecognizer, "192.168.0.1", "IP_ADDRESS"),
    (MacAddressRecognizer, "AA:BB:CC:DD:EE:FF", "MAC_ADDRESS"),
    (UrlRecognizer, "https://example.com", "URL"),
    (UuidRecognizer, "123e4567-e89b-12d3-a456-426614174000", "UUID"),
    (UsSsnRecognizer, "234-56-7890", "US_SSN"),
]


@pytest.mark.parametrize("recognizer_class,value,entity", PREDEFINED_CASES)
def test_predefined_recognizers_detect_fullwidth_values(
    recognizer_class, value, entity
):
    engine = make_engine([recognizer_class()])
    text = "value: " + to_fullwidth(value) + " end"
    ascii_score = max(
        r.score
        for r in engine.analyze("value: " + value + " end", language="en")
        if r.entity_type == entity
    )

    results = [
        r for r in engine.analyze(text, language="en") if r.entity_type == entity
    ]
    off_results = make_engine([recognizer_class()], normalize=False).analyze(
        text, language="en"
    )

    full_span = (7, 7 + len(value))
    assert full_span in [(r.start, r.end) for r in results]
    assert max(r.score for r in results) == ascii_score
    assert not [r for r in off_results if r.entity_type == entity]


def test_zero_width_separated_iban_is_detected():
    text = "DE89\u200b370400440532013000"

    results = make_engine([IbanRecognizer()]).analyze(text, language="en")

    assert [(r.entity_type, r.start, r.end) for r in results] == [
        ("IBAN_CODE", 0, len(text))
    ]


def test_other_recognizers_get_only_the_normalized_text():
    recognizer = RecordingRecognizer("John")
    text = "Name: Ｊｏｈｎ\u200b."

    results = make_engine([recognizer]).analyze(text, language="en")

    assert [text for text, _ in recognizer.calls] == ["Name: John."]
    assert [(r.entity_type, r.start, r.end) for r in results] == [("KEYWORD", 6, 10)]


def test_results_with_invalid_spans_are_skipped(caplog):
    # The normalized text is "Name: John", 10 characters long.
    recognizer = FixedSpansRecognizer(
        [("VALID", 6, 10), ("EMPTY", 5, 5), ("OUT_OF_RANGE", 3, 30)]
    )
    text = "Name: " + to_fullwidth("John") + ZERO_WIDTH_SPACE

    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        results = make_engine([recognizer]).analyze(text, language="en")

    assert [(r.entity_type, r.start, r.end) for r in results] == [("VALID", 6, 10)]
    assert "EMPTY result with an invalid span (5, 5)" in caplog.text
    assert "OUT_OF_RANGE result with an invalid span (3, 30)" in caplog.text


def test_results_with_invalid_spans_are_returned_as_before_without_normalization():
    recognizer = FixedSpansRecognizer(
        [("VALID", 6, 10), ("EMPTY", 5, 5), ("OUT_OF_RANGE", 3, 30)]
    )

    results = make_engine([recognizer], normalize=False).analyze(
        "Name: John", language="en"
    )

    assert sorted((r.entity_type, r.start, r.end) for r in results) == [
        ("EMPTY", 5, 5),
        ("OUT_OF_RANGE", 3, 30),
        ("VALID", 6, 10),
    ]


def test_allow_list_applies_to_the_normalized_text():
    text = "ID " + to_fullwidth(DIGITS)

    results = make_engine([id_recognizer()]).analyze(
        text, language="en", allow_list=[DIGITS]
    )

    assert results == []


def test_exact_allow_list_entries_are_normalized():
    text = "ID " + to_fullwidth(DIGITS)

    results = make_engine([id_recognizer()]).analyze(
        text, language="en", allow_list=[to_fullwidth(DIGITS)]
    )

    assert results == []


def test_explanation_notes_matches_changed_by_normalization():
    text = "ID " + to_fullwidth(DIGITS) + " and ID " + DIGITS

    results = make_engine([id_recognizer()]).analyze(
        text, language="en", return_decision_process=True
    )

    notes = {
        (r.start, r.end): NORMALIZED_NOTE in r.analysis_explanation.textual_explanation
        for r in results
    }
    assert notes == {(3, 21): True, (29, 47): False}


def test_custom_normalizer_is_used():
    text = "ID " + DIGITS[:4] + "#" + DIGITS[4:]
    engine = AnalyzerEngine(
        registry=RecognizerRegistry(recognizers=[id_recognizer()]),
        nlp_engine=no_op_nlp_engine(),
        text_normalizer=DropHashNormalizer(),
    )

    results = engine.analyze(text, language="en")

    assert [(r.entity_type, r.start, r.end) for r in results] == [("ID_NUM", 3, 22)]


def test_batch_analyzer_passes_original_text_and_normalized_artifacts(
    spacy_nlp_engine,
):
    if spacy_nlp_engine is None:
        pytest.skip("spaCy engine not available")
    recognizer = RecordingRecognizer("John")
    engine = make_engine([id_recognizer(), recognizer], nlp_engine=spacy_nlp_engine)
    texts = ["ID " + to_fullwidth(DIGITS), "plain text", "Name: Ｊｏｈｎ\u200b."]

    results = BatchAnalyzerEngine(analyzer_engine=engine).analyze_iterator(
        texts, language="en"
    )

    assert [[(r.entity_type, r.start, r.end) for r in res] for res in results] == [
        [("ID_NUM", 3, 21)],
        [],
        [("KEYWORD", 6, 10)],
    ]
    # Each recognizer call got NLP artifacts of the same text it analyzed.
    assert [text for text, _ in recognizer.calls] == [
        "ID " + DIGITS,
        "plain text",
        "Name: John.",
    ]
    assert all(text == tokens for text, tokens in recognizer.calls)


def test_batch_analyzer_uses_the_engine_normalizer(spacy_nlp_engine):
    if spacy_nlp_engine is None:
        pytest.skip("spaCy engine not available")
    recognizer = RecordingRecognizer("John")
    engine = AnalyzerEngine(
        registry=RecognizerRegistry(recognizers=[recognizer]),
        nlp_engine=spacy_nlp_engine,
        text_normalizer=DropHashNormalizer(),
    )

    results = BatchAnalyzerEngine(analyzer_engine=engine).analyze_iterator(
        ["Name: Jo#hn."], language="en"
    )

    assert [[(r.start, r.end) for r in res] for res in results] == [[(6, 11)]]
    assert recognizer.calls == [("Name: John.", "Name: John.")]


def test_spacy_ner_finds_fullwidth_name(spacy_nlp_engine):
    if spacy_nlp_engine is None:
        pytest.skip("spaCy engine not available")
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(nlp_engine=spacy_nlp_engine)
    # en_core_web_lg misses this name when it is written in full-width.
    text = "My name is " + to_fullwidth("Robert Brown") + "."

    results = AnalyzerEngine(
        registry=registry,
        nlp_engine=spacy_nlp_engine,
        text_normalizer=FullWidthAndInvisibleCharsNormalizer(),
    ).analyze(text, language="en", entities=["PERSON"])

    assert [(r.entity_type, r.start, r.end) for r in results] == [("PERSON", 11, 23)]
