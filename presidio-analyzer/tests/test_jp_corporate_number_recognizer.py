from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import JpCorporateNumberRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

ENTITY = "JP_CORPORATE_NUMBER"
BARE_SCORE = 0.05
T_PREFIX_SCORE = 0.3
CONTEXT_BOOST = 0.35  # LemmaContextAwareEnhancer default context_similarity_factor


@pytest.fixture(scope="module")
def recognizer():
    return JpCorporateNumberRecognizer()


@pytest.mark.parametrize(
    "text, start, end, score",
    [
        # National Tax Agency's own Corporate Number (public record).
        ("7000012050002", 0, 13, BARE_SCORE),
        ("1000012160153", 0, 13, BARE_SCORE),
        ("6010401011234", 0, 13, BARE_SCORE),
        # Embedded in Japanese text and in full-width digits.
        ("法人番号は1000012160153です。", 5, 18, BARE_SCORE),
        ("法人番号は１００００１２１６０１５３です。", 5, 18, BARE_SCORE),
        # Qualified Invoice Issuer registration number.
        ("登録番号はT7000012050002です。", 5, 19, T_PREFIX_SCORE),
        ("登録番号：Ｔ７００００１２０５０００２", 5, 19, T_PREFIX_SCORE),
        ("Invoice reg. no. t7000012050002", 17, 31, T_PREFIX_SCORE),
    ],
)
def test_when_valid_corporate_number_then_detected_with_pattern_score(
    recognizer, text, start, end, score
):
    results = recognizer.analyze(text, [ENTITY])

    assert len(results) == 1
    assert (results[0].start, results[0].end) == (start, end)
    # ~1 in 9 arbitrary 13-digit runs pass the checksum: never promote.
    assert results[0].score == pytest.approx(score)


@pytest.mark.parametrize(
    "text",
    [
        # Wrong check digit.
        "7000012050003",
        "T1000012160154",
        # Checksum-valid placeholder.
        "9111111111111",
        # Wrong length.
        "700001205000",
        "70000120500021",
        # Inside a longer alphanumeric identifier, on either side and in both
        # half-width and full-width letters.
        "AB7000012050002",
        "XT7000012050002",
        "7000012050002AB",
        "T7000012050002AB",
        "７００００１２０５０００２ＡＢ",
        "Ｔ７００００１２０５０００２ＡＢ",
        # Lookalikes of the same shape that fail the checksum: a millisecond
        # Unix timestamp and a JAN/EAN-13 barcode.
        "1761450000000",
        "4901234567894",
    ],
)
def test_when_invalid_or_lookalike_then_not_detected(recognizer, text):
    assert recognizer.analyze(text, [ENTITY]) == []


def test_t_prefix_is_not_double_counted(recognizer):
    results = recognizer.analyze("T7000012050002", [ENTITY])
    assert [(r.start, r.end, r.score) for r in results] == [
        (0, 14, pytest.approx(T_PREFIX_SCORE))
    ]


@pytest.mark.parametrize(
    "base, check",
    [("000012050002", 7), ("000012160153", 1), ("010401011234", 6)],
)
def test_compute_check_digit(base, check):
    assert JpCorporateNumberRecognizer._compute_check_digit(base) == check


def test_accepts_loader_kwargs():
    recognizer = JpCorporateNumberRecognizer(name="CustomJpCorp")
    assert recognizer.name == "CustomJpCorp"
    assert recognizer.supported_language == "ja"


@pytest.mark.parametrize("language", ["ja", "en"])
def test_loads_from_default_recognizers_yaml(language):
    """Registered in the default YAML; ``ja`` must be a top-level language."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "JpCorporateNumberRecognizer"]
    assert len(entries) == 1, "JpCorporateNumberRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "jp"
    assert entry["enabled"] is False

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": [language],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "JpCorporateNumberRecognizer"
    ]
    results = registry.recognizers[0].analyze("法人番号は1000012160153です。", [ENTITY])
    assert [(r.entity_type, r.start, r.end) for r in results] == [(ENTITY, 5, 18)]


def test_end_to_end_japanese_with_context():
    """法人番号 is tokenized as 法人 + 番号, so the context word is 法人."""
    pytest.importorskip("ja_core_news_sm")
    nlp_engine = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "ja", "model_name": "ja_core_news_sm"}],
        }
    ).create_engine()
    registry = RecognizerRegistry(supported_languages=["ja"])
    registry.add_recognizer(JpCorporateNumberRecognizer())
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=nlp_engine, supported_languages=["ja"]
    )

    with_context = analyzer.analyze(
        "法人番号は1000012160153です。", language="ja", entities=[ENTITY]
    )
    without = analyzer.analyze(
        "この数字を繰り返して：1000012160153", language="ja", entities=[ENTITY]
    )

    assert [r.score for r in with_context] == [
        pytest.approx(BARE_SCORE + CONTEXT_BOOST)
    ]
    assert [r.score for r in without] == [pytest.approx(BARE_SCORE)]
