from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.context_aware_enhancers import (
    CompositeContextAwareEnhancer,
    LemmaContextAwareEnhancer,
    PhraseContextAwareEnhancer,
)
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import PlIdCardRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result

# The valid numbers below are made up and completed with their check digit,
# the fourth character: ZZZ?12345 weighs 7*35 + 3*35 + 1*35 + 9*? + 7*1 + 3*2
# + 1*3 + 7*4 + 3*5 = 444 + 9*?, a multiple of 10 for ? = 4.
SCORE = 0.1
# Context enhancer defaults: a context word adds 0.35, to at least 0.4
SCORE_WITH_CONTEXT = 0.45


@pytest.fixture(scope="module")
def recognizer():
    return PlIdCardRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["PL_ID_CARD"]


def shipped_entry():
    """Return the PlIdCardRecognizer entry of ``default_recognizers.yaml``."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "PlIdCardRecognizer"]
    assert len(entries) == 1
    return entries[0]


def load_registry(recognizer_conf, language):
    return RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": [language],
            "recognizers": [recognizer_conf],
        }
    ).create_recognizer_registry()


def english_analyzer(nlp_engine, context_aware_enhancer=None):
    """Enable the shipped entry for English, with the English spaCy model.

    CI has no Polish spaCy model, so context in the text is tested this way,
    which a user analyzing English documents that carry Polish identity card
    numbers would also do.
    """
    registry = load_registry(
        dict(shipped_entry(), enabled=True, supported_languages=["en"]), "en"
    )
    return AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=["en"],
        context_aware_enhancer=context_aware_enhancer,
    )


@pytest.mark.parametrize(
    "text, expected_positions",
    [
        # fmt: off
        ("ZZZ412345", ((0, 9),)),
        ("ZZZ 412345", ((0, 10),)),
        ("ZZZ 412345", ((0, 10),)),  # a no-break space
        ("zzz412345", ((0, 9),)),  # touching the digits, any case
        ("Seria i numer: ZZY312345.", ((15, 24),)),
        ("ZZY312345 i ZZZ 412345", ((0, 9), (12, 22))),
        # fmt: on
    ],
)
def test_when_valid_id_card_number_then_detected_with_pattern_score(
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
        "ZZZ512345",  # wrong check digit
        "ABC123456",  # a product code of the same shape
        "FVS 123456",  # an invoice number of the same shape
        "ABA300000",  # the well-known sample, which passes the checksum
        "AAA000000",  # never issued, but passes the checksum
        # Prose: passes the checksum, but a spaced series must be in capitals
        "dla 400000",
        "for 400000",
        "zzz 412345",
        # Non-ASCII letters that case-insensitive [A-Z] matches: pass the
        # checksum once upper-cased
        "ıZZ512345",  # dotless i
        "ſZZ512345",  # long s
        "ZZZ4123456",  # seven digits
        "XZZZ412345",  # four letters
        "ZZZ-412345",  # a hyphen is not part of the format
        "ZZZ  412345",  # nor two spaces
        # fmt: on
    ],
)
def test_when_invalid_or_lookalike_then_not_detected(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


@pytest.mark.parametrize(
    "number, invalid",
    [
        ("ZZZ412345", False),
        ("ZZZ 412345", False),
        ("ZZZ 412345", False),
        ("zzz412345", False),
        ("ZZZ512345", True),
        ("ABA300000", True),
        ("aba 300000", True),
        ("ıZZ512345", True),
        ("ZZZ41234", True),
        ("ZZ4412345", True),
    ],
)
def test_invalidate_result_checks_format_checksum_and_samples(
    number, invalid, recognizer
):
    assert recognizer.invalidate_result(number) is invalid


def test_loads_from_default_recognizers_yaml_and_detects():
    """The shipped entry must load and detect once a user enables it.

    The top-level ``supported_languages`` defaults to ``["en"]`` and would
    filter out this ``pl``-only recognizer with only a log warning, so it is
    set to ``pl``. CI has no Polish spaCy model; the no-op NLP engine stands
    in for it, so context can only come from the ``context`` argument here.
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
    text = "Legitymujący się dowodem osobistym nr ZZZ 412345"

    results = analyzer.analyze(text, language="pl")
    boosted = analyzer.analyze(text, language="pl", context=["dowodem osobistym"])

    expected = [("PL_ID_CARD", 38, 48)]
    assert [(r.entity_type, r.start, r.end) for r in results] == expected
    assert [(r.entity_type, r.start, r.end) for r in boosted] == expected
    assert results[0].score == pytest.approx(SCORE)
    assert boosted[0].score == pytest.approx(SCORE_WITH_CONTEXT)


@pytest.mark.parametrize("matching_mode", ["substring", "whole_word"])
@pytest.mark.parametrize("context_word", PlIdCardRecognizer.CONTEXT)
def test_each_context_word_raises_score_in_both_matching_modes(
    context_word, matching_mode, spacy_nlp_engine
):
    enhancer = CompositeContextAwareEnhancer(
        [LemmaContextAwareEnhancer, PhraseContextAwareEnhancer],
        context_matching_mode=matching_mode,
    )
    analyzer = english_analyzer(spacy_nlp_engine, enhancer)

    results = analyzer.analyze(f"{context_word} ZZZ412345", language="en")

    assert [r.entity_type for r in results] == ["PL_ID_CARD"]
    assert results[0].score == pytest.approx(SCORE_WITH_CONTEXT)


@pytest.mark.parametrize(
    "text, expected_score",
    [
        ("Numer ZZZ412345", SCORE),
        ("Legitymujący się dowodem osobistym ZZZ 412345", SCORE_WITH_CONTEXT),
        ("Seria i numer dowodu osobistego: ZZZ412345", SCORE_WITH_CONTEXT),
        ("Rodzaj i numer dokumentu tożsamości: ZZZ412345", SCORE_WITH_CONTEXT),
        # "Dowód" alone is any proof or receipt, and is no context
        ("Dowód zakupu: ZZZ412345", SCORE),
        ("Dowód księgowy nr ZZZ412345", SCORE),
        ("Dowód rejestracyjny ZZZ412345", SCORE),
        ("Dowódca jednostki ZZZ412345", SCORE),
        # An invoice number that passes the checksum stays at the pattern score
        ("Dowód zakupu: FVS 600000", SCORE),
        # Context is looked up before the match only
        ("ZZZ412345 to numer dowodu osobistego", SCORE),
    ],
)
def test_context_raises_score_only_for_the_identity_card_before_the_number(
    text, expected_score, spacy_nlp_engine
):
    results = english_analyzer(spacy_nlp_engine).analyze(text, language="en")

    assert [r.entity_type for r in results] == ["PL_ID_CARD"]
    assert results[0].score == pytest.approx(expected_score)


def test_when_built_directly_then_same_as_yaml(recognizer):
    loaded = load_registry(dict(shipped_entry(), enabled=True), "pl").recognizers[0]

    assert type(loaded) is PlIdCardRecognizer
    assert loaded.supported_language == recognizer.supported_language == "pl"
    assert loaded.country_code() == recognizer.country_code() == "pl"
    assert loaded.supported_entities == recognizer.supported_entities == ["PL_ID_CARD"]
    assert loaded.context == recognizer.context
    assert [p.to_dict() for p in loaded.patterns] == [
        p.to_dict() for p in recognizer.patterns
    ]
