from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import PlRegonRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result

# The valid REGONs below are made-up digits completed with their check digit:
# 123456785 is 12345678 and its check digit 5, and 12345678512347 is that
# REGON, then 1234 and the 14-digit check digit 7. In 123456160 and
# 12345678500010 the weighted sum leaves 10, which gives the check digit 0.
SCORE = 0.05
# LemmaContextAwareEnhancer defaults: a context word adds 0.35, to at least 0.4
SCORE_WITH_CONTEXT = 0.4


@pytest.fixture(scope="module")
def recognizer():
    return PlRegonRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["PL_REGON"]


def shipped_entry():
    """Return the PlRegonRecognizer entry of ``default_recognizers.yaml``."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "PlRegonRecognizer"]
    assert len(entries) == 1
    return entries[0]


def load_registry(recognizer_conf, language):
    return RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": [language],
            "recognizers": [recognizer_conf],
        }
    ).create_recognizer_registry()


@pytest.mark.parametrize(
    "text, expected_positions",
    [
        # fmt: off
        ("123456785", ((0, 9),)),
        ("12345678512347", ((0, 14),)),
        ("123456160", ((0, 9),)),
        ("12345678500010", ((0, 14),)),
        ("REGON: 123456785.", ((7, 16),)),
        ("123456785 i 12345678512347", ((0, 9), (12, 26))),
        # fmt: on
    ],
)
def test_when_valid_regon_then_detected_with_pattern_score(
    text, expected_positions, recognizer, entities
):
    results = recognizer.analyze(text, entities)

    assert len(results) == len(expected_positions)
    for result, (start, end) in zip(results, expected_positions):
        assert_result(result, entities[0], start, end, SCORE)


@pytest.mark.parametrize(
    "text",
    [
        # fmt: off
        "123456784",  # wrong check digit
        "12345678512340",  # wrong 14-digit check digit
        "12345678612342",  # right 14-digit check digit, but 123456786 is no REGON
        "123456161",  # remainder 10 taken as the check digit
        "000000000",  # passes the checksum, but a form placeholder
        "00000000000018",  # and so is a local unit built on it
        "601234567",  # phone-shaped; fails the checksum, as 9 in 10 do
        "48123456785",  # a longer run that ends in a REGON
        "1234567851",  # a longer run that starts with one
        "123 456 785",  # separated groups
        # fmt: on
    ],
)
def test_when_invalid_or_lookalike_then_not_detected(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


@pytest.mark.parametrize(
    "number, invalid",
    [
        ("123456785", False),
        ("12345678512347", False),
        ("123456160", False),
        ("12345678500010", False),
        ("123456784", True),
        ("123456161", True),
        ("12345678612342", True),
        ("000000000", True),
        ("00000000000018", True),
        ("12345678", True),
        ("1234567851", True),
        ("12345678a", True),
    ],
)
def test_invalidate_result_checks_length_and_checksum(number, invalid, recognizer):
    assert recognizer.invalidate_result(number) is invalid


def test_loads_from_default_recognizers_yaml_and_detects():
    """The shipped entry must load and detect once a user enables it.

    The top-level ``supported_languages`` defaults to ``["en"]`` and would
    filter out this ``pl``-only recognizer with only a log warning, so it is
    set to ``pl``.
    CI has no Polish spaCy model; the no-op NLP engine stands in for it, so
    context can only come from the ``context`` argument here.
    """
    entry = shipped_entry()
    assert entry["enabled"] is False
    assert entry["country_code"] == "pl"
    assert entry["supported_languages"] == ["pl"]

    registry = load_registry(dict(entry, enabled=True), "pl")
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "pl", "model_name": "no_op"}]),
        supported_languages=["pl"],
    )
    text = "Sprzedawca: Przykład sp. z o.o., REGON: 123456785"

    results = analyzer.analyze(text, language="pl")
    boosted = analyzer.analyze(text, language="pl", context=["regon"])

    expected = [("PL_REGON", 40, 49)]
    assert [(r.entity_type, r.start, r.end) for r in results] == expected
    assert [(r.entity_type, r.start, r.end) for r in boosted] == expected
    assert results[0].score == pytest.approx(SCORE)
    assert boosted[0].score == pytest.approx(SCORE_WITH_CONTEXT)


@pytest.mark.parametrize(
    "text, expected_score",
    [
        ("Numer 123456785", SCORE),
        ("REGON 123456785", SCORE_WITH_CONTEXT),
        ("REGON: 12345678512347", SCORE_WITH_CONTEXT),
        ("Nadano numer REGON 123456785.", SCORE_WITH_CONTEXT),
        # Context is looked up before the match only
        ("123456785 to REGON", SCORE),
        # Substring matching: documented in the class docstring
        ("Oregon office 123456785", SCORE_WITH_CONTEXT),
    ],
)
def test_context_word_raises_score_only_when_it_precedes_regon(
    text, expected_score, spacy_nlp_engine
):
    """Context words before the number raise the score.

    Without a Polish spaCy model in CI, the recognizer is enabled for English
    through the YAML instead, which a user analyzing English documents that
    carry Polish REGONs would also do; "Oregon" then counts as context too.
    """
    registry = load_registry(
        dict(shipped_entry(), enabled=True, supported_languages=["en"]), "en"
    )
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )

    results = analyzer.analyze(text, language="en")

    assert [r.entity_type for r in results] == ["PL_REGON"]
    assert results[0].score == pytest.approx(expected_score)


def test_when_built_directly_then_same_as_yaml(recognizer):
    loaded = load_registry(dict(shipped_entry(), enabled=True), "pl").recognizers[0]

    assert type(loaded) is PlRegonRecognizer
    assert loaded.supported_language == recognizer.supported_language == "pl"
    assert loaded.country_code() == recognizer.country_code() == "pl"
    assert loaded.supported_entities == recognizer.supported_entities == ["PL_REGON"]
    assert loaded.context == recognizer.context
    assert [p.to_dict() for p in loaded.patterns] == [
        p.to_dict() for p in recognizer.patterns
    ]
