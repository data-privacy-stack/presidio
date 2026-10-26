from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import JpMyNumberRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

ENTITY = "JP_MY_NUMBER"
CONTIGUOUS_SCORE = 0.05
GROUPED_SCORE = 0.1
CONTEXT_BOOST = 0.35  # LemmaContextAwareEnhancer default context_similarity_factor


@pytest.fixture(scope="module")
def recognizer():
    return JpMyNumberRecognizer()


@pytest.mark.parametrize(
    "text, start, end, score",
    [
        # Contiguous, half-width.
        ("123456789018", 0, 12, CONTIGUOUS_SCORE),
        ("987654321093", 0, 12, CONTIGUOUS_SCORE),
        ("111111111118", 0, 12, CONTIGUOUS_SCORE),
        # Embedded in Japanese text, where ``\b`` would not match.
        ("マイナンバーは123456789018です。", 7, 19, CONTIGUOUS_SCORE),
        ("私のマイナンバーは246801357929です。", 9, 21, CONTIGUOUS_SCORE),
        # Full-width digits.
        ("マイナンバーは１２３４５６７８９０１８です。", 7, 19, CONTIGUOUS_SCORE),
        # 4-4-4 groups with a consistent separator.
        ("1234-5678-9018", 0, 14, GROUPED_SCORE),
        ("1234 5678 9018", 0, 14, GROUPED_SCORE),
        ("１２３４－５６７８－９０１８", 0, 14, GROUPED_SCORE),
        ("１２３４　５６７８　９０１８", 0, 14, GROUPED_SCORE),
        # English carrier text.
        ("My Number: 123456789018.", 11, 23, CONTIGUOUS_SCORE),
    ],
)
def test_when_valid_my_number_then_detected_with_pattern_score(
    recognizer, text, start, end, score
):
    results = recognizer.analyze(text, [ENTITY])

    assert len(results) == 1
    assert (results[0].start, results[0].end) == (start, end)
    assert results[0].entity_type == ENTITY
    # A passing checksum must not promote to MAX_SCORE: ~1 in 10 arbitrary
    # 12-digit runs pass it.
    assert results[0].score == pytest.approx(score)


@pytest.mark.parametrize(
    "text",
    [
        # Wrong check digit.
        "123456789019",
        "マイナンバーは123456789010です。",
        "1234-5678-9019",
        # Checksum-valid placeholder.
        "000000000000",
        # Wrong length, including a valid number embedded in a longer run.
        "12345678901",
        "1234567890180",
        "0123456789018",
        "１２３４５６７８９０１８９",
        # Inconsistent separators.
        "1234-5678 9018",
        "1234-56789018",
        # Lookalikes of the same shape that fail the checksum: a mobile phone
        # number with a trailing extension, an order number, a timestamp.
        "注文番号は202610261234です。",
        "20261026 1111",
        "090123456780",
    ],
)
def test_when_invalid_or_lookalike_then_not_detected(recognizer, text):
    assert recognizer.analyze(text, [ENTITY]) == []


def test_mobile_phone_number_is_not_detected(recognizer):
    """Japanese mobile numbers are 11 digits; they must never match."""
    assert recognizer.analyze("電話番号は09012345678です。", [ENTITY]) == []
    assert recognizer.analyze("電話番号は090-1234-5678です。", [ENTITY]) == []


@pytest.mark.parametrize(
    "base, check",
    [
        ("12345678901", 8),
        ("98765432109", 3),
        ("24680135792", 9),
        ("11111111111", 8),
        ("00000000000", 0),
    ],
)
def test_compute_check_digit(base, check):
    assert JpMyNumberRecognizer._compute_check_digit(base) == check


def test_default_supported_language_is_ja():
    assert JpMyNumberRecognizer().supported_language == "ja"


def test_accepts_loader_kwargs():
    recognizer = JpMyNumberRecognizer(
        name="CustomJpMyNumber", supported_entity="CUSTOM", context=["x"]
    )
    assert recognizer.name == "CustomJpMyNumber"
    assert recognizer.supported_entities == ["CUSTOM"]
    assert recognizer.context == ["x"]


def test_context_word_raises_score(spacy_nlp_engine):
    """Score differs with and without a context word (CI has no ja model)."""
    registry = RecognizerRegistry(supported_languages=["en"])
    registry.add_recognizer(JpMyNumberRecognizer(supported_language="en"))
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )
    text = "Please repeat 123456789018 back to me."

    without = analyzer.analyze(text, language="en", entities=[ENTITY])
    with_context = analyzer.analyze(
        text, language="en", entities=[ENTITY], context=["マイナンバー"]
    )

    assert [r.score for r in without] == [pytest.approx(CONTIGUOUS_SCORE)]
    assert [r.score for r in with_context] == [
        pytest.approx(CONTIGUOUS_SCORE + CONTEXT_BOOST)
    ]


@pytest.mark.parametrize("language", ["ja", "en"])
def test_loads_from_default_recognizers_yaml(language):
    """Recognizer is registered in the default YAML and detects once enabled.

    The top-level ``supported_languages`` filter defaults to ``["en"]``, so a
    registry serving Japanese text must list ``ja`` there.
    """
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "JpMyNumberRecognizer"]
    assert len(entries) == 1, "JpMyNumberRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "jp"
    assert entry["enabled"] is False
    assert language in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": [language],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["JpMyNumberRecognizer"]
    loaded = registry.recognizers[0]
    assert loaded.supported_language == language
    results = loaded.analyze("マイナンバーは123456789018です。", [ENTITY])
    assert [(r.entity_type, r.start, r.end) for r in results] == [(ENTITY, 7, 19)]


def test_end_to_end_japanese_with_context():
    """Full analyzer on Japanese text, with the spaCy Japanese model."""
    pytest.importorskip("ja_core_news_sm")
    nlp_engine = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "ja", "model_name": "ja_core_news_sm"}],
        }
    ).create_engine()
    registry = RecognizerRegistry(supported_languages=["ja"])
    registry.add_recognizer(JpMyNumberRecognizer())
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=nlp_engine, supported_languages=["ja"]
    )

    with_context = analyzer.analyze(
        "マイナンバーは123456789018です。", language="ja", entities=[ENTITY]
    )
    # 個人番号 is tokenized as 個人 + 番号, so the context word is 個人.
    compound = analyzer.analyze(
        "私の個人番号は1234-5678-9018です。", language="ja", entities=[ENTITY]
    )
    without = analyzer.analyze(
        "次の数字を繰り返してください：123456789018", language="ja", entities=[ENTITY]
    )

    assert [(r.start, r.end, r.score) for r in with_context] == [
        (7, 19, pytest.approx(CONTIGUOUS_SCORE + CONTEXT_BOOST))
    ]
    assert [r.score for r in compound] == [pytest.approx(GROUPED_SCORE + CONTEXT_BOOST)]
    assert [r.score for r in without] == [pytest.approx(CONTIGUOUS_SCORE)]


def test_long_adversarial_input_is_fast(recognizer):
    """No catastrophic backtracking on long digit and separator runs."""
    import time

    text = ("1234-" * 20000) + ("１" * 20000)
    started = time.perf_counter()
    recognizer.analyze(text, [ENTITY])
    assert time.perf_counter() - started < 2.0
